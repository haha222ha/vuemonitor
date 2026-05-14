import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPrimaryKeyMixin, Base


class AIPrediction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_predictions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Integer, nullable=False)  # Stored as integer percentage (0-100)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    reason: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        Index("idx_ai_predictions_product_id", "product_id"),
        Index("idx_ai_predictions_created_at", "created_at"),
    )