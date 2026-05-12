"""license enhancement - add revoke/change_log fields

Revision ID: 003_license_enhance
Revises: 002_team_tables
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_license_enhance"
down_revision = "002_team_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("license_codes", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("license_codes", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("license_codes", sa.Column("revoked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("license_codes", sa.Column("revoke_reason", sa.Text(), nullable=True))

    op.add_column("license_activations", sa.Column("device_name", sa.String(128), nullable=True))
    op.add_column("license_activations", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("license_activations", sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "license_change_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("license_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("license_codes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("license_change_logs")

    op.drop_column("license_activations", "last_heartbeat")
    op.drop_column("license_activations", "ip_address")
    op.drop_column("license_activations", "device_name")

    op.drop_column("license_codes", "revoke_reason")
    op.drop_column("license_codes", "revoked_by")
    op.drop_column("license_codes", "revoked_at")
    op.drop_column("license_codes", "note")
