import httpx
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from .config import config


class TunnelResponse(BaseModel):
    id: str
    slug: str
    assigned_port: int
    url: str
    dashboard_url: str
    status: str
    expires_at: Optional[datetime] = None
    ssh_command: str
    local_port: int
    local_url: Optional[str] = None


class TunnelStatus(BaseModel):
    id: str
    slug: str
    status: str
    url: str
    dashboard_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_active: Optional[datetime] = None


class SessionSummary(BaseModel):
    duration_seconds: int
    total_requests: int
    unique_visitors: int


class TunnelAPIClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or config.server_url).rstrip("/")
        self.token = token or config.auth_token

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def create_tunnel(
        self,
        port: int,
        local_url: Optional[str] = None,
        name: Optional[str] = None,
        ttl: int = 7200,
        auth_domain: Optional[str] = None,
        password: Optional[str] = None,
    ) -> TunnelResponse:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = {
                "local_port": port,
                "ttl_seconds": ttl,
            }
            if local_url:
                body["local_url"] = local_url
            if name:
                body["name"] = name
            if auth_domain:
                body["auth_domain"] = auth_domain
            if password:
                body["password"] = password

            response = await client.post(
                f"{self.base_url}/tunnels",
                json=body,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return TunnelResponse(**response.json())

    async def expire_tunnel(self, slug: str) -> SessionSummary:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{self.base_url}/tunnels/{slug}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return SessionSummary(**data["summary"])

    async def get_tunnel_status(self, slug: str) -> TunnelStatus:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/tunnels/{slug}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return TunnelStatus(**response.json())

    async def get_session_summary(self, slug: str) -> Optional[SessionSummary]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers(),
                )
                return None
            except Exception:
                return None

    async def register_ssh_key(self, public_key: str):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/users/ssh-key",
                json={"public_key": public_key},
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_me(self) -> Optional[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/auth/me",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                return None

    async def activate_tunnel(self, slug: str):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/internal/tunnel/{slug}/activate",
                headers={"X-Internal-Secret": "dev_internal_secret_key_change_in_production"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_tunnels(self) -> list:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/tunnels",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                return []
