import asyncio
import random
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.redis_client import get_redis
from app.config import settings


class FaultInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "")

        if "." not in host:
            return await call_next(request)

        slug = host.split(".")[0].split(":")[0]
        if slug in ("api", "dash", "localhost"):
            return await call_next(request)

        try:
            r = await get_redis()
            tunnel_data = await r.hgetall(f"tunnel:{slug}")
        except Exception:
            return await call_next(request)

        fault_config = tunnel_data.get("fault_injection")
        if not fault_config:
            return await call_next(request)

        if isinstance(fault_config, str):
            try:
                import json
                fault_config = json.loads(fault_config)
            except Exception:
                return await call_next(request)

        if not fault_config or not fault_config.get("enabled"):
            return await call_next(request)

        path = request.url.path
        pattern = fault_config.get("path_pattern")
        if pattern and not re.match(pattern, path):
            return await call_next(request)

        error_rate = fault_config.get("error_rate", 0)
        if random.random() < error_rate:
            error_code = fault_config.get("error_code", 500)
            return JSONResponse(
                {"error": "fault_injected", "message": "Simulated error"},
                status_code=error_code,
            )

        added_latency = fault_config.get("added_latency_ms", 0)
        if added_latency > 0:
            await asyncio.sleep(added_latency / 1000.0)

        return await call_next(request)
