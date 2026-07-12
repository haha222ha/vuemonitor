# -*- coding: utf-8 -*-
"""
PC-1：ProductAnalyzer `core/cloud_client.py` V2 补丁草案

合并目标仓库：`xhs_shelf_time/`（ProductAnalyzer，不在 vuemonitor 内）

用法（在 xhs_shelf_time 中）:
  1. 将本文件函数合并进 `core/cloud_client.py`，或:
     from cloud_client_insight_v2 import *  # 临时
  2. 侧栏/UI 调用 `resolve_menu_flags(fetch_member_profile())`
  3. Legacy zip 路径 **不要删**，仅按 show_legacy_zip 显隐

设计原则（Legacy 隔离）:
  - 新函数 **只增** insight API；不改 library/download/upload 签名
  - `legacy_zip_enabled=false` 时 UI 隐藏 zip，API 仍 403 兜底
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

# ---------------------------------------------------------------------------
# 合并进 cloud_client.py 时，复用现有 _request / get_token / get_cloud_base_url
# 以下为独立草案时的占位实现（单元测试可 mock）
# ---------------------------------------------------------------------------

_request = None  # type: ignore
_get_token = None  # type: ignore
_get_cloud_base_url = None  # type: ignore


def _bind_cloud_client(request_fn, get_token_fn, get_base_url_fn) -> None:
    """测试或集成时注入现网 cloud_client 依赖。"""
    global _request, _get_token, _get_cloud_base_url
    _request = request_fn
    _get_token = get_token_fn
    _get_cloud_base_url = get_base_url_fn


def _api(method: str, path: str, *, timeout: int = 30, json_body: dict | None = None) -> tuple[int, Any]:
    if _request is None or _get_token is None:
        raise RuntimeError("call _bind_cloud_client() first or merge into cloud_client.py")
    kwargs: dict[str, Any] = {"token": _get_token(), "timeout": timeout}
    if json_body is not None:
        kwargs["json"] = json_body
    return _request(method, path, **kwargs)


def _api_error(data: Any, code: int, default: str) -> str:
    if isinstance(data, dict):
        return str(data.get("detail") or data.get("message") or default)
    return default or f"HTTP {code}"


# --- V2 新增 API ---


def fetch_member_profile() -> dict[str, Any]:
    """GET /api/v1/member/profile — 含 entitlements / legacy_zip_enabled / insight_enabled。"""
    code, data = _api("GET", "/api/v1/member/profile")
    if code != 200:
        raise RuntimeError(_api_error(data, code, "获取会员资料失败"))
    return data if isinstance(data, dict) else {}


def fetch_insight_library() -> dict[str, Any]:
    """GET /api/v1/member/insight/library — 预生成情报列表（Cache-First，用户侧零 LLM）。"""
    code, data = _api("GET", "/api/v1/member/insight/library")
    if code != 200:
        raise RuntimeError(_api_error(data, code, "获取情报库失败"))
    return data if isinstance(data, dict) else {"items": []}


def fetch_insight_categories() -> dict[str, Any]:
    """GET /api/v1/member/insight/categories — 最新日类目摘要（可选）。"""
    code, data = _api("GET", "/api/v1/member/insight/categories")
    if code != 200:
        raise RuntimeError(_api_error(data, code, "获取情报类目失败"))
    return data if isinstance(data, dict) else {"items": []}


def insight_view_url(report_date: str, category: str, *, access_token: str | None = None) -> str:
    """
    构造情报 HTML 预览 URL（WebView / 系统浏览器）。
    iframe 需带 access_token  query 参数（与 Web 会员页一致）。
    """
    if _get_cloud_base_url is None or _get_token is None:
        raise RuntimeError("call _bind_cloud_client() first")
    base = (_get_cloud_base_url() or "https://monitor.xhs365.cn").rstrip("/")
    date = str(report_date or "")[:10]
    cat = quote(str(category or "").strip(), safe="")
    token = access_token if access_token is not None else (_get_token() or "")
    q = f"?access_token={quote(token)}" if token else ""
    return f"{base}/api/v1/member/insight/{date}/{cat}/view{q}"


def resolve_menu_flags(profile: dict[str, Any] | None) -> dict[str, Any]:
    """
    侧栏显隐 — 与 Web member_insight.js / legacy_gate 对齐。

    Returns:
        show_legacy_zip: 是否显示「选品数据报告」+ zip 下载 + plan_b 上传
        show_insight: 是否显示「AI 市场情报」
        default_section: 'insight' | 'legacy'
    """
    profile = profile or {}
    ent = profile.get("entitlements") or {}

    legacy = profile.get("legacy_zip_enabled")
    if legacy is None:
        legacy = ent.get("legacy_zip_enabled", True)  # 旧 API 兼容：默认保留 Legacy

    insight = profile.get("insight_enabled")
    if insight is None:
        insight = bool(ent.get("insight_enabled"))

    route = profile.get("portal_route") or ""
    if route == "insight_only":
        default_section = "insight"
    elif insight and legacy:
        default_section = "insight" if ent.get("insight_preview") else "legacy"
    elif insight:
        default_section = "insight"
    else:
        default_section = "legacy"

    return {
        "show_legacy_zip": bool(legacy),
        "show_insight": bool(insight),
        "default_section": default_section,
        "portal_route": route or ("insight_only" if insight and not legacy else "legacy_only"),
        "plan_code": profile.get("plan_code") or ent.get("plan_code"),
    }


def open_insight_in_browser(report_date: str, category: str) -> None:
    """便捷：系统默认浏览器打开情报（PyQt / tkinter 菜单可调用）。"""
    import webbrowser

    webbrowser.open(insight_view_url(report_date, category))


# --- Legacy API（保持不变，此处仅作文档锚点）---
#
# fetch_report_library()  -> GET /api/v1/member/library
# download_report(date)   -> GET /api/v1/member/reports/{date}/download
# upload_report_plan_b()  -> POST /api/v1/sync/report-upload
# fetch_watchlist()       -> GET /api/v1/member/watchlist
#
# PC-1 不修改以上函数；仅在 show_legacy_zip=False 时 UI 不调用。
