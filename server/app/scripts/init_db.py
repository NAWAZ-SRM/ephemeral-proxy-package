import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import engine
from app.models.tunnel import Base
from alembic.config import Config
from alembic import command


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    alembic_cfg = Config("alembic.ini")
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        pass
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
