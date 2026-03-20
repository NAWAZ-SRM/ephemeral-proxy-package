import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from datetime import datetime

from app.config import settings
from app.database import engine, async_session_maker
from app.redis_client import get_redis, close_redis
from app.services.port_pool import PortPoolService
from app.services.tunnel_cleanup import cleanup_loop
from app.models.tunnel import Tunnel
from app.api import tunnels, proxy, websocket, auth, users, admin
from app.middleware.tunnel_proxy import TunnelProxyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.fault_injection import FaultInjectionMiddleware
from app.schemas.tunnel import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(cleanup_loop())
    
    try:
        await PortPoolService.initialize_pool()
    except Exception as e:
        print(f"Warning: Could not initialize port pool: {e}")
    
    yield
    
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Tunnel API",
    description="Self-hosted SSH reverse tunnel service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TunnelProxyMiddleware)
app.add_middleware(FaultInjectionMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(tunnels.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(websocket.router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    db_status = "ok"
    redis_status = "ok"
    active_tunnels = 0
    pool_available = 0
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(func.count(Tunnel.id)).where(
                    Tunnel.status.in_(["pending", "active", "idle"])
                )
            )
            active_tunnels = result.scalar() or 0
    except Exception:
        db_status = "error"
    
    try:
        pool_available = await PortPoolService.get_available_count()
    except Exception:
        redis_status = "error"
    
    return HealthResponse(
        status="ok",
        database=db_status,
        redis=redis_status,
        active_tunnels=active_tunnels,
        port_pool_available=pool_available,
        version="1.0.0",
    )


@app.get("/")
async def root():
    return {
        "service": "Tunnel API",
        "version": "1.0.0",
        "status": "running",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)},
    )
