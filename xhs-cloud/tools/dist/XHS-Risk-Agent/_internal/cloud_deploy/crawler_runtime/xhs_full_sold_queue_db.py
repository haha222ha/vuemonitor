# -*- coding: utf-8 -*-
"""
【数据源⑥】主库补缺轻量队列 xhs_full_sold_queue.db

- 启动时一次性 seed（重查询只跑一次，约 2~5 分钟）
- 每批 fetch 毫秒级（与⑤ 跟踪库同思路）
- 扫描成功后标记 last_sync_at，当日不再重复取
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime

from xhs_sold_snapshot_skip import MAIN_DB, attach_main_db, today_str

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
FULL_SOLD_QUEUE_DB = os.path.join(DATA_DIR, "xhs_full_sold_queue.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS full_sold_goods (
    goods_id       TEXT PRIMARY KEY,
    title          TEXT DEFAULT '',
    sold_num       INTEGER DEFAULT 0,
    velocity_1d    REAL DEFAULT 0,
    pool           TEXT DEFAULT 'WATCH',
    last_seen      TEXT DEFAULT '',
    queue_date     TEXT NOT NULL,
    last_sync_at   TEXT DEFAULT '',
    sync_fail_count INTEGER DEFAULT 0,
    frozen_at      TEXT DEFAULT '',
    freeze_code    INTEGER DEFAULT 0,
    seeded_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fsq_pending
    ON full_sold_goods(queue_date, last_sync_at, frozen_at, velocity_1d, last_seen);
"""

_MIGRATE_COLUMNS = (
    ("frozen_at", "ALTER TABLE full_sold_goods ADD COLUMN frozen_at TEXT DEFAULT ''"),
    ("freeze_code", "ALTER TABLE full_sold_goods ADD COLUMN freeze_code INTEGER DEFAULT 0"),
)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db_conn(path=FULL_SOLD_QUEUE_DB, timeout=60, readonly=False):
    if readonly and os.path.isfile(path):
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, timeout=timeout, uri=True)
    else:
        conn = sqlite3.connect(path, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    if not readonly:
        conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(path=FULL_SOLD_QUEUE_DB):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = db_conn(path, readonly=False)
    conn.executescript(SCHEMA_SQL)
    c = conn.cursor()
    c.execute("PRAGMA table_info(full_sold_goods)")
    cols = {r[1] for r in c.fetchall()}
    for col, ddl in _MIGRATE_COLUMNS:
        if col not in cols:
            c.execute(ddl)
    conn.commit()
    conn.close()


def queue_stats(queue_date=None, queue_db=FULL_SOLD_QUEUE_DB):
    qd = queue_date or today_str()
    if not os.path.isfile(queue_db):
        return {"queue_date": qd, "total": 0, "pending": 0, "synced": 0, "frozen": 0}
    init_db(queue_db)
    conn = db_conn(queue_db, readonly=True)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM full_sold_goods WHERE queue_date=?", (qd,))
    total = int(c.fetchone()[0] or 0)
    c.execute(
        """SELECT COUNT(*) FROM full_sold_goods
           WHERE queue_date=? AND COALESCE(last_sync_at,'')=''
             AND COALESCE(frozen_at,'')=''""",
        (qd,),
    )
    pending = int(c.fetchone()[0] or 0)
    c.execute(
        """SELECT COUNT(*) FROM full_sold_goods
           WHERE queue_date=? AND COALESCE(frozen_at,'')<>''""",
        (qd,),
    )
    frozen = int(c.fetchone()[0] or 0)
    conn.close()
    return {
        "queue_date": qd,
        "total": total,
        "pending": pending,
        "synced": max(0, total - pending - frozen),
        "frozen": frozen,
    }


def count_pending(queue_date=None, queue_db=FULL_SOLD_QUEUE_DB):
    return queue_stats(queue_date, queue_db)["pending"]


def seed_full_sold_queue(
    main_db=MAIN_DB,
    queue_db=FULL_SOLD_QUEUE_DB,
    low_v1d_only=False,
    skip_today=True,
    min_sold=1,
    log_func=None,
    limit=0,
):
    """
    一次性从主库导入补缺队列（当日 skip_today 用 TEMP 表反连接，比逐行 NOT EXISTS 快）。
    limit>0 时分批导入：只取未 seed 过的前 limit 条（按 sold_num DESC 优先高销量）。
    返回 inserted 条数。
    """
    log = log_func or (lambda _m: None)
    if not os.path.isfile(main_db):
        log("主库不存在，跳过 seed")
        return 0

    init_db(queue_db)
    qd = today_str()
    conn = db_conn(queue_db, readonly=False)
    c = conn.cursor()
    c.execute("DELETE FROM full_sold_goods WHERE queue_date<?", (qd,))
    conn.commit()

    c.execute("SELECT COUNT(*) FROM full_sold_goods WHERE queue_date=?", (qd,))
    existing = int(c.fetchone()[0] or 0)

    batch_limit = int(limit or 0)
    if batch_limit > 0:
        if existing >= batch_limit:
            conn.close()
            log(f"补缺队列已有 {existing:,} 条 (>=批次上限 {batch_limit:,})，跳过 seed")
            return 0
    else:
        if existing > 0:
            conn.close()
            log(f"补缺队列已有今日数据 {existing:,} 条，跳过 seed")
            return 0

    attach_main_db(conn, main_db)
    v1d_filter = " AND COALESCE(g.velocity_1d,0) <= 0" if low_v1d_only else ""
    now = _now()
    limit_sql = f" LIMIT {int(batch_limit)}" if batch_limit > 0 else ""

    t0 = time.time()
    if skip_today:
        log("构建今日已快照商品集 (TEMP)...")
        conn.execute("DROP TABLE IF EXISTS temp.today_done")
        conn.execute(
            """CREATE TEMP TABLE today_done AS
               SELECT goods_id FROM xhs.sold_history
               WHERE snapshot_date=date('now','localtime')
               UNION
               SELECT DISTINCT goods_id FROM xhs.sold_snapshots
               WHERE snapshot_time>=date('now','localtime')"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_today_done ON today_done(goods_id)")
        conn.commit()
        log(f"今日已快照去重集就绪 ({time.time()-t0:.1f}s)，开始导入补缺队列...")

        if batch_limit > 0:
            c.execute(
                f"""INSERT OR IGNORE INTO full_sold_goods
                    (goods_id, title, sold_num, velocity_1d, pool, last_seen,
                     queue_date, last_sync_at, sync_fail_count, seeded_at)
                    SELECT g.goods_id, COALESCE(g.title,''), COALESCE(g.sold_num,0),
                           COALESCE(g.velocity_1d,0), COALESCE(g.pool,'WATCH'),
                           COALESCE(g.last_seen,''), ?, '', 0, ?
                    FROM xhs.goods g
                    LEFT JOIN today_done t ON t.goods_id = g.goods_id
                    LEFT JOIN full_sold_goods q ON q.goods_id = g.goods_id AND q.queue_date=?
                    WHERE g.lifecycle<3 AND g.sold_num>=?
                      {v1d_filter}
                      AND t.goods_id IS NULL
                      AND q.goods_id IS NULL
                    ORDER BY COALESCE(g.sold_num,0) DESC
                    {limit_sql}""",
                (qd, now, qd, int(min_sold or 1)),
            )
        else:
            c.execute(
                f"""INSERT OR IGNORE INTO full_sold_goods
                    (goods_id, title, sold_num, velocity_1d, pool, last_seen,
                     queue_date, last_sync_at, sync_fail_count, seeded_at)
                    SELECT g.goods_id, COALESCE(g.title,''), COALESCE(g.sold_num,0),
                           COALESCE(g.velocity_1d,0), COALESCE(g.pool,'WATCH'),
                           COALESCE(g.last_seen,''), ?, '', 0, ?
                    FROM xhs.goods g
                    LEFT JOIN today_done t ON t.goods_id = g.goods_id
                    WHERE g.lifecycle<3 AND g.sold_num>=?
                      {v1d_filter}
                      AND t.goods_id IS NULL""",
                (qd, now, int(min_sold or 1)),
            )
    else:
        log("导入补缺队列（含当日已快照）...")
        if batch_limit > 0:
            c.execute(
                f"""INSERT OR IGNORE INTO full_sold_goods
                    (goods_id, title, sold_num, velocity_1d, pool, last_seen,
                     queue_date, last_sync_at, sync_fail_count, seeded_at)
                    SELECT g.goods_id, COALESCE(g.title,''), COALESCE(g.sold_num,0),
                           COALESCE(g.velocity_1d,0), COALESCE(g.pool,'WATCH'),
                           COALESCE(g.last_seen,''), ?, '', 0, ?
                    FROM xhs.goods g
                    LEFT JOIN full_sold_goods q ON q.goods_id = g.goods_id AND q.queue_date=?
                    WHERE g.lifecycle<3 AND g.sold_num>=?
                      {v1d_filter}
                      AND q.goods_id IS NULL
                    ORDER BY COALESCE(g.sold_num,0) DESC
                    {limit_sql}""",
                (qd, now, qd, int(min_sold or 1)),
            )
        else:
            c.execute(
                f"""INSERT OR IGNORE INTO full_sold_goods
                    (goods_id, title, sold_num, velocity_1d, pool, last_seen,
                     queue_date, last_sync_at, sync_fail_count, seeded_at)
                    SELECT g.goods_id, COALESCE(g.title,''), COALESCE(g.sold_num,0),
                           COALESCE(g.velocity_1d,0), COALESCE(g.pool,'WATCH'),
                           COALESCE(g.last_seen,''), ?, '', 0, ?
                    FROM xhs.goods g
                    WHERE g.lifecycle<3 AND g.sold_num>=?
                      {v1d_filter}""",
                (qd, now, int(min_sold or 1)),
            )

    inserted = c.rowcount if c.rowcount >= 0 else 0
    conn.commit()
    c.execute("SELECT COUNT(*) FROM full_sold_goods WHERE queue_date=?", (qd,))
    total = int(c.fetchone()[0] or 0)
    conn.close()
    if batch_limit > 0:
        log(f"补缺队列分批 seed: 本次+{inserted:,} 累计 {total:,} 条 ({time.time()-t0:.1f}s)")
    else:
        log(f"补缺队列 seed 完成: {total:,} 条 ({time.time()-t0:.1f}s)")
    return total


def ensure_queue_seeded(
    low_v1d_only=False,
    skip_today=True,
    min_pending=100,
    main_db=MAIN_DB,
    queue_db=FULL_SOLD_QUEUE_DB,
    log_func=None,
    seed_limit=0,
):
    """队列待扫不足时自动 seed。seed_limit>0 时分批导入。返回 (pending, did_seed)。"""
    log = log_func or (lambda _m: None)
    pending = count_pending(queue_db=queue_db)
    if pending >= min_pending:
        return pending, False
    log(f"补缺队列待扫 {pending} 条，开始 seed...")
    seed_full_sold_queue(
        main_db=main_db,
        queue_db=queue_db,
        low_v1d_only=low_v1d_only,
        skip_today=skip_today,
        log_func=log,
        limit=seed_limit,
    )
    pending = count_pending(queue_db=queue_db)
    return pending, True


def _queue_order_sql(queue_sort):
    """
    monitor_first / sold_desc：高 sold_num + 近期 last_seen 优先（监控价值高）。
    cleanup_first / velocity_asc：低 v1d 优先（清死品，旧行为）。
    """
    sort_key = (queue_sort or "monitor_first").strip().lower()
    if sort_key in ("sold_desc", "monitor_first", "sold_first"):
        return (
            "COALESCE(sold_num,0) DESC, COALESCE(last_seen,'') DESC, goods_id ASC"
        )
    return (
        "COALESCE(velocity_1d,0) ASC, COALESCE(last_seen,'') ASC, goods_id ASC"
    )


def queue_pending_sold_tiers(
    high_sold_min=10,
    queue_db=FULL_SOLD_QUEUE_DB,
    queue_date=None,
):
    """待扫队列按销量分层，便于观察「监控优先 / 清死品」进度。"""
    qd = queue_date or today_str()
    threshold = max(1, int(high_sold_min or 10))
    if not os.path.isfile(queue_db):
        return {"threshold": threshold, "high_sold": 0, "low_sold": 0}
    init_db(queue_db)
    conn = db_conn(queue_db, readonly=True)
    c = conn.cursor()
    base = (
        "queue_date=? AND COALESCE(last_sync_at,'')='' "
        "AND COALESCE(frozen_at,'')=''"
    )
    c.execute(
        f"SELECT COUNT(*) FROM full_sold_goods WHERE {base} AND COALESCE(sold_num,0)>=?",
        (qd, threshold),
    )
    high = int(c.fetchone()[0] or 0)
    c.execute(
        f"SELECT COUNT(*) FROM full_sold_goods WHERE {base} AND COALESCE(sold_num,0)<?",
        (qd, threshold),
    )
    low = int(c.fetchone()[0] or 0)
    conn.close()
    return {"threshold": threshold, "high_sold": high, "low_sold": low}


def fetch_full_sold_queue_batch(
    limit=800,
    queue_db=FULL_SOLD_QUEUE_DB,
    queue_date=None,
    max_fail=3,
    queue_sort="monitor_first",
):
    """毫秒级取批：未同步且未冻结优先；sync_fail_count>=max_fail 当日跳过。"""
    order_sql = _queue_order_sql(queue_sort)
    qd = queue_date or today_str()
    if not os.path.isfile(queue_db):
        return []
    init_db(queue_db)
    limit = max(1, min(int(limit or 800), 5000))
    max_fail = max(1, int(max_fail or 3))
    conn = db_conn(queue_db, readonly=True)
    c = conn.cursor()
    c.execute(
        f"""SELECT goods_id, title, sold_num, velocity_1d, pool, last_seen
           FROM full_sold_goods
           WHERE queue_date=? AND COALESCE(last_sync_at,'')=''
             AND COALESCE(frozen_at,'')=''
             AND COALESCE(sync_fail_count,0) < ?
           ORDER BY {order_sql}
           LIMIT ?""",
        (qd, max_fail, limit),
    )
    rows = [
        {
            "goods_id": r[0],
            "title": r[1] or "",
            "sold_num": int(r[2] or 0),
            "velocity_1d": float(r[3] or 0),
            "pool": r[4] or "WATCH",
            "last_seen": r[5] or "",
        }
        for r in c.fetchall()
    ]
    conn.close()
    return rows


def mark_full_sold_sync_result(goods_id, ok=True, queue_db=FULL_SOLD_QUEUE_DB):
    if not goods_id or not os.path.isfile(queue_db):
        return
    init_db(queue_db)
    conn = db_conn(queue_db, readonly=False)
    c = conn.cursor()
    now = _now()
    if ok:
        c.execute(
            """UPDATE full_sold_goods SET last_sync_at=?, sync_fail_count=0
               WHERE goods_id=?""",
            (now, goods_id),
        )
    else:
        c.execute(
            """UPDATE full_sold_goods SET sync_fail_count=sync_fail_count+1
               WHERE goods_id=?""",
            (goods_id,),
        )
    conn.commit()
    conn.close()


def mark_full_sold_frozen(goods_id, code=600, queue_db=FULL_SOLD_QUEUE_DB):
    """队列标记冻结：frozen_at + 当日不再取批。"""
    if not goods_id or not os.path.isfile(queue_db):
        return
    init_db(queue_db)
    conn = db_conn(queue_db, readonly=False)
    c = conn.cursor()
    now = _now()
    c.execute(
        """UPDATE full_sold_goods SET frozen_at=?, freeze_code=?,
               last_sync_at=?, sync_fail_count=0
           WHERE goods_id=?""",
        (now, int(code or 600), now, goods_id),
    )
    conn.commit()
    conn.close()


def finalize_frozen_goods(goods_id, code=600, queue_db=FULL_SOLD_QUEUE_DB, log_func=None):
    """
    ⑥ 冻结品收尾：主库 lifecycle=3（与④ 一致）+ 队列 frozen_at。
    error_code 600=item freeze，602=商品不存在。
    """
    from xhs_detail_enrich_db import GOODS_GONE_MSG, mark_goods_gone

    mark_goods_gone(goods_id, int(code or 600), source="web_full")
    mark_full_sold_frozen(goods_id, code=code, queue_db=queue_db)
    if log_func:
        label = GOODS_GONE_MSG.get(int(code or 600), f"code={code}")
        log_func(f"冻结标注 {goods_id[:16]}… {label} (lifecycle=3, 风险库, frozen_at)")


def purge_synced_from_queue(queue_db=FULL_SOLD_QUEUE_DB, queue_date=None):
    """可选：压缩队列，删除今日已同步行。"""
    qd = queue_date or today_str()
    if not os.path.isfile(queue_db):
        return 0
    conn = db_conn(queue_db, readonly=False)
    c = conn.cursor()
    c.execute(
        """DELETE FROM full_sold_goods
           WHERE queue_date=? AND COALESCE(last_sync_at,'')<>''""",
        (qd,),
    )
    n = c.rowcount
    conn.commit()
    conn.close()
    return n
