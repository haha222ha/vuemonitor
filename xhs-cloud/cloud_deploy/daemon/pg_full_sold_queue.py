# -*- coding: utf-8 -*-
"""
PG 版 ⑥ 补缺队列 — 对齐 xhs_full_sold_queue_db，数据源为 monitor_goods。
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from cloud_deploy.cloud_api.database_pg import _conn, init_db

_logger = logging.getLogger(__name__)

QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS full_sold_queue (
    goods_id VARCHAR(32) PRIMARY KEY,
    title TEXT DEFAULT '',
    sold_num INT DEFAULT 0,
    velocity_1d NUMERIC(12,2) DEFAULT 0,
    pool VARCHAR(16) DEFAULT 'WATCH',
    last_seen TIMESTAMPTZ,
    queue_date DATE NOT NULL,
    last_sync_at TIMESTAMPTZ,
    sync_fail_count INT DEFAULT 0,
    frozen_at TIMESTAMPTZ,
    freeze_code INT DEFAULT 0,
    seeded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fsq_pending
    ON full_sold_queue (queue_date, last_sync_at, frozen_at, velocity_1d);
"""


def _today() -> str:
    return date.today().isoformat()


def _ensure_queue_table(c) -> None:
    c.execute("SET search_path TO xhs_monitor, public")
    for stmt in QUEUE_DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            c.execute(s)


def queue_stats(queue_date=None, queue_db=None):
    del queue_db
    qd = queue_date or _today()
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            c.execute("SELECT COUNT(*) FROM full_sold_queue WHERE queue_date=%s", (qd,))
            total = int(c.fetchone()[0] or 0)
            c.execute(
                """SELECT COUNT(*) FROM full_sold_queue
                   WHERE queue_date=%s AND last_sync_at IS NULL AND frozen_at IS NULL""",
                (qd,),
            )
            pending = int(c.fetchone()[0] or 0)
            c.execute(
                "SELECT COUNT(*) FROM full_sold_queue WHERE queue_date=%s AND frozen_at IS NOT NULL",
                (qd,),
            )
            frozen = int(c.fetchone()[0] or 0)
        conn.commit()
        return {
            "queue_date": qd,
            "total": total,
            "pending": pending,
            "synced": max(0, total - pending - frozen),
            "frozen": frozen,
        }
    finally:
        conn.close()


def count_pending(queue_date=None, queue_db=None):
    return queue_stats(queue_date, queue_db)["pending"]


def seed_full_sold_queue(
    main_db=None,
    queue_db=None,
    low_v1d_only=False,
    skip_today=True,
    min_sold=1,
    log_func=None,
    limit=0,
):
    del main_db, queue_db
    log = log_func or (lambda _m: None)
    qd = _today()
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            c.execute("DELETE FROM full_sold_queue WHERE queue_date < %s", (qd,))
            c.execute("SELECT COUNT(*) FROM full_sold_queue WHERE queue_date=%s", (qd,))
            existing = int(c.fetchone()[0] or 0)
            batch_limit = int(limit or 0)
            if batch_limit > 0 and existing >= batch_limit:
                log(f"补缺队列已有 {existing:,} 条，跳过 seed")
                return existing
            if batch_limit == 0 and existing > 0:
                log(f"补缺队列已有今日 {existing:,} 条，跳过 seed")
                return existing

            v1d_filter = " AND COALESCE(m.last_v1d,0) <= 0" if low_v1d_only else ""
            skip_sql = ""
            if skip_today:
                skip_sql = """
                  AND NOT EXISTS (
                    SELECT 1 FROM goods_sold_snapshots s
                    WHERE s.goods_id = m.goods_id
                      AND s.snapshot_time::date = CURRENT_DATE
                  )
                """
            limit_sql = f" LIMIT {batch_limit}" if batch_limit > 0 else ""

            c.execute(
                f"""INSERT INTO full_sold_queue
                    (goods_id, title, sold_num, velocity_1d, pool, last_seen, queue_date, seeded_at)
                    SELECT m.goods_id,
                           COALESCE(m.title,''),
                           COALESCE(m.last_sold,0),
                           COALESCE(m.last_v1d,0),
                           COALESCE(m.pool,'WATCH'),
                           m.updated_at,
                           %s::date,
                           NOW()
                    FROM monitor_goods m
                    WHERE m.monitor_status IN ('active','idle')
                      AND COALESCE(m.last_sold,0) >= %s
                      {v1d_filter}
                      {skip_sql}
                      AND NOT EXISTS (
                        SELECT 1 FROM full_sold_queue q
                        WHERE q.goods_id = m.goods_id AND q.queue_date = %s::date
                      )
                    ORDER BY COALESCE(m.last_sold,0) DESC, m.updated_at DESC
                    {limit_sql}
                    ON CONFLICT (goods_id) DO UPDATE SET
                        queue_date=EXCLUDED.queue_date,
                        title=EXCLUDED.title,
                        sold_num=EXCLUDED.sold_num,
                        velocity_1d=EXCLUDED.velocity_1d,
                        pool=EXCLUDED.pool,
                        last_seen=EXCLUDED.last_seen,
                        seeded_at=EXCLUDED.seeded_at,
                        last_sync_at=NULL,
                        sync_fail_count=0,
                        frozen_at=NULL""",
                (qd, int(min_sold or 1), qd),
            )
            inserted = c.rowcount if c.rowcount >= 0 else 0
            c.execute("SELECT COUNT(*) FROM full_sold_queue WHERE queue_date=%s", (qd,))
            total = int(c.fetchone()[0] or 0)
        conn.commit()
        log(f"PG 补缺队列 seed: 本次+{inserted:,} 累计 {total:,} 条")
        return total
    finally:
        conn.close()


def ensure_queue_seeded(
    low_v1d_only=False,
    skip_today=True,
    min_pending=100,
    main_db=None,
    queue_db=None,
    log_func=None,
    seed_limit=0,
):
    pending = count_pending()
    if pending >= min_pending:
        return pending, False
    log = log_func or (lambda _m: None)
    log(f"补缺队列待扫 {pending} 条，开始 seed...")
    seed_full_sold_queue(
        low_v1d_only=low_v1d_only,
        skip_today=skip_today,
        log_func=log,
        limit=seed_limit,
    )
    return count_pending(), True


def _queue_order_sql(queue_sort: str) -> str:
    sort_key = (queue_sort or "monitor_first").strip().lower()
    if sort_key in ("sold_desc", "monitor_first", "sold_first"):
        return "COALESCE(sold_num,0) DESC, last_seen DESC NULLS LAST, goods_id ASC"
    return "COALESCE(velocity_1d,0) ASC, last_seen ASC NULLS LAST, goods_id ASC"


def queue_pending_sold_tiers(high_sold_min=10, queue_db=None, queue_date=None):
    del queue_db
    qd = queue_date or _today()
    threshold = max(1, int(high_sold_min or 10))
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            base = "queue_date=%s AND last_sync_at IS NULL AND frozen_at IS NULL"
            c.execute(
                f"SELECT COUNT(*) FROM full_sold_queue WHERE {base} AND COALESCE(sold_num,0)>=%s",
                (qd, threshold),
            )
            high = int(c.fetchone()[0] or 0)
            c.execute(
                f"SELECT COUNT(*) FROM full_sold_queue WHERE {base} AND COALESCE(sold_num,0)<%s",
                (qd, threshold),
            )
            low = int(c.fetchone()[0] or 0)
        return {"threshold": threshold, "high_sold": high, "low_sold": low}
    finally:
        conn.close()


def fetch_full_sold_queue_batch(
    limit=800,
    queue_db=None,
    queue_date=None,
    max_fail=3,
    queue_sort="monitor_first",
):
    del queue_db
    qd = queue_date or _today()
    limit = max(1, min(int(limit or 800), 5000))
    max_fail = max(1, int(max_fail or 3))
    order_sql = _queue_order_sql(queue_sort)
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            c.execute(
                f"""SELECT goods_id, title, sold_num, velocity_1d, pool, last_seen
                    FROM full_sold_queue
                    WHERE queue_date=%s AND last_sync_at IS NULL AND frozen_at IS NULL
                      AND COALESCE(sync_fail_count,0) < %s
                    ORDER BY {order_sql}
                    LIMIT %s""",
                (qd, max_fail, limit),
            )
            rows = [
                {
                    "goods_id": r[0],
                    "title": r[1] or "",
                    "sold_num": int(r[2] or 0),
                    "velocity_1d": float(r[3] or 0),
                    "pool": r[4] or "WATCH",
                    "last_seen": r[5].isoformat() if r[5] else "",
                }
                for r in c.fetchall()
            ]
        return rows
    finally:
        conn.close()


def mark_full_sold_sync_result(goods_id, ok=True, queue_db=None):
    del queue_db
    if not goods_id:
        return
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            if ok:
                c.execute(
                    """UPDATE full_sold_queue SET last_sync_at=NOW(), sync_fail_count=0
                       WHERE goods_id=%s""",
                    (str(goods_id),),
                )
            else:
                c.execute(
                    "UPDATE full_sold_queue SET sync_fail_count=COALESCE(sync_fail_count,0)+1 WHERE goods_id=%s",
                    (str(goods_id),),
                )
        conn.commit()
    finally:
        conn.close()


def finalize_frozen_goods(goods_id, code=600, queue_db=None, log_func=None):
    del queue_db
    gid = str(goods_id)
    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            _ensure_queue_table(c)
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                "UPDATE monitor_goods SET monitor_status='delisted', updated_at=NOW() WHERE goods_id=%s",
                (gid,),
            )
            c.execute(
                """UPDATE full_sold_queue SET frozen_at=NOW(), freeze_code=%s,
                       last_sync_at=NOW(), sync_fail_count=0 WHERE goods_id=%s""",
                (int(code or 600), gid),
            )
        conn.commit()
    finally:
        conn.close()
    if log_func:
        log_func(f"冻结标注 {gid[:16]}… code={code} (PG delisted)")
