from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db as _get_db
from app.redis_client import get_redis
from app.models.tunnel import User
from app.services.auth_service import AuthService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        yield session


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    token = authorization.replace("Bearer ", "")
    user = await AuthService.get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    return user


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    return await AuthService.get_user_from_token(db, token)


async def get_redis_client():
    return await get_redis()
