# -*- coding: utf-8 -*-
"""从本地 SQLite 主库导出 goods.first_seen，供云端 backfill_monitor_first_seen.py 使用。"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3


def main():
    ap = argparse.ArgumentParser(description="导出 goods_id + first_seen")
    ap.add_argument(
        "--db",
        default=os.environ.get(
            "XHS_DB_PATH",
            r"D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db",
        ),
    )
    ap.add_argument(
        "--out",
        default="first_seen.json",
        help="输出 JSON 路径",
    )
    ap.add_argument(
        "--monitor-only",
        action="store_true",
        help="仅导出曾在历史 data.js 监控池出现过的 goods_id（需 --source）",
    )
    ap.add_argument(
        "--source",
        default=r"C:\Users\Administrator\Desktop\选品报告最新版本",
        help="历史全量报告目录（含多个 全量MMDD/data.js）",
    )
    args = ap.parse_args()

    goods_filter: set[str] | None = None
    if args.monitor_only:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from tools.export_monitor_pool_for_cloud import collect_monitor_goods

        goods_filter, _ = collect_monitor_goods(Path(args.source))
        print(f"监控池 goods_id: {len(goods_filter):,}")

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=120)
    cur = conn.execute(
        """SELECT goods_id, first_seen FROM goods
           WHERE first_seen IS NOT NULL AND TRIM(first_seen) != ''"""
    )
    out = []
    for gid, fs in cur:
        gid = str(gid or "").strip()
        if not gid:
            continue
        if goods_filter is not None and gid not in goods_filter:
            continue
        out.append({"goods_id": gid, "first_seen": str(fs)[:19]})
    conn.close()

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"已导出 {len(out):,} 条 -> {args.out}")


if __name__ == "__main__":
    main()
