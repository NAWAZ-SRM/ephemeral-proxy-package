import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.port_pool import PortPoolService
from app.redis_client import get_redis, close_redis


async def init_port_pool():
    count = await PortPoolService.initialize_pool()
    print(f"Initialized port pool with {count} ports (range: 20000-29999)")
    await close_redis()


if __name__ == "__main__":
    asyncio.run(init_port_pool())
