# -*- coding: utf-8 -*-
"""免费 AI 阅读样例 — 仅展示历史（非最新）预生成报告，禁止动态 LLM / 对话。"""
from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse

_ASSETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
)
_DEMO_SHELL = os.path.join(_ASSETS, "advisor_demo.html")

_META_CACHE: dict[str, Any] | None = None


def _list_items() -> list[dict]:
    from cloud_deploy.cloud_api.insight_routes import _list_items_from_disk

    return _list_items_from_disk()


def _env_demo_date() -> str:
    return (os.environ.get("XHS_ADVISOR_DEMO_DATE") or "").strip()[:10]


def _env_demo_category() -> str:
    return (os.environ.get("XHS_ADVISOR_DEMO_CATEGORY") or "").strip()


def _resolve_view_path(report_date: str, category: str) -> str | None:
    from cloud_deploy.cloud_api.insight_routes import _resolve_insight_html

    return _resolve_insight_html(report_date, category)


def pick_demo_report() -> dict[str, Any]:
    """选取历史（非最新）预生成情报作为免费样例。"""
    global _META_CACHE
    if _META_CACHE is not None:
        return dict(_META_CACHE)

    items = _list_items()
    if not items:
        out = {
            "available": False,
            "reason": "no_data",
            "message": "样例报告筹备中，请稍后刷新或先查看选品体验包",
        }
        _META_CACHE = out
        return dict(out)

    dates = sorted({str(it.get("report_date") or "")[:10] for it in items if it.get("report_date")}, reverse=True)
    latest_date = dates[0] if dates else ""
    forced_date = _env_demo_date()
    demo_date = ""

    if forced_date and forced_date != latest_date:
        if any(str(it.get("report_date") or "")[:10] == forced_date for it in items):
            demo_date = forced_date
    elif len(dates) >= 2:
        demo_date = dates[1]
    else:
        out = {
            "available": False,
            "reason": "no_historical",
            "latest_date": latest_date,
            "message": "暂仅有最新报告，免费样例需历史期次，请开通体验卡或会员",
        }
        _META_CACHE = out
        return dict(out)

    forced_cat = _env_demo_category()
    day_items = [it for it in items if str(it.get("report_date") or "")[:10] == demo_date]
    pick = None
    if forced_cat:
        for it in day_items:
            if it.get("category") == forced_cat:
                pick = it
                break
    if not pick and day_items:
        pick = sorted(day_items, key=lambda x: str(x.get("category") or ""))[0]

    if not pick:
        out = {
            "available": False,
            "reason": "no_category",
            "demo_date": demo_date,
            "message": "样例类目未找到",
        }
        _META_CACHE = out
        return dict(out)

    category = str(pick.get("category") or "")
    cats = [
        {
            "category": str(it.get("category") or ""),
            "title": it.get("title") or f"{it.get('category')} 情报",
            "stars": it.get("stars") or 3,
        }
        for it in sorted(day_items, key=lambda x: str(x.get("category") or ""))
    ]

    out = {
        "available": True,
        "report_date": demo_date,
        "latest_date": latest_date,
        "is_latest": False,
        "category": category,
        "title": pick.get("title") or f"{category} 情报",
        "stars": pick.get("stars") or 3,
        "categories": cats,
        "view_url": f"/api/v1/public/advisor-demo/view?date={demo_date}&category={category}",
        "shell_url": "/public/advisor-demo",
        "ai_modes": {
            "pregenerated_read": False,
            "dynamic_llm": False,
            "advisor_chat": False,
        },
        "notice": "免费样例仅可阅读历史预生成报告，不含最新数据，不支持 AI 动态调用与对话。",
    }
    _META_CACHE = out
    return dict(out)


def invalidate_demo_cache() -> None:
    global _META_CACHE
    _META_CACHE = None


def demo_info() -> dict[str, Any]:
    return pick_demo_report()


def demo_view_response(date: str, category: str) -> FileResponse:
    date = (date or "").strip()[:10]
    category = (category or "").strip()
    if not date or not category:
        raise HTTPException(status_code=400, detail="缺少 date 或 category")

    meta = pick_demo_report()
    if not meta.get("available"):
        raise HTTPException(status_code=404, detail=meta.get("message") or "样例不可用")

    latest = str(meta.get("latest_date") or "")[:10]
    if date == latest:
        raise HTTPException(status_code=403, detail="免费样例不可查看最新报告，请开通会员")

    allowed_dates = {str(meta.get("report_date") or "")[:10]}
    items = _list_items()
    for it in items:
        d = str(it.get("report_date") or "")[:10]
        if d and d != latest:
            allowed_dates.add(d)
    if date not in allowed_dates:
        raise HTTPException(status_code=403, detail="该日期不在免费样例范围内")

    path = _resolve_view_path(date, category)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="样例报告不存在")

    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "public, max-age=600", "X-Demo-Mode": "free-readonly"},
    )


def demo_shell_response() -> HTMLResponse:
    if not os.path.isfile(_DEMO_SHELL):
        raise HTTPException(status_code=404, detail="样例页未部署")
    with open(_DEMO_SHELL, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
