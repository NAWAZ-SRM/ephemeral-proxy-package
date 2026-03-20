from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.database import async_session_maker
from app.models.tunnel import Tunnel
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/tunnels/{slug}/live")
async def tunnel_live_websocket(
    websocket: WebSocket,
    slug: str,
    token: str = Query(None),
):
    async with async_session_maker() as session:
        result = await session.execute(select(Tunnel).where(Tunnel.slug == slug))
        tunnel = result.scalar_one_or_none()
        
        if not tunnel:
            await websocket.close(code=4004)
            return
        
        await ws_manager.connect(slug, websocket)
        
        try:
            await websocket.send_json({
                "type": "connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "slug": slug,
                    "status": tunnel.status,
                }
            })
            
            while True:
                data = await websocket.receive_text()
                
        except WebSocketDisconnect:
            await ws_manager.disconnect(slug, websocket)
