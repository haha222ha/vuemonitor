"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("nickname", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True)),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("email_notify_enabled", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("device_info", sa.String(255)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "license_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("duration_days", sa.SmallInteger, nullable=False),
        sa.Column("max_activations", sa.SmallInteger, nullable=False, server_default=sa.text("1")),
        sa.Column("current_activations", sa.SmallInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default="unused"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "license_activations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("license_id", UUID(as_uuid=True), sa.ForeignKey("license_codes.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_fingerprint", sa.String(255)),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "feature_gates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("feature_key", sa.String(100), unique=True, nullable=False),
        sa.Column("feature_name", sa.String(200), nullable=False),
        sa.Column("min_plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "feature_gate_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feature_key", sa.String(100), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_fg_usage_user_feature", "feature_gate_usage", ["user_id", "feature_key"])

    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("platform_product_id", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(500)),
        sa.Column("shop_name", sa.String(200)),
        sa.Column("category", sa.String(200)),
        sa.Column("image_url", sa.String(1000)),
        sa.Column("product_url", sa.String(1000)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_collected_at", sa.DateTime(timezone=True)),
        sa.Column("trend", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_products_user_platform", "products", ["user_id", "platform", "platform_product_id"], unique=True)

    op.create_table(
        "product_features",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("sales_count", sa.Integer),
        sa.Column("monthly_sales", sa.Integer),
        sa.Column("rating", sa.Numeric(3, 1)),
        sa.Column("review_count", sa.Integer),
        sa.Column("favorite_count", sa.Integer),
        sa.Column("source", sa.String(50), server_default="collect"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_pf_product_collected", "product_features", ["product_id", "collected_at"])

    op.create_table(
        "ai_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id")),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50)),
        sa.Column("model", sa.String(100)),
        sa.Column("prompt_tokens", sa.Integer, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer, server_default=sa.text("0")),
        sa.Column("result", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ai_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("analysis_id", UUID(as_uuid=True), sa.ForeignKey("ai_analyses.id")),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("content", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "collect_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_ids", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("result_summary", sa.JSON),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_collect_tasks_user_status", "collect_tasks", ["user_id", "status"])

    op.create_table(
        "collect_task_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("collect_tasks.id"), nullable=False),
        sa.Column("target_id", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("result", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "monitor_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id")),
        sa.Column("conditions", sa.JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
        sa.Column("trigger_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("related_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_notifications_user_read", "notifications", ["user_id", "is_read"])

    op.create_table(
        "rbac_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "rbac_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("module", sa.String(50)),
    )

    op.create_table(
        "rbac_role_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("rbac_roles.id"), nullable=False),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("rbac_permissions.id"), nullable=False),
    )

    op.create_table(
        "rbac_user_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("rbac_roles.id"), nullable=False),
    )

    op.create_table(
        "proxy_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_url", sa.String(500)),
        sa.Column("api_key", sa.String(500)),
        sa.Column("protocol", sa.String(20), server_default="http"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "proxy_pool",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("ip", sa.String(50), nullable=False),
        sa.Column("port", sa.Integer, nullable=False),
        sa.Column("protocol", sa.String(20), server_default="http"),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("proxy_providers.id")),
        sa.Column("health_score", sa.SmallInteger, server_default=sa.text("100")),
        sa.Column("status", sa.String(20), server_default="available"),
        sa.Column("fail_count", sa.SmallInteger, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "risk_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("collect_tasks.id")),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("risk_type", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("detail", sa.JSON),
        sa.Column("proxy_id", UUID(as_uuid=True), sa.ForeignKey("proxy_pool.id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_risk_events_type", "risk_events", ["risk_type", "occurred_at"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("detail", sa.JSON),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_table("risk_events")
    op.drop_table("proxy_pool")
    op.drop_table("proxy_providers")
    op.drop_table("rbac_user_roles")
    op.drop_table("rbac_role_permissions")
    op.drop_table("rbac_permissions")
    op.drop_table("rbac_roles")
    op.drop_table("notifications")
    op.drop_table("monitor_rules")
    op.drop_table("collect_task_items")
    op.drop_table("collect_tasks")
    op.drop_table("ai_reports")
    op.drop_table("ai_analyses")
    op.drop_table("product_features")
    op.drop_table("products")
    op.drop_table("feature_gate_usage")
    op.drop_table("feature_gates")
    op.drop_table("license_activations")
    op.drop_table("license_codes")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
