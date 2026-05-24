import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import AdminUser
from app.models.intelligence import IntelAuthCode, IntelMembership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["intel-admin"])


class GenerateCodesRequest(BaseModel):
    plan: str = Field(..., pattern="^(weekly|monthly|yearly)$")
    duration_days: int = Field(default=0, ge=0, le=3650)
    count: int = Field(default=1, ge=1, le=100)
    max_activations: int = Field(default=1, ge=1)
    note: str | None = None
    batch_id: str | None = None


class CodeListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    plan: str | None = None
    status: str | None = None
    batch_id: str | None = None


def _generate_code() -> str:
    segments = [secrets.token_hex(3).upper() for _ in range(4)]
    return "-".join(segments)


_INTEL_PLAN_DURATION = {"weekly": 7, "monthly": 30, "yearly": 365}


@router.post("/codes/generate")
async def generate_intel_codes(
    req: GenerateCodesRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    batch_id = req.batch_id or secrets.token_hex(4)
    duration = req.duration_days or _INTEL_PLAN_DURATION.get(req.plan, 30)
    codes = []

    for _ in range(req.count):
        code = _generate_code()
        auth_code = IntelAuthCode(
            code=code,
            plan=req.plan,
            duration_days=duration,
            max_activations=req.max_activations,
            batch_id=batch_id,
            note=req.note,
            created_by=admin.id,
        )
        db.add(auth_code)
        await db.flush()
        codes.append({
            "id": str(auth_code.id),
            "code": code,
            "plan": req.plan,
            "duration_days": duration,
            "batch_id": batch_id,
        })

    return {
        "batch_id": batch_id,
        "count": len(codes),
        "codes": codes,
    }


@router.get("/codes")
async def list_intel_codes(
    admin: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    plan: str | None = Query(None),
    status: str | None = Query(None),
    batch_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntelAuthCode)
    count_stmt = select(func.count(IntelAuthCode.id))

    if plan:
        stmt = stmt.where(IntelAuthCode.plan == plan)
        count_stmt = count_stmt.where(IntelAuthCode.plan == plan)
    if status:
        stmt = stmt.where(IntelAuthCode.status == status)
        count_stmt = count_stmt.where(IntelAuthCode.status == status)
    if batch_id:
        stmt = stmt.where(IntelAuthCode.batch_id == batch_id)
        count_stmt = count_stmt.where(IntelAuthCode.batch_id == batch_id)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.order_by(IntelAuthCode.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    codes = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(c.id), "code": c.code, "plan": c.plan,
                "duration_days": c.duration_days,
                "max_activations": c.max_activations,
                "current_activations": c.current_activations,
                "status": c.status, "batch_id": c.batch_id,
                "note": c.note,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "activated_at": c.activated_at.isoformat() if c.activated_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            }
            for c in codes
        ],
    }


@router.post("/codes/{code_id}/revoke")
async def revoke_intel_code(
    code_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntelAuthCode).where(IntelAuthCode.id == code_id)
    )
    auth_code = result.scalar_one_or_none()
    if not auth_code:
        raise HTTPException(status_code=404, detail="not found")
    if auth_code.status == "revoked":
        raise HTTPException(status_code=400, detail="already revoked")

    auth_code.status = "revoked"
    auth_code.revoked_at = datetime.now(UTC)

    memberships_result = await db.execute(
        select(IntelMembership).where(
            IntelMembership.auth_code_id == auth_code.id,
            IntelMembership.status == "active",
        )
    )
    for m in memberships_result.scalars():
        m.status = "revoked"

    await db.flush()

    return {"status": "revoked", "code_id": code_id}


@router.get("/memberships")
async def list_intel_memberships(
    admin: AdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    plan: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntelMembership)
    count_stmt = select(func.count(IntelMembership.id))

    if plan:
        stmt = stmt.where(IntelMembership.plan == plan)
        count_stmt = count_stmt.where(IntelMembership.plan == plan)
    if status:
        stmt = stmt.where(IntelMembership.status == status)
        count_stmt = count_stmt.where(IntelMembership.status == status)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.order_by(IntelMembership.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    members = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(m.id), "user_id": str(m.user_id),
                "plan": m.plan, "status": m.status,
                "started_at": m.started_at.isoformat() if m.started_at else None,
                "expires_at": m.expires_at.isoformat() if m.expires_at else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ],
    }


@router.get("/stats")
async def intel_stats(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    codes_total = await db.execute(select(func.count(IntelAuthCode.id)))
    codes_used = await db.execute(
        select(func.count(IntelAuthCode.id)).where(IntelAuthCode.status == "active")
    )
    codes_unused = await db.execute(
        select(func.count(IntelAuthCode.id)).where(IntelAuthCode.status == "unused")
    )

    members_active = await db.execute(
        select(func.count(IntelMembership.id)).where(IntelMembership.status == "active")
    )

    plan_counts = {}
    plans = ["weekly", "monthly", "yearly"]
    for p in plans:
        result = await db.execute(
            select(func.count(IntelMembership.id)).where(
                IntelMembership.plan == p,
                IntelMembership.status == "active",
            )
        )
        plan_counts[p] = result.scalar() or 0

    return {
        "total_codes": codes_total.scalar() or 0,
        "used_codes": codes_used.scalar() or 0,
        "unused_codes": codes_unused.scalar() or 0,
        "active_members": members_active.scalar() or 0,
        "active_by_plan": plan_counts,
    }