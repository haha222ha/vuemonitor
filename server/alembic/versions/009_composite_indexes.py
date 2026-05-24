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
    op.create_index("idx_product_metrics_product_snapshot", "product_metrics", ["product_id", "snapshot_time DESC"], if_not_exists=True)
    op.create_index("idx_collect_tasks_user_status", "collect_tasks", ["user_id", "status"], if_not_exists=True)
    op.create_index("idx_collect_task_items_task_status", "collect_task_items", ["task_id", "status"], if_not_exists=True)
    op.create_index("idx_alert_events_user_unacked", "alert_events", ["user_id", "is_acknowledged"], if_not_exists=True, postgresql_where="is_acknowledged = false")
    op.create_index("idx_alert_events_user_created", "alert_events", ["user_id", "created_at DESC"], if_not_exists=True)
    op.create_index("idx_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"], if_not_exists=True)
    op.create_index("idx_security_audit_timestamp_risk", "security_audit_log", ["timestamp DESC", "risk_score"], if_not_exists=True, postgresql_where="risk_score >= 50")
    op.create_index("idx_operation_audit_user_created", "operation_audit_log", ["user_id", "created_at DESC"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_product_metrics_product_snapshot", table_name="product_metrics", if_exists=True)
    op.drop_index("idx_collect_tasks_user_status", table_name="collect_tasks", if_exists=True)
    op.drop_index("idx_collect_task_items_task_status", table_name="collect_task_items", if_exists=True)
    op.drop_index("idx_alert_events_user_unacked", table_name="alert_events", if_exists=True)
    op.drop_index("idx_alert_events_user_created", table_name="alert_events", if_exists=True)
    op.drop_index("idx_refresh_tokens_user_expires", table_name="refresh_tokens", if_exists=True)
    op.drop_index("idx_security_audit_timestamp_risk", table_name="security_audit_log", if_exists=True)
    op.drop_index("idx_operation_audit_user_created", table_name="operation_audit_log", if_exists=True)
