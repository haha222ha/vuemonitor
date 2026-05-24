"""fix feature_gates and feature_gate_usage schema mismatch

Revision ID: 008_fix_feature_gates_schema
Revises: 007_product_categories
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "008_fix_feature_gates_schema"
down_revision = "007_product_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fg_usage_user_feature")

    op.alter_column("feature_gates", "feature_key", new_column_name="gate_key")
    op.alter_column("feature_gates", "feature_name", new_column_name="gate_name")
    op.alter_column("feature_gates", "min_plan", new_column_name="required_plan")

    op.add_column("feature_gates", sa.Column("gate_type", sa.String(20), nullable=False, server_default="quota"))
    op.add_column("feature_gates", sa.Column("config", JSONB, nullable=False, server_default="{}"))

    op.alter_column("feature_gate_usage", "feature_key", new_column_name="gate_key")

    op.add_column("feature_gate_usage", sa.Column("detail", JSONB, nullable=False, server_default="{}"))

    op.create_foreign_key(
        "fk_feature_gate_usage_gate_key",
        "feature_gate_usage",
        "feature_gates",
        ["gate_key"],
        ["gate_key"],
    )

    op.create_index(
        "idx_feature_gate_usage_user_gate",
        "feature_gate_usage",
        ["user_id", "gate_key"],
    )
    op.create_index(
        "idx_feature_gate_usage_used_at",
        "feature_gate_usage",
        ["used_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_feature_gate_usage_used_at", table_name="feature_gate_usage")
    op.drop_index("idx_feature_gate_usage_user_gate", table_name="feature_gate_usage")

    op.drop_constraint("fk_feature_gate_usage_gate_key", "feature_gate_usage", type_="foreignkey")

    op.drop_column("feature_gate_usage", "detail")

    op.alter_column("feature_gate_usage", "gate_key", new_column_name="feature_key")

    op.drop_column("feature_gates", "config")
    op.drop_column("feature_gates", "gate_type")

    op.alter_column("feature_gates", "required_plan", new_column_name="min_plan")
    op.alter_column("feature_gates", "gate_name", new_column_name="feature_name")
    op.alter_column("feature_gates", "gate_key", new_column_name="feature_key")

    op.create_index("idx_fg_usage_user_feature", "feature_gate_usage", ["user_id", "feature_key"])
