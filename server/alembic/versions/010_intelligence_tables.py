"""add intelligence system tables

Revision ID: 010_intelligence_tables
Revises: 009_composite_indexes
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "010_intelligence_tables"
down_revision = "009_composite_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_trends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("opportunity_score", sa.Float, server_default="0"),
        sa.Column("lifecycle", sa.String(20), server_default="early"),
        sa.Column("competition", sa.String(20), server_default="low"),
        sa.Column("freshness_days", sa.Integer, server_default="0"),
        sa.Column("risk_level", sa.String(20), server_default="low"),
        sa.Column("user_emotion", sa.String(100), nullable=True),
        sa.Column("monetization_potential", sa.String(50), nullable=True),
        sa.Column("trend_status", sa.String(20), server_default="active"),
        sa.Column("source_data", JSONB, server_default="{}"),
        sa.Column("direction", sa.String(10), server_default="rising"),
        sa.Column("peak_expected", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trend_history", JSONB, server_default="[]"),
        sa.Column("related_opportunity_scores", JSONB, server_default="[]"),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("actionable_insight", sa.Text, nullable=True),
        sa.Column("affected_opportunities", JSONB, server_default="[]"),
        sa.Column("risk_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_trends_category", "intelligence_trends", ["category"])
    op.create_index("idx_intel_trends_platform", "intelligence_trends", ["platform"])
    op.create_index("idx_intel_trends_lifecycle", "intelligence_trends", ["lifecycle"])
    op.create_index("idx_intel_trends_trend_status", "intelligence_trends", ["trend_status"])

    op.create_table(
        "intelligence_opportunities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sub_category", sa.String(100), nullable=True),
        sa.Column("opportunity_score", sa.Float, server_default="0"),
        sa.Column("verdict", sa.String(20), server_default="CAUTION"),
        sa.Column("verdict_score", sa.Float, server_default="0"),
        sa.Column("verdict_detail", JSONB, server_default="{}"),
        sa.Column("risk_flag", sa.Boolean, server_default="false"),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("startup_cost", sa.Integer, server_default="0"),
        sa.Column("monthly_ceiling", sa.String(50), nullable=True),
        sa.Column("time_to_first_revenue", sa.String(20), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("recommend", sa.Boolean, server_default="false"),
        sa.Column("persona_fit", JSONB, server_default="[]"),
        sa.Column("platform", JSONB, server_default="[]"),
        sa.Column("lifecycle_stage", sa.String(20), nullable=True),
        sa.Column("first_identified", sa.String(20), nullable=True),
        sa.Column("last_verified", sa.String(20), nullable=True),
        sa.Column("trend_direction", sa.String(10), nullable=True),
        sa.Column("key_metrics", JSONB, server_default="{}"),
        sa.Column("commercial_paths", JSONB, server_default="[]"),
        sa.Column("source_topic_id", sa.String(50), nullable=True),
        sa.Column("score_history", JSONB, server_default="[]"),
        sa.Column("publish_feedback", JSONB, server_default="{}"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("output_path", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_opps_category", "intelligence_opportunities", ["category"])
    op.create_index("idx_intel_opps_verdict", "intelligence_opportunities", ["verdict"])
    op.create_index("idx_intel_opps_status", "intelligence_opportunities", ["status"])

    op.create_table(
        "intelligence_risks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("alternative", sa.Text, nullable=True),
        sa.Column("early_signal", sa.Text, nullable=True),
        sa.Column("early_signals", JSONB, server_default="[]"),
        sa.Column("affected_track", sa.String(100), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("original_score", sa.Float, nullable=True),
        sa.Column("score_history", JSONB, server_default="[]"),
        sa.Column("downgraded_from", sa.String(200), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("risk_type", sa.String(20), server_default="eliminated"),
        sa.Column("eliminated_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_observed", sa.String(20), nullable=True),
        sa.Column("risk_description", sa.Text, nullable=True),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_risks_status", "intelligence_risks", ["status"])
    op.create_index("idx_intel_risks_severity", "intelligence_risks", ["severity"])
    op.create_index("idx_intel_risks_risk_type", "intelligence_risks", ["risk_type"])

    op.create_table(
        "intelligence_xhs_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), unique=True, nullable=False),
        sa.Column("hook_type", sa.String(50), nullable=True),
        sa.Column("emotion", sa.String(50), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("ctr_prediction", sa.Float, server_default="0"),
        sa.Column("competition", sa.String(20), nullable=True),
        sa.Column("source_topic_id", sa.String(50), nullable=True),
        sa.Column("topic_data", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_topics_hook_type", "intelligence_xhs_topics", ["hook_type"])

    op.create_table(
        "intelligence_platform_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(50), unique=True, nullable=False),
        sa.Column("current_focus", sa.Text, nullable=True),
        sa.Column("traffic_signal", sa.Text, nullable=True),
        sa.Column("policy_risk", sa.Text, nullable=True),
        sa.Column("change_direction", sa.String(10), nullable=True),
        sa.Column("magnitude", sa.String(20), nullable=True),
        sa.Column("impact_on_side_hustle", sa.Text, nullable=True),
        sa.Column("signal_history", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "intelligence_user_emotions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("keyword", sa.String(100), unique=True, nullable=False),
        sa.Column("emotion_type", sa.String(50), nullable=True),
        sa.Column("intensity", sa.String(20), nullable=True),
        sa.Column("keyword_cluster", JSONB, server_default="[]"),
        sa.Column("platform_source", sa.String(50), nullable=True),
        sa.Column("trend_direction", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_emotions_type", "intelligence_user_emotions", ["emotion_type"])

    op.create_table(
        "intelligence_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content_json", JSONB, server_default="{}"),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("week_number", sa.String(10), nullable=True),
        sa.Column("report_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_reports_type", "intelligence_reports", ["report_type"])
    op.create_index("idx_intel_reports_date", "intelligence_reports", ["report_date"])

    op.create_table(
        "intel_auth_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("duration_days", sa.SmallInteger, nullable=False),
        sa.Column("max_activations", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("current_activations", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unused"),
        sa.Column("batch_id", sa.String(64), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_intel_auth_codes_status", "intel_auth_codes", ["status"])
    op.create_index("idx_intel_auth_codes_plan", "intel_auth_codes", ["plan"])

    op.create_table(
        "intel_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auth_code_id", UUID(as_uuid=True), sa.ForeignKey("intel_auth_codes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_memberships_user_id", "intel_memberships", ["user_id"])
    op.create_index("idx_intel_memberships_status", "intel_memberships", ["status"])

    op.create_table(
        "intel_sync_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", sa.String(100), unique=True, nullable=False),
        sa.Column("sync_table", sa.String(50), nullable=False),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("created_count", sa.Integer, server_default="0"),
        sa.Column("updated_count", sa.Integer, server_default="0"),
        sa.Column("skipped_count", sa.Integer, server_default="0"),
        sa.Column("error_count", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="processing"),
        sa.Column("detail_log", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intel_sync_batch_id", "intel_sync_batches", ["batch_id"])
    op.create_index("idx_intel_sync_created_at", "intel_sync_batches", ["created_at"])


def downgrade() -> None:
    op.drop_table("intel_sync_batches")
    op.drop_table("intel_memberships")
    op.drop_table("intel_auth_codes")
    op.drop_table("intelligence_reports")
    op.drop_table("intelligence_user_emotions")
    op.drop_table("intelligence_platform_signals")
    op.drop_table("intelligence_xhs_topics")
    op.drop_table("intelligence_risks")
    op.drop_table("intelligence_opportunities")
    op.drop_table("intelligence_trends")
