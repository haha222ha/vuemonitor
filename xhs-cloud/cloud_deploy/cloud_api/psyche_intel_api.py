# -*- coding: utf-8 -*-
"""云端 · 测评情报 OS API（优先读已推送的 intel.json；有热库表时也可直查）。"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse


def _boards_root(get_settings) -> str:
    s = get_settings()
    return os.path.join(s.xhs_data_dir, "psyche_boards")


def load_latest_intel(get_settings) -> Optional[dict[str, Any]]:
    root = os.path.join(_boards_root(get_settings), "latest")
    for name in ("intel.json", "psyche_board.json"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if name == "intel.json" or data.get("overview"):
                    return data
            except Exception:
                continue
    # data.js 不在此解析
    return None


def try_build_from_pg(as_of: Optional[date] = None) -> Optional[dict[str, Any]]:
    """若进程可导入爬虫情报层且 XHS_DATABASE_URL/本地 PG 可用，则直出。"""
    try:
        from xhs_psyche_intel import build_intel_payload

        return build_intel_payload(as_of, persist=False, radar_limit=80)
    except Exception:
        return None


def register_psyche_intel_routes(app, *, get_settings, cookie_ok, board_token, board_password):
    """挂到 cloud_api.main 上。"""

    def _require_cookie(request: Request) -> None:
        if not cookie_ok(request):
            raise HTTPException(status_code=401, detail="未登录情报看板")

    @app.get("/api/v1/psyche/intel")
    def psyche_intel_bundle(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings)
        if not data or not data.get("overview"):
            live = try_build_from_pg()
            if live:
                return live
            raise HTTPException(status_code=404, detail="暂无情报数据，请先在本机生成并推送看板")
        return data

    @app.get("/api/v1/psyche/overview")
    def psyche_overview(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        ov = data.get("overview")
        if not ov:
            raise HTTPException(status_code=404, detail="暂无 overview")
        return ov

    @app.get("/api/v1/psyche/growth")
    def psyche_growth(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        return {"items": data.get("growth_radar") or [], "as_of": (data.get("overview") or {}).get("as_of")}

    @app.get("/api/v1/psyche/shops")
    def psyche_shops(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        return {"items": data.get("shops") or []}

    @app.get("/api/v1/psyche/tracks")
    def psyche_tracks(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        return {"items": data.get("tracks") or []}

    @app.get("/api/v1/psyche/report")
    def psyche_report(request: Request):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        return data.get("daily_report") or {}

    @app.get("/api/v1/psyche/goods/{goods_id}")
    def psyche_goods_detail(request: Request, goods_id: str):
        _require_cookie(request)
        data = load_latest_intel(get_settings) or try_build_from_pg() or {}
        gid = str(goods_id or "").strip()
        for row in data.get("growth_radar") or []:
            if str(row.get("goods_id") or "") == gid:
                return row
        # 回落：仅系列（需云端能 import 爬虫层）
        try:
            from xhs_psyche_intel import fetch_product_series, _connect

            conn = _connect()
            try:
                return {"goods_id": gid, "series": fetch_product_series(conn, gid, 14)}
            finally:
                conn.close()
        except Exception:
            raise HTTPException(status_code=404, detail="商品不在当日雷达中")
