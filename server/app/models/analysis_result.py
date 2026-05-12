import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import UUIDPrimaryKeyMixin, Base


class AnalysisResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "analysis_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_analysis_results_user_id", "user_id"),
        Index("idx_analysis_results_analysis_type", "analysis_type"),
        Index("idx_analysis_results_created_at", "created_at"),
    )


class PromptTemplate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "prompt_templates"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_prompt_templates_analysis_type", "analysis_type"),
    )