# -*- coding: utf-8 -*-
"""
详情补全面板 — 共享数据库查询与统计（候选商品 / 状态计数）

统计口径（与 gen_report / xhs_report_scope 一致）:
  虚拟: velocity_1d > 1 OR actual_velocity_1d >= 1
  实体: velocity_1d > 5 OR actual_velocity_1d >= 5
  待补全 = 上述高增量 + detail_fetched=0
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime

from xhs_report_scope import (
    SCOPE_LABEL,
    combined_increment_sql,
    increment_sql,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
DB_PATH = os.path.join(DATA_DIR, "xhs_burst_monitor.db")
PANEL_LOG_PATH = os.path.join(DATA_DIR, "detail_enrich_panel.log")

# 兼容旧引用
VELOCITY_MIN = 5
SCOPE_WHERE = "lifecycle IN (0,1,2)"

GOODS_GONE_CODES = frozenset({600, 602})
GOODS_GONE_MSG = {
    600: "商品已下架",
    602: "商品不存在",
}
POOL_ORDER_SQL = (
    "CASE WHEN pool='BURST' THEN 0 WHEN pool='ACCEL' THEN 1 "
    "WHEN pool='WATCH' THEN 2 ELSE 3 END, "
    "COALESCE(actual_velocity_1d, 0) DESC, velocity_1d DESC"
)


def db_conn(timeout: int = 60):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def is_goods_gone_code(code) -> bool:
    return isinstance(code, int) and code in GOODS_GONE_CODES


def mark_goods_gone_with_conn(c, goods_id: str, code: int = 600) -> None:
    """将商品标为已删除/下架：lifecycle=3，并写 detail_fetched 避免重复补全。"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute(
            """UPDATE goods SET
               lifecycle=3, delisted=1,
               detail_fetched=1, detail_fetch_time=?,
               last_seen=?, scan_weight=0
               WHERE goods_id=?""",
            (now_str, now_str, goods_id),
        )
    except sqlite3.OperationalError:
        c.execute(
            """UPDATE goods SET
               lifecycle=3,
               detail_fetched=1, detail_fetch_time=?,
               last_seen=?, scan_weight=0
               WHERE goods_id=?""",
            (now_str, now_str, goods_id),
        )


def mark_goods_gone(goods_id: str, code: int = 600, source: str = "detail_enrich") -> bool:
    conn = None
    try:
        conn = db_conn(timeout=30)
        c = conn.cursor()
        mark_goods_gone_with_conn(c, goods_id, code)
        conn.commit()
        label = GOODS_GONE_MSG.get(code, f"code={code}")
        append_panel_log("GONE", f"{goods_id[:16]} {label} (lifecycle=3)")
        try:
            from xhs_goods_risk_registry import record_goods_risk

            record_goods_risk(goods_id, code=code, source=source)
        except Exception as e:
            append_panel_log("GONE", f"{goods_id[:16]} 风险注册表写入跳过: {e}")
        return True
    except Exception as e:
        append_panel_log("GONE", f"{goods_id[:16]} 标记失败 code={code}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def append_panel_log(tag: str, message: str) -> None:
    """写入面板统一日志文件。"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(PANEL_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}][{tag}] {message}\n")
    except Exception:
        pass


def _count_segment(c, is_virtual: bool, *, detail_fetched: int | None = None) -> int:
    where, params = increment_sql(is_virtual)
    sql = f"SELECT COUNT(*) FROM goods WHERE {where}"
    if detail_fetched is not None:
        sql += " AND COALESCE(detail_fetched, 0) = ?"
        params = (*params, detail_fetched)
    return c.execute(sql, params).fetchone()[0]


def query_panel_stats(today_used_mem: int = 0, today: str | None = None) -> dict:
    """面板「当前状态」统一统计（双赛道，同 gen_report）。"""
    today = today or datetime.now().strftime("%Y-%m-%d")
    updated_at = datetime.now().strftime("%H:%M:%S")
    conn = None
    try:
        conn = db_conn()
        c = conn.cursor()

        virtual_total = _count_segment(c, True)
        physical_total = _count_segment(c, False)
        virtual_enriched = _count_segment(c, True, detail_fetched=1)
        physical_enriched = _count_segment(c, False, detail_fetched=1)
        virtual_pending = _count_segment(c, True, detail_fetched=0)
        physical_pending = _count_segment(c, False, detail_fetched=0)

        total_v1d = virtual_total + physical_total
        enriched_v1d = virtual_enriched + physical_enriched
        pending = virtual_pending + physical_pending

        c.execute(
            f"""SELECT COUNT(*) FROM goods
               WHERE {combined_increment_sql()}
                 AND COALESCE(detail_fetched, 0) = 1"""
        )
        enriched_all = c.fetchone()[0]

        c.execute(
            f"""SELECT COUNT(*) FROM goods
               WHERE {combined_increment_sql()}
                 AND COALESCE(detail_fetched, 0) = 1
                 AND detail_fetch_time >= ?""",
            (today,),
        )
        used_db = c.fetchone()[0]

        used_today = max(today_used_mem, used_db)
        coverage = round(enriched_v1d / total_v1d * 100, 1) if total_v1d else 0.0

        return {
            "used_today": used_today,
            "pending": pending,
            "total_v1d": total_v1d,
            "enriched_v1d": enriched_v1d,
            "enriched": enriched_all,
            "virtual_total": virtual_total,
            "physical_total": physical_total,
            "virtual_enriched": virtual_enriched,
            "physical_enriched": physical_enriched,
            "virtual_pending": virtual_pending,
            "physical_pending": physical_pending,
            "coverage": coverage,
            "scope_label": SCOPE_LABEL,
            "updated_at": updated_at,
        }
    except Exception as e:
        append_panel_log("STATS", f"查询失败: {e}")
        return {
            "used_today": today_used_mem,
            "pending": 0,
            "total_v1d": 0,
            "enriched_v1d": 0,
            "enriched": 0,
            "virtual_total": 0,
            "physical_total": 0,
            "virtual_enriched": 0,
            "physical_enriched": 0,
            "virtual_pending": 0,
            "physical_pending": 0,
            "coverage": 0.0,
            "scope_label": SCOPE_LABEL,
            "updated_at": updated_at,
            "error": str(e),
        }
    finally:
        if conn:
            conn.close()


def fetch_pending_candidates(
    top_n: int = 500,
    min_sold: int = 0,
    pool_priority: bool = True,
    extra_skip_ids: set | None = None,
    log_func=None,
) -> list[dict]:
    """
    获取待详情补全候选（虚拟 v1d>1/真实≥1，实体 v1d>5/真实≥5，detail_fetched=0）。
    """
    log = log_func or (lambda _m: None)
    skip = extra_skip_ids or set()
    order = POOL_ORDER_SQL if pool_priority else "COALESCE(actual_velocity_1d, 0) DESC, velocity_1d DESC"
    limit = min(top_n if top_n < 999999 else 50000, 50000)
    sql_limit = limit * 2 if skip else limit

    t0 = time.time()
    conn = None
    log(f"[候选] SQL 查询中 (最多 {sql_limit} 条)...")
    for attempt in range(4):
        try:
            conn = db_conn(timeout=8)
            c = conn.cursor()
            c.execute(
                f"""
                SELECT goods_id, title, sold_num, deal_price, store_id, store_name,
                       velocity_1d, daily_growth_rate, burst_score, pool, keyword,
                       is_virtual, COALESCE(actual_velocity_1d, 0)
                FROM goods
                WHERE {combined_increment_sql()}
                  AND sold_num >= ?
                  AND COALESCE(detail_fetched, 0) = 0
                ORDER BY {order}
                LIMIT ?
                """,
                (min_sold, sql_limit),
            )
            rows = c.fetchall()
            break
        except sqlite3.OperationalError as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            if "locked" in str(e).lower() and attempt < 3:
                wait = 1.5 * (attempt + 1)
                log(f"[候选] DB 繁忙，{wait:.1f}s 后重试 ({attempt + 1}/3)...")
                time.sleep(wait)
                continue
            log(f"[候选] 查询失败: {e}")
            append_panel_log("CAND", f"error={e}")
            return []
        except Exception as e:
            log(f"[候选] 查询失败: {e}")
            append_panel_log("CAND", f"error={e}")
            return []
    else:
        return []

    try:
        results = []
        skipped_jsonl = 0
        for row in rows:
            gid = row[0]
            if gid in skip:
                skipped_jsonl += 1
                continue
            results.append({
                "goods_id": gid,
                "title": row[1] or "",
                "sold_num": row[2] or 0,
                "deal_price": row[3] or 0,
                "store_id": row[4] or "",
                "store_name": row[5] or "",
                "velocity_1d": row[6] or 0,
                "daily_growth_rate": row[7] or 0,
                "burst_score": row[8] or 0,
                "pool": row[9] or "WATCH",
                "keyword": row[10] or "",
                "is_virtual": bool(row[11]),
                "actual_velocity_1d": row[12] or 0,
            })
            if len(results) >= limit:
                break
        log(
            f"[候选] 查询完成 {len(results)} 个 "
            f"({SCOPE_LABEL}, SQL {len(rows)} 行, JSONL跳过 {skipped_jsonl}, {time.time()-t0:.1f}s)"
        )
        append_panel_log("CAND", f"count={len(results)} skipped_jsonl={skipped_jsonl}")
        return results
    except Exception as e:
        log(f"[候选] 结果处理失败: {e}")
        append_panel_log("CAND", f"error={e}")
        return []
    finally:
        if conn:
            conn.close()


def fetch_app_serial_candidates(top_n: int = 999999, log_func=None) -> list[dict]:
    """APP 串行详情专用候选（字段较少）。"""
    full = fetch_pending_candidates(
        top_n=top_n,
        min_sold=0,
        pool_priority=True,
        log_func=log_func,
    )
    return [
        {
            "goods_id": x["goods_id"],
            "title": x["title"],
            "store_id": x["store_id"],
            "velocity_1d": x["velocity_1d"],
            "pool": x["pool"],
        }
        for x in full
    ]
