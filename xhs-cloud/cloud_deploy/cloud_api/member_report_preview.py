# -*- coding: utf-8
"""会员报告在线预览：从 zip / incoming 解压到缓存并安全提供静态文件。"""
from __future__ import annotations

import os
import shutil
import tempfile

ALLOWED_BASENAMES = frozenset(
    {
        "index_vue.html",
        "index_with_gr.html",
        "index.html",
        "data.js",
        "enrich.js",
    }
)
ALLOWED_EXTENSIONS = frozenset(
    {
        ".html",
        ".js",
        ".css",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
    }
)


def _preview_cache_root() -> str:
    from cloud_deploy.cloud_api.config import get_settings

    s = get_settings()
    base = os.path.join(os.path.dirname(s.xhs_report_archive_dir), "preview_cache")
    os.makedirs(base, exist_ok=True)
    return base


def _cache_dir(report_date: str, archive_type: str) -> str:
    safe_date = str(report_date or "")[:10]
    safe_type = str(archive_type or "member_daily_zip").strip()
    return os.path.join(_preview_cache_root(), f"{safe_type}_{safe_date}")


def ensure_member_report_dir(report_date: str, archive_type: str) -> str:
    """返回含 data.js 的报告目录（优先缓存 / incoming，否则从 zip 解压）。"""
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.cloud_api.report_upload_service import extract_report_zip

    cache = _cache_dir(report_date, archive_type)
    if os.path.isfile(os.path.join(cache, "data.js")):
        return cache

    zip_path = db.get_archive_path(report_date, archive_type)
    if not zip_path or not os.path.isfile(zip_path):
        raise FileNotFoundError("报告不存在")

    s = get_settings()
    folder_guess = os.path.splitext(os.path.basename(zip_path))[0]
    incoming_dir = os.path.join(s.xhs_report_incoming_dir, folder_guess)
    src_dir = ""
    tmp_parent = ""

    if os.path.isfile(os.path.join(incoming_dir, "data.js")):
        src_dir = incoming_dir
    else:
        tmp_parent = tempfile.mkdtemp(prefix="xhs_preview_", dir=_preview_cache_root())
        src_dir = extract_report_zip(zip_path, tmp_parent)

    if os.path.isdir(cache):
        shutil.rmtree(cache, ignore_errors=True)
    shutil.copytree(src_dir, cache)

    if tmp_parent and os.path.isdir(tmp_parent):
        shutil.rmtree(tmp_parent, ignore_errors=True)

    if not os.path.isfile(os.path.join(cache, "data.js")):
        raise FileNotFoundError("报告缺少 data.js")
    return cache


def resolve_member_report_file(report_date: str, archive_type: str, rel_path: str) -> str:
    root = os.path.abspath(ensure_member_report_dir(report_date, archive_type))
    rel = (rel_path or "index_vue.html").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise ValueError("无效路径")
    full = os.path.abspath(os.path.join(root, rel))
    if not full.startswith(root + os.sep) and full != root:
        raise ValueError("无效路径")
    if not os.path.isfile(full):
        raise FileNotFoundError(rel)

    base = os.path.basename(full)
    ext = os.path.splitext(base)[1].lower()
    if base in ALLOWED_BASENAMES or ext in ALLOWED_EXTENSIONS:
        return full
    raise ValueError("不允许的文件类型")


def guess_media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".html":
        return "text/html; charset=utf-8"
    if ext == ".js":
        return "application/javascript; charset=utf-8"
    if ext == ".css":
        return "text/css; charset=utf-8"
    if ext == ".json":
        return "application/json; charset=utf-8"
    if ext == ".svg":
        return "image/svg+xml"
    import mimetypes

    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"
