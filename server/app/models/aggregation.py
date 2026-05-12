import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import UUIDPrimaryKeyMixin, Base


class AggregationAudit(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aggregation_audit"

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(nullable=False, index=True)
    sample_users: Mapped[int] = mapped_column(Integer, nullable=False)
    min_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_threshold: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_aggregation_audit_date", "date"),
    )