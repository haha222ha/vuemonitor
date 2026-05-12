import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Float, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPrimaryKeyMixin, Base


class ProductMetrics(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_metrics"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    add_to_cart: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sales_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        Index("idx_product_metrics_product_id", "product_id"),
        Index("idx_product_metrics_snapshot_time", "snapshot_time"),
    )