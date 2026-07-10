# -*- coding: utf-8
"""免费体验包 · 免登录公开访问。"""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

_TRIAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "trial_experience",
)
_TRIAL_ZIP = _TRIAL_DIR + ".zip"
_META_CACHE: dict[str, Any] | None = None

_ALLOWED_FILES = frozenset({
    "index_trial.html",
    "data.js",
    "trial_theme.css",
    "report_theme.js",
    "report_theme.css",
    "README.txt",
})


def trial_dir() -> str:
    return _TRIAL_DIR


def trial_zip_path() -> str:
    return _TRIAL_ZIP


def trial_available() -> bool:
    return os.path.isfile(os.path.join(_TRIAL_DIR, "data.js"))


def _load_meta() -> dict[str, Any]:
    global _META_CACHE
    if _META_CACHE is not None:
        return _META_CACHE
    js_path = os.path.join(_TRIAL_DIR, "data.js")
    if not os.path.isfile(js_path):
        return {}
    with open(js_path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if raw.startswith("var REPORT_DATA"):
        raw = raw.split("=", 1)[1].strip().rstrip(";")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    meta = data.get("meta") or {}
    _META_CACHE = meta
    return meta


def invalidate_meta_cache() -> None:
    global _META_CACHE
    _META_CACHE = None


def trial_info() -> dict[str, Any]:
    if not trial_available():
        raise HTTPException(status_code=404, detail="体验包尚未部署")
    meta = _load_meta()
    upsell = meta.get("upsell") or {}
    return {
        "available": True,
        "title": meta.get("title") or "选品报告 · 免费体验包",
        "subtitle": meta.get("subtitle") or "",
        "date": meta.get("date") or "",
        "count": meta.get("count") or 0,
        "virtual_count": meta.get("virtual_count") or 0,
        "physical_count": meta.get("physical_count") or 0,
        "max_items": meta.get("max_items") or 3000,
        "source_total": meta.get("source_total") or 0,
        "tier_counts": meta.get("tier_counts") or {},
        "pack_version": meta.get("pack_version") or "v1",
        "preview_url": "/public/trial/preview",
        "download_url": "/api/v1/public/trial-report/download",
        "upsell": upsell,
        "pc_client_paid_only": bool(upsell.get("pc_client_paid_only", True)),
        "custom_keyword_member_price": upsell.get("custom_keyword_member_price", 9.9),
        "custom_keyword_guest_price": upsell.get("custom_keyword_guest_price", 29.9),
    }


def resolve_trial_file(filename: str) -> str:
    name = (filename or "").strip().replace("\\", "/").split("/")[-1]
    if name not in _ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="文件不存在")
    path = os.path.join(_TRIAL_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="体验包文件缺失")
    return path


def trial_file_response(filename: str) -> FileResponse:
    path = resolve_trial_file(filename)
    media = "application/octet-stream"
    if filename.endswith(".html"):
        media = "text/html; charset=utf-8"
    elif filename.endswith(".js"):
        media = "application/javascript; charset=utf-8"
    elif filename.endswith(".css"):
        media = "text/css; charset=utf-8"
    elif filename.endswith(".txt"):
        media = "text/plain; charset=utf-8"
    return FileResponse(path, media_type=media, headers={"Cache-Control": "public, max-age=300"})


def trial_preview_html() -> HTMLResponse:
    """在线预览页：注入资源根路径，使 data.js / css 从 /public/trial/ 加载。"""
    path = resolve_trial_file("index_trial.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    inject = (
        '<script>window.__TRIAL_ASSET_BASE__="/public/trial/";</script>'
    )
    marker = "<head>"
    if inject not in html and marker in html:
        html = html.replace(marker, marker + "\n" + inject, 1)
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=60"})


def trial_download_response() -> FileResponse:
    if os.path.isfile(_TRIAL_ZIP):
        return FileResponse(
            _TRIAL_ZIP,
            media_type="application/zip",
            filename="选品报告体验包.zip",
            headers={"Cache-Control": "public, max-age=300"},
        )
    if not trial_available():
        raise HTTPException(status_code=404, detail="体验包尚未部署")
    raise HTTPException(status_code=404, detail="体验包 ZIP 未生成，请运行 build_trial_experience_pack.py")
