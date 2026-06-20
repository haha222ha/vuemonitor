# -*- coding: utf-8 -*-
"""主库写空闲检测 — gen_report / 大批量回写前错峰等待。"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
MAIN_DB = os.path.join(DATA_DIR, "xhs_burst_monitor.db")
LIVE_JSON = os.path.join(DATA_DIR, "detail_enrich_live.json")

# 建议 gen_report 运行的时段（本地时间）
PREFERRED_REPORT_HOURS = range(18, 23)


def is_background_writer_active(max_age_sec=45):
    """详情补全 / ⑤ 等面板近期有写入活动。"""
    if not os.path.isfile(LIVE_JSON):
        return False
    try:
        age = time.time() - os.path.getmtime(LIVE_JSON)
        if age > max_age_sec:
            return False
        with open(LIVE_JSON, encoding="utf-8") as f:
            data = json.load(f)
        phase = str(data.get("phase") or "")
        progress = data.get("progress") or {}
        if isinstance(progress, dict):
            phase = str(progress.get("phase") or phase)
        running_flag = data.get("running")
        if running_flag is False:
            return False
        # running=true 但 updated_at 已过期 → 视为僵尸状态，不阻塞写库
        ts = data.get("updated_at") or data.get("time") or ""
        ts_age = None
        if ts:
            try:
                t = datetime.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S")
                ts_age = (datetime.now() - t).total_seconds()
            except Exception:
                pass
        if ts_age is not None and ts_age > max_age_sec:
            return False
        if phase in ("running", "init") and (ts_age is None or ts_age <= max_age_sec):
            return True
        if ts_age is not None and ts_age < max_age_sec:
            return True
        return age <= max_age_sec
    except Exception:
        return False


def try_db_write_lock(db_path=MAIN_DB, timeout_sec=3):
    """尝试短暂独占写锁；成功表示当前无其它写者。"""
    try:
        conn = sqlite3.connect(db_path, timeout=timeout_sec)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False


def wait_main_db_idle(max_wait_sec=180, poll_sec=5, db_path=MAIN_DB, log_func=None):
    """
    等待主库可写。返回 (ok, waited_sec)。
    ok=False 表示超时仍 busy。
    """
    def _log(msg):
        if log_func:
            log_func(msg)
        else:
            print(msg, flush=True)

    t0 = time.time()
    while time.time() - t0 < max_wait_sec:
        if is_background_writer_active():
            _log(f"  检测到详情补全/⑤ 运行中，等待 {poll_sec}s...")
            time.sleep(poll_sec)
            continue
        if try_db_write_lock(db_path):
            waited = int(time.time() - t0)
            if waited > 0:
                _log(f"  主库已空闲 (等待 {waited}s)")
            return True, waited
        _log(f"  主库 locked，{poll_sec}s 后重试...")
        time.sleep(poll_sec)

    return False, int(time.time() - t0)


def report_time_hint():
    """当前是否处于建议跑 gen_report 的时段。"""
    h = datetime.now().hour
    in_window = h in PREFERRED_REPORT_HOURS
    return {
        "hour": h,
        "preferred": in_window,
        "hint": "19:00–22:00 为建议报告时段（与 App/⑤ 写库错峰）" if not in_window else "当前处于建议报告时段",
    }
