# -*- coding: utf-8 -*-
"""PG 读取与报告行转换。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cloud_deploy.reporting.constants import DEFAULT_MIN_ACTUAL, DEFAULT_MIN_ACTUAL_VIRTUAL, DEFAULT_MIN_V1D, DEFAULT_MIN_V1D_VIRTUAL, REPORT_COLUMNS


def thresholds_for(is_virtual: bool, min_v1d=DEFAULT_MIN_V1D, min_actual=DEFAULT_MIN_ACTUAL,
                   min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL, min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL):
    if is_virtual:
        return min_v1d_virtual, min_actual_virtual
    return min_v1d, min_actual


def passes_threshold(item: list, min_v1d=DEFAULT_MIN_V1D, min_actual=DEFAULT_MIN_ACTUAL,
                     min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL, min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL) -> bool:
    is_v = bool(item[24]) if len(item) > 24 else False
    v1d = float(item[7] or 0)
    actual = float(item[6] or 0)
    sold = float(item[3] or 0) if len(item) > 3 else 0
    if sold > 200000:
        return False
    if v1d > 50000 or actual > 50000:
        return False
    th_v1d, th_actual = thresholds_for(is_v, min_v1d, min_actual, min_v1d_virtual, min_actual_virtual)
    return v1d > th_v1d or actual >= th_actual


def dedup_by_title(items: list) -> list:
    best: dict[str, list] = {}
    for item in items:
        title = (item[1] or "").strip()
        if not title:
            continue
        prev = best.get(title)
        if not prev:
            best[title] = item
            continue
        a_act, a_v1d = float(item[6] or 0), float(item[7] or 0)
        p_act, p_v1d = float(prev[6] or 0), float(prev[7] or 0)
        if a_act > p_act or (a_act == p_act and a_v1d > p_v1d):
            best[title] = item
    out = list(best.values())
    out.sort(key=lambda r: (-float(r[6] or 0), -float(r[7] or 0)))
    return out


def _f(v, default=0):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default=0):
    if v is None:
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def db_row_to_item(row: dict) -> list:
    """report_daily_items 行 → gen_report items 数组。"""
    sold = _i(row.get("sold"))
    actual_v1d = _f(row.get("actual_v1d"))
    v1d = _f(row.get("v1d"))
    actual_gr = _f(row.get("actual_gr"))
    vsr = _f(row.get("vsr"))
    return [
        row.get("goods_id") or "",
        row.get("title") or "",
        _f(row.get("price")),
        sold,
        _f(row.get("v1h")),
        _f(row.get("v6h")),
        actual_v1d,
        v1d,
        actual_gr,
        _f(row.get("gr")),
        _f(row.get("actual_vsr")),
        vsr,
        _f(row.get("acc")),
        _f(row.get("burst")),
        row.get("pool") or "",
        str(row.get("first_seen") or "")[:19],
        row.get("store_id") or "",
        row.get("store_name") or "",
        str(row.get("shelf_time") or "")[:19],
        _i(row.get("shop_sales")),
        _i(row.get("shop_fans")),
        _f(row.get("shop_fsr")),
        _f(row.get("goods_fsr")),
        row.get("behavior") or "",
        1 if row.get("is_virtual") else 0,
        _f(row.get("base_hours")),
        str(row.get("base_at") or "")[:19],
        row.get("anomaly") or 0,
    ]


def sold_row_to_item(row: dict, prev_sold: int | None) -> list | None:
    """由 monitor_goods + sold_daily 构造 item。无昨日基线时优先用 sd.delta。"""
    sold = _i(row.get("sold_num"))
    delta = _i(row.get("delta"))
    if prev_sold is None:
        if delta > 0:
            actual_v1d = float(delta)
        else:
            return None
    else:
        actual_v1d = max(0.0, float(sold - prev_sold))
    if actual_v1d <= 0:
        return None
    v1d = actual_v1d
    sold_base = max(prev_sold or 0, 1) if (prev_sold or 0) > 0 else max(sold - int(actual_v1d), 1)
    actual_gr = round(actual_v1d / sold_base * 100, 2) if sold_base > 0 else 0
    actual_vsr = round(actual_v1d / sold, 4) if sold > 0 else 0
    vsr = actual_vsr
    return [
        row.get("goods_id") or "",
        row.get("title") or "",
        _f(row.get("deal_price") or row.get("price")),
        sold,
        0.0,
        0.0,
        round(actual_v1d, 1),
        round(v1d, 1),
        actual_gr,
        actual_gr,
        actual_vsr,
        vsr,
        0.0,
        0.0,
        row.get("pool") or "WATCH",
        str(row.get("first_tracked_at") or row.get("first_seen") or "")[:19],
        row.get("store_id") or "",
        row.get("store_name") or "",
        "",
        0,
        0,
        0.0,
        0.0,
        "",
        1 if row.get("is_virtual") else 0,
        24.0,
        "",
        0,
    ]


def fetch_pool_stats(conn) -> dict:
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            "SELECT COUNT(*) FROM monitor_goods WHERE monitor_status IN ('active','idle')"
        )
        active = int(c.fetchone()[0] or 0)
        c.execute("SELECT COUNT(*) FROM monitor_goods")
        total = int(c.fetchone()[0] or 0)
    return {"active_goods": active, "total_goods": total}


def fetch_items_from_daily_table(conn, report_date: str) -> list:
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            """SELECT * FROM report_daily_items
               WHERE report_date=%s ORDER BY rank_no ASC, actual_v1d DESC""",
            (report_date,),
        )
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return [db_row_to_item(r) for r in rows]


def fetch_items_from_sold_daily(conn, report_date: str) -> list:
    d = date.fromisoformat(report_date)
    prev = (d - timedelta(days=1)).isoformat()
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            """
            SELECT m.goods_id, m.title, m.is_virtual, m.pool, m.store_id, m.store_name,
                   m.first_tracked_at,
                   sd.sold_num, sd.delta, sd.deal_price,
                   sp.sold_num AS prev_sold
            FROM monitor_goods m
            JOIN goods_sold_daily sd ON sd.goods_id = m.goods_id AND sd.snapshot_date = %s
            LEFT JOIN goods_sold_daily sp ON sp.goods_id = m.goods_id AND sp.snapshot_date = %s
            WHERE m.monitor_status IN ('active', 'idle')
            """,
            (report_date, prev),
        )
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
    items = []
    for r in rows:
        prev_raw = r.get("prev_sold")
        prev_sold = _i(prev_raw) if prev_raw is not None else None
        item = sold_row_to_item(r, prev_sold)
        if item and (float(item[6]) > 0 or float(item[7]) > 0):
            items.append(item)
    items.sort(key=lambda x: (-float(x[6]), -float(x[7])))
    return items


def fetch_items_for_period(conn, start_date: str, end_date: str) -> list:
    """周期内每 goods_id 保留 actual_v1d 最高的一行。"""
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            """
            SELECT DISTINCT ON (goods_id) *
            FROM report_daily_items
            WHERE report_date >= %s AND report_date <= %s
            ORDER BY goods_id, actual_v1d DESC, v1d DESC
            """,
            (start_date, end_date),
        )
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
    items = [db_row_to_item(r) for r in rows]
    items.sort(key=lambda x: (-float(x[6]), -float(x[7])))
    return items
