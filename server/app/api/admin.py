from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_maker
from app.models.tunnel import Tunnel
from app.redis_client import get_redis
from app.config import settings

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tunnel/{slug}/activate")
async def activate_tunnel(
    slug: str,
    x_internal_secret: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    
    result = await db.execute(select(Tunnel).where(Tunnel.slug == slug))
    tunnel = result.scalar_one_or_none()
    
    if not tunnel:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    
    tunnel.status = "active"
    tunnel.last_active = datetime.now(timezone.utc)
    await db.commit()
    
    r = await get_redis()
    await r.hset(f"tunnel:{slug}", "status", "active")
    
    return {"message": "Tunnel activated"}


@router.get("/ports/available")
async def get_available_ports():
    from app.services.port_pool import PortPoolService
    count = await PortPoolService.get_available_count()
    return {"available": count}


@router.post("/ports/release/{port}")
async def release_port(
    port: int,
    x_internal_secret: str = Header(None),
):
    if x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    
    from app.services.port_pool import PortPoolService
    await PortPoolService.release_port(port)
    return {"message": "Port released"}
