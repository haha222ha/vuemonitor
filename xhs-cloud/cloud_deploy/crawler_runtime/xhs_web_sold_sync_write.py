# -*- coding: utf-8 -*-
"""
【数据源⑤】Web HTTP 销量快照同步 — 对齐 APP 关键词扫描落库口径。

- 每次扫描必写 sold_snapshots（含销量未变），供 velocity_1d 重算
- sold_history 仅维护当日行；delta 仅在销量上升时累加
- goods.sold_num 仅在 API 销量上升时更新（不向下覆盖）
- 缺失店铺/标题字段空值补齐（不覆盖已有值）
"""
from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_DB = os.path.join(APP_DIR, "crawl_data", "xhs_burst_monitor.db")
FOCUS_DB = os.path.join(APP_DIR, "crawl_data", "xhs_focus_monitor.db")

_logger = logging.getLogger(__name__)
DATA_SOURCE = "web_sold_sync"


def _db_conn():
    conn = sqlite3.connect(MAIN_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _focus_conn():
    conn = sqlite3.connect(FOCUS_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _sync_to_focus_db(goods_id, detail, new_sold, old_sold, ds, now_str, today):
    """同步写入焦点库（备份库），与爆品库口径对齐。"""
    conn = None
    try:
        conn = _focus_conn()
        c = conn.cursor()
        c.execute("SELECT sold_num, deal_price FROM goods WHERE goods_id=?", (goods_id,))
        row = c.fetchone()
        deal_price = float(detail.get("deal_price") or (row[1] if row else 0) or 0)

        if row:
            f_old_sold = int(row[0] or 0)
            if new_sold > f_old_sold:
                delta = new_sold - f_old_sold
                c.execute(
                    """UPDATE goods SET
                       sold_num=?, last_seen=?,
                       scan_count=COALESCE(scan_count,0)+1,
                       data_source=?
                       WHERE goods_id=?""",
                    (new_sold, now_str, ds, goods_id),
                )
                c.execute(
                    "SELECT delta FROM sold_history WHERE goods_id=? AND snapshot_date=?",
                    (goods_id, today),
                )
                if c.fetchone():
                    c.execute(
                        "UPDATE sold_history SET sold_num=?, deal_price=?, delta=delta+? WHERE goods_id=? AND snapshot_date=?",
                        (new_sold, deal_price, delta, goods_id, today),
                    )
                else:
                    c.execute(
                        "INSERT INTO sold_history (goods_id, snapshot_date, sold_num, deal_price, delta) VALUES (?,?,?,?,?)",
                        (goods_id, today, new_sold, deal_price, delta),
                    )
            else:
                c.execute(
                    """UPDATE goods SET
                       last_seen=?,
                       scan_count=COALESCE(scan_count,0)+1,
                       data_source=?
                       WHERE goods_id=?""",
                    (now_str, ds, goods_id),
                )
                c.execute(
                    "SELECT delta FROM sold_history WHERE goods_id=? AND snapshot_date=?",
                    (goods_id, today),
                )
                if not c.fetchone():
                    c.execute(
                        "INSERT INTO sold_history (goods_id, snapshot_date, sold_num, deal_price, delta) VALUES (?,?,?,?,0)",
                        (goods_id, today, new_sold, deal_price),
                    )
        else:
            title = str(detail.get("product_name") or detail.get("shop_name") or "")
            store_id = str(detail.get("shop_id") or "")
            store_name = str(detail.get("shop_name") or "")
            c.execute(
                """INSERT INTO goods (goods_id, title, deal_price, sold_num, store_id, store_name,
                   first_seen, last_seen, scan_count, data_source)
                   VALUES (?,?,?,?,?,?,?,?,1,?)""",
                (goods_id, title, deal_price, new_sold, store_id, store_name, now_str, now_str, ds),
            )
            c.execute(
                "INSERT INTO sold_history (goods_id, snapshot_date, sold_num, deal_price, delta) VALUES (?,?,?,?,0)",
                (goods_id, today, new_sold, deal_price),
            )
        conn.commit()
    except Exception as e:
        _logger.warning("焦点库同步失败 %s: %s", goods_id, e)
    finally:
        if conn:
            conn.close()


def _apply_missing_fields(c, goods_id, detail, now_str):
    """⑤ 附加：主库缺失的店铺/标题字段用 HTTP 结果补齐（不覆盖已有值）。"""
    store_id = str(detail.get("shop_id") or "")
    store_name = str(detail.get("shop_name") or "")
    shop_fans = str(detail.get("fans_count") or 0)
    shop_sales = str(detail.get("shop_total_sales") or 0)
    title = str(detail.get("product_name") or "")
    shop_item_score = str(detail.get("shop_score") or "")
    region = str(detail.get("ship_from") or "")
    category_tag = str(detail.get("category_tag") or "")

    c.execute(
        """UPDATE goods SET
            title=COALESCE(NULLIF(title,''),?),
            store_id=COALESCE(NULLIF(store_id,''),?),
            store_name=COALESCE(NULLIF(store_name,''),?),
            shop_fans=CASE WHEN (shop_fans IS NULL OR shop_fans='' OR shop_fans='0')
                            AND ?!='0' AND ?!='' THEN ? ELSE shop_fans END,
            shop_sales=CASE WHEN (shop_sales IS NULL OR shop_sales='' OR shop_sales='0')
                             AND ?!='0' AND ?!='' THEN ? ELSE shop_sales END,
            shop_item_score=COALESCE(NULLIF(shop_item_score,''),?),
            region=COALESCE(NULLIF(region,''),?),
            goods_type_detail=COALESCE(NULLIF(goods_type_detail,''),?),
            detail_fetched=CASE WHEN COALESCE(detail_fetched,0)=0 THEN 1 ELSE detail_fetched END,
            detail_fetch_time=CASE WHEN COALESCE(detail_fetched,0)=0 THEN ? ELSE detail_fetch_time END
           WHERE goods_id=?""",
        (
            title,
            store_id, store_name,
            shop_fans, shop_fans, shop_fans,
            shop_sales, shop_sales, shop_sales,
            shop_item_score,
            region,
            category_tag,
            now_str,
            goods_id,
        ),
    )


def _ensure_today_history(c, goods_id, today, sold_num, deal_price, delta_add=0):
    """确保当日 sold_history 存在；delta_add>0 时累加增量。"""
    c.execute(
        "SELECT sold_num, delta FROM sold_history WHERE goods_id=? AND snapshot_date=?",
        (goods_id, today),
    )
    row = c.fetchone()
    if row:
        if delta_add > 0:
            c.execute(
                """UPDATE sold_history SET
                   sold_num=?, deal_price=?, delta=delta+?
                   WHERE goods_id=? AND snapshot_date=?""",
                (sold_num, deal_price, delta_add, goods_id, today),
            )
        return

    c.execute(
        """INSERT INTO sold_history
           (goods_id, snapshot_date, sold_num, deal_price, delta)
           VALUES (?,?,?,?,?)""",
        (goods_id, today, sold_num, deal_price, max(0, int(delta_add))),
    )


def sync_sold_to_main_db(goods_id, detail, enrich_missing=True, data_source=None):
    """
    APP 同款销量快照落库（非粗暴覆盖原表）：
    - 必写 sold_snapshots
    - 维护当日 sold_history
    - sold_num 仅在上行时更新
    data_source: web_sold_sync(⑤) / web_full_sold_sync(⑥) / 自定义
    """
    ds = data_source or DATA_SOURCE
    try:
        new_sold = int(detail.get("real_sales") or 0)
    except (TypeError, ValueError):
        return False, "invalid_sales", 0, 0

    if new_sold <= 0:
        return False, "no_sales", 0, 0

    conn = None
    try:
        conn = _db_conn()
        c = conn.cursor()
        c.execute("SELECT sold_num, deal_price FROM goods WHERE goods_id=?", (goods_id,))
        row = c.fetchone()
        if not row:
            return False, "not_in_main", 0, new_sold

        old_sold = int(row[0] or 0)
        deal_price = float(row[1] or 0)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")

        c.execute(
            "INSERT INTO sold_snapshots (goods_id, sold_num, snapshot_time, data_source) VALUES (?,?,?,?)",
            (goods_id, new_sold, now_str, ds),
        )

        if new_sold > old_sold:
            delta = new_sold - old_sold
            c.execute(
                """UPDATE goods SET
                   sold_num=?, last_seen=?,
                   scan_count=COALESCE(scan_count,0)+1,
                   data_source=?
                   WHERE goods_id=?""",
                (new_sold, now_str, ds, goods_id),
            )
            _ensure_today_history(c, goods_id, today, new_sold, deal_price, delta_add=delta)
            status = "updated"
            effective_sold = new_sold
        elif new_sold == old_sold:
            c.execute(
                """UPDATE goods SET
                   last_seen=?,
                   scan_count=COALESCE(scan_count,0)+1,
                   data_source=?
                   WHERE goods_id=?""",
                (now_str, ds, goods_id),
            )
            _ensure_today_history(c, goods_id, today, new_sold, deal_price, delta_add=0)
            status = "snapshot"
        else:
            c.execute(
                """UPDATE goods SET
                   last_seen=?,
                   scan_count=COALESCE(scan_count,0)+1,
                   data_source=?
                   WHERE goods_id=?""",
                (now_str, ds, goods_id),
            )
            _ensure_today_history(c, goods_id, today, old_sold, deal_price, delta_add=0)
            status = "snapshot"

        if enrich_missing:
            _apply_missing_fields(c, goods_id, detail, now_str)

        conn.commit()
        _sync_to_focus_db(goods_id, detail, new_sold, old_sold, ds, now_str, today)
        return True, status, old_sold, new_sold if new_sold >= old_sold else old_sold
    except Exception as e:
        _logger.warning("销量快照落库失败 %s: %s", goods_id, e)
        return False, "db_error", 0, new_sold
    finally:
        if conn:
            conn.close()


def recalc_velocity_after_sync(goods_ids):
    """批量重算 velocity（⑤ 每批扫描结束后调用）。"""
    if not goods_ids:
        return 0
    from xhs_sold_velocity import recalc_velocity_for_goods

    conn = None
    try:
        conn = _db_conn()
        c = conn.cursor()
        n = recalc_velocity_for_goods(c, goods_ids)
        conn.commit()
        return n
    except Exception as e:
        _logger.warning("velocity 重算失败: %s", e)
        return 0
    finally:
        if conn:
            conn.close()
