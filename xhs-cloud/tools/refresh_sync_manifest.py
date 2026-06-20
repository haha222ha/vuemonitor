# -*- coding: utf-8 -*-
"""Refresh server_sync_pack/manifest.json from export_manifest + historical_reports."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "server_sync_pack"


def refresh(pack: Path) -> dict:
    hist = pack / "historical_reports"
    pool = pack / "monitor_pool"
    exp = json.loads((pool / "export_manifest.json").read_text(encoding="utf-8"))
    reports: list[dict] = []
    total_mb = 0.0
    for d in sorted(hist.iterdir()):
        if not d.is_dir():
            continue
        js = d / "data.js"
        if not js.is_file():
            continue
        mb = round(js.stat().st_size / 1024 / 1024, 2)
        total_mb += mb
        reports.append({"dir_name": d.name, "data_js_mb": mb})
    manifest = {
        "prepared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "main_db": exp.get("main_db", ""),
        "output_root": str(pack.resolve()),
        "pool_rule": exp.get("pool_rule", ""),
        "historical_reports": {
            "total_reports": len(reports),
            "total_data_js_mb": round(total_mb, 2),
            "reports": reports,
        },
        "monitor_pool": {
            "monitor_goods_count": exp.get("monitor_goods_count", 0),
            "sold_history_rows": exp.get("sold_history", {}).get("total_rows", 0),
            "sold_history_files": len(exp.get("sold_history", {}).get("files", [])),
        },
    }
    (pack / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=str(DEFAULT_PACK))
    args = ap.parse_args()
    m = refresh(Path(args.pack))
    mp = m["monitor_pool"]
    print(f"monitor_goods={mp['monitor_goods_count']} sold_history_rows={mp['sold_history_rows']}")


if __name__ == "__main__":
    main()
