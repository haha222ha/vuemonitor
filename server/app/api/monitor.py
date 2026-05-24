import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.middleware.auth import CurrentUser
from app.models.monitor import MonitorRule, Notification
from app.models.product import Product, ProductFeature
from app.services.operation_audit import record_operation

router = APIRouter(prefix="/monitor", tags=["monitor"])


class RuleCreateRequest(BaseModel):
    product_id: str
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., pattern="^(price_drop|sales_surge|stock_change|rating_drop|custom)$")
    conditions: dict


class RuleUpdateRequest(BaseModel):
    rule_name: str | None = None
    conditions: dict | None = None
    is_active: bool | None = None


@router.post("/rules", status_code=201)
async def create_rule(
    req: RuleCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    rule = MonitorRule(
        user_id=user.id,
        product_id=uuid.UUID(req.product_id),
        rule_name=req.rule_name,
        rule_type=req.rule_type,
        conditions=req.conditions,
    )
    db.add(rule)
    await db.flush()

    await record_operation(
        user_id=str(user.id),
        action="monitor:rule_create",
        resource_type="monitor_rule",
        resource_id=str(rule.id),
        detail=f"type={req.rule_type}, name={req.rule_name[:30]}",
    )

    return {"code": 0, "data": {"id": str(rule.id)}}


@router.get("/rules")
async def list_rules(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    product_id: str | None = None,
    is_active: bool | None = None,
):
    query = select(MonitorRule).where(MonitorRule.user_id == user.id)
    if product_id:
        query = query.where(MonitorRule.product_id == uuid.UUID(product_id))
    if is_active is not None:
        query = query.where(MonitorRule.is_active == is_active)

    result = await db.execute(query.order_by(MonitorRule.created_at.desc()))
    rules = result.scalars().all()

    return {
        "code": 0,
        "data": [
            {
                "id": str(r.id),
                "product_id": str(r.product_id),
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "conditions": r.conditions,
                "is_active": r.is_active,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                "trigger_count": r.trigger_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
    }


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    req: RuleUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorRule).where(MonitorRule.id == uuid.UUID(rule_id), MonitorRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="规则不存在")

    if req.rule_name is not None:
        rule.rule_name = req.rule_name
    if req.conditions is not None:
        rule.conditions = req.conditions
    if req.is_active is not None:
        rule.is_active = req.is_active

    await record_operation(
        user_id=str(user.id),
        action="monitor:rule_update",
        resource_type="monitor_rule",
        resource_id=rule_id,
    )

    return {"code": 0, "data": {"updated": True}}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorRule).where(MonitorRule.id == uuid.UUID(rule_id), MonitorRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="规则不存在")

    await db.delete(rule)

    await record_operation(
        user_id=str(user.id),
        action="monitor:rule_delete",
        resource_type="monitor_rule",
        resource_id=rule_id,
    )
    return {"code": 0, "data": {"deleted": True}}


@router.get("/notifications")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    is_read: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Notification).where(Notification.user_id == user.id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    notifications = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "is_read": n.is_read,
                    "related_id": str(n.related_id) if n.related_id else None,
                    "related_type": n.related_type,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ],
        },
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == uuid.UUID(notification_id), Notification.user_id == user.id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException(message="通知不存在")

    notification.is_read = True
    return {"code": 0, "data": {"read": True}}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id, not Notification.is_read)
    )
    for n in result.scalars().all():
        n.is_read = True
    return {"code": 0, "data": {"read_all": True}}


@router.get("/auto-detect")
async def auto_detect_anomalies(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30),
    threshold: float = Query(2.0, ge=1.0, le=5.0, description="标准差倍数阈值"),
):
    since = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(Product).where(Product.user_id == user.id, Product.is_active)
    )
    products = result.scalars().all()

    anomalies = []
    features_by_product: dict[uuid.UUID, list[ProductFeature]] = defaultdict(list)
    if products:
        product_ids = [p.id for p in products]
        all_features_result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id.in_(product_ids), ProductFeature.collected_at >= since)
            .order_by(ProductFeature.product_id, ProductFeature.collected_at.asc())
        )
        for f in all_features_result.scalars():
            features_by_product[f.product_id].append(f)

    for p in products:
        features = features_by_product.get(p.id, [])
        if len(features) < 3:
            continue

        prices = [float(f.price) for f in features if f.price is not None]
        sales = [f.sales_count for f in features if f.sales_count is not None]

        latest = features[-1]

        if len(prices) >= 3:
            avg_p = sum(prices[:-1]) / len(prices[:-1])
            std_p = (sum((x - avg_p) ** 2 for x in prices[:-1]) / len(prices[:-1])) ** 0.5
            if std_p > 0 and prices[-1] is not None:
                z_score = abs(prices[-1] - avg_p) / std_p
                if z_score > threshold:
                    direction = "spike" if prices[-1] > avg_p else "drop"
                    anomalies.append({
                        "product_id": str(p.id),
                        "product_name": p.product_name,
                        "platform": p.platform,
                        "anomaly_type": f"price_{direction}",
                        "metric": "price",
                        "current_value": prices[-1],
                        "average_value": round(avg_p, 2),
                        "z_score": round(z_score, 2),
                        "detected_at": latest.collected_at.isoformat() if latest.collected_at else None,
                    })

        if len(sales) >= 3:
            avg_s = sum(sales[:-1]) / len(sales[:-1])
            std_s = (sum((x - avg_s) ** 2 for x in sales[:-1]) / len(sales[:-1])) ** 0.5
            if std_s > 0 and sales[-1] is not None:
                z_score = abs(sales[-1] - avg_s) / std_s
                if z_score > threshold:
                    direction = "surge" if sales[-1] > avg_s else "drop"
                    anomalies.append({
                        "product_id": str(p.id),
                        "product_name": p.product_name,
                        "platform": p.platform,
                        "anomaly_type": f"sales_{direction}",
                        "metric": "sales_count",
                        "current_value": sales[-1],
                        "average_value": round(avg_s, 1),
                        "z_score": round(z_score, 2),
                        "detected_at": latest.collected_at.isoformat() if latest.collected_at else None,
                    })

    anomalies.sort(key=lambda a: a["z_score"], reverse=True)

    summary = {
        "total_anomalies": len(anomalies),
        "price_anomalies": sum(1 for a in anomalies if a["metric"] == "price"),
        "sales_anomalies": sum(1 for a in anomalies if a["metric"] == "sales_count"),
        "products_affected": len(set(a["product_id"] for a in anomalies)),
        "threshold": threshold,
        "days": days,
    }

    return {"code": 0, "data": {"anomalies": anomalies, "summary": summary}}
