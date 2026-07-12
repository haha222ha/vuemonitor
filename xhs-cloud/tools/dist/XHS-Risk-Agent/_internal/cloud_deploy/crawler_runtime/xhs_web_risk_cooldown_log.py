# -*- coding: utf-8 -*-
"""
Web 端风控冷却事件日志 — 记录触发/计划恢复/实际恢复，便于分析真实冷却时长。

表：web_risk_cooldown_events（主库 crawl_data/xhs_burst_monitor.db）
"""
from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timedelta

from xhs_sold_snapshot_skip import MAIN_DB

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS web_risk_cooldown_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT NOT NULL DEFAULT 'full_sold_daemon',
    engine           TEXT DEFAULT '',
    trigger_at       TEXT NOT NULL,
    trigger_reason   TEXT DEFAULT '',
    planned_sec      INTEGER NOT NULL DEFAULT 0,
    planned_until    TEXT NOT NULL,
    recovered_at     TEXT DEFAULT '',
    recovery_mode    TEXT DEFAULT '',
    actual_sec       INTEGER DEFAULT 0,
    risk_level       INTEGER DEFAULT 0,
    batch_ok         INTEGER DEFAULT 0,
    batch_fail       INTEGER DEFAULT 0,
    batch_risk       INTEGER DEFAULT 0,
    success_rate     REAL DEFAULT 0,
    probe_engine     TEXT DEFAULT '',
    probe_goods_id   TEXT DEFAULT '',
    note             TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_wrce_trigger ON web_risk_cooldown_events(trigger_at DESC);
CREATE INDEX IF NOT EXISTS idx_wrce_source ON web_risk_cooldown_events(source, trigger_at DESC);
CREATE INDEX IF NOT EXISTS idx_wrce_open ON web_risk_cooldown_events(recovered_at);
"""


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn(db_path=MAIN_DB, timeout=30):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ensure_schema(db_path=MAIN_DB):
    conn = _conn(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


def begin_cooldown_event(
    source="full_sold_daemon",
    engine="api",
    planned_sec=1800,
    trigger_reason="",
    risk_level=0,
    batch_ok=0,
    batch_fail=0,
    batch_risk=0,
    success_rate=0.0,
    note="",
    db_path=MAIN_DB,
):
    """
    记录风控冷却开始。返回 event_id。
    """
    ensure_schema(db_path)
    trigger_at = _now_str()
    planned_until = (datetime.now() + timedelta(seconds=int(planned_sec or 0))).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn = _conn(db_path)
    c = conn.cursor()
    c.execute(
        """INSERT INTO web_risk_cooldown_events
           (source, engine, trigger_at, trigger_reason, planned_sec, planned_until,
            risk_level, batch_ok, batch_fail, batch_risk, success_rate, note)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source,
            engine or "",
            trigger_at,
            trigger_reason or "",
            int(planned_sec or 0),
            planned_until,
            int(risk_level or 0),
            int(batch_ok or 0),
            int(batch_fail or 0),
            int(batch_risk or 0),
            float(success_rate or 0),
            note or "",
        ),
    )
    event_id = c.lastrowid
    conn.commit()
    conn.close()
    return int(event_id or 0)


def end_cooldown_event(
    event_id,
    recovery_mode,
    probe_engine="",
    probe_goods_id="",
    note="",
    db_path=MAIN_DB,
):
    """
    标记冷却结束。
    recovery_mode: probe_early | timeout | manual_stop | daemon_stop | error
    """
    if not event_id:
        return
    ensure_schema(db_path)
    recovered_at = _now_str()
    conn = _conn(db_path)
    c = conn.cursor()
    c.execute(
        "SELECT trigger_at FROM web_risk_cooldown_events WHERE id=?",
        (int(event_id),),
    )
    row = c.fetchone()
    actual_sec = 0
    if row and row[0]:
        try:
            t0 = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            actual_sec = max(0, int((datetime.now() - t0).total_seconds()))
        except Exception:
            pass
    c.execute(
        """UPDATE web_risk_cooldown_events SET
           recovered_at=?, recovery_mode=?, actual_sec=?,
           probe_engine=?, probe_goods_id=?, note=?
           WHERE id=? AND COALESCE(recovered_at,'')=''""",
        (
            recovered_at,
            recovery_mode or "",
            actual_sec,
            probe_engine or "",
            probe_goods_id or "",
            note or "",
            int(event_id),
        ),
    )
    conn.commit()
    conn.close()


def close_open_events(source="full_sold_daemon", recovery_mode="manual_stop", note="", db_path=MAIN_DB):
    """挂机停止时，关闭未结束的冷却记录。"""
    ensure_schema(db_path)
    conn = _conn(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT id FROM web_risk_cooldown_events
           WHERE source=? AND COALESCE(recovered_at,'')=''""",
        (source,),
    )
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    for eid in ids:
        end_cooldown_event(eid, recovery_mode, note=note, db_path=db_path)


def fetch_recent_events(limit=30, source=None, db_path=MAIN_DB):
    ensure_schema(db_path)
    conn = _conn(db_path)
    c = conn.cursor()
    if source:
        c.execute(
            """SELECT id, source, engine, trigger_at, trigger_reason, planned_sec,
                      planned_until, recovered_at, recovery_mode, actual_sec,
                      risk_level, batch_ok, batch_fail, batch_risk, success_rate,
                      probe_engine, note
               FROM web_risk_cooldown_events
               WHERE source=?
               ORDER BY id DESC LIMIT ?""",
            (source, int(limit)),
        )
    else:
        c.execute(
            """SELECT id, source, engine, trigger_at, trigger_reason, planned_sec,
                      planned_until, recovered_at, recovery_mode, actual_sec,
                      risk_level, batch_ok, batch_fail, batch_risk, success_rate,
                      probe_engine, note
               FROM web_risk_cooldown_events
               ORDER BY id DESC LIMIT ?""",
            (int(limit),),
        )
    cols = [
        "id", "source", "engine", "trigger_at", "trigger_reason", "planned_sec",
        "planned_until", "recovered_at", "recovery_mode", "actual_sec",
        "risk_level", "batch_ok", "batch_fail", "batch_risk", "success_rate",
        "probe_engine", "note",
    ]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows


def summarize_cooldown_stats(days=30, source="full_sold_daemon", db_path=MAIN_DB):
    """汇总分析：平均/中位实际冷却、探活提前恢复比例等。"""
    ensure_schema(db_path)
    conn = _conn(db_path)
    c = conn.cursor()
    since = (datetime.now() - timedelta(days=int(days or 30))).strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """SELECT COUNT(*),
                  AVG(actual_sec), MIN(actual_sec), MAX(actual_sec),
                  SUM(CASE WHEN recovery_mode='probe_early' THEN 1 ELSE 0 END),
                  SUM(CASE WHEN recovery_mode='timeout' THEN 1 ELSE 0 END),
                  AVG(planned_sec)
           FROM web_risk_cooldown_events
           WHERE source=? AND trigger_at>=? AND COALESCE(recovered_at,'')<>''""",
        (source, since),
    )
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return {
            "days": days,
            "source": source,
            "count": 0,
        }
    return {
        "days": days,
        "source": source,
        "count": int(row[0] or 0),
        "avg_actual_sec": int(row[1] or 0),
        "min_actual_sec": int(row[2] or 0),
        "max_actual_sec": int(row[3] or 0),
        "probe_early_count": int(row[4] or 0),
        "timeout_count": int(row[5] or 0),
        "avg_planned_sec": int(row[6] or 0),
    }


def format_event_line(ev):
    """单行可读摘要。"""
    aid = ev.get("id")
    trig = ev.get("trigger_at", "")
    rec = ev.get("recovered_at") or "进行中"
    mode = ev.get("recovery_mode") or "-"
    planned = ev.get("planned_sec", 0)
    actual = ev.get("actual_sec", 0)
    reason = ev.get("trigger_reason", "")
    return (
        f"#{aid} {trig} → {rec} | 计划{planned // 60}m 实际{actual // 60}m "
        f"| {mode} | {reason}"
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Web风控冷却事件查询")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--source", default="full_sold_daemon")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()
    if args.summary:
        s = summarize_cooldown_stats(days=args.days, source=args.source)
        print(s)
    else:
        for ev in fetch_recent_events(limit=args.limit, source=args.source):
            print(format_event_line(ev))
