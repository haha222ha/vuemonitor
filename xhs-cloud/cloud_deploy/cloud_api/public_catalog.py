# -*- coding: utf-8 -*-
"""对外 SaaS 货架公开目录（自用目录不再公开）。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["public-catalog"])

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
_SHELF = _ASSETS / "saas_shelf"


def _load_public_apps() -> list[dict]:
    raw = (os.environ.get("PUBLIC_APPS_JSON") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("apps"), list):
                return data["apps"]
        except json.JSONDecodeError:
            pass
    path = _SHELF / "public_apps.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("apps") or []
    return []


@router.get("/saas", response_class=HTMLResponse)
@router.get("/saas/", response_class=HTMLResponse)
@router.get("/saas/index.html", response_class=HTMLResponse)
def saas_shelf_home():
    path = _SHELF / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="货架未部署")
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/v1/public/apps")
def public_apps():
    apps = _load_public_apps()
    return {"ok": True, "apps": apps, "total": len(apps)}


@router.get("/api/v1/public/internal-apps")
def public_internal_apps_gone():
    # Plan A：自用目录不再公开；未登录探测一律 404
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/hub", response_class=HTMLResponse)
@router.get("/hub/", response_class=HTMLResponse)
def saas_hub_gone():
    raise HTTPException(status_code=404, detail="Not Found")
