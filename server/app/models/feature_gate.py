import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, Base


class FeatureGate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feature_gates"

    gate_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    gate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    required_plan: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None]
    config: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    usage_records: Mapped[list["FeatureGateUsage"]] = relationship(back_populates="gate", cascade="all, delete-orphan")


class FeatureGateUsage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feature_gate_usage"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gate_key: Mapped[str] = mapped_column(String(100), ForeignKey("feature_gates.gate_key"), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")

    gate: Mapped["FeatureGate"] = relationship(back_populates="usage_records")

    __table_args__ = (
        Index("idx_feature_gate_usage_user_gate", "user_id", "gate_key"),
        Index("idx_feature_gate_usage_used_at", "used_at"),
    )
