#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查云端是否具备「精品+监控池当日增量」选品报告的数据条件。"""
from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap


def check(report_date: str) -> dict:
    bootstrap()
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute("SELECT COUNT(*) FROM premium_goods WHERE lifecycle < 3")
            premium = int(c.fetchone()[0] or 0)
            c.execute(
                "SELECT COUNT(*) FROM premium_goods_daily WHERE snap_date = %s",
                (report_date,),
            )
            daily_rows = int(c.fetchone()[0] or 0)
            c.execute(
                """
                SELECT COUNT(*) FROM premium_goods_daily
                WHERE snap_date = %s AND COALESCE(actual_delta, 0) > 0
                """,
                (report_date,),
            )
            daily_actual = int(c.fetchone()[0] or 0)
            c.execute(
                """
                SELECT COUNT(*) FROM goods_sold_daily sd
                JOIN monitor_goods m ON m.goods_id = sd.goods_id
                WHERE sd.snapshot_date = %s
                  AND m.monitor_status IN ('active', 'idle')
                  AND COALESCE(sd.delta, 0) > 0
                """,
                (report_date,),
            )
            monitor_incr = int(c.fetchone()[0] or 0)
    finally:
        conn.close()
    ok = daily_actual > 0 or monitor_incr > 0
    return {
        "report_date": report_date,
        "premium_goods": premium,
        "premium_goods_daily_rows": daily_rows,
        "premium_daily_actual_gt0": daily_actual,
        "monitor_pool_incr_gt0": monitor_incr,
        "selection_report_ready": ok,
        "hint": (
            "可 cloud_gen_report --source auto"
            if ok
            else "精品: 本地 push-daily；监控池: 确认云 daemon 已写入 goods_sold_daily"
        ),
    }


def main():
    ap = argparse.ArgumentParser(description="云端选品报告（精品+监控池增量）数据就绪检查")
    ap.add_argument("--date", default="", help="YYYY-MM-DD")
    args = ap.parse_args()
    from datetime import datetime

    report_date = args.date or datetime.now().strftime("%Y-%m-%d")
    r = check(report_date)
    for k, v in r.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
