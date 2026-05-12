import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, Base


class MembershipPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "membership_plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Integer, nullable=False)  # Stored as cents
    ai_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    task_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'{}'")

    # Relationships
    user_memberships: Mapped[list["UserMembership"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class UserMembership(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("membership_plans.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)  # 0: inactive, 1: active, 2: expired

    # Relationships
    user: Mapped["User"] = relationship()
    plan: Mapped["MembershipPlan"] = relationship(back_populates="user_memberships")

    __table_args__ = (
        Index("idx_user_memberships_user_id", "user_id"),
        Index("idx_user_memberships_plan_id", "plan_id"),
        Index("idx_user_memberships_status", "status"),
    )