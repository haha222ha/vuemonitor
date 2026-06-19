# -*- coding: utf-8
"""打包 + 登记 + PG 同步 公共步骤。"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime

from cloud_deploy.scripts.report_packager import pack_report_dir


def parse_meta_from_data_js(data_js_path: str) -> dict:
    from cloud_deploy.cloud_api.sync_service import _parse_report_payload

    with open(data_js_path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        return _parse_report_payload(text).get("meta") or {}
    except Exception:
        return {}


def pack_register_sync(
    report_dir: str,
    archive_type: str,
    archive_dir: str,
    sync_pg: bool = True,
) -> dict:
    from cloud_deploy.cloud_api import database
    from cloud_deploy.cloud_api.config import get_settings

    database.init_db()
    s = get_settings()

    pack_info = pack_report_dir(report_dir)
    os.makedirs(archive_dir, exist_ok=True)
    dest_zip = os.path.join(archive_dir, pack_info["file_name"])
    if os.path.abspath(pack_info["zip_path"]) != os.path.abspath(dest_zip):
        shutil.copy2(pack_info["zip_path"], dest_zip)

    data_js = os.path.join(report_dir, "data.js")
    meta = parse_meta_from_data_js(data_js) if os.path.isfile(data_js) else {}
    meta["_sha256"] = pack_info["sha256"]
    report_date = str(meta.get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]

    st = os.stat(dest_zip)
    database.upsert_report_archive(
        report_date=report_date,
        archive_type=archive_type,
        storage_path=dest_zip,
        file_name=os.path.basename(dest_zip),
        file_size=int(st.st_size),
        sha256=str(pack_info["sha256"]),
        row_count=int(meta.get("count") or 0),
        meta=meta,
    )

    pg_result = {}
    if sync_pg and s.xhs_database_url.startswith("postgres") and os.path.isfile(data_js):
        from cloud_deploy.scripts.sync_report_to_pg import sync_report_to_pg

        pg_result = sync_report_to_pg(data_js, source=meta.get("source", "cloud_pipeline"))

    return {
        "report_date": report_date,
        "archive_type": archive_type,
        "zip": dest_zip,
        "meta_count": meta.get("count"),
        "pg": pg_result,
    }
