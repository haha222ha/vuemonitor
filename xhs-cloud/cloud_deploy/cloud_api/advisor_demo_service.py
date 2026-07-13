# -*- coding: utf-8 -*-
"""免费 AI 阅读样例 — 展示最新 AI 选品顾问预生成报告（2026-07-13 改造：允许展示最新日期）。"""
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


def _advisor_published_root() -> str:
    """AI 顾问报告发布目录。"""
    root = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
    return os.path.join(root, "data", "advisor_published")


def _list_advisor_reports() -> list[dict]:
    """从 advisor_published/ 目录扫描可用报告。"""
    base = _advisor_published_root()
    items: list[dict] = []
    if not os.path.isdir(base):
        return items
    for day_dir in sorted(os.listdir(base), reverse=True):
        full_day = os.path.join(base, day_dir)
        if not os.path.isdir(full_day):
            continue
        advice_path = os.path.join(full_day, "advice.json")
        html_path = os.path.join(full_day, "advisor.html")
        if not os.path.isfile(html_path):
            continue
        date = day_dir[:10]
        title = f"AI 选品顾问 · {date}"
        stars = 3
        if os.path.isfile(advice_path):
            try:
                import json
                with open(advice_path, "r", encoding="utf-8") as f:
                    advice = json.load(f)
                ov = advice.get("daily_overview") or {}
                if ov.get("title"):
                    title = ov["title"]
                directions = advice.get("direction_advices") or []
                if directions:
                    stars = min(5, max(3, len(directions) // 6 + 3))
            except Exception:
                pass
        items.append({
            "category": "advisor",
            "report_date": date,
            "stars": stars,
            "title": title,
            "html_path": html_path,
        })
    items.sort(key=lambda x: x.get("report_date", ""), reverse=True)
    return items


def _list_items() -> list[dict]:
    """兼容旧接口：优先返回 AI 顾问报告，无则回退情报库。"""
    advisor_items = _list_advisor_reports()
    if advisor_items:
        return advisor_items
    # 回退到情报库
    try:
        from cloud_deploy.cloud_api.insight_routes import _list_items_from_disk
        return _list_items_from_disk()
    except Exception:
        return []


def _env_demo_date() -> str:
    return (os.environ.get("XHS_ADVISOR_DEMO_DATE") or "").strip()[:10]


def _env_demo_category() -> str:
    return (os.environ.get("XHS_ADVISOR_DEMO_CATEGORY") or "").strip()


def _resolve_view_path(report_date: str, category: str) -> str | None:
    """解析报告 HTML 路径：优先 advisor_published，回退情报库。"""
    # 1) AI 顾问报告
    advisor_path = os.path.join(_advisor_published_root(), report_date, "advisor.html")
    if os.path.isfile(advisor_path):
        return advisor_path
    # 2) 回退情报库
    try:
        from cloud_deploy.cloud_api.insight_routes import _resolve_insight_html
        return _resolve_insight_html(report_date, category)
    except Exception:
        return None


def pick_demo_report() -> dict[str, Any]:
    """选取 AI 选品顾问报告作为免费样例（2026-07-13 改造：允许展示最新日期）。"""
    global _META_CACHE
    if _META_CACHE is not None:
        return dict(_META_CACHE)

    items = _list_items()
    if not items:
        out = {
            "available": False,
            "reason": "no_data",
            "message": "样例报告筹备中，请稍后刷新或开通体验卡阅读完整 AI 分析",
        }
        _META_CACHE = out
        return dict(out)

    dates = sorted({str(it.get("report_date") or "")[:10] for it in items if it.get("report_date")}, reverse=True)
    latest_date = dates[0] if dates else ""
    forced_date = _env_demo_date()

    # 优先用环境变量指定的日期，否则用最新日期（允许展示最新报告）
    if forced_date and any(str(it.get("report_date") or "")[:10] == forced_date for it in items):
        demo_date = forced_date
    elif dates:
        demo_date = dates[0]  # 用最新日期（2026-07-13 改造：不再要求"历史"报告）
    else:
        demo_date = ""

    if not demo_date:
        out = {
            "available": False,
            "reason": "no_data",
            "message": "样例报告筹备中，请稍后刷新",
        }
        _META_CACHE = out
        return dict(out)

    day_items = [it for it in items if str(it.get("report_date") or "")[:10] == demo_date]
    pick = day_items[0] if day_items else None

    if not pick:
        out = {
            "available": False,
            "reason": "no_category",
            "demo_date": demo_date,
            "message": "样例未找到",
        }
        _META_CACHE = out
        return dict(out)

    category = str(pick.get("category") or "advisor")
    cats = [
        {
            "category": str(it.get("category") or ""),
            "title": it.get("title") or f"AI 选品顾问 · {demo_date}",
            "stars": it.get("stars") or 3,
        }
        for it in sorted(day_items, key=lambda x: str(x.get("category") or ""))
    ]

    out = {
        "available": True,
        "report_date": demo_date,
        "latest_date": latest_date,
        "is_latest": demo_date == latest_date,
        "category": category,
        "title": pick.get("title") or f"AI 选品顾问 · {demo_date}",
        "stars": pick.get("stars") or 3,
        "categories": cats,
        "view_url": f"/api/v1/public/advisor-demo/view?date={demo_date}&category={category}",
        "shell_url": "/public/advisor-demo",
        "ai_modes": {
            "pregenerated_read": True,
            "dynamic_llm": False,
            "advisor_chat": False,
        },
        "notice": "免费样例展示 AI 预生成报告，完整能力请开通体验卡或会员。",
    }
    _META_CACHE = out
    return dict(out)


def invalidate_demo_cache() -> None:
    global _META_CACHE
    _META_CACHE = None


def demo_info() -> dict[str, Any]:
    return pick_demo_report()


def demo_directions() -> dict[str, Any]:
    """返回真实方向解读列表（前 10 个含预览，其余只有标题）。"""
    import json

    meta = pick_demo_report()
    if not meta.get("available"):
        return {"available": False, "report_date": "", "directions": []}

    report_date = meta.get("report_date") or ""
    advice_path = os.path.join(_advisor_published_root(), report_date, "advice.json")
    if not os.path.isfile(advice_path):
        return {"available": False, "report_date": report_date, "directions": []}

    try:
        with open(advice_path, "r", encoding="utf-8") as f:
            advice = json.load(f)
    except Exception:
        return {"available": False, "report_date": report_date, "directions": []}

    raw_dirs = advice.get("direction_advices") or []
    directions: list[dict] = []
    for i, block in enumerate(raw_dirs):
        if not isinstance(block, dict):
            continue
        title = block.get("title") or block.get("key") or f"方向 {i + 1}"
        content = (block.get("content") or block.get("summary") or "").strip()
        unlocked = i < 10
        directions.append({
            "title": title,
            "content": content if unlocked else "",
            "unlocked": unlocked,
        })

    return {
        "available": True,
        "report_date": report_date,
        "total": len(directions),
        "unlocked_count": min(10, len(directions)),
        "directions": directions,
    }


def demo_view_response(date: str, category: str) -> FileResponse:
    date = (date or "").strip()[:10]
    category = (category or "").strip()
    if not date:
        raise HTTPException(status_code=400, detail="缺少 date")

    meta = pick_demo_report()
    if not meta.get("available"):
        raise HTTPException(status_code=404, detail=meta.get("message") or "样例不可用")

    # 2026-07-13 改造：允许查看最新日期报告（去掉 403 限制）

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
