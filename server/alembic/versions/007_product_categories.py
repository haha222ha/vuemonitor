"""add product_categories table

Revision ID: 007_product_categories
Revises: 006_aipic_tables
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007_product_categories"
down_revision = "006_aipic_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_product_categories_user_id", "product_categories", ["user_id"])

    op.add_column("products", sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True))
    op.create_index("idx_products_category_id", "products", ["category_id"])


def downgrade() -> None:
    op.drop_index("idx_products_category_id", "products")
    op.drop_column("products", "category_id")
    op.drop_index("idx_product_categories_user_id", "product_categories")
    op.drop_table("product_categories")
