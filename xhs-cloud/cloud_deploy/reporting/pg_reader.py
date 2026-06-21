# -*- coding: utf-8 -*-
"""PG 读取与报告行转换（输出 28 列，与桌面报告 data.js 对齐）。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cloud_deploy.reporting.constants import (
    DEFAULT_MIN_ACTUAL,
    DEFAULT_MIN_ACTUAL_VIRTUAL,
    DEFAULT_MIN_V1D,
    DEFAULT_MIN_V1D_VIRTUAL,
    REPORT_COLUMNS,
    item_at,
)


def thresholds_for(is_virtual: bool, min_v1d=DEFAULT_MIN_V1D, min_actual=DEFAULT_MIN_ACTUAL,
                   min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL, min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL):
    if is_virtual:
        return min_v1d_virtual, min_actual_virtual
    return min_v1d, min_actual


def passes_threshold_values(
    *,
    is_virtual: bool,
    v1d: float,
    actual_v1d: float,
    sold: float,
    min_v1d=DEFAULT_MIN_V1D,
    min_actual=DEFAULT_MIN_ACTUAL,
    min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL,
    min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL,
) -> bool:
    if sold > 200000:
        return False
    if v1d > 50000 or actual_v1d > 50000:
        return False
    th_v1d, th_actual = thresholds_for(
        is_virtual, min_v1d, min_actual, min_v1d_virtual, min_actual_virtual
    )
    return v1d > th_v1d or actual_v1d >= th_actual


def passes_threshold_row(row: dict, min_v1d=DEFAULT_MIN_V1D, min_actual=DEFAULT_MIN_ACTUAL,
                         min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL,
                         min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL) -> bool:
    return passes_threshold_values(
        is_virtual=bool(row.get("is_virtual")),
        v1d=_f(row.get("v1d")),
        actual_v1d=_f(row.get("actual_v1d")),
        sold=_f(row.get("sold")),
        min_v1d=min_v1d,
        min_actual=min_actual,
        min_v1d_virtual=min_v1d_virtual,
        min_actual_virtual=min_actual_virtual,
    )


def passes_threshold(item: list, min_v1d=DEFAULT_MIN_V1D, min_actual=DEFAULT_MIN_ACTUAL,
                     min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL, min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL) -> bool:
    return passes_threshold_values(
        is_virtual=bool(item_at(item, "is_virtual")),
        v1d=float(item_at(item, "v1d", 0) or 0),
        actual_v1d=float(item_at(item, "actual_v1d", 0) or 0),
        sold=float(item_at(item, "sold", 0) or 0),
        min_v1d=min_v1d,
        min_actual=min_actual,
        min_v1d_virtual=min_v1d_virtual,
        min_actual_virtual=min_actual_virtual,
    )


def dedup_by_title(items: list) -> list:
    best: dict[str, list] = {}
    for item in items:
        title = (item_at(item, "title", "") or "").strip()
        if not title:
            continue
        prev = best.get(title)
        if not prev:
            best[title] = item
            continue
        a_act = float(item_at(item, "actual_v1d", 0) or 0)
        a_v1d = float(item_at(item, "v1d", 0) or 0)
        p_act = float(item_at(prev, "actual_v1d", 0) or 0)
        p_v1d = float(item_at(prev, "v1d", 0) or 0)
        if a_act > p_act or (a_act == p_act and a_v1d > p_v1d):
            best[title] = item
    out = list(best.values())
    out.sort(key=lambda r: (-float(item_at(r, "actual_v1d", 0) or 0), -float(item_at(r, "v1d", 0) or 0)))
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


def _fmt_ts(v) -> str:
    if v is None or v == "":
        return ""
    s = str(v).strip()
    return s[:19] if len(s) >= 10 else s


def _norm_anomaly(v) -> int:
    if v in (None, "", 0, "0", False):
        return 0
    if str(v).strip().lower() in ("0", "false", "no"):
        return 0
    return 1


def calc_fan_sales_ratios(shop_fans: int, shop_sales: int, sold: int) -> tuple[float | None, float | None]:
    fans = _i(shop_fans)
    shop_sales_n = _i(shop_sales)
    sold_n = _i(sold)
    shop_fsr = round(fans / shop_sales_n, 6) if fans > 0 and shop_sales_n > 0 else None
    goods_fsr = round(fans / sold_n, 6) if fans > 0 and sold_n > 0 else None
    return shop_fsr, goods_fsr


def row_to_report_item(row: dict) -> list:
    """report_daily_items 行或等价 dict → 28 列 items 数组。"""
    sold = _i(row.get("sold") if row.get("sold") is not None else row.get("sold_num"))
    actual_v1d = _f(row.get("actual_v1d"))
    shop_sales = _i(row.get("shop_sales"))
    shop_fans = _i(row.get("shop_fans"))
    shop_fsr = row.get("shop_fsr")
    goods_fsr = row.get("goods_fsr")
    if shop_fsr is None or goods_fsr is None:
        calc_shop, calc_goods = calc_fan_sales_ratios(shop_fans, shop_sales, sold)
        if shop_fsr is None:
            shop_fsr = calc_shop
        if goods_fsr is None:
            goods_fsr = calc_goods

    v1d = _f(row.get("v1d"))
    if v1d <= 0 and actual_v1d > 0:
        v1d = actual_v1d
    actual_gr = _f(row.get("actual_gr"))
    gr = _f(row.get("gr"))
    if gr <= 0 and actual_gr > 0:
        gr = actual_gr
    actual_vsr = _f(row.get("actual_vsr")) or (round(actual_v1d / sold, 4) if sold > 0 else 0)
    vsr = _f(row.get("vsr"))
    if vsr <= 0 and v1d > 0 and sold > 0:
        vsr = round(v1d / sold, 4)
    elif vsr <= 0 and actual_vsr > 0:
        vsr = actual_vsr

    base_hours = row.get("base_hours")
    values = {
        "goods_id": row.get("goods_id") or "",
        "title": row.get("title") or "",
        "price": _f(row.get("price") if row.get("price") is not None else row.get("deal_price")),
        "sold": sold,
        "v1h": _f(row.get("v1h")),
        "v6h": _f(row.get("v6h")),
        "actual_v1d": actual_v1d,
        "v1d": v1d,
        "actual_gr": actual_gr,
        "gr": gr,
        "actual_vsr": actual_vsr,
        "vsr": vsr,
        "acc": _f(row.get("acc")),
        "burst": _f(row.get("burst")),
        "pool": row.get("pool") or "WATCH",
        "first_seen": _fmt_ts(row.get("first_seen")),
        "store_id": row.get("store_id") or "",
        "store_name": row.get("store_name") or "",
        "shelf_time": _fmt_ts(row.get("shelf_time")),
        "shop_sales": shop_sales,
        "shop_fans": shop_fans,
        "shop_fsr": _f(shop_fsr) if shop_fsr is not None else 0.0,
        "goods_fsr": _f(goods_fsr) if goods_fsr is not None else 0.0,
        "behavior": row.get("behavior") or "",
        "is_virtual": 1 if row.get("is_virtual") else 0,
        "base_hours": _f(base_hours) if base_hours not in (None, "") else 0.0,
        "base_at": _fmt_ts(row.get("base_at")),
        "anomaly": _norm_anomaly(row.get("anomaly")),
    }
    return [values[k] for k in REPORT_COLUMNS]


def db_row_to_item(row: dict) -> list:
    """report_daily_items 行 → 28 列 items 数组。"""
    return row_to_report_item(row)


def _pick_str(*vals: Any) -> str:
    for v in vals:
        s = str(v or "").strip()
        if s:
            return s
    return ""


def _pick_first_seen(row: dict) -> str:
    """真实首次发现：优先历史 report / monitor_goods.first_seen，勿用入云时间 first_tracked_at。"""
    for key in ("mg_first_seen", "rdi_first_seen_min", "rdi_first_seen"):
        v = row.get(key)
        if v is None or v == "":
            continue
        s = str(v).strip()
        if len(s) >= 10:
            return s[:19]
    ft = row.get("first_tracked_at")
    return str(ft)[:19] if ft else ""


def _pick_int(*vals: Any) -> int:
    for v in vals:
        n = _i(v, 0)
        if n > 0:
            return n
    return 0


def sold_row_to_item(row: dict, prev_sold: int | None) -> list | None:
    """由 monitor_goods + goods_sold_daily (+ 可选 report_daily_items 补齐) 构造报告 item。"""
    sold = _i(row.get("sold_num"))
    delta = _i(row.get("delta"))
    gm_actual = _f(row.get("gm_actual_v1d"))
    gm_v1d = _f(row.get("gm_v1d"))
    gm_gr = _f(row.get("gm_gr"))
    rdi_actual = _f(row.get("rdi_actual_v1d"))
    rdi_v1d = _f(row.get("rdi_v1d"))

    if prev_sold is None:
        if delta > 0:
            actual_v1d = float(delta)
        elif gm_actual > 0:
            actual_v1d = gm_actual
        elif rdi_actual > 0:
            actual_v1d = rdi_actual
        else:
            return None
    else:
        actual_v1d = max(0.0, float(sold - prev_sold))
        if actual_v1d <= 0 and delta > 0:
            actual_v1d = float(delta)
        elif actual_v1d <= 0 and gm_actual > 0:
            actual_v1d = gm_actual

    if actual_v1d <= 0:
        return None

    v1d = rdi_v1d if rdi_v1d > 0 else (gm_v1d if gm_v1d > 0 else actual_v1d)
    sold_base = max(prev_sold or 0, 1) if (prev_sold or 0) > 0 else max(sold - int(actual_v1d), 1)
    actual_gr = _f(row.get("rdi_actual_gr")) or round(actual_v1d / sold_base * 100, 2)
    gr = _f(row.get("rdi_gr")) or gm_gr or actual_gr
    actual_vsr = _f(row.get("rdi_actual_vsr")) or (round(actual_v1d / sold, 4) if sold > 0 else 0)
    vsr = _f(row.get("rdi_vsr")) or (round(v1d / sold, 4) if sold > 0 and v1d != actual_v1d else actual_vsr)
    price = _f(row.get("deal_price") or row.get("rdi_price"))
    title = _pick_str(row.get("title"), row.get("rdi_title"))
    store_id = _pick_str(row.get("store_id"), row.get("rdi_store_id"))
    store_name = _pick_str(row.get("store_name"), row.get("rdi_store_name"))
    shop_sales = _pick_int(row.get("shop_sales"), row.get("rdi_shop_sales"), row.get("mg_shop_sales"))
    shop_fans = _pick_int(row.get("shop_fans"), row.get("rdi_shop_fans"), row.get("mg_shop_fans"))
    behavior = _pick_str(row.get("rdi_behavior"))
    pool = _pick_str(row.get("pool"), row.get("rdi_pool")) or "WATCH"
    is_virtual = row.get("is_virtual")
    if is_virtual is None:
        is_virtual = row.get("rdi_is_virtual")

    merged = {
        "goods_id": row.get("goods_id") or "",
        "title": title,
        "price": price,
        "sold": sold,
        "v1h": row.get("rdi_v1h"),
        "v6h": row.get("rdi_v6h"),
        "actual_v1d": round(actual_v1d, 1),
        "v1d": round(v1d, 1),
        "actual_gr": actual_gr,
        "gr": gr,
        "actual_vsr": actual_vsr,
        "vsr": vsr,
        "acc": row.get("rdi_acc"),
        "burst": row.get("rdi_burst"),
        "pool": pool,
        "first_seen": _pick_first_seen(row),
        "store_id": store_id,
        "store_name": store_name,
        "shelf_time": row.get("rdi_shelf_time"),
        "shop_sales": shop_sales,
        "shop_fans": shop_fans,
        "shop_fsr": row.get("rdi_shop_fsr"),
        "goods_fsr": row.get("rdi_goods_fsr"),
        "behavior": behavior,
        "is_virtual": is_virtual,
        "base_hours": row.get("rdi_base_hours"),
        "base_at": row.get("rdi_base_at"),
        "anomaly": row.get("rdi_anomaly") or 0,
    }
    return row_to_report_item(merged)


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


def _monitor_goods_has_shop_cols(conn) -> bool:
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            """SELECT 1 FROM information_schema.columns
               WHERE table_schema='xhs_monitor' AND table_name='monitor_goods'
                 AND column_name='shop_sales' LIMIT 1"""
        )
        return c.fetchone() is not None


def _monitor_goods_has_first_seen(conn) -> bool:
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            """SELECT 1 FROM information_schema.columns
               WHERE table_schema='xhs_monitor' AND table_name='monitor_goods'
                 AND column_name='first_seen' LIMIT 1"""
        )
        return c.fetchone() is not None


def fetch_items_from_sold_daily(conn, report_date: str) -> list:
    d = date.fromisoformat(report_date)
    prev = (d - timedelta(days=1)).isoformat()
    mg_shop = (
        "m.shop_sales AS mg_shop_sales, m.shop_fans AS mg_shop_fans,"
        if _monitor_goods_has_shop_cols(conn)
        else "NULL::int AS mg_shop_sales, NULL::int AS mg_shop_fans,"
    )
    mg_fs = (
        "m.first_seen AS mg_first_seen,"
        if _monitor_goods_has_first_seen(conn)
        else "NULL::timestamptz AS mg_first_seen,"
    )
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        c.execute(
            f"""
            SELECT m.goods_id, m.title, m.is_virtual, m.pool, m.store_id, m.store_name,
                   m.first_tracked_at,
                   {mg_fs}
                   {mg_shop}
                   (SELECT MIN(r.first_seen)
                    FROM report_daily_items r
                    WHERE r.goods_id = m.goods_id AND r.first_seen IS NOT NULL) AS rdi_first_seen_min,
                   sd.sold_num, sd.delta, sd.deal_price,
                   sp.sold_num AS prev_sold,
                   gm.actual_v1d AS gm_actual_v1d, gm.v1d AS gm_v1d, gm.gr AS gm_gr,
                   rdi.title AS rdi_title,
                   rdi.price AS rdi_price,
                   rdi.actual_v1d AS rdi_actual_v1d,
                   rdi.v1d AS rdi_v1d,
                   rdi.actual_gr AS rdi_actual_gr,
                   rdi.gr AS rdi_gr,
                   rdi.actual_vsr AS rdi_actual_vsr,
                   rdi.vsr AS rdi_vsr,
                   rdi.v1h AS rdi_v1h,
                   rdi.v6h AS rdi_v6h,
                   rdi.acc AS rdi_acc,
                   rdi.burst AS rdi_burst,
                   rdi.pool AS rdi_pool,
                   rdi.first_seen AS rdi_first_seen,
                   rdi.store_id AS rdi_store_id,
                   rdi.store_name AS rdi_store_name,
                   rdi.shelf_time AS rdi_shelf_time,
                   rdi.shop_sales AS rdi_shop_sales,
                   rdi.shop_fans AS rdi_shop_fans,
                   rdi.shop_fsr AS rdi_shop_fsr,
                   rdi.goods_fsr AS rdi_goods_fsr,
                   rdi.behavior AS rdi_behavior,
                   rdi.is_virtual AS rdi_is_virtual,
                   rdi.base_hours AS rdi_base_hours,
                   rdi.base_at AS rdi_base_at,
                   rdi.anomaly AS rdi_anomaly
            FROM monitor_goods m
            JOIN goods_sold_daily sd ON sd.goods_id = m.goods_id AND sd.snapshot_date = %s
            LEFT JOIN goods_sold_daily sp ON sp.goods_id = m.goods_id AND sp.snapshot_date = %s
            LEFT JOIN goods_metrics_daily gm
                   ON gm.goods_id = m.goods_id AND gm.metric_date = %s
            LEFT JOIN LATERAL (
                SELECT *
                FROM report_daily_items r
                WHERE r.goods_id = m.goods_id
                ORDER BY r.report_date DESC
                LIMIT 1
            ) rdi ON TRUE
            WHERE m.monitor_status IN ('active', 'idle')
            """,
            (report_date, prev, report_date),
        )
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
    items = []
    for r in rows:
        prev_raw = r.get("prev_sold")
        prev_sold = _i(prev_raw) if prev_raw is not None else None
        item = sold_row_to_item(r, prev_sold)
        if item and (
            float(item_at(item, "actual_v1d", 0) or 0) > 0
            or float(item_at(item, "v1d", 0) or 0) > 0
        ):
            items.append(item)
    items.sort(key=lambda x: (-float(item_at(x, "actual_v1d", 0) or 0), -float(item_at(x, "v1d", 0) or 0)))
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
    items.sort(key=lambda x: (-float(item_at(x, "actual_v1d", 0) or 0), -float(item_at(x, "v1d", 0) or 0)))
    return items
