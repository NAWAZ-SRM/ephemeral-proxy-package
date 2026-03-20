import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class TunnelProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "")

        if "." not in host:
            return await call_next(request)

        slug_part = host.split(".")[0].split(":")[0]

        if slug_part in ("api", "dash", "localhost"):
            return await call_next(request)

        from app.services.tunnel_proxy import TunnelProxy
        response = await TunnelProxy.proxy_request(request, slug_part)
        return response
