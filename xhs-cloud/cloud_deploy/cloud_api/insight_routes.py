# -*- coding: utf-8 -*-
"""
V2 情报 API — PR-1/PR-2：library 扫描预生成目录，view 支持 iframe token。
"""
from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from cloud_deploy.cloud_api.auth import current_user, member_from_token, security
from cloud_deploy.cloud_api.entitlements_v2 import filter_insight_library
from cloud_deploy.cloud_api.member_entitlements import assert_insight_allowed

router = APIRouter(prefix="/api/v1/member/insight", tags=["insight"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CATEGORY_RE = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$")


def _validate_path_params(report_date: str, category: str) -> None:
    if not _DATE_RE.match(report_date):
        raise HTTPException(status_code=400, detail="report_date 格式应为 YYYY-MM-DD")
    if not _CATEGORY_RE.match(category):
        raise HTTPException(status_code=400, detail="category 含非法字符")


def _insight_data_root() -> str:
    root = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
    sub = "insight_shadow" if _shadow_mode() else "report_archives"
    return os.path.join(root, "data", sub)


def _shadow_mode() -> bool:
    return os.environ.get("XHS_INSIGHT_SHADOW", "1").strip().lower() in ("1", "true", "yes", "on")


def _resolve_insight_html(report_date: str, category: str) -> str | None:
    day = report_date.replace("-", "")
    base = _insight_data_root()
    candidates = [
        os.path.join(base, f"insight_{day}", category, "index.html"),
        os.path.join(base, f"insight_{day}_{category}", "index.html"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _load_insight_json(report_date: str, category: str) -> dict | None:
    day = report_date.replace("-", "")
    path = os.path.join(_insight_data_root(), f"insight_{day}", category, "insight.json")
    if not os.path.isfile(path):
        return None
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return None


def _list_items_from_disk() -> list[dict]:
    base = _insight_data_root()
    items: list[dict] = []
    if not os.path.isdir(base):
        return items
    for day_dir in sorted(os.listdir(base), reverse=True):
        if not day_dir.startswith("insight_"):
            continue
        full_day = os.path.join(base, day_dir)
        if not os.path.isdir(full_day):
            continue
        date = day_dir.replace("insight_", "")
        if len(date) == 8:
            report_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        else:
            report_date = date
        for cat in os.listdir(full_day):
            cat_path = os.path.join(full_day, cat)
            if not os.path.isdir(cat_path):
                continue
            if not os.path.isfile(os.path.join(cat_path, "index.html")):
                continue
            if not _CATEGORY_RE.match(cat):
                continue
            meta = _load_insight_json(report_date, cat) or {}
            report = meta.get("report") or {}
            items.append(
                {
                    "category": cat,
                    "report_date": report_date,
                    "stars": report.get("opportunity_stars") or 3,
                    "title": f"{cat} 情报",
                }
            )
    items.sort(key=lambda x: (x.get("report_date", ""), x.get("category", "")), reverse=True)
    return items


def _strip_internal_fields(data: dict) -> None:
    for k in ("goods_id", "store_id", "store_name", "title", "items", "columns"):
        data.pop(k, None)


def _user_for_request(
    access_token: str,
    cred: HTTPAuthorizationCredentials | None,
) -> dict:
    token = (cred.credentials if cred else None) or (access_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    return member_from_token(token)


@router.get("/library")
def insight_library(user: dict = Depends(current_user)):
    ent = assert_insight_allowed(user["id"])
    items = _list_items_from_disk()
    items = filter_insight_library(items, ent)
    return {
        "items": items,
        "shadow_mode": _shadow_mode(),
        "legacy_note": "V1 zip 仍在 /api/v1/member/library",
    }


@router.get("/categories")
def insight_categories(user: dict = Depends(current_user)):
    """PR-2：从最新预生成摘要返回类目列表（只读）。"""
    assert_insight_allowed(user["id"])
    items = _list_items_from_disk()
    latest_date = items[0]["report_date"] if items else None
    cats = []
    seen = set()
    for it in items:
        if latest_date and it.get("report_date") != latest_date:
            continue
        c = it.get("category")
        if c and c not in seen:
            seen.add(c)
            cats.append({"category": c, "report_date": it.get("report_date")})
    return {"report_date": latest_date, "items": cats}


@router.get("/{report_date}/{category}/view")
def insight_view(
    report_date: str,
    category: str,
    access_token: str = "",
    cred: HTTPAuthorizationCredentials | None = Depends(security),
):
    user = _user_for_request(access_token, cred)
    assert_insight_allowed(user["id"])
    _validate_path_params(report_date, category)
    path = _resolve_insight_html(report_date, category)
    if not path:
        raise HTTPException(status_code=404, detail="情报报告不存在")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@router.get("/{report_date}/{category}/summary")
def insight_summary(report_date: str, category: str, user: dict = Depends(current_user)):
    ent = assert_insight_allowed(user["id"])
    _validate_path_params(report_date, category)
    data = _load_insight_json(report_date, category)
    if not data:
        raise HTTPException(status_code=404, detail="情报报告不存在")
    _strip_internal_fields(data)
    allowed = filter_insight_library(
        [{"report_date": report_date, "category": category}],
        ent,
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="当前授权不可查看该日期情报")
    return data
