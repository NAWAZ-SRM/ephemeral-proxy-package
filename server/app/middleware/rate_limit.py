import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.redis_client import get_redis
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "")

        if "." not in host:
            return await call_next(request)

        slug = host.split(".")[0].split(":")[0]
        if slug in ("api", "dash", "localhost"):
            return await call_next(request)

        try:
            r = await get_redis()
            key = f"ratelimit:{slug}"

            now = time.time()
            window_start = now - 60

            pipe = r.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, 60)
            results = await pipe.execute()

            count = results[2]
            limit = settings.RATE_LIMIT_PER_MINUTE

            if count > limit:
                return JSONResponse(
                    {
                        "error": "rate_limited",
                        "message": f"Too many requests to this tunnel. Retry after {int(60 - (now - window_start))}s.",
                    },
                    status_code=429,
                )
        except Exception:
            pass

        return await call_next(request)
