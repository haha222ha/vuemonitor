# -*- coding: utf-8 -*-
"""
合并到 cloud_api/main.py 的路由片段（Phase 2c）

用法:
  from cloud_deploy.cloud_api.insight_routes import router as insight_router
  app.include_router(insight_router)
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/api/v1/member/insight", tags=["insight"])

# 路径参数校验:防止路径遍历
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CATEGORY_RE = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$")


def _validate_path_params(report_date: str, category: str) -> None:
    if not _DATE_RE.match(report_date):
        raise HTTPException(400, "report_date 格式应为 YYYY-MM-DD")
    if not _CATEGORY_RE.match(category):
        raise HTTPException(400, "category 含非法字符")


def _current_user():
    """Replace with: from cloud_deploy.cloud_api.auth import current_user"""
    raise NotImplementedError("wire current_user from auth.py")


@router.get("/library")
def insight_library(user: dict = Depends(_current_user)):
    """List published insight reports for member."""
    # ent = db.get_member_entitlements(user["id"])
    # if "insight_daily_html" not in allowed: raise 403
    return {"items": [], "membership": user, "legacy_note": "V1 zip under /member/library"}


@router.get("/{report_date}/{category}/view", response_class=HTMLResponse)
def insight_view(report_date: str, category: str, user: dict = Depends(_current_user)):
    _validate_path_params(report_date, category)
    path = _resolve_insight_html(report_date, category)
    if not path:
        raise HTTPException(404, "情报报告不存在")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@router.get("/{report_date}/{category}/summary")
def insight_summary(report_date: str, category: str, user: dict = Depends(_current_user)):
    _validate_path_params(report_date, category)
    data = _load_insight_json(report_date, category)
    if not data:
        raise HTTPException(404, "情报报告不存在")
    _strip_internal_fields(data)
    return data


def _resolve_insight_html(report_date: str, category: str) -> str | None:
    return None  # db.get_insight_archive_path(...)


def _load_insight_json(report_date: str, category: str) -> dict | None:
    return None


def _strip_internal_fields(data: dict) -> None:
    for k in ("goods_id", "store_id", "store_name", "title", "items", "columns"):
        data.pop(k, None)
