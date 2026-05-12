"""add new tables for M12-M18 features

Revision ID: 004_new_tables
Revises: 003_license_enhance
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "004_new_tables"
down_revision = "003_license_enhance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # M12 — license_codes ALTER: add license_key, max_devices,
    #        bound_user_id, bound_device_fingerprint
    # ============================================================
    op.add_column("license_codes", sa.Column("license_key", sa.String(19), unique=True, nullable=True))
    op.add_column("license_codes", sa.Column("max_devices", sa.Integer, server_default=sa.text("1"), nullable=True))
    op.add_column("license_codes", sa.Column("bound_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("license_codes", sa.Column("bound_device_fingerprint", sa.String(255), nullable=True))

    # ============================================================
    # M13 — user_quotas
    # ============================================================
    op.create_table(
        "user_quotas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gate_key", sa.String(100), nullable=False),
        sa.Column("used_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("limit_count", sa.Integer, nullable=True),
        sa.Column("period", sa.String(20), nullable=False, server_default="daily"),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "gate_key", "period", name="uq_user_quotas_user_gate_period"),
    )
    op.create_index("idx_user_quotas_user_id", "user_quotas", ["user_id"])

    # ============================================================
    # M14 — features (anonymized feature values)
    # ============================================================
    op.create_table(
        "features",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("growth_rate", sa.Float, nullable=True),
        sa.Column("acceleration", sa.Float, nullable=True),
        sa.Column("volatility", sa.Float, nullable=True),
        sa.Column("competition_index", sa.Float, nullable=True),
        sa.Column("lifecycle_stage", sa.String(20), nullable=True),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("sales_velocity", sa.Float, nullable=True),
        sa.Column("is_anonymized", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_features_user_id", "features", ["user_id"])
    op.create_index("idx_features_platform", "features", ["platform"])
    op.create_index("idx_features_category", "features", ["category"])

    # ============================================================
    # M14 — category_stats (category aggregation statistics)
    # ============================================================
    op.create_table(
        "category_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("watch_count", sa.Integer, nullable=True),
        sa.Column("unique_products", sa.Integer, nullable=True),
        sa.Column("unique_users", sa.Integer, nullable=True),
        sa.Column("avg_growth_rate", sa.Float, nullable=True),
        sa.Column("avg_volatility", sa.Float, nullable=True),
        sa.Column("heat_index", sa.Float, nullable=True),
        sa.Column("up_trend_ratio", sa.Float, nullable=True),
        sa.Column("down_trend_ratio", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("category", "platform", "date", name="uq_category_stats_cat_plat_date"),
    )
    op.create_index("idx_category_stats_category", "category_stats", ["category"])
    op.create_index("idx_category_stats_date", "category_stats", ["date"])

    # ============================================================
    # M14 — enhanced_features
    # ============================================================
    op.create_table(
        "enhanced_features",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("product_id", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("base_growth_rate", sa.Float, nullable=True),
        sa.Column("enhanced_growth_rate", sa.Float, nullable=True),
        sa.Column("market_share_percentile", sa.Float, nullable=True),
        sa.Column("heat_trend", sa.String(20), nullable=True),
        sa.Column("prediction_score", sa.Float, nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_enhanced_features_product_id", "enhanced_features", ["product_id"])

    # ============================================================
    # M15 — analysis_results
    # ============================================================
    op.create_table(
        "analysis_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=True),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("input_snapshot", JSONB, nullable=True),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_analysis_results_user_id", "analysis_results", ["user_id"])
    op.create_index("idx_analysis_results_type", "analysis_results", ["analysis_type"])
    op.create_index("idx_analysis_results_created_at", "analysis_results", ["created_at"])

    # ============================================================
    # M15 — prompt_templates
    # ============================================================
    op.create_table(
        "prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("output_schema", JSONB, nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_prompt_templates_type", "prompt_templates", ["analysis_type"])

    # ============================================================
    # M17 — aggregation_audit
    # ============================================================
    op.create_table(
        "aggregation_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("sample_users", sa.Integer, nullable=True),
        sa.Column("min_threshold", sa.Integer, nullable=True),
        sa.Column("passed_threshold", sa.Boolean, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aggregation_audit_date", "aggregation_audit", ["date"])

    # ============================================================
    # M18 — membership_plans
    # ============================================================
    op.create_table(
        "membership_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("ai_quota", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("task_limit", sa.Integer, nullable=False, server_default=sa.text("5")),
        sa.Column("max_projects", sa.Integer, nullable=False, server_default=sa.text("10")),
        sa.Column("features", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ============================================================
    # M18 — user_membership
    # ============================================================
    op.create_table(
        "user_membership",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("membership_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default=sa.text("1")),
    )
    op.create_index("idx_user_membership_user_id", "user_membership", ["user_id"])
    op.create_index("idx_user_membership_plan_id", "user_membership", ["plan_id"])

    # ============================================================
    # M18 — product_metrics
    # ============================================================
    op.create_table(
        "product_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("views", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("likes", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("favorites", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("comments", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("add_to_cart", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("sales_estimate", sa.Integer, nullable=True, server_default=sa.text("0")),
        sa.Column("trend_score", sa.Float, nullable=True),
        sa.Column("ai_score", sa.Float, nullable=True),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_product_metrics_product_id", "product_metrics", ["product_id"])
    op.create_index("idx_product_metrics_snapshot_time", "product_metrics", ["snapshot_time"])

    # ============================================================
    # M18 — ai_predictions
    # ============================================================
    op.create_table(
        "ai_predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("label", sa.String(20), nullable=False),
        sa.Column("breakdown", JSONB, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_predictions_product_id", "ai_predictions", ["product_id"])
    op.create_index("idx_ai_predictions_score", "ai_predictions", ["score"])

    # ============================================================
    # M18 — tasks (scheduler tasks, independent from collect_tasks)
    # ============================================================
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=True),
        sa.Column("schedule_type", sa.String(20), nullable=False, server_default="once"),
        sa.Column("cron_expression", sa.String(50), nullable=True),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tasks_user_id", "tasks", ["user_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])

    # ============================================================
    # M18 — task_logs
    # ============================================================
    op.create_table(
        "task_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("log", sa.Text, nullable=True),
        sa.Column("duration", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_task_logs_task_id", "task_logs", ["task_id"])

    # ============================================================
    # M18 — product_id_mapping (local ↔ cloud product mapping)
    # ============================================================
    op.create_table(
        "product_id_mapping",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("local_product_id", sa.String(255), unique=True, nullable=False),
        sa.Column("cloud_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_product_id_mapping_user_id", "product_id_mapping", ["user_id"])
    op.create_index("idx_product_id_mapping_cloud", "product_id_mapping", ["cloud_product_id"])
    op.create_index("idx_product_id_mapping_sync_status", "product_id_mapping", ["sync_status"])

    # ============================================================
    # M18 — db_config (runtime key-value configuration)
    # ============================================================
    op.create_table(
        "db_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("db_config")
    op.drop_table("product_id_mapping")
    op.drop_table("task_logs")
    op.drop_table("tasks")
    op.drop_table("ai_predictions")
    op.drop_table("product_metrics")
    op.drop_table("user_membership")
    op.drop_table("membership_plans")
    op.drop_table("aggregation_audit")
    op.drop_table("prompt_templates")
    op.drop_table("analysis_results")
    op.drop_table("enhanced_features")
    op.drop_table("category_stats")
    op.drop_table("features")
    op.drop_table("user_quotas")

    # Revert license_codes ALTER
    op.drop_column("license_codes", "bound_device_fingerprint")
    op.drop_column("license_codes", "bound_user_id")
    op.drop_column("license_codes", "max_devices")
    op.drop_column("license_codes", "license_key")
