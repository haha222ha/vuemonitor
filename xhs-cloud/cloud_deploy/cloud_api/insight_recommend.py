# -*- coding: utf-8 -*-
"""基于 user_behavior 的轻量「为你推荐」（T2 骨架）。"""
from __future__ import annotations

from typing import Any, Callable


def top_categories_for_user(conn, user_id: int, *, limit: int = 5) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = 'user_behavior'
            LIMIT 1
            """
        )
        if not cur.fetchone():
            return []
        cur.execute(
            """
            SELECT category, COUNT(*) AS n
            FROM user_behavior
            WHERE user_id = %s AND category IS NOT NULL AND category <> ''
              AND action IN ('view', 'generate', 'library')
            GROUP BY category
            ORDER BY n DESC, MAX(created_at) DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    out: list[str] = []
    for row in rows:
        cat = row[0] if not isinstance(row, dict) else row.get("category")
        if cat and cat not in out:
            out.append(str(cat))
    return out


def build_recommendations(
    conn,
    user_id: int,
    list_disk_items: Callable[[], list[dict]],
    *,
    limit: int = 4,
) -> dict[str, Any]:
    preferred = top_categories_for_user(conn, user_id, limit=limit)
    items = list_disk_items()
    by_cat: dict[str, dict] = {}
    for it in items:
        cat = str(it.get("category") or "")
        if cat and cat not in by_cat:
            by_cat[cat] = it

    recs: list[dict] = []
    for cat in preferred:
        if cat in by_cat:
            recs.append({**by_cat[cat], "reason": "based_on_history"})
        if len(recs) >= limit:
            break

    if len(recs) < limit:
        for it in items:
            cat = str(it.get("category") or "")
            if cat and all(r.get("category") != cat for r in recs):
                recs.append({**it, "reason": "trending"})
            if len(recs) >= limit:
                break

    return {"items": recs[:limit], "source": "user_behavior" if preferred else "library"}
