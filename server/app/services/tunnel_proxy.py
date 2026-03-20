import httpx
import time
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request
from starlette.responses import StreamingResponse, JSONResponse

from app.redis_client import get_redis
from app.config import settings


MAX_BODY_LOG_SIZE = 4096


class TunnelProxy:
    @staticmethod
    async def proxy_request(request: Request, slug: str):
        r = await get_redis()
        tunnel_data = await r.hgetall(f"tunnel:{slug}")
        
        if not tunnel_data or tunnel_data.get("status") not in ("active", "idle"):
            return JSONResponse(
                {"error": "tunnel_expired", "message": "This tunnel has expired or never existed."},
                status_code=410
            )
        
        blocked_countries = tunnel_data.get("blocked_countries", "")
        if blocked_countries:
            try:
                blocked_list = json.loads(blocked_countries) if isinstance(blocked_countries, str) else blocked_countries
                if blocked_list:
                    from app.services.geo_ip import GeoIPService
                    visitor_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or ""
                    country = GeoIPService.get_country_code(visitor_ip)
                    if country in blocked_list:
                        return JSONResponse(
                            {"error": "blocked", "message": "Access to this tunnel is restricted."},
                            status_code=403
                        )
            except Exception:
                pass
        
        assigned_port = int(tunnel_data["port"])
        local_url = tunnel_data.get("local_url")
        
        if local_url:
            from urllib.parse import urlparse
            parsed = urlparse(local_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            headers = dict(request.headers)
            headers.pop("host", None)
            headers["host"] = parsed.netloc
        else:
            base_url = f"http://localhost:{assigned_port}"
            headers = dict(request.headers)
            headers.pop("host", None)
            headers["host"] = f"localhost:{assigned_port}"
        
        url = f"{base_url}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        
        start_time = time.perf_counter()
        
        try:
            body = await request.body()
            req_body = body[:MAX_BODY_LOG_SIZE] if body else b""
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                proxy_response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    follow_redirects=False,
                )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            res_body = b""
            async for chunk in proxy_response.aiter_bytes(chunk_size=8192):
                res_body += chunk
                if len(res_body) > MAX_BODY_LOG_SIZE:
                    res_body = res_body[:MAX_BODY_LOG_SIZE]
                    break
            
            asyncio.create_task(TunnelProxy._log_and_broadcast(
                slug=slug,
                request=request,
                req_body=req_body,
                status_code=proxy_response.status_code,
                latency_ms=latency_ms,
                response_headers=dict(proxy_response.headers),
                res_body=res_body,
            ))
            
            return StreamingResponse(
                content=proxy_response.aiter_bytes(),
                status_code=proxy_response.status_code,
                headers=dict(proxy_response.headers),
                media_type=proxy_response.headers.get("content-type")
            )
        
        except httpx.TimeoutException:
            return JSONResponse(
                {"error": "upstream_timeout", "message": "The tunneled application did not respond in time."},
                status_code=504
            )
        except Exception as e:
            return JSONResponse(
                {"error": "upstream_error", "message": "Could not reach the tunneled application."},
                status_code=502
            )

    @staticmethod
    async def _log_and_broadcast(
        slug: str,
        request: Request,
        req_body: bytes,
        status_code: int,
        latency_ms: int,
        response_headers: dict,
        res_body: bytes,
    ):
        from app.models.tunnel import RequestLog, Tunnel
        from app.database import async_session_maker
        from app.services.geo_ip import GeoIPService
        from app.services.websocket_manager import ws_manager
        from datetime import datetime
        
        visitor_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or "unknown"
        country_code = GeoIPService.get_country_code(visitor_ip)
        
        req_body_text = None
        if req_body:
            try:
                req_body_text = req_body.decode("utf-8", errors="replace")
                if len(req_body_text) > MAX_BODY_LOG_SIZE:
                    req_body_text = req_body_text[:MAX_BODY_LOG_SIZE] + "\n[body truncated]"
            except Exception:
                req_body_text = f"[binary data, {len(req_body)} bytes]"
        
        res_body_text = None
        if res_body:
            try:
                res_body_text = res_body.decode("utf-8", errors="replace")
                if len(res_body_text) > MAX_BODY_LOG_SIZE:
                    res_body_text = res_body_text[:MAX_BODY_LOG_SIZE] + "\n[body truncated]"
            except Exception:
                res_body_text = f"[binary data, {len(res_body)} bytes]"
        
        async with async_session_maker() as session:
            from sqlalchemy import select
            from app.models.tunnel import Tunnel
            
            result = await session.execute(select(Tunnel).where(Tunnel.slug == slug))
            tunnel = result.scalar_one_or_none()
            
            if tunnel:
                log = RequestLog(
                    tunnel_id=tunnel.id,
                    method=request.method,
                    path=request.url.path,
                    query_params=json.loads(request.url.query or "{}"),
                    req_headers=dict(request.headers),
                    req_body=req_body_text,
                    status_code=status_code,
                    res_headers=response_headers,
                    res_body=res_body_text,
                    latency_ms=latency_ms,
                    visitor_ip=visitor_ip,
                    country_code=country_code,
                )
                session.add(log)
                tunnel.total_requests += 1
                tunnel.last_active = datetime.now(timezone.utc)
                if tunnel.status == "idle":
                    tunnel.status = "active"
                await session.commit()
                
                event_data = {
                    "type": "request",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "id": str(log.id),
                        "method": log.method,
                        "path": log.path,
                        "status_code": log.status_code,
                        "latency_ms": log.latency_ms,
                        "country_code": log.country_code,
                        "flag_emoji": GeoIPService.get_country_flag(log.country_code or "XX"),
                        "visitor_ip_masked": ".".join((visitor_ip.split(".")[:-1] + ["xxx"])[:4]),
                    }
                }
                await ws_manager.broadcast(slug, event_data)
