import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.auth import CurrentUser
from app.models.alert_rule import AlertRule, AlertEvent
from app.services.alert_rule_engine import alert_rule_engine, SUPPORTED_METRICS, SUPPORTED_OPERATORS, SEVERITY_LEVELS

router = APIRouter(prefix="/alert-rules", tags=["告警规则"])


@router.get("")
async def list_alert_rules(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    is_active: bool | None = None,
):
    query = select(AlertRule).where(AlertRule.user_id == user.id)
    if is_active is not None:
        query = query.where(AlertRule.is_active == is_active)
    query = query.order_by(AlertRule.created_at.desc())
    result = await db.execute(query)
    rules = result.scalars().all()

    return {
        "code": 0,
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "rule_type": r.rule_type,
                "metric": r.metric,
                "operator": r.operator,
                "threshold": r.threshold,
                "window_minutes": r.window_minutes,
                "cooldown_minutes": r.cooldown_minutes,
                "severity": r.severity,
                "channels": r.channels,
                "filters": r.filters,
                "is_active": r.is_active,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                "trigger_count": r.trigger_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
    }


@router.post("")
async def create_alert_rule(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    name: str = Query(..., max_length=200),
    rule_type: str = Query(..., max_length=30),
    metric: str = Query(..., max_length=50),
    operator: str = Query(..., max_length=10),
    threshold: float = Query(...),
    window_minutes: int = Query(5, ge=1, le=1440),
    cooldown_minutes: int = Query(30, ge=1, le=1440),
    severity: str = Query("warning"),
    channels: dict | None = None,
    filters: dict | None = None,
):
    if metric not in SUPPORTED_METRICS:
        raise BadRequestException(message=f"不支持的指标: {metric}，支持: {list(SUPPORTED_METRICS.keys())}")
    if operator not in SUPPORTED_OPERATORS:
        raise BadRequestException(message=f"不支持的操作符: {operator}，支持: {list(SUPPORTED_OPERATORS.keys())}")
    if severity not in SEVERITY_LEVELS:
        raise BadRequestException(message=f"不支持的严重级别: {severity}，支持: {SEVERITY_LEVELS}")

    rule = AlertRule(
        user_id=user.id,
        name=name,
        rule_type=rule_type,
        metric=metric,
        operator=operator,
        threshold=threshold,
        window_minutes=window_minutes,
        cooldown_minutes=cooldown_minutes,
        severity=severity,
        channels=channels or {},
        filters=filters,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return {"code": 0, "data": {"id": str(rule.id), "name": rule.name}}


@router.get("/metrics")
async def get_supported_metrics():
    return {"code": 0, "data": SUPPORTED_METRICS}


@router.get("/operators")
async def get_supported_operators():
    return {"code": 0, "data": {k: {"label": k} for k in SUPPORTED_OPERATORS.keys()}}


@router.get("/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == uuid.UUID(rule_id), AlertRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="告警规则不存在")

    return {
        "code": 0,
        "data": {
            "id": str(rule.id),
            "name": rule.name,
            "rule_type": rule.rule_type,
            "metric": rule.metric,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "window_minutes": rule.window_minutes,
            "cooldown_minutes": rule.cooldown_minutes,
            "severity": rule.severity,
            "channels": rule.channels,
            "filters": rule.filters,
            "is_active": rule.is_active,
            "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
            "trigger_count": rule.trigger_count,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        },
    }


@router.put("/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    name: str | None = None,
    metric: str | None = None,
    operator: str | None = None,
    threshold: float | None = None,
    window_minutes: int | None = None,
    cooldown_minutes: int | None = None,
    severity: str | None = None,
    channels: dict | None = None,
    filters: dict | None = None,
    is_active: bool | None = None,
):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == uuid.UUID(rule_id), AlertRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="告警规则不存在")

    if metric is not None:
        if metric not in SUPPORTED_METRICS:
            raise BadRequestException(message=f"不支持的指标: {metric}")
        rule.metric = metric
    if operator is not None:
        if operator not in SUPPORTED_OPERATORS:
            raise BadRequestException(message=f"不支持的操作符: {operator}")
        rule.operator = operator
    if threshold is not None:
        rule.threshold = threshold
    if name is not None:
        rule.name = name
    if window_minutes is not None:
        rule.window_minutes = window_minutes
    if cooldown_minutes is not None:
        rule.cooldown_minutes = cooldown_minutes
    if severity is not None:
        if severity not in SEVERITY_LEVELS:
            raise BadRequestException(message=f"不支持的严重级别: {severity}")
        rule.severity = severity
    if channels is not None:
        rule.channels = channels
    if filters is not None:
        rule.filters = filters
    if is_active is not None:
        rule.is_active = is_active

    await db.commit()

    return {"code": 0, "data": {"id": str(rule.id), "updated": True}}


@router.delete("/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == uuid.UUID(rule_id), AlertRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="告警规则不存在")

    await db.delete(rule)
    await db.commit()

    return {"code": 0, "data": {"deleted": True}}


@router.post("/{rule_id}/evaluate")
async def evaluate_alert_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == uuid.UUID(rule_id), AlertRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="告警规则不存在")

    event = await alert_rule_engine.evaluate_rule(rule, db)
    if event:
        return {
            "code": 0,
            "data": {
                "triggered": True,
                "event_id": str(event.id),
                "severity": event.severity,
                "title": event.title,
                "detail": event.detail,
                "metric_value": event.metric_value,
                "threshold_value": event.threshold_value,
            },
        }
    return {"code": 0, "data": {"triggered": False}}


@router.get("/events/all")
async def list_alert_events(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    severity: str | None = None,
    acknowledged: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    events = await alert_rule_engine.get_events(
        user.id, db, severity=severity, acknowledged=acknowledged, limit=limit
    )
    return {
        "code": 0,
        "data": [
            {
                "id": str(e.id),
                "rule_id": str(e.rule_id),
                "severity": e.severity,
                "title": e.title,
                "detail": e.detail,
                "metric_value": e.metric_value,
                "threshold_value": e.threshold_value,
                "context": e.context,
                "is_acknowledged": e.is_acknowledged,
                "acknowledged_at": e.acknowledged_at.isoformat() if e.acknowledged_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_alert_event(
    event_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    success = await alert_rule_engine.acknowledge_event(uuid.UUID(event_id), user.id, db)
    if not success:
        raise NotFoundException(message="告警事件不存在")
    return {"code": 0, "data": {"acknowledged": True}}


@router.get("/stats/summary")
async def get_alert_stats(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    total_rules = await db.execute(
        select(func.count()).select_from(AlertRule).where(AlertRule.user_id == user.id)
    )
    active_rules = await db.execute(
        select(func.count()).select_from(AlertRule).where(
            AlertRule.user_id == user.id, AlertRule.is_active == True
        )
    )
    recent_events = await db.execute(
        select(func.count()).select_from(AlertEvent).where(AlertEvent.user_id == user.id)
    )
    unack_events = await db.execute(
        select(func.count()).select_from(AlertEvent).where(
            AlertEvent.user_id == user.id, AlertEvent.is_acknowledged == False
        )
    )

    return {
        "code": 0,
        "data": {
            "total_rules": total_rules.scalar() or 0,
            "active_rules": active_rules.scalar() or 0,
            "total_events": recent_events.scalar() or 0,
            "unacknowledged_events": unack_events.scalar() or 0,
        },
    }
