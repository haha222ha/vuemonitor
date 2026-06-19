# -*- coding: utf-8
"""清理 PG goods_sold_snapshots 超 retention 窗口的数据。"""
from __future__ import annotations

import argparse
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)


def prune(retention_days: int | None = None) -> dict:
    from cloud_deploy.scripts.bootstrap_env import bootstrap

    bootstrap()
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.sync_service import prune_sold_snapshots, snapshot_retention_days

    init_db()
    conn = _conn()
    try:
        days = retention_days if retention_days is not None else snapshot_retention_days()
        deleted = prune_sold_snapshots(conn, days)
    finally:
        conn.close()
    result = {"deleted_rows": deleted, "retention_days": days}
    print(f"[prune-snapshots] {result}", flush=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retention-days", type=int, default=0)
    args = ap.parse_args()
    prune(args.retention_days or None)


if __name__ == "__main__":
    main()
