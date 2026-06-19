# -*- coding: utf-8 -*-
"""
报告 → PG 同步核心逻辑（对齐 docs/选品监控云服务需求规格书_v2.md §3–§6）。

- 来源：gen_report 产出的 data.js（items + meta），不是 13GB 主库平迁
- 监控池：v1d > 0 OR actual_v1d > 0 才入 monitor_goods
- 日报行：items 全量写入 report_daily_items（28 列）
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import psycopg2.extras

# 与 gen_report.COLUMNS 一致
REPORT_COLUMNS = [
    "goods_id", "title", "price", "sold", "v1h", "v6h", "actual_v1d", "v1d",
    "actual_gr", "gr", "actual_vsr", "vsr", "acc", "burst",
    "pool", "first_seen", "store_id", "store_name", "shelf_time",
    "shop_sales", "shop_fans", "shop_fsr", "goods_fsr",
    "behavior", "is_virtual", "base_hours", "base_at", "anomaly",
]

COL = {name: i for i, name in enumerate(REPORT_COLUMNS)}


def parse_data_js(data_js_path: str) -> tuple[str, dict, list]:
    with open(data_js_path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"var\s+REPORT_DATA\s*=\s*(\{.*\})\s*;\s*$", text, re.S)
    if not m:
        raise RuntimeError(f"无法解析 data.js: {data_js_path}")
    payload = json.loads(m.group(1))
    meta = payload.get("meta") or {}
    report_date = str(meta.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    items = payload.get("items") or []
    return report_date, meta, items


def _field(item: Any, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    idx = COL.get(key)
    if idx is None or not isinstance(item, (list, tuple)) or idx >= len(item):
        return default
    return item[idx]


def _num(v, default=0):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v, default=0):
    if v is None or v == "":
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if v in (1, "1", "true", "True"):
        return True
    return False


def item_to_daily_row(report_date: str, rank_no: int, item: Any) -> tuple | None:
    gid = str(_field(item, "goods_id", "") or "").strip()
    if not gid:
        return None
    return (
        report_date,
        gid,
        rank_no,
        _field(item, "title") or "",
        _num(_field(item, "price")),
        _int(_field(item, "sold")),
        _num(_field(item, "v1h")),
        _num(_field(item, "v6h")),
        _num(_field(item, "actual_v1d")),
        _num(_field(item, "v1d")),
        _num(_field(item, "actual_gr")),
        _num(_field(item, "gr")),
        _num(_field(item, "actual_vsr")),
        _num(_field(item, "vsr")),
        _num(_field(item, "acc")),
        _num(_field(item, "burst")),
        _field(item, "pool") or "",
        _field(item, "first_seen") or None,
        _field(item, "store_id") or "",
        _field(item, "store_name") or "",
        _field(item, "shelf_time") or None,
        _int(_field(item, "shop_sales")),
        _int(_field(item, "shop_fans")),
        _num(_field(item, "shop_fsr")),
        _num(_field(item, "goods_fsr")),
        _field(item, "behavior") or "",
        _bool(_field(item, "is_virtual")),
        _num(_field(item, "base_hours")),
        _field(item, "base_at") or None,
        str(_field(item, "anomaly") or ""),
    )


def qualifies_monitor_pool(item: Any) -> bool:
    v1d = _num(_field(item, "v1d"))
    actual = _num(_field(item, "actual_v1d"))
    return v1d > 0 or actual > 0


def apply_daily_report(conn, report_date: str, meta: dict, items: list, source: str = "local_gen_report") -> dict:
    """
    幂等写入：report_daily_meta + report_daily_items + monitor_goods（v1d>0 或 actual>0）
    + goods_metrics_daily；返回需 sold_history backfill 的新 goods_id 列表。
    """
    daily_rows = []
    monitor_rows = []
    metrics_rows = []
    need_backfill: list[str] = []

    for rank, item in enumerate(items, start=1):
        row = item_to_daily_row(report_date, rank, item)
        if not row:
            continue
        daily_rows.append(row)
        gid = row[1]
        v1d = row[9]
        actual_v1d = row[8]
        metrics_rows.append((gid, report_date, v1d, actual_v1d, row[11], row[15], row[16]))

        if qualifies_monitor_pool(item):
            monitor_rows.append(
                (
                    gid,
                    row[3],
                    row[26],
                    row[16],
                    v1d,
                    actual_v1d,
                    row[5],
                    report_date,
                    row[18],
                    row[19],
                    max(v1d, actual_v1d),
                )
            )

    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")

        c.execute(
            """INSERT INTO report_daily_meta (
                   report_date, row_count, virtual_count, physical_count,
                   meta_json, source, generated_at, synced_at
               ) VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW())
               ON CONFLICT (report_date) DO UPDATE SET
                   row_count=EXCLUDED.row_count,
                   virtual_count=EXCLUDED.virtual_count,
                   physical_count=EXCLUDED.physical_count,
                   meta_json=EXCLUDED.meta_json,
                   source=EXCLUDED.source,
                   generated_at=EXCLUDED.generated_at,
                   synced_at=NOW()""",
            (
                report_date,
                len(daily_rows),
                int(meta.get("virtual_v1d") or 0),
                int(meta.get("physical_v1d") or 0),
                json.dumps(meta, ensure_ascii=False),
                source,
            ),
        )

        if daily_rows:
            psycopg2.extras.execute_values(
                c,
                """INSERT INTO report_daily_items (
                       report_date, goods_id, rank_no, title, price, sold,
                       v1h, v6h, actual_v1d, v1d, actual_gr, gr, actual_vsr, vsr,
                       acc, burst, pool, first_seen, store_id, store_name, shelf_time,
                       shop_sales, shop_fans, shop_fsr, goods_fsr, behavior,
                       is_virtual, base_hours, base_at, anomaly
                   ) VALUES %s
                   ON CONFLICT (report_date, goods_id) DO UPDATE SET
                       rank_no=EXCLUDED.rank_no, title=EXCLUDED.title, price=EXCLUDED.price,
                       sold=EXCLUDED.sold, v1h=EXCLUDED.v1h, v6h=EXCLUDED.v6h,
                       actual_v1d=EXCLUDED.actual_v1d, v1d=EXCLUDED.v1d,
                       actual_gr=EXCLUDED.actual_gr, gr=EXCLUDED.gr,
                       actual_vsr=EXCLUDED.actual_vsr, vsr=EXCLUDED.vsr,
                       acc=EXCLUDED.acc, burst=EXCLUDED.burst, pool=EXCLUDED.pool,
                       first_seen=EXCLUDED.first_seen, store_id=EXCLUDED.store_id,
                       store_name=EXCLUDED.store_name, shelf_time=EXCLUDED.shelf_time,
                       shop_sales=EXCLUDED.shop_sales, shop_fans=EXCLUDED.shop_fans,
                       shop_fsr=EXCLUDED.shop_fsr, goods_fsr=EXCLUDED.goods_fsr,
                       behavior=EXCLUDED.behavior, is_virtual=EXCLUDED.is_virtual,
                       base_hours=EXCLUDED.base_hours, base_at=EXCLUDED.base_at,
                       anomaly=EXCLUDED.anomaly""",
                daily_rows,
                page_size=500,
            )

        if metrics_rows:
            psycopg2.extras.execute_values(
                c,
                """INSERT INTO goods_metrics_daily (
                       goods_id, metric_date, v1d, actual_v1d, gr, burst, pool
                   ) VALUES %s
                   ON CONFLICT (goods_id, metric_date) DO UPDATE SET
                       v1d=EXCLUDED.v1d, actual_v1d=EXCLUDED.actual_v1d,
                       gr=EXCLUDED.gr, burst=EXCLUDED.burst, pool=EXCLUDED.pool""",
                metrics_rows,
                page_size=500,
            )

        if monitor_rows:
            for row in monitor_rows:
                gid = row[0]
                c.execute("SELECT goods_id FROM goods_sync_state WHERE goods_id=%s", (gid,))
                is_new = c.fetchone() is None
                if is_new:
                    need_backfill.append(gid)

            psycopg2.extras.execute_values(
                c,
                """INSERT INTO monitor_goods (
                       goods_id, title, is_virtual, pool, last_v1d, last_actual_v1d,
                       last_sold, last_report_date, store_id, store_name, peak_v1d,
                       monitor_status, first_tracked_at, source, updated_at
                   ) VALUES %s
                   ON CONFLICT (goods_id) DO UPDATE SET
                       title=EXCLUDED.title,
                       is_virtual=EXCLUDED.is_virtual,
                       pool=EXCLUDED.pool,
                       last_v1d=EXCLUDED.last_v1d,
                       last_actual_v1d=EXCLUDED.last_actual_v1d,
                       last_sold=EXCLUDED.last_sold,
                       last_report_date=EXCLUDED.last_report_date,
                       store_id=EXCLUDED.store_id,
                       store_name=EXCLUDED.store_name,
                       peak_v1d=GREATEST(monitor_goods.peak_v1d, EXCLUDED.peak_v1d),
                       monitor_status=CASE
                           WHEN monitor_goods.monitor_status='delisted' THEN 'delisted'
                           ELSE 'active' END,
                       updated_at=NOW()""",
                monitor_rows,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',NOW(),'daily_report',NOW())",
                page_size=500,
            )

            psycopg2.extras.execute_values(
                c,
                """INSERT INTO goods_sync_state (goods_id, sold_daily_backfill_done, updated_at)
                   VALUES %s
                   ON CONFLICT (goods_id) DO NOTHING""",
                [(gid, False) for gid in need_backfill],
                page_size=500,
            )

    conn.commit()

    return {
        "report_date": report_date,
        "items_upserted": len(daily_rows),
        "monitor_pool_added": len(need_backfill),
        "monitor_pool_updated": len(monitor_rows) - len(need_backfill),
        "monitor_pool_total": len(monitor_rows),
        "need_sold_history_backfill": need_backfill[:100],
        "need_sold_history_backfill_count": len(need_backfill),
    }


def apply_sold_history_batch(conn, rows: list[dict]) -> int:
    """批量写入 sold_history 行 → goods_sold_daily。"""
    if not rows:
        return 0
    tuples = []
    goods_ids = set()
    for r in rows:
        gid = str(r["goods_id"])
        tuples.append(
            (
                gid,
                r["snapshot_date"],
                int(r.get("sold_num") or 0),
                r.get("deal_price"),
                int(r.get("delta") or 0),
                r.get("source") or "local_sync",
            )
        )
        goods_ids.add(gid)

    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        psycopg2.extras.execute_values(
            c,
            """INSERT INTO goods_sold_daily (
                   goods_id, snapshot_date, sold_num, deal_price, delta, source
               ) VALUES %s
               ON CONFLICT (goods_id, snapshot_date) DO UPDATE SET
                   sold_num=EXCLUDED.sold_num,
                   deal_price=EXCLUDED.deal_price,
                   delta=EXCLUDED.delta,
                   source=EXCLUDED.source""",
            tuples,
            page_size=1000,
        )
        for gid in goods_ids:
            c.execute(
                """UPDATE goods_sync_state SET
                       sold_daily_row_count = (
                           SELECT COUNT(*) FROM goods_sold_daily WHERE goods_id=%s
                       ),
                       updated_at=NOW()
                   WHERE goods_id=%s""",
                (gid, gid),
            )
    conn.commit()
    return len(tuples)
