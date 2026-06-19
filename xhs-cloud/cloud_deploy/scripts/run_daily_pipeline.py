# -*- coding: utf-8 -*-
"""
报告入库流水线（独立系统 · 不调用 gen_report / track_queue）。

本地 gen_report 产出 全量MMDD/ 或 zip 后，scp 到服务器 incoming 目录，
本脚本：打 zip → 登记 PG → sync data.js → 可选 sold_history 回补。

用法:
  python cloud_deploy/scripts/run_daily_pipeline.py
  python cloud_deploy/scripts/run_daily_pipeline.py --report-dir /path/to/全量0619
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_DEPLOY = os.path.dirname(SCRIPT_DIR)
CLOUD_ROOT = os.path.dirname(CLOUD_DEPLOY)
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap
from cloud_deploy.scripts.report_packager import pack_report_dir


def _log(msg: str) -> None:
    print(f"[ingest] {msg}", flush=True)


def _parse_meta_from_data_js(data_js_path: str) -> dict:
    from cloud_deploy.cloud_api.sync_service import _parse_report_payload

    with open(data_js_path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        return _parse_report_payload(text).get("meta") or {}
    except Exception:
        return {}


def _find_report_dir(report_dir: str, incoming_dir: str) -> str:
    if report_dir and os.path.isdir(report_dir):
        return report_dir
    for base in (incoming_dir,):
        if not base or not os.path.isdir(base):
            continue
        dirs = [
            os.path.join(base, d)
            for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d)) and d.startswith("全量")
        ]
        if dirs:
            dirs.sort()
            return dirs[-1]
    raise RuntimeError(f"未找到报告目录，请 scp 全量MMDD 到 {incoming_dir}")


def register_archive(report_date: str, archive_type: str, zip_path: str, meta: dict) -> None:
    from cloud_deploy.cloud_api import database

    st = os.stat(zip_path)
    database.upsert_report_archive(
        report_date=report_date,
        archive_type=archive_type,
        storage_path=zip_path,
        file_name=os.path.basename(zip_path),
        file_size=int(st.st_size),
        sha256=str(meta.get("_sha256") or ""),
        row_count=int(meta.get("count") or 0),
        meta=meta,
    )


def run_ingest(report_dir: str = "") -> dict:
    bootstrap()
    from cloud_deploy.cloud_api import database
    from cloud_deploy.cloud_api.config import get_settings

    s = get_settings()
    database.init_db()
    database.ensure_admin()

    report_dir = _find_report_dir(report_dir, s.xhs_report_incoming_dir)
    _log(f"Step1: ingest {report_dir}")

    data_js = os.path.join(report_dir, "data.js")
    if not os.path.isfile(data_js):
        raise RuntimeError(f"缺少 data.js: {report_dir}")

    _log("Step2: pack zip ...")
    pack_info = pack_report_dir(report_dir)
    os.makedirs(s.xhs_report_archive_dir, exist_ok=True)
    dest_zip = os.path.join(s.xhs_report_archive_dir, pack_info["file_name"])
    if os.path.abspath(pack_info["zip_path"]) != os.path.abspath(dest_zip):
        shutil.copy2(pack_info["zip_path"], dest_zip)

    meta = _parse_meta_from_data_js(data_js)
    meta["_sha256"] = pack_info["sha256"]
    report_date = str(meta.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]

    _log(f"Step3: register archive {report_date}")
    register_archive(
        report_date=report_date,
        archive_type="member_daily_zip",
        zip_path=dest_zip,
        meta=meta,
    )

    if s.xhs_database_url.startswith("postgres"):
        from cloud_deploy.scripts.sync_report_to_pg import sync_report_to_pg

        pg_result = sync_report_to_pg(data_js)
        _log(f"Step4: sync PG {pg_result}")

        from cloud_deploy.scripts.sync_pipeline_hooks import run_post_report_pg_steps

        post = run_post_report_pg_steps(s, _log)
        _log(f"Step5+: post hooks {post}")
    else:
        _log("Step4: skip PG（未配置 XHS_DATABASE_URL）")

    result = {"report_date": report_date, "zip": dest_zip, "meta_count": meta.get("count")}
    _log(f"Done: {result}")
    return result


def main():
    ap = argparse.ArgumentParser(description="报告入库（不运行 gen_report）")
    ap.add_argument("--report-dir", default="", help="指定 全量MMDD 目录，默认取 incoming 最新")
    args = ap.parse_args()
    run_ingest(report_dir=args.report_dir)


if __name__ == "__main__":
    main()
