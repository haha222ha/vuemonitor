# -*- coding: utf-8 -*-
"""本地整理待同步到服务器的完整上云数据包。

包含两部分（对齐需求规格书）：
  1. historical_reports/  — gen_report 历史日报（data.js + html）
  2. monitor_pool/        — 报告日增量>0 商品的 sold_history（从 SQLite 导出，非 13GB 全库）

用法:
  python tools/prepare_server_sync.py
  python tools/prepare_server_sync.py --source "C:/Users/.../每日选品全量数据"
  python tools/prepare_server_sync.py --main-db "D:/.../xhs_burst_monitor.db" --snapshots
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"d:\vuemonitor\xhs-cloud\server_sync_pack\historical_reports")
DEFAULT_DB = Path(r"D:\0619xhs备份\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db")
if not DEFAULT_DB.is_file():
    DEFAULT_DB = Path(r"D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db")
OUT_ROOT = ROOT / "server_sync_pack"
HIST_DIR = OUT_ROOT / "historical_reports"
POOL_DIR = OUT_ROOT / "monitor_pool"
HTML_TPL = ROOT / "cloud_deploy" / "assets" / "index_with_gr.html"


def _read_date(data_js: Path) -> str:
    head = data_js.read_text(encoding="utf-8", errors="replace")[:800]
    m = re.search(r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"', head)
    return m.group(1) if m else ""


def prepare_reports(source: Path, hist: Path) -> tuple[list[dict], float]:
    if not source.is_dir():
        raise FileNotFoundError(f"源目录不存在: {source}")

    hist.mkdir(parents=True, exist_ok=True)

    by_date: dict[str, dict] = {}
    for d in source.iterdir():
        if not d.is_dir():
            continue
        js = d / "data.js"
        if not js.is_file():
            continue
        size = js.stat().st_size
        date = _read_date(js) or d.name
        prev = by_date.get(date)
        if not prev or size > prev["size"]:
            by_date[date] = {"dir": d, "size": size, "date": date}

    reports = []
    total_mb = 0.0
    for date in sorted(by_date.keys()):
        item = by_date[date]
        src: Path = item["dir"]
        dest_name = src.name if src.name.startswith("全量") else f"全量{date.replace('-', '')[4:]}"
        dest = hist / dest_name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        has_html = (dest / "index_with_gr.html").is_file()
        if not has_html and HTML_TPL.is_file():
            shutil.copy2(HTML_TPL, dest / "index_with_gr.html")
            has_html = True

        mb = round(item["size"] / 1024 / 1024, 2)
        total_mb += mb
        reports.append(
            {
                "report_date": date,
                "dir_name": dest_name,
                "source_dir": src.name,
                "data_js_mb": mb,
                "has_html": has_html,
                "server_path": f"/opt/xhs-cloud/data/import_batch/historical_reports/{dest_name}",
            }
        )
        print(f"  [report] {date} -> {dest_name} ({mb} MB)")

    return reports, total_mb


def prepare_monitor_pool(
    source: Path, main_db: Path, pool_dir: Path, include_snapshots: bool
) -> dict:
    from tools.export_monitor_pool_for_cloud import export_monitor_pool

    print(f"\n导出监控池 sold_history（日增量>0）")
    return export_monitor_pool(source, main_db, pool_dir, include_snapshots=include_snapshots)


def prepare(
    source: Path,
    out_root: Path,
    main_db: Path,
    include_snapshots: bool = False,
) -> dict:
    hist = out_root / "historical_reports"
    pool = out_root / "monitor_pool"

    print("=== 1/2 历史日报 ===")
    reports, total_mb = prepare_reports(source, hist)

    pool_manifest = prepare_monitor_pool(source, main_db, pool, include_snapshots)

    manifest = {
        "prepared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_root": str(source),
        "main_db": str(main_db),
        "output_root": str(out_root),
        "pool_rule": "v1d > 0 OR actual_v1d > 0",
        "historical_reports": {
            "total_reports": len(reports),
            "total_data_js_mb": round(total_mb, 2),
            "reports": reports,
        },
        "monitor_pool": {
            "monitor_goods_count": pool_manifest.get("monitor_goods_count", 0),
            "sold_history_rows": pool_manifest.get("sold_history", {}).get("total_rows", 0),
            "sold_history_files": len(
                pool_manifest.get("sold_history", {}).get("files", [])
            ),
            "export_manifest": str(pool / "export_manifest.json"),
        },
    }

    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    scp_ps1 = out_root / "scp_upload.ps1"
    scp_ps1.write_text(
        f"""# 填写 ECS 信息后运行
$ECS = "your-server-ip"
$USER = "admin"
$SRC = "{out_root}"
$DEST = "/opt/xhs-cloud/data/import_batch/"

ssh ${{USER}}@${{ECS}} "mkdir -p $DEST"
scp -r "$SRC\\historical_reports" "${{USER}}@${{ECS}}:$DEST"
scp -r "$SRC\\monitor_pool" "${{USER}}@${{ECS}}:$DEST"
scp "$SRC\\manifest.json" "${{USER}}@${{ECS}}:$DEST"
Write-Host "上传完成。服务器依次执行 import_historical_reports + import_monitor_pool_offline"
""",
        encoding="utf-8",
    )

    readme = out_root / "README.md"
    readme.write_text(
        f"""# 服务器同步数据包

- 生成时间: {manifest['prepared_at']}
- 历史日报: {manifest['historical_reports']['total_reports']} 份 / {manifest['historical_reports']['total_data_js_mb']} MB
- 监控池商品: {manifest['monitor_pool']['monitor_goods_count']}（日增量>0，非 13GB 全库）
- sold_history 行数: {manifest['monitor_pool']['sold_history_rows']}

## 数据说明

| 目录 | 内容 | 不上传 |
|------|------|--------|
| `historical_reports/全量*` | gen_report 日报 data.js | 13GB SQLite 全库 |
| `monitor_pool/sold_history/` | 监控池商品日级销量历史 | 未入池商品 |
| `monitor_pool/monitor_goods_ids.json` | 监控池 goods_id 清单 | — |

## 上传

```powershell
cd {out_root}
.\\scp_upload.ps1
```

## 服务器导入（按顺序）

```bash
cd /opt/xhs-cloud

# 1. 历史日报 → report_daily_items + monitor_goods
sudo -u admin env PYTHONPATH=/opt/xhs-cloud ./venv/bin/python \\
  cloud_deploy/scripts/import_historical_reports.py \\
  --root /opt/xhs-cloud/data/import_batch/historical_reports

# 2. 监控池 sold_history → goods_sold_daily
sudo -u admin env PYTHONPATH=/opt/xhs-cloud ./venv/bin/python \\
  cloud_deploy/scripts/import_monitor_pool_offline.py \\
  --pack /opt/xhs-cloud/data/import_batch/monitor_pool
```
""",
        encoding="utf-8",
    )

    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--main-db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(OUT_ROOT))
    ap.add_argument("--snapshots", action="store_true", help="同时导出近 90 天 sold_snapshots")
    args = ap.parse_args()
    print(f"源报告: {args.source}")
    print(f"主库:   {args.main_db}")
    print(f"输出:   {args.out}")
    m = prepare(
        Path(args.source),
        Path(args.out),
        Path(args.main_db),
        include_snapshots=args.snapshots,
    )
    hr = m["historical_reports"]
    mp = m["monitor_pool"]
    print(
        f"\n完成: 日报 {hr['total_reports']} 份 ({hr['total_data_js_mb']} MB), "
        f"监控池 {mp['monitor_goods_count']} 商品 / sold_history {mp['sold_history_rows']} 行"
    )
    print(f"清单: {Path(args.out) / 'manifest.json'}")


if __name__ == "__main__":
    main()
