import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, Base


class CollectTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collect_tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    result_summary: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="collect_tasks")
    items: Mapped[list["CollectTaskItem"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_collect_tasks_user_id", "user_id"),
        Index("idx_collect_tasks_status", "status"),
    )


class CollectTaskItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "collect_task_items"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collect_tasks.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped["CollectTask"] = relationship(back_populates="items")

    __table_args__ = (
        Index("idx_collect_task_items_task_id", "task_id"),
    )
