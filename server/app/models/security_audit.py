import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(8), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(40), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    query: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str] = mapped_column(String(100), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    user_id: Mapped[str | None] = mapped_column(String(36))
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("idx_security_audit_timestamp", "timestamp"),
        Index("idx_security_audit_path", "path"),
        Index("idx_security_audit_risk_score", "risk_score"),
        Index("idx_security_audit_client_ip", "client_ip"),
    )
