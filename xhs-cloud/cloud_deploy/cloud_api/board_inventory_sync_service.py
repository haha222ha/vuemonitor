# -*- coding: utf-8 -*-
"""看板底账 board_inventory_goods → 云端 PG（与本机同构，禁止搬热库全表）。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS board_inventory_goods (
  goods_id TEXT PRIMARY KEY,
  title TEXT,
  store_name TEXT,
  sold_num INTEGER,
  deal_price DOUBLE PRECISION,
  is_virtual SMALLINT DEFAULT 1,
  keyword TEXT,
  image_url TEXT,
  first_snap DATE,
  last_snap DATE,
  snap_days INTEGER,
  sum_delta_all BIGINT,
  sum_delta_7d BIGINT,
  sum_delta_30d BIGINT,
  active_days_all INTEGER,
  active_days_30d INTEGER,
  lane_hint TEXT,
  scene_l1 TEXT,
  scene_l2 TEXT,
  scene_l3 TEXT,
  scene_source TEXT,
  abc_class TEXT,
  xyz_class TEXT,
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
ALTER TABLE board_inventory_goods ADD COLUMN IF NOT EXISTS image_url TEXT;
CREATE INDEX IF NOT EXISTS idx_board_inv_lane ON board_inventory_goods(lane_hint);
CREATE INDEX IF NOT EXISTS idx_board_inv_s7 ON board_inventory_goods(sum_delta_7d DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_board_inv_s30 ON board_inventory_goods(sum_delta_30d DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_board_inv_sall ON board_inventory_goods(sum_delta_all DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_board_inv_scene2 ON board_inventory_goods(scene_l2);
CREATE INDEX IF NOT EXISTS idx_board_inv_abc ON board_inventory_goods(abc_class);
CREATE INDEX IF NOT EXISTS idx_board_inv_last ON board_inventory_goods(last_snap DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS board_inventory_meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

_COLS = (
    "goods_id",
    "title",
    "store_name",
    "sold_num",
    "deal_price",
    "is_virtual",
    "keyword",
    "image_url",
    "first_snap",
    "last_snap",
    "snap_days",
    "sum_delta_all",
    "sum_delta_7d",
    "sum_delta_30d",
    "active_days_all",
    "active_days_30d",
    "lane_hint",
    "scene_l1",
    "scene_l2",
    "scene_l3",
    "scene_source",
    "abc_class",
    "xyz_class",
    "updated_at",
)


def ensure_board_inventory_schema(conn) -> None:
    with conn.cursor() as c:
        c.execute("CREATE SCHEMA IF NOT EXISTS xhs_monitor")
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(DDL)
    conn.commit()


def _as_date(v: Any):
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _as_ts(v: Any):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip().replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt)
        except Exception:
            continue
    return None


def _row_tuple(r: dict) -> tuple | None:
    gid = str(r.get("goods_id") or "").strip()
    if len(gid) < 5:
        return None
    return (
        gid,
        (str(r.get("title") or "")[:300] or None),
        (str(r.get("store_name") or "")[:120] or None),
        int(r.get("sold_num") or 0),
        float(r["deal_price"]) if r.get("deal_price") is not None and str(r.get("deal_price")) != "" else None,
        int(r.get("is_virtual") if r.get("is_virtual") is not None else 1),
        (str(r.get("keyword") or "")[:80] or None),
        (str(r.get("image_url") or "")[:500] or None),
        _as_date(r.get("first_snap")),
        _as_date(r.get("last_snap")),
        int(r["snap_days"]) if r.get("snap_days") is not None else None,
        int(r["sum_delta_all"]) if r.get("sum_delta_all") is not None else None,
        int(r["sum_delta_7d"]) if r.get("sum_delta_7d") is not None else None,
        int(r["sum_delta_30d"]) if r.get("sum_delta_30d") is not None else None,
        int(r["active_days_all"]) if r.get("active_days_all") is not None else None,
        int(r["active_days_30d"]) if r.get("active_days_30d") is not None else None,
        (str(r.get("lane_hint") or "")[:64] or None),
        (str(r.get("scene_l1") or "")[:80] or None),
        (str(r.get("scene_l2") or "")[:80] or None),
        (str(r.get("scene_l3") or "")[:80] or None),
        (str(r.get("scene_source") or "")[:40] or None),
        (str(r.get("abc_class") or "")[:8] or None),
        (str(r.get("xyz_class") or "")[:8] or None),
        _as_ts(r.get("updated_at")) or datetime.now(),
    )


def apply_board_inventory_batch(
    conn,
    rows: list[dict],
    *,
    meta: dict | None = None,
    final_batch: bool = False,
) -> dict:
    """批量 UPSERT board_inventory_goods。"""
    ensure_board_inventory_schema(conn)
    tuples = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        t = _row_tuple(r)
        if t:
            tuples.append(t)
    upserted = 0
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        if tuples:
            cols = ", ".join(_COLS)
            updates = ", ".join(
                f"{c}=EXCLUDED.{c}" for c in _COLS if c != "goods_id"
            )
            psycopg2.extras.execute_values(
                c,
                f"""
                INSERT INTO board_inventory_goods ({cols}) VALUES %s
                ON CONFLICT (goods_id) DO UPDATE SET {updates}
                """,
                tuples,
                page_size=500,
            )
            upserted = len(tuples)
        if meta and isinstance(meta, dict):
            for k, v in meta.items():
                if not k:
                    continue
                c.execute(
                    """
                    INSERT INTO board_inventory_meta(key, value) VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
                    """,
                    (str(k)[:120], str(v)[:2000]),
                )
        if final_batch:
            c.execute(
                """
                INSERT INTO board_inventory_meta(key, value) VALUES ('synced_at', %s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
            )
            c.execute("SELECT COUNT(*) FROM board_inventory_goods")
            n = int(c.fetchone()[0] or 0)
            c.execute(
                """
                INSERT INTO board_inventory_meta(key, value) VALUES ('goods_count', %s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
                """,
                (str(n),),
            )
    conn.commit()
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute("SELECT COUNT(*) FROM board_inventory_goods")
        total = int(c.fetchone()[0] or 0)
    return {"ok": True, "upserted": upserted, "total": total, "final_batch": bool(final_batch)}


def board_inventory_stats(conn) -> dict:
    ensure_board_inventory_schema(conn)
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute("SELECT COUNT(*) FROM board_inventory_goods")
        n = int(c.fetchone()[0] or 0)
        c.execute("SELECT key, value FROM board_inventory_meta")
        meta = {str(k): v for k, v in (c.fetchall() or [])}
    return {"ok": True, "goods_count": n, "meta": meta}
