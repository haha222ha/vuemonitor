#!/usr/bin/env python3
"""Quick audit of gen_report / cloud_gen_report data.js."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

COLS = [
    "goods_id", "title", "price", "sold", "v1h", "v6h", "actual_v1d", "v1d",
    "actual_gr", "gr", "actual_vsr", "vsr", "acc", "burst",
    "pool", "first_seen", "store_id", "store_name", "shelf_time",
    "shop_sales", "shop_fans", "shop_fsr", "goods_fsr",
    "behavior", "is_virtual", "base_hours", "base_at", "anomaly",
]


def load_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"var\s+REPORT_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m:
        m = re.search(r"var\s+REPORT_DATA\s*=\s*(\{.*\})", text, re.S)
    if not m:
        raise RuntimeError("cannot parse REPORT_DATA")
    return json.loads(m.group(1))


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Administrator\Desktop\全量0621\data.js")
    data = load_report(path)
    meta = data.get("meta") or {}
    items = data.get("items") or []
    print("=== META ===")
    for k in (
        "date", "time", "count", "count_raw", "filter_mode", "filter_label",
        "total_goods", "active_goods", "metric_mode", "metric_note", "source", "output_dir",
    ):
        if k in meta:
            print(f"  {k}: {meta[k]}")
    print(f"  items_len: {len(items)}")
    print(f"  file_mb: {path.stat().st_size / 1024 / 1024:.1f}")

    idx = {n: i for i, n in enumerate(COLS)}
    empty = Counter()
    zero = Counter()
    sample_missing = []
    for it in items:
        if not isinstance(it, list):
            continue
        for name in (
            "title", "store_id", "store_name", "shop_sales", "shop_fans",
            "shelf_time", "price", "sold", "actual_v1d", "v1d",
        ):
            i = idx[name]
            v = it[i] if i < len(it) else None
            if v in (None, "", "0", 0):
                empty[name] += 1
            if name in ("shop_sales", "shop_fans", "sold", "price") and (v in (None, "", 0, "0")):
                zero[name] += 1
        if len(sample_missing) < 3:
            if not (it[idx["store_id"]] and it[idx["store_name"]]):
                sample_missing.append(it)

    n = max(len(items), 1)
    print("\n=== FIELD FILL RATE (empty/zero) ===")
    for name in (
        "title", "store_id", "store_name", "shop_sales", "shop_fans",
        "shelf_time", "price", "sold", "actual_v1d", "v1d",
    ):
        print(f"  {name:12} empty~{empty[name]:6} ({empty[name]*100/n:5.1f}%)")

    # v1h/v6h always 0 in sold_daily path
    v1h0 = sum(1 for it in items if isinstance(it, list) and float(it[idx["v1h"]] or 0) == 0)
    v6h0 = sum(1 for it in items if isinstance(it, list) and float(it[idx["v6h"]] or 0) == 0)
    print(f"  v1h==0: {v1h0} ({v1h0*100/n:.1f}%)")
    print(f"  v6h==0: {v6h0} ({v6h0*100/n:.1f}%)")

    # actual == v1d (no estimate split)
    same = sum(
        1
        for it in items
        if isinstance(it, list) and float(it[idx["actual_v1d"]] or 0) == float(it[idx["v1d"]] or 0)
    )
    print(f"  actual_v1d==v1d: {same} ({same*100/n:.1f}%)")

    pools = Counter(str(it[idx["pool"]] if isinstance(it, list) else "") for it in items)
    print("\n=== POOL ===")
    for k, v in pools.most_common(8):
        print(f"  {k or '(empty)'}: {v}")

    if sample_missing:
        print("\n=== SAMPLE missing store ===")
        for it in sample_missing[:2]:
            gid = it[idx["goods_id"]]
            title = str(it[idx["title"]])[:30]
            sid = it[idx["store_id"]]
            ss = it[idx["shop_sales"]]
            sf = it[idx["shop_fans"]]
            print(f"  id={gid} title={title} store_id={sid} shop_sales={ss} shop_fans={sf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
