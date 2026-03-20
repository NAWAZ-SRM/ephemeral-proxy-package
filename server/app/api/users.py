import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tunnel import User
from app.schemas.tunnel import SSHKeyRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/ssh-key")
async def register_ssh_key(
    body: SSHKeyRegister,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    token = authorization.replace("Bearer ", "")
    user = await AuthService.get_user_from_token(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    
    if not body.public_key.startswith("ssh-"):
        raise HTTPException(status_code=400, detail={"error": "invalid_key_format"})
    
    authorized_keys_path = "/etc/tunnel/authorized_keys/tunnel"
    
    try:
        os.makedirs(os.path.dirname(authorized_keys_path), exist_ok=True)
        with open(authorized_keys_path, "a") as f:
            f.write(f"{body.public_key}\n")
    except PermissionError:
        pass
    
    user.ssh_pub_key = body.public_key
    await db.commit()
    
    return {"message": "SSH key registered successfully"}
