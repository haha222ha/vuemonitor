# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.middleware.auth import AdminUser
from app.services.xhs_cloud_client import XhsCloudClient, XhsCloudNotConfigured, get_xhs_cloud_client

router = APIRouter(prefix="/xhs-cloud/admin", tags=["xhs-cloud-admin"])

_PLAN_DURATION = {"weekly": 7, "monthly": 30, "yearly": 365}


class GenerateMemberCodesRequest(BaseModel):
    plan_code: str = Field(default="monthly", pattern="^(weekly|monthly|yearly)$")
    duration_days: int = Field(default=0, ge=0, le=3650)
    count: int = Field(default=1, ge=1, le=100)
    max_activations: int = Field(default=1, ge=1, le=100)
    note: str = ""


@router.get("/status")
async def member_cloud_status(
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    portal_url = client.member_portal_url
    if not portal_url and client.base_url:
        portal_url = f"{client.base_url}/member"

    if not client.is_configured:
        return {
            "code": 0,
            "data": {
                "configured": False,
                "online": False,
                "member_portal_url": portal_url or "",
                "message": "请在 server/.env 配置 XHS_CLOUD_API_URL 和 XHS_CLOUD_SYNC_KEY（与 /opt/xhs-cloud/.env 一致）",
            },
        }

    health = await client.health()
    online = health.get("status") == "ok"
    stats = {}
    error = None
    if online:
        try:
            stats = await client.stats()
        except HTTPException as e:
            error = e.detail
        except Exception as e:
            error = str(e)

    return {
        "code": 0,
        "data": {
            "configured": True,
            "online": online,
            "health": health,
            "stats": stats,
            "member_portal_url": portal_url or "",
            "error": error,
        },
    }


@router.get("/codes")
async def list_member_codes(
    admin: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.list_codes(limit=limit, status=status)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    items = result.get("items") or []
    return {"code": 0, "data": {"items": items, "total": len(items)}}


@router.post("/codes/generate")
async def generate_member_codes(
    req: GenerateMemberCodesRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    duration = req.duration_days or _PLAN_DURATION.get(req.plan_code, 30)
    payload = {
        "count": req.count,
        "plan_code": req.plan_code,
        "duration_days": duration,
        "max_activations": req.max_activations,
        "note": req.note,
    }
    try:
        result = await client.generate_codes(payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    codes = result.get("codes") or []
    return {
        "code": 0,
        "data": {
            "codes": [{"code": c, "plan_code": req.plan_code, "duration_days": duration} for c in codes],
            "count": len(codes),
            "plan_code": req.plan_code,
            "duration_days": duration,
        },
    }
