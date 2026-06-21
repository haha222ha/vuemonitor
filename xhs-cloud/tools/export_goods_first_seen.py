# -*- coding: utf-8 -*-
"""
从「选品报告库」导出 goods_id + first_seen，供云端 backfill_monitor_first_seen.py 使用。

默认从本地全量报告 data.js 读取每行的 first_seen（与 HTML 展示一致），
可选再用 SQLite goods.first_seen 补全缺失项。

用法:
  python tools/export_goods_first_seen.py
  python tools/export_goods_first_seen.py --source "C:\\Users\\Administrator\\Desktop"
  python tools/export_goods_first_seen.py --source Desktop --extra-source Downloads
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cloud_deploy.cloud_api.sync_service import _parse_report_payload


def _field(item, col_map: dict[str, int], key: str, default=""):
    if isinstance(item, dict):
        return item.get(key, default)
    idx = col_map.get(key)
    if idx is None or idx >= len(item):
        return default
    return item[idx] if item[idx] is not None else default


def _norm_date(s: str) -> str:
    s = str(s or "").strip()
    return s[:19] if len(s) >= 10 else ""


def _pick_earlier(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    return a if a <= b else b


def collect_from_reports(roots: list[Path]) -> dict[str, str]:
    """扫描 全量*/data.js，按 goods_id 保留最早 first_seen。"""
    best: dict[str, str] = {}
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        files.extend(sorted(root.glob("全量*/data.js")))
        if (root / "data.js").is_file() and root.name.startswith("全量"):
            files.append(root / "data.js")

    seen_paths: set[str] = set()
    for js in files:
        rp = str(js.resolve())
        if rp in seen_paths:
            continue
        seen_paths.add(rp)
        try:
            text = js.read_text(encoding="utf-8")
            payload = _parse_report_payload(text)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"  [skip] {js}: {e}", flush=True)
            continue

        columns = payload.get("columns") or (payload.get("meta") or {}).get("columns") or []
        if not columns:
            print(f"  [skip] {js}: 无 columns", flush=True)
            continue
        col_map = {str(n): i for i, n in enumerate(columns)}
        if "first_seen" not in col_map or "goods_id" not in col_map:
            print(f"  [skip] {js}: 缺 first_seen/goods_id 列", flush=True)
            continue

        n = 0
        for item in payload.get("items") or []:
            gid = str(_field(item, col_map, "goods_id", "") or "").strip()
            fs = _norm_date(_field(item, col_map, "first_seen", ""))
            if not gid or not fs:
                continue
            best[gid] = _pick_earlier(best.get(gid, ""), fs)
            n += 1
        print(f"  [report] {js.parent.name}: {n:,} 行 -> 累计 {len(best):,} goods", flush=True)

    return best


def fill_from_sqlite(best: dict[str, str], db_path: str) -> int:
    if not db_path or not os.path.isfile(db_path):
        return 0
    added = 0
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=120)
    try:
        for gid, fs in conn.execute(
            """SELECT goods_id, first_seen FROM goods
               WHERE first_seen IS NOT NULL AND TRIM(first_seen) != ''"""
        ):
            gid = str(gid or "").strip()
            fs = _norm_date(fs)
            if not gid or not fs:
                continue
            if gid in best:
                continue
            best[gid] = fs
            added += 1
    finally:
        conn.close()
    return added


def resolve_roots(sources: list[str]) -> list[Path]:
    home = Path.home()
    out: list[Path] = []
    for s in sources:
        s = s.strip()
        if not s:
            continue
        if s.lower() in ("desktop", "downloads"):
            p = home / ("Desktop" if s.lower() == "desktop" else "Downloads")
        else:
            p = Path(s)
        out.append(p.expanduser().resolve())
    return out


def main():
    ap = argparse.ArgumentParser(description="从选品报告库导出 first_seen")
    ap.add_argument(
        "--source",
        action="append",
        default=[],
        help="报告根目录（可多次指定；含 全量MMDD/data.js）。默认 Desktop",
    )
    ap.add_argument(
        "--extra-source",
        action="append",
        default=[],
        help="额外报告目录，如 Downloads",
    )
    ap.add_argument(
        "--db",
        default=os.environ.get(
            "XHS_DB_PATH",
            r"D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db",
        ),
        help="可选：用 SQLite goods.first_seen 补全报告里没有的 goods_id",
    )
    ap.add_argument(
        "--no-sqlite",
        action="store_true",
        help="仅使用报告 data.js，不读 SQLite",
    )
    ap.add_argument(
        "--out",
        default=str(ROOT / "tools" / "first_seen.json"),
        help="输出 JSON",
    )
    args = ap.parse_args()

    sources = args.source or ["Desktop"]
    sources.extend(args.extra_source or [])
    roots = resolve_roots(sources)
    print(f"扫描报告目录: {[str(r) for r in roots]}", flush=True)

    best = collect_from_reports(roots)
    print(f"报告库汇总: {len(best):,} 个 goods_id 有 first_seen", flush=True)

    if not args.no_sqlite:
        added = fill_from_sqlite(best, args.db)
        if added:
            print(f"SQLite 补全: +{added:,} -> 共 {len(best):,}", flush=True)

    out_rows = [{"goods_id": gid, "first_seen": fs} for gid, fs in sorted(best.items())]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False)
    mb = out_path.stat().st_size / 1024 / 1024
    print(f"已写入 {len(out_rows):,} 条 -> {out_path} ({mb:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
