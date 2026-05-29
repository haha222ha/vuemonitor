"""extend products.platform_product_id to 255 chars

Revision ID: 011_platform_pid_255
Revises: 010_intelligence_tables
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "011_platform_pid_255"
down_revision = "010_intelligence_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "platform_product_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "platform_product_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
