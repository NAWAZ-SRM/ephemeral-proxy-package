import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.tunnel import Tunnel, RequestLog
from app.services.port_pool import PortPoolService
from app.services.websocket_manager import ws_manager
from app.redis_client import get_redis
from app.config import settings


async def expire_tunnel(tunnel: Tunnel, reason: str = "ttl_exceeded"):
    async with async_session_maker() as session:
        tunnel.status = "expired"
        await session.commit()
        
        await PortPoolService.release_port(tunnel.assigned_port)
        
        r = await get_redis()
        await r.delete(f"tunnel:{tunnel.slug}")
        
        duration = int((datetime.now(timezone.utc) - tunnel.created_at.replace(tzinfo=timezone.utc)).total_seconds())
        result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.tunnel_id == tunnel.id)
        )
        total_requests = result.scalar() or 0
        
        unique_result = await session.execute(
            select(func.count(func.distinct(RequestLog.visitor_ip)))
            .where(RequestLog.tunnel_id == tunnel.id)
        )
        unique_visitors = unique_result.scalar() or 0
        
        await r.hset(f"summary:{tunnel.slug}", mapping={
            "total_requests": str(total_requests),
            "unique_ips": str(unique_visitors),
            "duration_seconds": str(duration),
        })
        await r.expire(f"summary:{tunnel.slug}", 86400)
        
        await ws_manager.broadcast(tunnel.slug, {
            "type": "expired",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "reason": reason,
                "summary": {
                    "total_requests": total_requests,
                    "duration_seconds": duration,
                    "unique_visitors": unique_visitors,
                }
            }
        })


async def expire_ttl_tunnels():
    async with async_session_maker() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Tunnel).where(
                Tunnel.expires_at <= now,
                Tunnel.status.in_(["pending", "active", "idle"])
            )
        )
        tunnels = result.scalars().all()
        for tunnel in tunnels:
            await expire_tunnel(tunnel, "ttl_exceeded")


async def expire_idle_tunnels():
    async with async_session_maker() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.IDLE_EXPIRE_MINUTES)
        result = await session.execute(
            select(Tunnel).where(
                Tunnel.last_active <= cutoff,
                Tunnel.status == "idle"
            )
        )
        tunnels = result.scalars().all()
        for tunnel in tunnels:
            await expire_tunnel(tunnel, "idle_timeout")


async def delete_old_expired_tunnels():
    async with async_session_maker() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await session.execute(
            select(Tunnel).where(
                Tunnel.status == "expired",
                Tunnel.updated_at <= cutoff
            )
        )
        tunnels = result.scalars().all()
        
        for tunnel in tunnels:
            await session.execute(
                delete(RequestLog).where(RequestLog.tunnel_id == tunnel.id)
            )
            await session.execute(delete(Tunnel).where(Tunnel.id == tunnel.id))
        
        await session.commit()


async def mark_idle_tunnels():
    async with async_session_maker() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.IDLE_WARN_MINUTES)
        result = await session.execute(
            select(Tunnel).where(
                Tunnel.last_active <= cutoff,
                Tunnel.status == "active"
            )
        )
        tunnels = result.scalars().all()
        for tunnel in tunnels:
            tunnel.status = "idle"
            await session.commit()
            
            await ws_manager.broadcast(tunnel.slug, {
                "type": "status_change",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "old_status": "active",
                    "new_status": "idle",
                    "message": f"No requests in {settings.IDLE_WARN_MINUTES} minutes. Auto-expires in {settings.IDLE_EXPIRE_MINUTES} more minutes."
                }
            })


async def cleanup_loop():
    while True:
        try:
            await mark_idle_tunnels()
            await expire_ttl_tunnels()
            await expire_idle_tunnels()
            await delete_old_expired_tunnels()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        await asyncio.sleep(60)
