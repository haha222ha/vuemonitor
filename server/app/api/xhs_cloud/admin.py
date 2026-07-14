# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.middleware.auth import AdminUser
from app.services.xhs_cloud_client import XhsCloudClient, XhsCloudNotConfigured, get_xhs_cloud_client

router = APIRouter(prefix="/xhs-cloud/admin", tags=["xhs-cloud-admin"])

_PLAN_CODE_PATTERN = (
    r"^(monthly|quarterly|halfyear|yearly|weekly|experience_3d|"
    r"experience|experience_insight|experience_ai|"
    r"insight_monthly|insight_pro_monthly)$"
)

_PLAN_DURATION = {
    "monthly": 30,
    "quarterly": 90,
    "halfyear": 183,
    "yearly": 365,
    "weekly": 7,
    "experience_3d": 3,
    "experience": 36500,
    "experience_insight": 7,
    "experience_ai": 7,
    "insight_monthly": 30,
    "insight_pro_monthly": 30,
}

# 在线支付同价套餐权益（月 39 / 季 99 / 半年 188 / 年 299）
_STANDARD_AI_ENTITLEMENTS: dict = {
    "insight_enabled": True,
    "insight_only": True,
    "insight_categories_per_day": 5,
    "insight_compare": True,
    "insight_timeline_days": 30,
    "insight_workflow": True,
    "insight_pdf_export": True,
    "insight_llm_tokens_per_day": 40_000,
    "advisor_read": True,
    "advisor_directions_per_day": 28,
    "advisor_history_days": 365,
    "advisor_chat_daily": 10,
    "legacy_zip_enabled": False,
}

_EXPERIENCE_3D_ENTITLEMENTS: dict = {
    "plan_code": "experience_3d",
    "insight_enabled": True,
    "insight_only": True,
    "insight_categories_per_day": 3,
    "insight_compare": False,
    "insight_timeline_days": 7,
    "insight_workflow": False,
    "insight_pdf_export": False,
    "insight_llm_tokens_per_day": 0,
    "advisor_read": True,
    "advisor_directions_per_day": 8,
    "advisor_history_days": 30,
    "advisor_chat_daily": 0,
    "legacy_zip_enabled": False,
}

_PLAN_ENTITLEMENTS: dict[str, dict] = {
    "experience_3d": dict(_EXPERIENCE_3D_ENTITLEMENTS),
    "insight_monthly": {
        **_STANDARD_AI_ENTITLEMENTS,
        "plan_code": "insight_monthly",
    },
    "insight_pro_monthly": {
        **_STANDARD_AI_ENTITLEMENTS,
        "plan_code": "insight_pro_monthly",
    },
}


def _build_note(entitlements: dict, remark: str = "") -> str:
    payload: dict = {"entitlements": entitlements}
    text = (remark or "").strip()
    if text and not text.startswith("{"):
        payload["remark"] = text
    return json.dumps(payload, ensure_ascii=False)


def _normalize_dates(dates: list[str]) -> list[str]:
    out: list[str] = []
    for raw in dates or []:
        d = str(raw).strip()[:10]
        if d and re.match(r"^\d{4}-\d{2}-\d{2}$", d) and d not in out:
            out.append(d)
    return out


class GenerateMemberCodesRequest(BaseModel):
    plan_code: str = Field(default="yearly", pattern=_PLAN_CODE_PATTERN)
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
    remark = (req.note or "").strip()
    plan_code = req.plan_code
    ui_plan = req.plan_code

    if req.plan_code in _PLAN_ENTITLEMENTS:
        ent = dict(_PLAN_ENTITLEMENTS[req.plan_code])
        plan_code = req.plan_code
        duration = req.duration_days or _PLAN_DURATION[req.plan_code]
        note = _build_note(ent, remark)
    elif req.plan_code in ("monthly", "quarterly", "halfyear", "yearly"):
        ent = dict(_STANDARD_AI_ENTITLEMENTS)
        ent["plan_code"] = req.plan_code
        plan_code = req.plan_code
        duration = req.duration_days or _PLAN_DURATION[req.plan_code]
        note = _build_note(ent, remark)
    elif req.plan_code in ("experience_ai", "experience_insight"):
        dates = _normalize_dates(req.allowed_report_dates)
        if not dates:
            raise HTTPException(status_code=400, detail="AI 体验码请至少选择一个可阅读的 report_date（YYYY-MM-DD）")
        ent = {
            "plan_code": "experience",
            "insight_enabled": True,
            "insight_only": True,
            "insight_categories_per_day": 1,
            "insight_compare": False,
            "insight_pdf_export": False,
            "insight_timeline_days": 7,
            "advisor_read": True,
            "advisor_directions_per_day": 3,
            "advisor_history_days": 7,
            "legacy_zip_enabled": False,
            "allowed_report_dates": dates,
        }
        plan_code = "experience"
        ui_plan = "experience_ai"
        duration = req.duration_days or _PLAN_DURATION["experience_ai"]
        note = _build_note(ent, remark)
    elif req.plan_code == "experience":
        # Legacy ZIP 体验（API 兼容；Admin UI 已下线）
        dates = _normalize_dates(req.allowed_report_dates)
        archive_types = [
            str(t).strip() for t in (req.allowed_archive_types or ["member_daily_zip"]) if str(t).strip()
        ]
        ent = {
            "allowed_report_dates": dates,
            "allowed_archive_types": archive_types or ["member_daily_zip"],
            "pc_full": True,
            "report_download_limited": True,
            "legacy_zip_enabled": True,
        }
        if not dates:
            raise HTTPException(status_code=400, detail="Legacy 体验码请至少选择一个报告日期")
        duration = req.duration_days or _PLAN_DURATION["experience"]
        note = _build_note(ent, remark)
    else:
        duration = req.duration_days or _PLAN_DURATION.get(req.plan_code, 30)
        note = remark

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
            "codes": [{"code": c, "plan_code": ui_plan, "duration_days": duration} for c in codes],
            "count": len(codes),
            "plan_code": ui_plan,
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


class MemberContactRequest(BaseModel):
    wechat_qr_url: str | None = Field(default=None, max_length=512)
    wechat_label: str | None = Field(default=None, max_length=64)
    contact_text: str | None = Field(default=None, max_length=256)
    float_icon_url: str | None = Field(default=None, max_length=512)


@router.get("/member-contact")
async def get_member_contact(
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.get_member_contact()
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.put("/member-contact")
async def save_member_contact(
    req: MemberContactRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    payload = req.model_dump(exclude_unset=True)
    try:
        result = await client.save_member_contact(payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.post("/member-contact/upload")
async def upload_member_contact_qr(
    admin: AdminUser,
    file: UploadFile = File(...),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片超过 5MB 限制")
    try:
        result = await client.upload_member_contact_qr(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "image/png",
        )
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


# ========== A/B 测试指标 ==========

class AbTestScoreRequest(BaseModel):
    test_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    ranking_key: str = Field(..., min_length=1, max_length=128)
    mode: str = Field(..., pattern=r"^[AB]$")
    accuracy_score: int | None = Field(default=None, ge=1, le=5)
    insight_score: int | None = Field(default=None, ge=1, le=5)
    hallucination: int | None = Field(default=None, ge=0, le=1)


@router.get("/ab-test/metrics")
async def get_ab_test_metrics(
    admin: AdminUser,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    ranking_key: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.get_ab_test_metrics(
            date_from=date_from,
            date_to=date_to,
            ranking_key=ranking_key,
            mode=mode,
            limit=limit,
        )
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.get("/ab-test/aggregate")
async def get_ab_test_aggregate(
    admin: AdminUser,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.get_ab_test_aggregate(date_from=date_from, date_to=date_to)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.get("/ab-test/dates")
async def list_ab_test_dates(
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.list_ab_test_dates()
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.put("/ab-test/score")
async def save_ab_test_score(
    req: AbTestScoreRequest,
    admin: AdminUser,
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    payload = req.model_dump(exclude_unset=True)
    try:
        result = await client.save_ab_test_score(payload)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}


@router.get("/ab-test/report")
async def get_ab_test_report(
    admin: AdminUser,
    report_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    mode: str = Query(..., pattern=r"^[AB]$"),
    client: XhsCloudClient = Depends(get_xhs_cloud_client),
):
    del admin
    try:
        result = await client.get_ab_test_report(report_date=report_date, mode=mode)
    except XhsCloudNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"code": 0, "data": result}
