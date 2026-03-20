import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from app.database import get_db
from app.models.tunnel import Tunnel, RequestLog, TunnelStats
from app.schemas.tunnel import (
    TunnelCreate, TunnelResponse, TunnelStatus, TunnelExpireResponse,
    TunnelSettingsUpdate, TunnelStatsData
)
from app.services.port_pool import PortPoolService
from app.services.auth_service import AuthService
from app.services.websocket_manager import ws_manager
from app.redis_client import get_redis
from app.config import settings

router = APIRouter(prefix="/tunnels", tags=["tunnels"])


def _scheme() -> str:
    return "https" if settings.USE_HTTPS else "http"


def _tunnel_url(slug: str) -> str:
    return f"{_scheme()}://{slug}.{settings.BASE_DOMAIN}"


def _dashboard_url(slug: str) -> str:
    return f"{_scheme()}://dash.{settings.BASE_DOMAIN}/t/{slug}"


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    return await AuthService.get_user_from_token(db, token)


def generate_slug() -> str:
    return secrets.token_hex(4)


@router.post("", response_model=TunnelResponse, status_code=201)
async def create_tunnel(
    body: TunnelCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    slug = body.name or generate_slug()
    
    if body.name:
        existing = await db.execute(select(Tunnel).where(Tunnel.slug == slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail={
                "error": "slug_taken",
                "message": f"Custom name '{body.name}' is already in use"
            })
    
    if user:
        active_count = await db.execute(
            select(func.count(Tunnel.id)).where(
                Tunnel.owner_id == user.id,
                Tunnel.status.in_(["pending", "active", "idle"])
            )
        )
        if active_count.scalar() >= settings.MAX_TUNNELS_PER_USER:
            raise HTTPException(status_code=429, detail={
                "error": "too_many_tunnels",
                "message": f"Max {settings.MAX_TUNNELS_PER_USER} active tunnels per user"
            })
    
    try:
        assigned_port = await PortPoolService.allocate_port()
    except RuntimeError:
        raise HTTPException(status_code=503, detail={
            "error": "port_pool_exhausted",
            "message": "No ports available. Please try again later."
        })
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=body.ttl_seconds)
    
    password_hash = None
    if body.password:
        password_hash = bcrypt.hash(body.password)
    
    tunnel = Tunnel(
        slug=slug,
        owner_id=user.id if user else None,
        owner_email=user.email if user else None,
        assigned_port=assigned_port,
        local_port=body.local_port,
        local_url=body.local_url,
        status="pending",
        ttl_seconds=body.ttl_seconds,
        auth_domain=body.auth_domain,
        password_hash=password_hash,
        expires_at=expires_at,
    )
    
    db.add(tunnel)
    await db.commit()
    await db.refresh(tunnel)
    
    r = await get_redis()
    await r.hset(f"tunnel:{slug}", mapping={
        "port": str(assigned_port),
        "status": "pending",
        "owner_email": user.email if user else "",
        "auth_domain": body.auth_domain or "",
        "password_hash": password_hash or "",
        "expires_at": str(int(expires_at.timestamp())),
        "local_url": body.local_url or "",
    })
    await r.expire(f"tunnel:{slug}", body.ttl_seconds + 3600)
    
    ssh_command = (
        f"ssh -R {assigned_port}:localhost:{body.local_port} -N "
        f"-i ~/.tunnel/tunnel_ed25519 tunnel@{settings.BASE_DOMAIN}"
    )
    
    return TunnelResponse(
        id=tunnel.id,
        slug=slug,
        assigned_port=assigned_port,
        url=f"{_scheme()}://{slug}.{settings.BASE_DOMAIN}",
        dashboard_url=f"{_scheme()}://dash.{settings.BASE_DOMAIN}/t/{slug}",
        status="pending",
        expires_at=expires_at,
        ssh_command=ssh_command,
        local_port=body.local_port,
        local_url=body.local_url,
    )


@router.get("/{slug}", response_model=TunnelStatus)
async def get_tunnel(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tunnel).where(Tunnel.slug == slug))
    tunnel = result.scalar_one_or_none()
    
    if not tunnel:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    stats = None
    if tunnel.total_requests > 0:
        stats = TunnelStatsData(
            total_requests=tunnel.total_requests,
            unique_ips=0,
            bytes_transferred=tunnel.total_bytes or 0,
        )
    
    return TunnelStatus(
        id=tunnel.id,
        slug=tunnel.slug,
        status=tunnel.status,
        url=f"{_scheme()}://{slug}.{settings.BASE_DOMAIN}",
        dashboard_url=f"{_scheme()}://dash.{settings.BASE_DOMAIN}/t/{slug}",
        created_at=tunnel.created_at,
        expires_at=tunnel.expires_at,
        last_active=tunnel.last_active,
        stats=stats,
    )


@router.delete("/{slug}", response_model=TunnelExpireResponse)
async def expire_tunnel(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    result = await db.execute(select(Tunnel).where(Tunnel.slug == slug))
    tunnel = result.scalar_one_or_none()
    
    if not tunnel:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    if user and tunnel.owner_id and tunnel.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"error": "not_owner"})
    
    await PortPoolService.release_port(tunnel.assigned_port)
    
    duration = int((datetime.now(timezone.utc) - tunnel.created_at.replace(tzinfo=timezone.utc)).total_seconds())
    
    count_result = await db.execute(
        select(func.count(RequestLog.id)).where(RequestLog.tunnel_id == tunnel.id)
    )
    total_requests = count_result.scalar() or 0
    
    unique_result = await db.execute(
        select(func.count(func.distinct(RequestLog.visitor_ip)))
        .where(RequestLog.tunnel_id == tunnel.id)
    )
    unique_visitors = unique_result.scalar() or 0
    
    tunnel.status = "expired"
    await db.commit()
    
    r = await get_redis()
    await r.delete(f"tunnel:{slug}")
    
    await ws_manager.broadcast(slug, {
        "type": "expired",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "reason": "ctrl_c",
            "summary": {
                "total_requests": total_requests,
                "duration_seconds": duration,
                "unique_visitors": unique_visitors,
            }
        }
    })
    
    return TunnelExpireResponse(
        message="Tunnel expired",
        summary={
            "duration_seconds": duration,
            "total_requests": total_requests,
            "unique_visitors": unique_visitors,
        }
    )


@router.get("/{slug}/requests")
async def get_request_logs(
    slug: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    method: Optional[str] = None,
    status_min: Optional[int] = None,
    status_max: Optional[int] = None,
    path: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    tunnel_result = await db.execute(select(Tunnel.id).where(Tunnel.slug == slug))
    tunnel_id = tunnel_result.scalar_one_or_none()
    
    if not tunnel_id:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    query = select(RequestLog).where(RequestLog.tunnel_id == tunnel_id)
    
    if method:
        query = query.where(RequestLog.method == method.upper())
    if status_min is not None:
        query = query.where(RequestLog.status_code >= status_min)
    if status_max is not None:
        query = query.where(RequestLog.status_code <= status_max)
    if path:
        query = query.where(RequestLog.path.contains(path))
    
    count_query = select(func.count(RequestLog.id)).where(RequestLog.tunnel_id == tunnel_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(RequestLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    from app.schemas.request_log import RequestLogPage, RequestLogResponse
    return RequestLogPage(
        total=total,
        page=page,
        limit=limit,
        requests=[RequestLogResponse.model_validate(log) for log in logs]
    )


@router.get("/{slug}/requests/{request_id}")
async def get_request_detail(
    slug: str,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    tunnel_result = await db.execute(select(Tunnel.id).where(Tunnel.slug == slug))
    tunnel_id = tunnel_result.scalar_one_or_none()
    
    if not tunnel_id:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    result = await db.execute(
        select(RequestLog).where(
            RequestLog.id == request_id,
            RequestLog.tunnel_id == tunnel_id
        )
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    from app.schemas.request_log import RequestLogDetail
    return RequestLogDetail.model_validate(log)


@router.patch("/{slug}/settings")
async def update_tunnel_settings(
    slug: str,
    body: TunnelSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    result = await db.execute(select(Tunnel).where(Tunnel.slug == slug))
    tunnel = result.scalar_one_or_none()
    
    if not tunnel:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    if not user or tunnel.owner_id != user.id:
        raise HTTPException(status_code=403, detail={"error": "not_owner"})
    
    r = await get_redis()
    updates = {}
    
    if body.ttl_seconds is not None:
        tunnel.ttl_seconds = body.ttl_seconds
        tunnel.expires_at = datetime.now(timezone.utc) + timedelta(seconds=body.ttl_seconds)
        new_expiry = int(tunnel.expires_at.timestamp())
        updates["expires_at"] = str(new_expiry)
    
    if body.password is not None:
        tunnel.password_hash = bcrypt.hash(body.password) if body.password else None
        updates["password_hash"] = tunnel.password_hash or ""
    
    if body.fault_injection is not None:
        import json
        tunnel.fault_injection = body.fault_injection
        updates["fault_injection"] = json.dumps(body.fault_injection)
    
    if body.blocked_countries is not None:
        import json
        tunnel.blocked_countries = body.blocked_countries
        updates["blocked_countries"] = json.dumps(body.blocked_countries)
    
    await db.commit()
    
    if updates:
        await r.hset(f"tunnel:{slug}", mapping=updates)
    
    return {"message": "Settings updated"}
