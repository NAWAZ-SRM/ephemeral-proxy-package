import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    ssh_pub_key = Column(Text, nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tunnels = relationship("Tunnel", back_populates="owner")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_google_id", "google_id"),
    )


class Tunnel(Base):
    __tablename__ = "tunnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(32), unique=True, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    owner_email = Column(String(255), nullable=True)
    assigned_port = Column(Integer, nullable=False)
    local_port = Column(Integer, nullable=False)
    local_url = Column(String(255), nullable=True)
    status = Column(String(16), nullable=False, default="pending")
    ttl_seconds = Column(Integer, nullable=False, default=7200)
    auth_domain = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_active = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    fault_injection = Column(JSONB, nullable=True)
    blocked_countries = Column(ARRAY(String(2)), default=[])
    total_requests = Column(Integer, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)

    owner = relationship("User", back_populates="tunnels")
    request_logs = relationship("RequestLog", back_populates="tunnel", cascade="all, delete-orphan")
    stats = relationship("TunnelStats", back_populates="tunnel", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tunnels_slug", "slug"),
        Index("idx_tunnels_status", "status"),
        Index("idx_tunnels_owner_id", "owner_id"),
        Index("idx_tunnels_expires_at", "expires_at", postgresql_where=status.in_(["pending", "active", "idle"])),
        Index("idx_tunnels_last_active", "last_active", postgresql_where=status == "idle"),
    )


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tunnel_id = Column(UUID(as_uuid=True), ForeignKey("tunnels.id", ondelete="CASCADE"), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(Text, nullable=False)
    query_params = Column(JSONB, default={})
    req_headers = Column(JSONB, default={})
    req_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    res_headers = Column(JSONB, default={})
    res_body = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    visitor_ip = Column(String(45), nullable=True)
    country_code = Column(String(2), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    tunnel = relationship("Tunnel", back_populates="request_logs")

    __table_args__ = (
        Index("idx_request_logs_tunnel_id", "tunnel_id"),
        Index("idx_request_logs_created_at", "created_at"),
        Index("idx_request_logs_status_code", "status_code"),
        Index("idx_request_logs_tunnel_time", "tunnel_id", "created_at"),
        Index("idx_request_logs_errors", "tunnel_id", postgresql_where=status_code >= 400),
    )


class TunnelStats(Base):
    __tablename__ = "tunnel_stats"

    tunnel_id = Column(UUID(as_uuid=True), ForeignKey("tunnels.id", ondelete="CASCADE"), primary_key=True)
    total_requests = Column(Integer, nullable=False, default=0)
    unique_ips = Column(Integer, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)
    avg_latency_ms = Column(Integer, default=0)
    country_breakdown = Column(JSONB, default={})
    method_breakdown = Column(JSONB, default={})
    status_breakdown = Column(JSONB, default={})
    peak_rps = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tunnel = relationship("Tunnel", back_populates="stats")
