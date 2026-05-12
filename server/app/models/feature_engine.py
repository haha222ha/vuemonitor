import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import UUIDPrimaryKeyMixin, Base


class Feature(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "features"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    acceleration: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    competition_index: Mapped[float] = mapped_column(Float, nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    sales_velocity: Mapped[float] = mapped_column(Float, nullable=False)
    is_anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_features_user_id", "user_id"),
        Index("idx_features_platform", "platform"),
        Index("idx_features_category", "category"),
    )


class CategoryStat(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "category_stats"

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(nullable=False)
    watch_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_products: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_users: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    heat_index: Mapped[float] = mapped_column(Float, nullable=False)
    up_trend_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    down_trend_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()", nullable=False
    )

    __table_args__ = (
        UniqueConstraint("category", "platform", "date", name="uq_category_stats_category_platform_date"),
    )


class EnhancedFeature(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "enhanced_features"

    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    base_growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    enhanced_growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    market_share_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_score: Mapped[float] = mapped_column(Float, nullable=False)
    heat_trend: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_enhanced_features_product_id", "product_id"),
    )