# -*- coding: utf-8 -*-
r"""
本地 gen_report 完成后推云（独立客户端，不修改 gen_report.py）。

配置（Windows cmd 示例）:
  set XHS_CLOUD_PKG_ROOT=E:/vuemonitor/xhs-cloud
  set XHS_CLOUD_API_URL=http://你的服务器:8080
  set XHS_CLOUD_SYNC_KEY=与服务器 .env 一致
  set XHS_DB_PATH=D:/path/to/xhs_burst_monitor.db   # 可选，sold_history 回补

用法:
  python tools/cloud_sync_client.py push --data-js 全量0619/data.js
  python tools/cloud_sync_client.py backfill-sold
  python tools/cloud_sync_client.py backfill-snapshots
  python tools/cloud_sync_client.py sync-incr-daily
  python tools/cloud_sync_client.py after-report --data-js 全量0619/data.js
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_XHS_CLOUD_ROOT = os.environ.get(
    "XHS_CLOUD_PKG_ROOT",
    os.path.dirname(_TOOLS),  # xhs-cloud/
)
if _XHS_CLOUD_ROOT not in sys.path:
    sys.path.insert(0, _XHS_CLOUD_ROOT)


def _log(msg: str) -> None:
    print(f"[cloud-sync] {msg}", flush=True)


def _api_base() -> str:
    return os.environ.get("XHS_CLOUD_API_URL", "http://127.0.0.1:8080").rstrip("/")


def _sync_key() -> str:
    return os.environ.get("XHS_CLOUD_SYNC_KEY", "")


def push_daily_report(data_js_path: str) -> dict:
    from cloud_deploy.cloud_api.sync_service import parse_data_js

    report_date, meta, items = parse_data_js(data_js_path)
    api_url = _api_base()
    sync_key = _sync_key()

    if sync_key and api_url:
        body = json.dumps(
            {
                "report_date": report_date,
                "meta": meta,
                "items": items,
                "source": "local_gen_report",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{api_url}/api/v1/sync/daily-report",
            data=body,
            headers={"Content-Type": "application/json", "X-Sync-Key": sync_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                _log(f"API 推送完成: {result}")
                return result
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"推云失败 HTTP {e.code}: {detail}") from e

    db_url = os.environ.get("XHS_DATABASE_URL", "")
    if db_url.startswith("postgres"):
        from cloud_deploy.scripts.sync_report_to_pg import sync_report_to_pg

        return sync_report_to_pg(data_js_path)

    raise RuntimeError(
        "请配置 XHS_CLOUD_API_URL + XHS_CLOUD_SYNC_KEY，或直连 XHS_DATABASE_URL"
    )


def push_sold_history(main_db: str | None = None) -> dict:
    main_db = main_db or os.environ.get("XHS_DB_PATH", "")
    if not main_db or not os.path.isfile(main_db):
        raise RuntimeError("请设置 XHS_DB_PATH 指向本地 SQLite 主库（只读回补 sold_history）")
    from cloud_deploy.scripts.backfill_sold_history_pg import backfill_sold_history

    return backfill_sold_history(main_db)


def push_sold_snapshots(main_db: str | None = None) -> dict:
    main_db = main_db or os.environ.get("XHS_DB_PATH", "")
    if not main_db or not os.path.isfile(main_db):
        raise RuntimeError("请设置 XHS_DB_PATH 指向本地 SQLite 主库")
    from cloud_deploy.scripts.backfill_sold_snapshots_pg import backfill_sold_snapshots

    return backfill_sold_snapshots(main_db)


def push_incr_daily(main_db: str | None = None) -> dict:
    main_db = main_db or os.environ.get("XHS_DB_PATH", "")
    if not main_db or not os.path.isfile(main_db):
        raise RuntimeError("请设置 XHS_DB_PATH")
    from cloud_deploy.scripts.sync_incremental_sold_daily import sync_incremental_sold_daily

    return sync_incremental_sold_daily(main_db)


def push_after_report(data_js_path: str, backfill_sold: bool = True, backfill_snapshots: bool = True) -> dict:
    result = push_daily_report(data_js_path)
    if backfill_sold:
        try:
            if result.get("need_sold_history_backfill_count", 0) > 0:
                result["sold_history_backfill"] = push_sold_history()
            result["sold_history_incr"] = push_incr_daily()
        except Exception as e:
            _log(f"sold_history 同步跳过: {e}")
    if backfill_snapshots:
        try:
            result["sold_snapshots_backfill"] = push_sold_snapshots()
        except Exception as e:
            _log(f"sold_snapshots 同步跳过: {e}")
    return result


def main():
    ap = argparse.ArgumentParser(description="选品报告上云（不修改 gen_report）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_push = sub.add_parser("push", help="推送 data.js 到云端 PG")
    p_push.add_argument("--data-js", required=True)

    p_bf = sub.add_parser("backfill-sold", help="回补监控池 sold_history")
    p_bf.add_argument("--main-db", default="")

    p_sn = sub.add_parser("backfill-snapshots", help="回补监控池 sold_snapshots(90d)")
    p_sn.add_argument("--main-db", default="")

    p_inc = sub.add_parser("sync-incr-daily", help="已在池商品 sold_history 增量")
    p_inc.add_argument("--main-db", default="")

    p_all = sub.add_parser("after-report", help="推送 + sold_history + snapshots")
    p_all.add_argument("--data-js", required=True)
    p_all.add_argument("--no-backfill", action="store_true")
    p_all.add_argument("--no-snapshots", action="store_true")

    args = ap.parse_args()
    if args.cmd == "push":
        push_daily_report(args.data_js)
    elif args.cmd == "backfill-sold":
        push_sold_history(args.main_db or None)
    elif args.cmd == "backfill-snapshots":
        push_sold_snapshots(args.main_db or None)
    elif args.cmd == "sync-incr-daily":
        push_incr_daily(args.main_db or None)
    elif args.cmd == "after-report":
        push_after_report(
            args.data_js,
            backfill_sold=not args.no_backfill,
            backfill_snapshots=not args.no_snapshots,
        )


if __name__ == "__main__":
    main()
