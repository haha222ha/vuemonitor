import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.operation_audit import OperationAuditLog
from sqlalchemy import text

logger = logging.getLogger(__name__)

SENSITIVE_ACTIONS = {
    "auth:login", "auth:logout", "auth:register", "auth:password_change",
    "data:export", "data:import", "data:delete",
    "monitor:rule_create", "monitor:rule_update", "monitor:rule_delete",
    "team:create", "team:member_add", "team:member_remove", "team:role_change",
    "settings:api_key_update", "settings:license_update",
    "gdpr:deletion_request", "gdpr:data_export",
    "admin:user_update", "admin:user_delete",
}


async def record_operation(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO operation_audit_log
                    (user_id, action, resource_type, resource_id, detail,
                     old_value, new_value, ip_address, user_agent)
                    VALUES
                    (:user_id, :action, :resource_type, :resource_id, :detail,
                     :old_value::jsonb, :new_value::jsonb, :ip_address, :user_agent)
                """),
                {
                    "user_id": str(user_id),
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "detail": detail,
                    "old_value": json.dumps(old_value) if old_value else None,
                    "new_value": json.dumps(new_value) if new_value else None,
                    "ip_address": ip_address,
                    "user_agent": (user_agent or "")[:500],
                },
            )
    except Exception as e:
        logger.error(f"Failed to record operation audit: {e}")

    if action in SENSITIVE_ACTIONS:
        logger.warning(
            "sensitive_operation",
            extra={
                "user_id": str(user_id),
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )
