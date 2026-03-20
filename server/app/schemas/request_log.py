from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RequestLogResponse(BaseModel):
    id: UUID
    method: str
    path: str
    query_params: dict
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    visitor_ip: Optional[str] = None
    country_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RequestLogDetail(BaseModel):
    id: UUID
    method: str
    path: str
    query_params: dict
    req_headers: dict
    req_body: Optional[str] = None
    status_code: Optional[int] = None
    res_headers: dict
    res_body: Optional[str] = None
    latency_ms: Optional[int] = None
    visitor_ip: Optional[str] = None
    country_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RequestLogPage(BaseModel):
    total: int
    page: int
    limit: int
    requests: list[RequestLogResponse]
