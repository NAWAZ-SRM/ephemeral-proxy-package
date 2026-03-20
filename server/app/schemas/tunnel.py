from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TunnelCreate(BaseModel):
    local_port: int = Field(..., ge=1, le=65535)
    local_url: Optional[str] = None
    name: Optional[str] = Field(None, pattern=r"^[a-z0-9-]{3,32}$")
    ttl_seconds: int = Field(default=7200, ge=0, le=86400)
    auth_domain: Optional[str] = None
    password: Optional[str] = None


class TunnelResponse(BaseModel):
    id: UUID
    slug: str
    assigned_port: int
    url: str
    dashboard_url: str
    status: str
    expires_at: Optional[datetime] = None
    ssh_command: str
    local_port: int
    local_url: Optional[str] = None

    class Config:
        from_attributes = True


class TunnelStatus(BaseModel):
    id: UUID
    slug: str
    status: str
    url: str
    dashboard_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    stats: Optional["TunnelStatsData"] = None

    class Config:
        from_attributes = True


class TunnelStatsData(BaseModel):
    total_requests: int
    unique_ips: int
    bytes_transferred: int


class TunnelExpireResponse(BaseModel):
    message: str
    summary: dict


class TunnelSettingsUpdate(BaseModel):
    ttl_seconds: Optional[int] = None
    password: Optional[str] = None
    fault_injection: Optional[dict] = None
    blocked_countries: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserMe(BaseModel):
    id: UUID
    email: str
    ssh_key_registered: bool = False
    active_tunnels: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class SSHKeyRegister(BaseModel):
    public_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    active_tunnels: int = 0
    port_pool_available: int = 0
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    error: str
    message: str


TunnelStatus.model_rebuild()
