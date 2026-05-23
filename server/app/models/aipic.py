import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AipicConfig(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aipic_config"

    default_model: Mapped[str] = mapped_column(String(50), nullable=False, default="gpt-image-2")
    daily_generate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    content_filter_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_queue_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    worker_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    stuck_task_timeout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AipicAuthCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_auth_codes"

    auth_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="未激活", index=True)
    activate_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    batch_no: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    batch_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    export_tag: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    __table_args__ = (
        Index("idx_aipic_auth_codes_status", "status"),
        Index("idx_aipic_auth_codes_batch_no", "batch_no"),
    )


class AipicUserCredits(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_user_credits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_purchased: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_generate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    today_generated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reset_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)


class AipicCreditsLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aipic_credits_log"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    change_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_aipic_credits_log_user_type", "user_id", "change_type"),
    )


class AipicGenerateQueue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_generate_queue"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, default="gpt-image-2")
    ratio_key: Mapped[str] = mapped_column(String(20), nullable=False, default="square")
    style_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text2img")
    quality_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    credits_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_image_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    task_status: Mapped[str] = mapped_column(String(20), nullable=False, default="待执行", index=True)
    queue_order: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    execute_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fail_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_image_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)

    __table_args__ = (
        Index("idx_aipic_queue_user_status", "user_id", "task_status"),
        Index("idx_aipic_queue_status_order", "task_status", "queue_order"),
    )


class AipicStyleLibrary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_style_library"

    style_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    style_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style_negative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    preview_image: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="通用", index=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AipicUserWork(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aipic_user_works"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ratio_key: Mapped[str] = mapped_column(String(20), nullable=False, default="square")
    style_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text2img")
    quality_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    credits_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_image_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    output_image_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_aipic_user_works_user", "user_id", "is_deleted"),
    )


class AipicDailySummary(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aipic_daily_summary"

    summary_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
