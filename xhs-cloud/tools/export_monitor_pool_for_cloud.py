# -*- coding: utf-8 -*-
"""
从本地 SQLite 主库导出「监控池」数据（报告中日增量>0 的商品 + sold_history）。

对齐需求规格书 v2 FR-M02：
  - 监控池：data.js 中 v1d>0 OR actual_v1d>0
  - sold_history：监控池商品全部日级记录
  - sold_snapshots：可选，仅近 90 天

用法:
  python tools/export_monitor_pool_for_cloud.py
  python tools/export_monitor_pool_for_cloud.py --source "C:/Users/.../每日选品全量数据" --main-db "D:/.../xhs_burst_monitor.db"
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cloud_deploy.cloud_api.sync_service import _field, _num, parse_data_js

DEFAULT_SOURCE = Path(r"d:\vuemonitor\xhs-cloud\server_sync_pack\historical_reports")
DEFAULT_DB = Path(r"D:\0619xhs备份\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db")
if not DEFAULT_DB.is_file():
    DEFAULT_DB = Path(r"D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db")
DEFAULT_OUT = ROOT / "server_sync_pack" / "monitor_pool"


def _read_date(data_js: Path) -> str:
    head = data_js.read_text(encoding="utf-8", errors="replace")[:800]
    m = re.search(r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"', head)
    return m.group(1) if m else ""


def _collect_report_dirs(source: Path) -> list[Path]:
    """按 report_date 去重，保留 data.js 最大的一份。"""
    by_date: dict[str, tuple[Path, int]] = {}
    for d in source.iterdir():
        if not d.is_dir():
            continue
        js = d / "data.js"
        if not js.is_file():
            continue
        size = js.stat().st_size
        date = _read_date(js) or d.name
        prev = by_date.get(date)
        if not prev or size > prev[1]:
            by_date[date] = (d, size)
    return [by_date[k][0] for k in sorted(by_date.keys())]


def _in_monitor_pool(item) -> bool:
    v1d = _num(_field(item, "v1d"), 0)
    actual = _num(_field(item, "actual_v1d"), 0)
    return v1d > 0 or actual > 0


def collect_monitor_goods(source: Path) -> tuple[set[str], list[dict]]:
    """从全部历史 data.js 汇总监控池 goods_id（并集）。"""
    goods: set[str] = set()
    reports: list[dict] = []
    for d in _collect_report_dirs(source):
        js = d / "data.js"
        report_date, meta, items = parse_data_js(str(js))
        pool_count = 0
        for item in items:
            if _in_monitor_pool(item):
                gid = str(_field(item, "goods_id", "") or "").strip()
                if gid:
                    goods.add(gid)
                    pool_count += 1
        reports.append(
            {
                "report_date": report_date,
                "dir_name": d.name,
                "items_total": len(items),
                "monitor_pool_rows": pool_count,
                "data_js_mb": round(js.stat().st_size / 1024 / 1024, 2),
            }
        )
        print(f"  [report] {report_date} {d.name}: 监控池行 {pool_count}/{len(items)}")
    return goods, reports


def _fetch_sold_history_chunk(
    conn: sqlite3.Connection, goods_ids: list[str]
) -> list[dict]:
    if not goods_ids:
        return []
    c = conn.cursor()
    placeholders = ",".join("?" * len(goods_ids))
    c.execute(
        f"""SELECT goods_id, snapshot_date, sold_num, delta
            FROM sold_history WHERE goods_id IN ({placeholders})
            ORDER BY goods_id, snapshot_date""",
        goods_ids,
    )
    return [
        {
            "goods_id": gid,
            "snapshot_date": snap,
            "sold_num": sold,
            "delta": delta,
            "source": "local_sold_history",
        }
        for gid, snap, sold, delta in c.fetchall()
    ]


def _fetch_snapshots_chunk(
    conn: sqlite3.Connection, goods_ids: list[str], since: str
) -> list[dict]:
    if not goods_ids:
        return []
    c = conn.cursor()
    placeholders = ",".join("?" * len(goods_ids))
    c.execute(
        f"""SELECT goods_id, snapshot_time, sold_num, data_source
            FROM sold_snapshots
            WHERE goods_id IN ({placeholders}) AND snapshot_time >= ?
            ORDER BY goods_id, snapshot_time""",
        (*goods_ids, since),
    )
    return [
        {
            "goods_id": gid,
            "snapshot_time": snap,
            "sold_num": sold,
            "data_source": src or "local_sold_snapshots",
        }
        for gid, snap, sold, src in c.fetchall()
    ]


def _write_jsonl_gz(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def export_sold_history(
    main_db: Path,
    goods_ids: list[str],
    out_dir: Path,
    goods_per_query: int = 100,
    rows_per_file: int = 100_000,
) -> dict:
    hist_dir = out_dir / "sold_history"
    hist_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{main_db}?mode=ro", uri=True, timeout=300)
    files: list[dict] = []
    part = 0
    buffer: list[dict] = []
    total_rows = 0
    goods_with_rows = 0

    try:
        for i in range(0, len(goods_ids), goods_per_query):
            chunk_ids = goods_ids[i : i + goods_per_query]
            rows = _fetch_sold_history_chunk(conn, chunk_ids)
            if rows:
                goods_with_rows += len({r["goods_id"] for r in rows})
            buffer.extend(rows)
            while len(buffer) >= rows_per_file:
                part += 1
                chunk = buffer[:rows_per_file]
                buffer = buffer[rows_per_file:]
                fname = f"part-{part:04d}.jsonl.gz"
                n = _write_jsonl_gz(hist_dir / fname, chunk)
                total_rows += n
                mb = round((hist_dir / fname).stat().st_size / 1024 / 1024, 2)
                files.append({"file": fname, "rows": n, "mb": mb})
                print(f"  [sold_history] {fname}: {n} 行, {mb} MB")

        if buffer:
            part += 1
            fname = f"part-{part:04d}.jsonl.gz"
            n = _write_jsonl_gz(hist_dir / fname, buffer)
            total_rows += n
            mb = round((hist_dir / fname).stat().st_size / 1024 / 1024, 2)
            files.append({"file": fname, "rows": n, "mb": mb})
            print(f"  [sold_history] {fname}: {n} 行, {mb} MB")
    finally:
        conn.close()

    return {
        "goods_queried": len(goods_ids),
        "goods_with_history": goods_with_rows,
        "total_rows": total_rows,
        "files": files,
    }


def export_sold_snapshots(
    main_db: Path,
    goods_ids: list[str],
    out_dir: Path,
    retention_days: int = 90,
    goods_per_query: int = 50,
    rows_per_file: int = 200_000,
) -> dict:
    snap_dir = out_dir / "sold_snapshots"
    since = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(f"file:{main_db}?mode=ro", uri=True, timeout=300)
    files: list[dict] = []
    part = 0
    buffer: list[dict] = []
    total_rows = 0

    try:
        for i in range(0, len(goods_ids), goods_per_query):
            chunk_ids = goods_ids[i : i + goods_per_query]
            rows = _fetch_snapshots_chunk(conn, chunk_ids, since)
            buffer.extend(rows)
            while len(buffer) >= rows_per_file:
                part += 1
                chunk = buffer[:rows_per_file]
                buffer = buffer[rows_per_file:]
                fname = f"part-{part:04d}.jsonl.gz"
                n = _write_jsonl_gz(snap_dir / fname, chunk)
                total_rows += n
                mb = round((snap_dir / fname).stat().st_size / 1024 / 1024, 2)
                files.append({"file": fname, "rows": n, "mb": mb})
                print(f"  [snapshots] {fname}: {n} 行, {mb} MB")

        if buffer:
            part += 1
            fname = f"part-{part:04d}.jsonl.gz"
            n = _write_jsonl_gz(snap_dir / fname, buffer)
            total_rows += n
            mb = round((snap_dir / fname).stat().st_size / 1024 / 1024, 2)
            files.append({"file": fname, "rows": n, "mb": mb})
            print(f"  [snapshots] {fname}: {n} 行, {mb} MB")
    finally:
        conn.close()

    return {
        "retention_days": retention_days,
        "since": since,
        "total_rows": total_rows,
        "files": files,
    }


def export_monitor_pool(
    source: Path,
    main_db: Path,
    out_dir: Path,
    include_snapshots: bool = False,
) -> dict:
    if not source.is_dir():
        raise FileNotFoundError(f"报告源目录不存在: {source}")
    if not main_db.is_file():
        raise FileNotFoundError(f"SQLite 主库不存在: {main_db}")

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"扫描报告: {source}")
    goods_set, report_meta = collect_monitor_goods(source)
    goods_ids = sorted(goods_set)
    print(f"监控池商品（去重）: {len(goods_ids)}")

    (out_dir / "monitor_goods_ids.json").write_text(
        json.dumps(goods_ids, ensure_ascii=False, indent=0), encoding="utf-8"
    )

    print(f"导出 sold_history ← {main_db}")
    hist_stats = export_sold_history(main_db, goods_ids, out_dir)

    snap_stats = None
    if include_snapshots:
        print(f"导出 sold_snapshots（近 90 天）")
        snap_stats = export_sold_snapshots(main_db, goods_ids, out_dir)

    manifest = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_root": str(source),
        "main_db": str(main_db),
        "pool_rule": "v1d > 0 OR actual_v1d > 0",
        "monitor_goods_count": len(goods_ids),
        "reports": report_meta,
        "sold_history": hist_stats,
        "sold_snapshots": snap_stats,
    }
    (out_dir / "export_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main():
    ap = argparse.ArgumentParser(description="导出监控池 sold_history 上云数据包")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--main-db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--snapshots", action="store_true", help="同时导出近 90 天 sold_snapshots")
    args = ap.parse_args()

    m = export_monitor_pool(
        Path(args.source),
        Path(args.main_db),
        Path(args.out),
        include_snapshots=args.snapshots,
    )
    print(
        f"\n完成: 监控池 {m['monitor_goods_count']} 商品, "
        f"sold_history {m['sold_history']['total_rows']} 行"
    )
    print(f"清单: {Path(args.out) / 'export_manifest.json'}")


if __name__ == "__main__":
    main()
