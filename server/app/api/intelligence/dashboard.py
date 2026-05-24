from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import (
    IntelligenceOpportunity,
    IntelligencePlatformSignal,
    IntelligenceRisk,
    IntelligenceTrend,
    IntelligenceUserEmotion,
    IntelligenceXhsTopic,
)

router = APIRouter(prefix="/dashboard", tags=["intel-dashboard"])

PLAN_LIMITS = {
    "free": {"top_trends": 3, "top_opps": 0, "top_risks": 0},
    "weekly": {"top_trends": 5, "top_opps": 3, "top_risks": 3},
    "monthly": {"top_trends": 0, "top_opps": 0, "top_risks": 0},
    "yearly": {"top_trends": 0, "top_opps": 0, "top_risks": 0},
    "enterprise": {"top_trends": 0, "top_opps": 0, "top_risks": 0},
}


@router.get("")
async def get_dashboard(
    plan: str = Depends(get_intel_plan),
    db: AsyncSession = Depends(get_db),
):
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    trends_result = await db.execute(
        select(IntelligenceTrend).where(
            IntelligenceTrend.trend_status == "active"
        ).order_by(IntelligenceTrend.opportunity_score.desc())
    )
    all_trends = trends_result.scalars().all()

    opps_result = await db.execute(
        select(IntelligenceOpportunity).where(
            IntelligenceOpportunity.status == "active",
            IntelligenceOpportunity.verdict == "RECOMMENDED",
        ).order_by(IntelligenceOpportunity.verdict_score.desc())
    )
    all_opps = opps_result.scalars().all()

    risks_result = await db.execute(
        select(IntelligenceRisk).where(
            IntelligenceRisk.status.in_(["active", "monitoring"])
        ).order_by(IntelligenceRisk.severity.desc())
    )
    all_risks = risks_result.scalars().all()

    limit_trends = limits["top_trends"]
    limit_opps = limits["top_opps"]
    limit_risks = limits["top_risks"]

    trend_count = await db.execute(
        select(func.count(IntelligenceTrend.id)).where(IntelligenceTrend.trend_status == "active")
    )
    opp_count = await db.execute(
        select(func.count(IntelligenceOpportunity.id)).where(IntelligenceOpportunity.verdict == "RECOMMENDED")
    )
    risk_count = await db.execute(
        select(func.count(IntelligenceRisk.id)).where(IntelligenceRisk.status.in_(["active", "monitoring"]))
    )

    def trend_to_dict(t):
        return {
            "id": str(t.id), "title": t.title, "category": t.category,
            "platform": t.platform, "opportunity_score": t.opportunity_score,
            "lifecycle": t.lifecycle, "direction": t.direction,
            "risk_level": t.risk_level, "user_emotion": t.user_emotion,
        }

    def opp_to_dict(o):
        return {
            "id": str(o.id), "name": o.name, "category": o.category,
            "verdict_score": o.verdict_score, "difficulty": o.difficulty,
            "startup_cost": o.startup_cost, "monthly_ceiling": o.monthly_ceiling,
            "persona_fit": o.persona_fit, "commercial_paths": o.commercial_paths,
        }

    def risk_to_dict(r):
        return {
            "id": str(r.id), "name": r.name, "severity": r.severity,
            "status": r.status, "reason": r.reason,
            "alternative": r.alternative, "risk_type": r.risk_type,
        }

    return {
        "plan": plan,
        "summary": {
            "active_trends": trend_count.scalar() or 0,
            "recommended_opportunities": opp_count.scalar() or 0,
            "active_risks": risk_count.scalar() or 0,
        },
        "top_trends": [trend_to_dict(t) for t in all_trends[:limit_trends]] if limit_trends > 0 else [trend_to_dict(t) for t in all_trends],
        "top_opportunities": [opp_to_dict(o) for o in all_opps[:limit_opps]] if limit_opps > 0 else [opp_to_dict(o) for o in all_opps],
        "top_risks": [risk_to_dict(r) for r in all_risks[:limit_risks]] if limit_risks > 0 else [risk_to_dict(r) for r in all_risks],
    }