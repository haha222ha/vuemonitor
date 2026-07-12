# -*- coding: utf-8 -*-
"""
类目关注（member_insight_watchlist）— 与商品 watchlist 并存。

商品收藏: GET/POST /api/v1/member/watchlist  (goods_id, title, …) — 现网已有
类目关注: GET/PUT /api/v1/member/insight/watchlist  (category) — V2 新增

合并到 main.py:
  from cloud_deploy.cloud_api.insight_watchlist import router as insight_watchlist_router
  app.include_router(insight_watchlist_router)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/api/v1/member/insight", tags=["insight-watchlist"])


def _current_member():
    """Replace: from cloud_deploy.cloud_api.auth import current_member"""
    raise NotImplementedError("wire current_member")


def _db_list_categories(user_id: int) -> list[str]:
    """SELECT category FROM member_insight_watchlist WHERE user_id=%s ORDER BY sort_order"""
    raise NotImplementedError


def _db_replace_categories(user_id: int, categories: list[str]) -> list[str]:
    raise NotImplementedError


class WatchlistBody(BaseModel):
    categories: list[str]

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        import re
        out = []
        for c in v:
            c = str(c).strip()
            if not c:
                continue
            if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", c):
                raise ValueError(f"非法类目: {c}")
            if c not in out:
                out.append(c)
        if len(out) > 30:
            raise ValueError("关注类目最多 30 个")
        return out


@router.get("/watchlist")
def get_insight_watchlist(user: dict = Depends(_current_member)):
    cats = _db_list_categories(user["id"])
    return {"categories": cats, "count": len(cats)}


@router.put("/watchlist")
def put_insight_watchlist(body: WatchlistBody, user: dict = Depends(_current_member)):
    # ent = get_member_entitlements(user["id"])
    # max_watch = ent.get("insight_categories_per_day", 5) * 2
    cats = _db_replace_categories(user["id"], body.categories)
    return {"categories": cats, "count": len(cats)}


# --- SQL（合并进 init/migration）---
WATCHLIST_DDL = """
CREATE TABLE IF NOT EXISTS xhs_monitor.member_insight_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES xhs_monitor.users(id) ON DELETE CASCADE,
    category VARCHAR(64) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, category)
);
CREATE INDEX IF NOT EXISTS idx_insight_watchlist_user ON xhs_monitor.member_insight_watchlist(user_id);
"""
