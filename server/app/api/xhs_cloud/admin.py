# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.middleware.auth import AdminUser
from app.services.xhs_cloud_client import XhsCloudClient, XhsCloudNotConfigured, get_xhs_cloud_client

router = APIRouter(prefix="/xhs-cloud/admin", tags=["xhs-cloud-admin"])

_PLAN_DURATION = {
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
    "experience": 36500,
    "experience_insight": 7,
}


class GenerateMemberCodesRequest(BaseModel):
    plan_code: str = Field(
        default="monthly",
        pattern="^(weekly|monthly|yearly|experience|experience_insight)$",
    )
    duration_days: int = Field(default=0, ge=0, le=36500)
    count: int = Field(default=1, ge=1, le=100)
    max_activations: int = Field(default=1, ge=1, le=100)
    note: str = ""
    allowed_report_dates: list[str] = Field(default_factory=list)
    allowed_archive_types: list[str] = Field(default_factory=list)


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
    note = (req.note or "").strip()
    plan_code = req.plan_code
    if req.plan_code == "experience":
        import json

        dates = [str(d).strip()[:10] for d in (req.allowed_report_dates or []) if str(d).strip()]
        archive_types = [
            str(t).strip() for t in (req.allowed_archive_types or ["member_daily_zip"]) if str(t).strip()
        ]
        entitlements = {
            "allowed_report_dates": dates,
            "allowed_archive_types": archive_types or ["member_daily_zip"],
            "pc_full": True,
            "report_download_limited": True,
        }
        note = json.dumps({"entitlements": entitlements}, ensure_ascii=False)
        if not dates:
            raise HTTPException(status_code=400, detail="体验会员请至少选择一个可下载的报告日期")
        duration = req.duration_days or _PLAN_DURATION["experience"]
    elif req.plan_code == "experience_insight":
        import json

        entitlements = {
            "plan_code": "experience",
            "insight_enabled": True,
            "insight_only": True,
            "insight_categories_per_day": 1,
            "insight_compare": False,
            "insight_pdf_export": False,
            "insight_timeline_days": 7,
            "legacy_zip_enabled": False,
        }
        note = json.dumps({"entitlements": entitlements}, ensure_ascii=False)
        plan_code = "experience"
        duration = req.duration_days or _PLAN_DURATION["experience_insight"]
    else:
        duration = req.duration_days or _PLAN_DURATION.get(req.plan_code, 30)
    payload = {
        "count": req.count,
        "plan_code": plan_code,
        "duration_days": duration,
        "max_activations": req.max_activations,
        "note": note,
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


@router.post("/codes/{code}/revoke")
async def revoke_member_code(
    code: str,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.revoke_code(code)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


class InsightLlmConfigRequest(BaseModel):
    enabled: bool | None = None
    provider: str | None = Field(default=None, max_length=32)
    base_url: str | None = Field(default=None, max_length=256)
    model: str | None = Field(default=None, max_length=64)
    api_key: str | None = Field(default=None, max_length=512)
    thinking_disabled: bool | None = None
    budget_tokens_per_day: int | None = Field(default=None, ge=1000, le=10_000_000)


@router.get("/insight-llm-config")
async def get_insight_llm_config(
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.get_insight_llm_config()
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.put("/insight-llm-config")
async def save_insight_llm_config(
    req: InsightLlmConfigRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    payload = req.model_dump(exclude_unset=True)
    try:
        result = await client.save_insight_llm_config(payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.post("/insight-llm-config/test")
async def test_insight_llm_config(
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.test_insight_llm_config()
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}



class MemberFeedbackUpdateRequest(BaseModel):
    status: str | None = Field(default=None, max_length=16)
    admin_note: str | None = Field(default=None, max_length=2000)


@router.get("/member-feedback")
async def list_member_feedback_admin(
    admin: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.list_member_feedback(limit=limit, status=status)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    items = result.get("items") or []
    return {"code": 0, "data": {"items": items, "total": len(items)}}


@router.patch("/member-feedback/{item_id}")
async def update_member_feedback_admin(
    item_id: int,
    req: MemberFeedbackUpdateRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    payload = req.model_dump(exclude_unset=True)
    try:
        result = await client.update_member_feedback(item_id, payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.get("/member-keyword-requests")
async def list_member_keyword_requests_admin(
    admin: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.list_member_keyword_requests(limit=limit, status=status)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    items = result.get("items") or []
    return {"code": 0, "data": {"items": items, "total": len(items)}}


@router.patch("/member-keyword-requests/{item_id}")
async def update_member_keyword_request_admin(
    item_id: int,
    req: MemberFeedbackUpdateRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    payload = req.model_dump(exclude_unset=True)
    try:
        result = await client.update_member_keyword_request(item_id, payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}
