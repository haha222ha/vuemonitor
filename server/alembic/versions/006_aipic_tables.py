"""add aipic module tables

Revision ID: 006_aipic_tables
Revises: 005_missing_tables
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006_aipic_tables"
down_revision = "005_missing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aipic_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("default_model", sa.String(50), nullable=False, server_default="gpt-image-2"),
        sa.Column("daily_generate_limit", sa.Integer, nullable=False, server_default=sa.text("500")),
        sa.Column("content_filter_enabled", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("max_queue_size", sa.Integer, nullable=False, server_default=sa.text("1000")),
        sa.Column("worker_count", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column("stuck_task_timeout_minutes", sa.Integer, nullable=False, server_default=sa.text("10")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "aipic_auth_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("auth_code", sa.String(64), unique=True, nullable=False),
        sa.Column("package_type", sa.String(20), nullable=False),
        sa.Column("valid_days", sa.Integer, nullable=False),
        sa.Column("credits", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default="未激活"),
        sa.Column("activate_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_no", sa.String(50), nullable=False, server_default=""),
        sa.Column("batch_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("export_tag", sa.String(100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_auth_codes_status", "aipic_auth_codes", ["status"])
    op.create_index("idx_aipic_auth_codes_batch_no", "aipic_auth_codes", ["batch_no"])

    op.create_table(
        "aipic_user_credits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("credits", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_purchased", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_used", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("daily_generate_limit", sa.Integer, nullable=False, server_default=sa.text("10")),
        sa.Column("today_generated_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_reset_date", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_user_credits_user_id", "aipic_user_credits", ["user_id"])

    op.create_table(
        "aipic_credits_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_amount", sa.Integer, nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_credits_log_user_type", "aipic_credits_log", ["user_id", "change_type"])

    op.create_table(
        "aipic_generate_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(64), unique=True, nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("model_name", sa.String(50), nullable=False, server_default="gpt-image-2"),
        sa.Column("ratio_key", sa.String(20), nullable=False, server_default="square"),
        sa.Column("style_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("task_type", sa.String(20), nullable=False, server_default="text2img"),
        sa.Column("quality_tier", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("credits_cost", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("input_image_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("task_status", sa.String(20), nullable=False, server_default="待执行"),
        sa.Column("queue_order", sa.Numeric, nullable=False, server_default=sa.text("0")),
        sa.Column("execute_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fail_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("output_image_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("seed", sa.Integer, nullable=False, server_default=sa.text("-1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_queue_user_status", "aipic_generate_queue", ["user_id", "task_status"])
    op.create_index("idx_aipic_queue_status_order", "aipic_generate_queue", ["task_status", "queue_order"])

    op.create_table(
        "aipic_style_library",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("style_name", sa.String(100), unique=True, nullable=False),
        sa.Column("style_prompt", sa.Text, nullable=False),
        sa.Column("style_negative_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("preview_image", sa.String(500), nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False, server_default="通用"),
        sa.Column("is_preset", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_style_category", "aipic_style_library", ["category"])

    op.create_table(
        "aipic_user_works",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(64), unique=True, nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("negative_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("ratio_key", sa.String(20), nullable=False, server_default="square"),
        sa.Column("style_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("task_type", sa.String(20), nullable=False, server_default="text2img"),
        sa.Column("quality_tier", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("credits_cost", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("input_image_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("output_image_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_favorite", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_aipic_user_works_user", "aipic_user_works", ["user_id", "is_deleted"])

    op.create_table(
        "aipic_daily_summary",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("summary_date", sa.Date, unique=True, nullable=False),
        sa.Column("total_users", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_generated", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("active_users", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("aipic_daily_summary")
    op.drop_table("aipic_user_works")
    op.drop_table("aipic_style_library")
    op.drop_table("aipic_generate_queue")
    op.drop_table("aipic_credits_log")
    op.drop_table("aipic_user_credits")
    op.drop_table("aipic_auth_codes")
    op.drop_table("aipic_config")
