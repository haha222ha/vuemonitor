"""add composite indexes for query optimization

Revision ID: 009_composite_indexes
Revises: 008_fix_feature_gates_schema
Create Date: 2026-05-23
"""

from alembic import op

revision = "009_composite_indexes"
down_revision = "008_fix_feature_gates_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_metrics_product_snapshot ON product_metrics (product_id, snapshot_time DESC)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_collect_tasks_user_status ON collect_tasks (user_id, status)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_collect_task_items_task_status ON collect_task_items (task_id, status)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alert_events_user_unacked ON alert_events (user_id, is_acknowledged) WHERE is_acknowledged = false")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alert_events_user_created ON alert_events (user_id, created_at DESC)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_refresh_tokens_user_expires ON refresh_tokens (user_id, expires_at)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_security_audit_timestamp_risk ON security_audit_log (timestamp DESC, risk_score) WHERE risk_score >= 50")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_operation_audit_user_created ON operation_audit_log (user_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_product_metrics_product_snapshot")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_collect_tasks_user_status")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_collect_task_items_task_status")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_alert_events_user_unacked")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_alert_events_user_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_refresh_tokens_user_expires")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_security_audit_timestamp_risk")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_operation_audit_user_created")
