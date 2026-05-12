import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, Base


class UserQuota(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_key: Mapped[str] = mapped_column(String(100), nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "gate_key", "period", name="uq_user_quota_user_gate_period"),
        Index("idx_user_quotas_user_id", "user_id"),
    )