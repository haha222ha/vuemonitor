# -*- coding: utf-8 -*-
"""
实验室类目关注 — API 契约与现网 insight_watchlist 一致。

存储: output/insight_watchlist.json（生产为 member_insight_watchlist 表）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.lab_session import get_active_persona, subscription_path

WATCHLIST_PATH_LEGACY = Path(__file__).resolve().parents[1] / "output" / "insight_watchlist.json"


def _watchlist_path() -> Path:
    return subscription_path().parent / "insight_watchlist.json"


def _load() -> dict[str, Any]:
    path = _watchlist_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 兼容旧全局文件
    if WATCHLIST_PATH_LEGACY.is_file():
        try:
            return json.loads(WATCHLIST_PATH_LEGACY.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"categories": ["美甲美睫", "小学教辅"], "persona": get_active_persona()}


def _save(data: dict[str, Any]) -> None:
    path = _watchlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["persona"] = get_active_persona()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_watchlist() -> dict[str, Any]:
    data = _load()
    cats = data.get("categories") or []
    return {"categories": cats, "count": len(cats), "persona": get_active_persona()}


def put_watchlist(categories: list[str], *, max_items: int = 30) -> dict[str, Any]:
    cats = []
    for c in categories:
        c = str(c).strip()
        if c and c not in cats:
            cats.append(c)
    cats = cats[:max_items]
    _save({"categories": cats})
    return {"categories": cats, "count": len(cats)}
