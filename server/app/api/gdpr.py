import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.auth import CurrentUser
from app.models.user import User

router = APIRouter(prefix="/gdpr", tags=["GDPR合规"])

GDPR_TABLES = [
    ("products", "user_id"),
    ("product_features", "user_id"),
    ("monitor_rules", "user_id"),
    ("ai_analyses", "user_id"),
    ("ai_reports", "user_id"),
    ("notifications", "user_id"),
    ("sync_records", "user_id"),
    ("alert_rules", "user_id"),
    ("alert_events", "user_id"),
    ("team_members", "user_id"),
    ("scheduled_tasks", "user_id"),
]


@router.get("/data-summary")
async def get_data_summary(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    summary = {}
    for table_name, user_col in GDPR_TABLES:
        try:
            from sqlalchemy import text
            result = await db.execute(
                text(f"SELECT COUNT(*) FROM {table_name} WHERE {user_col} = :uid"),
                {"uid": str(user.id)},
            )
            count = result.scalar() or 0
            summary[table_name] = count
        except Exception:
            summary[table_name] = -1

    return {
        "code": 0,
        "data": {
            "user_id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else None,
            "tables": summary,
            "total_records": sum(v for v in summary.values() if v >= 0),
        },
    }


@router.post("/export")
async def export_user_data(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    format: str = Query("json", regex="^(json|csv)$"),
):
    from sqlalchemy import text

    exported = {}
    for table_name, user_col in GDPR_TABLES:
        try:
            result = await db.execute(
                text(f"SELECT * FROM {table_name} WHERE {user_col} = :uid"),
                {"uid": str(user.id)},
            )
            rows = result.mappings().all()
            exported[table_name] = [dict(row) for row in rows]
        except Exception:
            exported[table_name] = []

    user_data = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user.id),
        "email": user.email,
        "data": exported,
    }

    return {
        "code": 0,
        "data": user_data,
        "message": "数据导出成功，根据GDPR数据可携带性要求，您可以下载所有个人数据",
    }


@router.post("/deletion-request")
async def request_data_deletion(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    confirm_email: str = Query(..., description="需确认邮箱地址"),
):
    if confirm_email != user.email:
        raise BadRequestException(message="邮箱地址不匹配，请确认后重试")

    from sqlalchemy import text

    deleted_tables = {}
    for table_name, user_col in GDPR_TABLES:
        try:
            result = await db.execute(
                text(f"DELETE FROM {table_name} WHERE {user_col} = :uid"),
                {"uid": str(user.id)},
            )
            deleted_tables[table_name] = result.rowcount
        except Exception:
            deleted_tables[table_name] = -1

    user.is_active = False
    user.email = f"deleted_{user.id}@gdpr-anonymized.local"
    if hasattr(user, "hashed_password"):
        user.hashed_password = "GDPR_DELETED"
    if hasattr(user, "display_name"):
        user.display_name = "Deleted User"

    await db.commit()

    return {
        "code": 0,
        "data": {
            "deleted_tables": deleted_tables,
            "total_deleted": sum(v for v in deleted_tables.values() if v >= 0),
            "anonymized": True,
            "message": "根据GDPR被遗忘权要求，您的个人数据已被删除，账户已匿名化",
        },
    }


@router.post("/consent")
async def update_consent(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    data_collection: bool = True,
    analytics: bool = True,
    marketing: bool = False,
    third_party_sharing: bool = False,
):
    consent = {
        "data_collection": data_collection,
        "analytics": analytics,
        "marketing": marketing,
        "third_party_sharing": third_party_sharing,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
    }

    if hasattr(user, "preferences"):
        prefs = user.preferences or {}
        prefs["gdpr_consent"] = consent
        user.preferences = prefs
        await db.commit()

    return {
        "code": 0,
        "data": consent,
        "message": "同意偏好已更新",
    }


@router.get("/privacy-policy")
async def get_privacy_policy():
    return {
        "code": 0,
        "data": {
            "version": "1.0",
            "effective_date": "2025-01-01",
            "policy": {
                "data_controller": "VueMonitor",
                "data_types_collected": [
                    "账户信息（邮箱、用户名）",
                    "商品监控数据（URL、价格、销量）",
                    "使用数据（操作日志、功能使用统计）",
                    "设备信息（操作系统、浏览器类型）",
                ],
                "data_purposes": [
                    "提供商品监控和分析服务",
                    "改进产品功能和用户体验",
                    "发送服务通知和告警",
                ],
                "legal_basis": [
                    "合同履行（提供服务）",
                    "合法利益（改进服务）",
                    "明确同意（营销通信）",
                ],
                "user_rights": [
                    "访问权 - 查看您的个人数据",
                    "更正权 - 修改不准确的数据",
                    "删除权 - 请求删除您的数据",
                    "可携带权 - 导出您的数据",
                    "反对权 - 反对特定数据处理",
                    "限制处理权 - 限制数据处理方式",
                ],
                "data_retention": "数据在账户活跃期间保留，删除请求后30天内完成删除",
                "contact": "privacy@vuemonitor.com",
            },
        },
    }
