#!/usr/bin/env python3
"""cloud_daemon 采集状态（队列覆盖 / 最近批次 / 今日扫描率）。"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
sys.path.insert(0, ROOT)


def main() -> int:
    from cloud_deploy.scripts.bootstrap_env import bootstrap

    bootstrap()
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    init_db()
    conn = _conn()
    try:
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                "SELECT COUNT(*) FROM monitor_goods WHERE monitor_status IN ('active','idle')"
            )
            pool = int(c.fetchone()[0] or 0)
            c.execute(
                """SELECT COUNT(*) FROM monitor_goods
                   WHERE monitor_status IN ('active','idle')
                     AND last_scan_at::date = CURRENT_DATE"""
            )
            scanned_today = int(c.fetchone()[0] or 0)
            c.execute(
                """SELECT run_at, batch_size, ok, fail, risk, frozen, wall_ms, note
                   FROM daemon_scan_stats ORDER BY id DESC LIMIT 5"""
            )
            rows = c.fetchall()
    finally:
        conn.close()

    pct = (scanned_today / pool * 100) if pool else 0.0
    print(f"监控池 active/idle: {pool:,}")
    print(f"今日已扫:           {scanned_today:,} ({pct:.2f}%)")
    print(f"待扫(约):           {max(0, pool - scanned_today):,}")
    print("")
    print("最近 5 批:")
    if not rows:
        print("  (无 daemon_scan_stats 记录 — 确认 XHS_DAEMON_MODE=cloud 且服务在跑)")
    for r in rows:
        print(
            f"  {r[0]} batch={r[1]} ok={r[2]} fail={r[3]} risk={r[4]} "
            f"frozen={r[5]} {r[6]}ms | {r[7] or ''}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
