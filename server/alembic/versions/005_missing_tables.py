"""add missing tables for alert, ai templates, security/operation audit

Revision ID: 005_missing_tables
Revises: 004_new_tables
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005_missing_tables"
down_revision = "004_new_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("window_minutes", sa.Integer, nullable=False, server_default=sa.text("5")),
        sa.Column("cooldown_minutes", sa.Integer, nullable=False, server_default=sa.text("30")),
        sa.Column("severity", sa.String(10), nullable=False, server_default="warning"),
        sa.Column("channels", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("filters", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_alert_rules_user_id", "alert_rules", ["user_id"])
    op.create_index("idx_alert_rules_active", "alert_rules", ["user_id", "is_active"])

    op.create_table(
        "alert_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("rule_id", UUID(as_uuid=True), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("metric_value", sa.Float, nullable=True),
        sa.Column("threshold_value", sa.Float, nullable=True),
        sa.Column("context", JSONB, nullable=True),
        sa.Column("is_acknowledged", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_alert_events_user_id", "alert_events", ["user_id"])
    op.create_index("idx_alert_events_rule_id", "alert_events", ["rule_id"])
    op.create_index("idx_alert_events_created", "alert_events", ["created_at"])

    op.create_table(
        "ai_report_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("metrics", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("chart_types", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("output_format", sa.String(20), nullable=False, server_default="pdf"),
        sa.Column("prompt_template", sa.Text, nullable=True),
        sa.Column("sections", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_report_templates_user_id", "ai_report_templates", ["user_id"])

    op.create_table(
        "security_audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.String(8), nullable=False),
        sa.Column("timestamp", sa.String(40), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("query", sa.Text, nullable=True),
        sa.Column("client_ip", sa.String(100), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("risk_flags", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("response_time_ms", sa.Float, nullable=True),
    )
    op.create_index("idx_security_audit_timestamp", "security_audit_log", ["timestamp"])
    op.create_index("idx_security_audit_path", "security_audit_log", ["path"])
    op.create_index("idx_security_audit_risk_score", "security_audit_log", ["risk_score"])
    op.create_index("idx_security_audit_client_ip", "security_audit_log", ["client_ip"])

    op.create_table(
        "operation_audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_operation_audit_user_id", "operation_audit_log", ["user_id"])
    op.create_index("idx_operation_audit_action", "operation_audit_log", ["action"])
    op.create_index("idx_operation_audit_resource", "operation_audit_log", ["resource_type", "resource_id"])
    op.create_index("idx_operation_audit_created_at", "operation_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("operation_audit_log")
    op.drop_table("security_audit_log")
    op.drop_table("ai_report_templates")
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
