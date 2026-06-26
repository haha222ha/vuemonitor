# -*- coding: utf-8 -*-
r"""
本地 gen_report 完成后推云（方案 B：上传 zip → 云 ingest → 会员下载）。

配置:
  XHS_CLOUD_PKG_ROOT=E:/vuemonitor/xhs-cloud
  XHS_CLOUD_API_URL=https://monitor.xhs365.cn
  XHS_CLOUD_SYNC_KEY=与服务器 .env 一致
  XHS_CLOUD_REPORT_MODE=plan_b   # 默认；pg=旧模式写 PG

用法:
  python tools/cloud_sync_client.py upload-bundle --report-dir E:/每日选品全量数据/全量0626
  python tools/cloud_sync_client.py upload-bundle --data-js E:/.../全量0626/data.js
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import urllib.error
import urllib.request

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_XHS_CLOUD_ROOT = os.environ.get(
    "XHS_CLOUD_PKG_ROOT",
    os.path.dirname(_TOOLS),
)
if _XHS_CLOUD_ROOT not in sys.path:
    sys.path.insert(0, _XHS_CLOUD_ROOT)

SYNC_USER_AGENT = "XHS-Local-Sync/1.0"


def _log(msg: str) -> None:
    print(f"[cloud-sync] {msg}", flush=True)


def _api_base() -> str:
    return os.environ.get("XHS_CLOUD_API_URL", "http://127.0.0.1:8080").rstrip("/")


def _sync_key() -> str:
    return os.environ.get("XHS_CLOUD_SYNC_KEY", "")


def _http_headers(extra: dict | None = None) -> dict[str, str]:
    headers = {"User-Agent": SYNC_USER_AGENT}
    if extra:
        headers.update(extra)
    return headers


def is_plan_b_mode() -> bool:
    mode = (os.environ.get("XHS_CLOUD_REPORT_MODE") or "plan_b").strip().lower()
    return mode in ("plan_b", "distribute", "upload", "bundle")


def _multipart_upload(url: str, file_path: str, field_name: str = "file") -> dict:
    sync_key = _sync_key()
    if not sync_key:
        raise RuntimeError("XHS_CLOUD_SYNC_KEY 未配置")
    boundary = f"----XHSBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    timeout = max(600, int(len(body) / 50000) + 120)
    req = urllib.request.Request(
        url,
        data=body,
        headers=_http_headers(
            {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Sync-Key": sync_key,
            }
        ),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"上传失败 HTTP {e.code}: {detail}") from e


def push_report_bundle(report_dir: str, log_func=None) -> dict:
    """打包 全量MMDD/ 为 zip 并上传到云 ingest（方案 B）。"""
    log = log_func or _log
    report_dir = os.path.abspath(report_dir)
    if not os.path.isdir(report_dir):
        raise FileNotFoundError(report_dir)
    from cloud_deploy.scripts.report_packager import pack_report_dir

    pack = pack_report_dir(report_dir)
    zip_path = pack["zip_path"]
    size_mb = int(pack.get("file_size_bytes") or os.path.getsize(zip_path)) / (1024 * 1024)
    log(f"打包完成 {pack['file_name']} ({size_mb:.1f} MB)，上传中…")
    api = _api_base()
    if not api:
        raise RuntimeError("XHS_CLOUD_API_URL 未配置")
    result = _multipart_upload(f"{api}/api/v1/sync/report-upload", zip_path)
    log(
        f"云 ingest 完成: date={result.get('report_date')} "
        f"zip={result.get('zip')} count={result.get('meta_count')}"
    )
    result["local_zip"] = zip_path
    result["via"] = "report-upload"
    return result


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
            headers=_http_headers({"Content-Type": "application/json", "X-Sync-Key": sync_key}),
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


def push_after_report(
    data_js_path: str,
    backfill_sold: bool = True,
    backfill_snapshots: bool = True,
    log_func=None,
) -> dict:
    report_dir = os.path.dirname(os.path.abspath(data_js_path))
    if is_plan_b_mode():
        return push_report_bundle(report_dir, log_func=log_func)
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
    ap = argparse.ArgumentParser(description="选品报告上云")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ub = sub.add_parser("upload-bundle", help="方案B: 打包目录 zip 上传并云 ingest")
    p_ub.add_argument("--report-dir", default="", help="全量MMDD 目录")
    p_ub.add_argument("--data-js", default="", help="或指定 data.js（取其父目录）")

    p_push = sub.add_parser("push", help="旧模式: 推送 data.js 到云端 PG")
    p_push.add_argument("--data-js", required=True)

    sub.add_parser("backfill-sold", help="回补监控池 sold_history").add_argument("--main-db", default="")
    sub.add_parser("backfill-snapshots", help="回补 sold_snapshots").add_argument("--main-db", default="")
    sub.add_parser("sync-incr-daily", help="sold_history 增量").add_argument("--main-db", default="")

    p_all = sub.add_parser("after-report", help="推云（plan_b=upload-bundle，pg=旧逻辑）")
    p_all.add_argument("--data-js", required=True)
    p_all.add_argument("--no-backfill", action="store_true")
    p_all.add_argument("--no-snapshots", action="store_true")

    args = ap.parse_args()
    if args.cmd == "upload-bundle":
        rd = args.report_dir.strip()
        if not rd and args.data_js:
            rd = os.path.dirname(os.path.abspath(args.data_js))
        if not rd:
            ap.error("需 --report-dir 或 --data-js")
        print(json.dumps(push_report_bundle(rd), ensure_ascii=False, indent=2))
    elif args.cmd == "push":
        push_daily_report(args.data_js)
    elif args.cmd == "backfill-sold":
        push_sold_history(getattr(args, "main_db", "") or None)
    elif args.cmd == "backfill-snapshots":
        push_sold_snapshots(getattr(args, "main_db", "") or None)
    elif args.cmd == "sync-incr-daily":
        push_incr_daily(getattr(args, "main_db", "") or None)
    elif args.cmd == "after-report":
        push_after_report(
            args.data_js,
            backfill_sold=not args.no_backfill,
            backfill_snapshots=not args.no_snapshots,
        )


if __name__ == "__main__":
    main()
