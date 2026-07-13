# -*- coding: utf-8 -*-
"""会员 AI 选品顾问 API — 只读阅读。"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.auth import current_user
from cloud_deploy.cloud_api.member_entitlements import (
    assert_advisor_allowed,
    enrich_member_profile,
    resolve_entitlements,
)

router = APIRouter(prefix="/api/v1/member/advisor", tags=["advisor"])
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _advisor_root() -> str:
    root = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
    sub = os.environ.get("XHS_ADVISOR_PUBLISH_DIR", "data/advisor_published")
    return os.path.join(root, sub)


def _load_public_advice(report_date: str) -> dict:
    path = os.path.join(_advisor_root(), report_date, "advice.json")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="当日 AI 报告尚未发布")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data.pop("rankings", None)
        data.pop("context", None)
    return data


def _list_advisor_dates() -> list[str]:
    base = _advisor_root()
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base), reverse=True):
        if not _DATE_RE.match(name):
            continue
        if os.path.isfile(os.path.join(base, name, "advice.json")):
            out.append(name)
    return out


def _advisor_library_items() -> list[dict]:
    items = []
    for date in _list_advisor_dates():
        manifest = os.path.join(_advisor_root(), date, "report_manifest.json")
        summary = ""
        if os.path.isfile(manifest):
            try:
                meta = json.loads(open(manifest, encoding="utf-8").read())
                summary = str(meta.get("summary") or "")
            except (OSError, json.JSONDecodeError):
                pass
        items.append({
            "report_date": date,
            "summary": summary,
            "archive_type": "member_ai_advisor_zip",
        })
    return items


def _insight_today_items(user_id: int) -> list[dict]:
    from cloud_deploy.cloud_api.insight_routes import _list_items_from_disk
    from cloud_deploy.cloud_api.entitlements_v2 import filter_insight_library

    items = _list_items_from_disk()
    ent = resolve_entitlements(user_id, db.get_member_profile(user_id))
    items = filter_insight_library(items, ent)
    if not items:
        return []
    dates = sorted({str(it.get("report_date") or "")[:10] for it in items}, reverse=True)
    latest = dates[0]
    return [it for it in items if str(it.get("report_date") or "")[:10] == latest]


@router.get("/library")
def advisor_library(user: dict = Depends(current_user)):
    assert_advisor_allowed(user["id"])
    return {"items": _advisor_library_items()}


@router.get("/dashboard")
def advisor_dashboard(user: dict = Depends(current_user)):
    assert_advisor_allowed(user["id"])
    profile = db.get_member_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    enriched = enrich_member_profile(profile, user["id"]) or profile
    ent = enriched.get("entitlements") or {}

    dates = _list_advisor_dates()
    advisor_date = dates[0] if dates else ""
    overview = None
    directions: list[dict] = []
    status = "pending"

    if advisor_date:
        try:
            advice = _load_public_advice(advisor_date)
            status = "published"
            ov = advice.get("daily_overview") or {}
            overview = {
                "title": ov.get("title") or "今日市场观察",
                "summary": (ov.get("summary") or ov.get("content") or "")[:240],
                "read_url": f"/api/v1/member/advisor/{advisor_date}/articles/overview",
            }
            for block in advice.get("direction_advices") or []:
                if not isinstance(block, dict):
                    continue
                directions.append({
                    "key": block.get("key") or "",
                    "title": block.get("title") or block.get("key") or "维度解读",
                    "summary": (block.get("summary") or block.get("content") or "")[:200],
                })
        except HTTPException:
            status = "pending"

    insights = []
    for it in _insight_today_items(user["id"])[:20]:
        insights.append({
            "category": it.get("category") or "",
            "stars": it.get("stars") or 0,
            "report_date": str(it.get("report_date") or "")[:10],
            "summary": it.get("summary") or "",
        })

    report_date = advisor_date or (insights[0]["report_date"] if insights else "")
    archive_months = sorted({d[:7] for d in dates}, reverse=True)

    return {
        "membership": {
            "is_active": enriched.get("is_active"),
            "days_left": enriched.get("days_remaining"),
            "plan_label": enriched.get("plan_label") or enriched.get("plan_code"),
            "username": enriched.get("username"),
        },
        "entitlements": ent,
        "today": {
            "report_date": report_date,
            "status": status,
            "overview": overview,
            "directions": directions,
            "insights": insights,
        },
        "archive_hint": {
            "latest_month": archive_months[0] if archive_months else "",
            "total_days": len(dates),
            "advisor_dates": dates[:30],
        },
    }


@router.get("/{report_date}")
def advisor_day(report_date: str, user: dict = Depends(current_user)):
    assert_advisor_allowed(user["id"], report_date=report_date)
    if not _DATE_RE.match(report_date):
        raise HTTPException(status_code=400, detail="report_date 格式应为 YYYY-MM-DD")
    return _load_public_advice(report_date)


@router.get("/{report_date}/articles/{article_key}")
def advisor_article(report_date: str, article_key: str, user: dict = Depends(current_user)):
    assert_advisor_allowed(user["id"], report_date=report_date)
    data = _load_public_advice(report_date)
    if article_key == "overview":
        block = data.get("daily_overview")
    else:
        block = next(
            (d for d in data.get("direction_advices", []) if d.get("key") == article_key),
            None,
        )
    if not block:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {
        "report_date": report_date,
        "key": article_key,
        "title": block.get("title") or article_key,
        "content": block.get("content") or block.get("summary") or "",
    }


@router.get("/{report_date}/view")
def advisor_html(report_date: str, user: dict = Depends(current_user)):
    assert_advisor_allowed(user["id"], report_date=report_date)
    html = os.path.join(_advisor_root(), report_date, "advisor.html")
    if not os.path.isfile(html):
        raise HTTPException(status_code=404, detail="HTML 视图不存在")
    return FileResponse(
        html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "private, max-age=300"},
    )
