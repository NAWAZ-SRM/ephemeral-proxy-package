from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx

from app.database import get_db
from app.models.tunnel import User, Tunnel
from app.schemas.tunnel import AuthResponse, UserResponse, UserMe
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCallback(BaseModel):
    code: str
    redirect_uri: str


class DeviceCodeResponse(BaseModel):
    device_code: str
    verification_url: str
    user_code: str


@router.post("/google", response_model=AuthResponse)
async def google_auth(
    body: GoogleCallback,
    db: AsyncSession = Depends(get_db),
):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": "placeholder",
                "client_secret": "placeholder",
                "redirect_uri": body.redirect_uri,
                "grant_type": "authorization_code",
            }
        )
    
    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail={"error": "invalid_code"})
    
    token_data = token_response.json()
    id_token = token_data.get("id_token")
    
    if id_token:
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token}
            )
            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                email = user_info.get("email")
                google_id = user_info.get("sub")
                
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                
                if not user:
                    user = User(email=email, google_id=google_id)
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
                else:
                    user.google_id = google_id
                    await db.commit()
                
                access_token = AuthService.create_access_token(str(user.id), user.email)
                
                return AuthResponse(
                    access_token=access_token,
                    user=UserResponse.model_validate(user)
                )
    
    raise HTTPException(status_code=401, detail={"error": "invalid_code"})


@router.get("/me", response_model=UserMe)
async def get_me(
    authorization: str = None,
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    token = authorization.replace("Bearer ", "")
    user = await AuthService.get_user_from_token(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    active_count = await db.execute(
        select(func.count(Tunnel.id)).where(
            Tunnel.owner_id == user.id,
            Tunnel.status.in_(["pending", "active", "idle"])
        )
    )
    
    return UserMe(
        id=user.id,
        email=user.email,
        ssh_key_registered=bool(user.ssh_pub_key),
        active_tunnels=active_count.scalar() or 0,
        created_at=user.created_at,
    )


@router.post("/device", response_model=DeviceCodeResponse)
async def device_code():
    return DeviceCodeResponse(
        device_code="placeholder_device_code",
        verification_url=f"https://tunnel.dev/auth/device",
        user_code="XXXX-XXXX",
    )
