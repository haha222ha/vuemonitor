# -*- coding: utf-8
"""
云端生成日报（读 PG，不依赖 gen_report.py）。

数据源（--source）:
  auto       优先 report_daily_items，无则 goods_sold_daily 计算
  pg_items   仅 report_daily_items
  sold_daily 仅 monitor_goods + goods_sold_daily

输出: {XHS_REPORT_OUTPUT_DIR}/全量MMDD/ → data.js + html
"""
from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap


def _log(msg: str) -> None:
    print(f"[cloud-gen-report] {msg}", flush=True)


def _html_template() -> str:
    for p in (
        os.environ.get("XHS_HTML_TEMPLATE", ""),
        os.path.join(CLOUD_ROOT, "cloud_deploy", "assets", "index_with_gr.html"),
        r"C:\Users\Administrator\Desktop\每日选品全量数据\index_with_gr.html",
    ):
        if p and os.path.isfile(p):
            return p
    return ""


def generate_daily_report(
    report_date: str = "",
    source: str = "auto",
    dedup: bool = True,
    min_v1d=5,
    min_actual=5,
    min_v1d_virtual=1,
    min_actual_virtual=1,
) -> dict:
    bootstrap()
    from datetime import datetime

    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.reporting.data_js_builder import build_report_payload, resolve_output_dir, write_report_dir
    from cloud_deploy.reporting.pg_reader import (
        dedup_by_title,
        fetch_items_from_daily_table,
        fetch_items_from_sold_daily,
        passes_threshold,
    )

    s = get_settings()
    if not s.xhs_database_url.startswith("postgres"):
        raise RuntimeError("cloud_gen_report 需要配置 XHS_DATABASE_URL")

    report_date = report_date or datetime.now().strftime("%Y-%m-%d")
    init_db()
    conn = _conn()
    try:
        items = []
        if source in ("auto", "sold_daily"):
            items = fetch_items_from_sold_daily(conn, report_date)
            _log(f"sold_daily: {len(items)} 行")
        if (not items and source in ("auto", "pg_items")) or source == "pg_items":
            items = fetch_items_from_daily_table(conn, report_date)
            _log(f"pg_items: {len(items)} 行")
    finally:
        conn.close()

    raw = len(items)
    items = [it for it in items if passes_threshold(it, min_v1d, min_actual, min_v1d_virtual, min_actual_virtual)]
    if dedup:
        items = dedup_by_title(items)

    report_root = os.environ.get("XHS_REPORT_OUTPUT_DIR", os.path.join(s.xhs_data_dir, "reports"))
    out_dir = resolve_output_dir(report_root, report_date, "daily")
    payload = build_report_payload(
        items,
        report_date,
        scope="daily",
        min_v1d=min_v1d,
        min_actual=min_actual,
        min_v1d_virtual=min_v1d_virtual,
        min_actual_virtual=min_actual_virtual,
        source="cloud_gen_report",
    )
    payload["meta"]["count_raw"] = raw
    write_report_dir(out_dir, payload, _html_template())
    _log(f"输出: {out_dir} items={len(items)} (raw={raw})")
    return {"report_date": report_date, "output_dir": out_dir, "count": len(items), "raw": raw}


def main():
    ap = argparse.ArgumentParser(description="云端 PG 生成日报")
    ap.add_argument("--date", default="", help="YYYY-MM-DD")
    ap.add_argument("--source", choices=("auto", "pg_items", "sold_daily"), default="auto")
    ap.add_argument("--no-dedup", action="store_true")
    ap.add_argument("--min-v1d", type=float, default=5)
    ap.add_argument("--min-actual", type=float, default=5)
    ap.add_argument("--min-v1d-virtual", type=float, default=1)
    ap.add_argument("--min-actual-virtual", type=float, default=1)
    args = ap.parse_args()
    generate_daily_report(
        report_date=args.date,
        source=args.source,
        dedup=not args.no_dedup,
        min_v1d=args.min_v1d,
        min_actual=args.min_actual,
        min_v1d_virtual=args.min_v1d_virtual,
        min_actual_virtual=args.min_actual_virtual,
    )


if __name__ == "__main__":
    main()
