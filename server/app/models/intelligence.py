import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IntelligenceTrend(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_trends"

    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0)
    lifecycle: Mapped[str] = mapped_column(String(20), default="early")
    competition: Mapped[str] = mapped_column(String(20), default="low")
    freshness_days: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    user_emotion: Mapped[str | None] = mapped_column(String(100))
    monetization_potential: Mapped[str | None] = mapped_column(String(50))
    trend_status: Mapped[str] = mapped_column(String(20), default="active")
    source_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    direction: Mapped[str] = mapped_column(String(10), default="rising")
    peak_expected: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trend_history: Mapped[list] = mapped_column(JSONB, default=list)
    related_opportunity_scores: Mapped[list] = mapped_column(JSONB, default=list)
    evidence: Mapped[str | None] = mapped_column(Text)
    actionable_insight: Mapped[str | None] = mapped_column(Text)
    affected_opportunities: Mapped[list] = mapped_column(JSONB, default=list)
    risk_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_intel_trends_category", "category"),
        Index("idx_intel_trends_platform", "platform"),
        Index("idx_intel_trends_lifecycle", "lifecycle"),
        Index("idx_intel_trends_trend_status", "trend_status"),
    )


class IntelligenceOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_opportunities"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String(100))
    opportunity_score: Mapped[float] = mapped_column(Float, default=0)
    verdict: Mapped[str] = mapped_column(String(20), default="CAUTION")
    verdict_score: Mapped[float] = mapped_column(Float, default=0)
    verdict_detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    risk_flag: Mapped[bool] = mapped_column(default=False)
    difficulty: Mapped[str | None] = mapped_column(String(20))
    startup_cost: Mapped[int] = mapped_column(Integer, default=0)
    monthly_ceiling: Mapped[str | None] = mapped_column(String(50))
    time_to_first_revenue: Mapped[str | None] = mapped_column(String(20))
    risk_level: Mapped[str | None] = mapped_column(String(20))
    recommend: Mapped[bool] = mapped_column(default=False)
    persona_fit: Mapped[list] = mapped_column(JSONB, default=list)
    platform: Mapped[list] = mapped_column(JSONB, default=list)
    lifecycle_stage: Mapped[str | None] = mapped_column(String(20))
    first_identified: Mapped[str | None] = mapped_column(String(20))
    last_verified: Mapped[str | None] = mapped_column(String(20))
    trend_direction: Mapped[str | None] = mapped_column(String(10))
    key_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    commercial_paths: Mapped[list] = mapped_column(JSONB, default=list)
    source_topic_id: Mapped[str | None] = mapped_column(String(50))
    score_history: Mapped[list] = mapped_column(JSONB, default=list)
    publish_feedback: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    output_path: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_intel_opps_category", "category"),
        Index("idx_intel_opps_verdict", "verdict"),
        Index("idx_intel_opps_status", "status"),
    )


class IntelligenceRisk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_risks"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="active")
    reason: Mapped[str | None] = mapped_column(Text)
    alternative: Mapped[str | None] = mapped_column(Text)
    early_signal: Mapped[str | None] = mapped_column(Text)
    early_signals: Mapped[list] = mapped_column(JSONB, default=list)
    affected_track: Mapped[str | None] = mapped_column(String(100))
    platform: Mapped[str | None] = mapped_column(String(50))
    original_score: Mapped[float | None] = mapped_column(Float)
    score_history: Mapped[list] = mapped_column(JSONB, default=list)
    downgraded_from: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str | None] = mapped_column(String(200))
    risk_type: Mapped[str] = mapped_column(String(20), default="eliminated")
    eliminated_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_observed: Mapped[str | None] = mapped_column(String(20))
    risk_description: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_intel_risks_status", "status"),
        Index("idx_intel_risks_severity", "severity"),
        Index("idx_intel_risks_risk_type", "risk_type"),
    )


class IntelligenceXhsTopic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_xhs_topics"

    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hook_type: Mapped[str | None] = mapped_column(String(50))
    emotion: Mapped[str | None] = mapped_column(String(50))
    platform: Mapped[str | None] = mapped_column(String(50))
    content_type: Mapped[str | None] = mapped_column(String(50))
    ctr_prediction: Mapped[float] = mapped_column(Float, default=0)
    competition: Mapped[str | None] = mapped_column(String(20))
    source_topic_id: Mapped[str | None] = mapped_column(String(50))
    topic_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_intel_topics_hook_type", "hook_type"),
    )


class IntelligencePlatformSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_platform_signals"

    platform: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    current_focus: Mapped[str | None] = mapped_column(Text)
    traffic_signal: Mapped[str | None] = mapped_column(Text)
    policy_risk: Mapped[str | None] = mapped_column(Text)
    change_direction: Mapped[str | None] = mapped_column(String(10))
    magnitude: Mapped[str | None] = mapped_column(String(20))
    impact_on_side_hustle: Mapped[str | None] = mapped_column(Text)
    signal_history: Mapped[list] = mapped_column(JSONB, default=list)


class IntelligenceUserEmotion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_user_emotions"

    keyword: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    emotion_type: Mapped[str | None] = mapped_column(String(50))
    intensity: Mapped[str | None] = mapped_column(String(20))
    keyword_cluster: Mapped[list] = mapped_column(JSONB, default=list)
    platform_source: Mapped[str | None] = mapped_column(String(50))
    trend_direction: Mapped[str | None] = mapped_column(String(20))

    __table_args__ = (
        Index("idx_intel_emotions_type", "emotion_type"),
    )


class IntelligenceReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_reports"

    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_html: Mapped[str | None] = mapped_column(Text)
    week_number: Mapped[str | None] = mapped_column(String(10))
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_intel_reports_type", "report_type"),
        Index("idx_intel_reports_date", "report_date"),
    )


class IntelAuthCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intel_auth_codes"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    current_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unused")
    batch_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    intel_memberships: Mapped[list["IntelMembership"]] = relationship(back_populates="auth_code", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_intel_auth_codes_status", "status"),
        Index("idx_intel_auth_codes_plan", "plan"),
    )


class IntelMembership(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intel_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    auth_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel_auth_codes.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    auth_code: Mapped["IntelAuthCode"] = relationship(back_populates="intel_memberships")

    __table_args__ = (
        Index("idx_intel_memberships_user_id", "user_id"),
        Index("idx_intel_memberships_status", "status"),
    )


class IntelSyncBatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intel_sync_batches"

    batch_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sync_table: Mapped[str] = mapped_column(String(50), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    detail_log: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_intel_sync_batch_id", "batch_id"),
        Index("idx_intel_sync_created_at", "created_at"),
    )