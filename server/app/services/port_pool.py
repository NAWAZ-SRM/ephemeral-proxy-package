import redis.asyncio as redis
from app.config import settings
from app.redis_client import get_redis


class PortPoolService:
    POOL_KEY = "port:pool"

    @staticmethod
    async def initialize_pool():
        r = await get_redis()
        count = await r.zcard(PortPoolService.POOL_KEY)
        if count == 0:
            ports = list(range(settings.PORT_POOL_MIN, settings.PORT_POOL_MAX + 1))
            port_scores = {port: 0 for port in ports}
            await r.zadd(PortPoolService.POOL_KEY, port_scores)
            return len(ports)
        return count

    @staticmethod
    async def allocate_port() -> int:
        r = await get_redis()
        result = await r.zpopmin(PortPoolService.POOL_KEY, 1)
        if not result:
            raise RuntimeError("Port pool exhausted")
        port, _ = result[0]
        return int(port)

    @staticmethod
    async def release_port(port: int):
        r = await get_redis()
        await r.zadd(PortPoolService.POOL_KEY, {port: 0})

    @staticmethod
    async def get_available_count() -> int:
        r = await get_redis()
        return await r.zcount(PortPoolService.POOL_KEY, 0, 0)
