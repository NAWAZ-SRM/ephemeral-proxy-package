from fastapi import APIRouter, Request
from app.services.tunnel_proxy import TunnelProxy

router = APIRouter(tags=["proxy"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_tunnel(path: str, request: Request):
    host = request.headers.get("host", "")
    if "." in host:
        slug = host.split(".")[0]
        return await TunnelProxy.proxy_request(request, slug)
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_host", "message": "No tunnel slug found in host. Use API endpoints directly."}
    )
