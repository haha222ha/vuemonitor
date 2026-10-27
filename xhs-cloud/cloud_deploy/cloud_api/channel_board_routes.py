# -*- coding: utf-8 -*-
"""私密 · 增量商品库/渠道选品看板（密码门 + zip 上传），镜像 takeon/psyche。"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from cloud_deploy.cloud_api.auth import verify_sync_key

router = APIRouter(tags=["channel-board"])


def _password() -> str:
    return (
        os.environ.get("XHS_CHANNEL_BOARD_PASSWORD")
        or os.environ.get("XHS_PRIVATE_BOARD_PASSWORD")
        or os.environ.get("XHS_PSYCHE_BOARD_PASSWORD")
        or "channel2026"
    ).strip()


def _token(password: str = "") -> str:
    raw = (password or _password()).strip()
    return hashlib.sha256(f"xhs-channel-board|{raw}".encode("utf-8")).hexdigest()


def _cookie_ok(request: Request) -> bool:
    got = request.cookies.get("channel_board_auth") or ""
    return bool(got) and hmac.compare_digest(got, _token())


def _boards_root() -> str:
    from cloud_deploy.cloud_api.config import get_settings

    return os.path.join(get_settings().xhs_data_dir, "channel_boards")


@router.post("/api/v1/sync/channel-board-upload")
async def sync_channel_board_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.reporting.constants import ARCHIVE_CHANNEL_BOARD

    filename = os.path.basename(file.filename or "channel-board.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-channel-board-")
    zip_path = os.path.join(tmp_dir, filename)
    try:
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(file.file, out)

        extract_root = os.path.join(tmp_dir, "extract")
        os.makedirs(extract_root, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        report_dir = ""
        for root, _dirs, files in os.walk(extract_root):
            if (
                "index.html" in files
                and "channel_board.json" in files
                and "channel_board_data.js" in files
            ):
                report_dir = root
                break
        if not report_dir:
            raise HTTPException(status_code=400, detail="zip 内未找到增量商品库看板目录")

        with open(os.path.join(report_dir, "channel_board.json"), encoding="utf-8") as f:
            marker = json.load(f)
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")

        boards_root = _boards_root()
        dest_live = os.path.join(boards_root, report_date)
        os.makedirs(boards_root, exist_ok=True)
        if os.path.isdir(dest_live):
            shutil.rmtree(dest_live)
        shutil.copytree(report_dir, dest_live)

        latest = os.path.join(boards_root, "latest")
        if os.path.isdir(latest):
            shutil.rmtree(latest)
        shutil.copytree(dest_live, latest)

        archive_dir = get_settings().xhs_report_archive_dir
        os.makedirs(archive_dir, exist_ok=True)
        dest_zip = os.path.join(
            archive_dir, f"channel_board_{report_date.replace('-', '')}.zip"
        )
        shutil.copy2(zip_path, dest_zip)
        h = hashlib.sha256()
        with open(dest_zip, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)

        db.init_db()
        db.upsert_report_archive(
            report_date=report_date,
            archive_type=ARCHIVE_CHANNEL_BOARD,
            storage_path=dest_zip,
            file_name=os.path.basename(dest_zip),
            file_size=int(os.path.getsize(dest_zip)),
            sha256=h.hexdigest(),
            row_count=int(marker.get("items_exported") or marker.get("total") or 0),
            meta={
                "report_kind": "channel_incremental_board",
                "private": True,
                "view_path": "/channel/",
                **marker,
            },
        )
        return {
            "ok": True,
            "report_date": report_date,
            "view_url": "/channel/",
            "live_dir": dest_live,
            "row_count": int(marker.get("items_exported") or 0),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/channel", response_class=HTMLResponse)
@router.get("/channel/", response_class=HTMLResponse)
def channel_gate(request: Request):
    if _cookie_ok(request):
        return RedirectResponse(url="/channel/board/", status_code=302)
    return HTMLResponse(
        """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<title>增量商品库</title>
<style>
body{font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#0a0f0e;color:#e8f2ee;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{width:400px;padding:28px;background:#141c1a;border:1px solid #24332e;border-radius:14px}
h1{font-size:20px;margin:0 0 8px}p{color:#8aa399;font-size:13px;line-height:1.5}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #24332e;background:#0c1110;color:#fff;box-sizing:border-box}
button{margin-top:12px;width:100%;padding:11px;border:0;border-radius:10px;background:#14b8a6;color:#042f2e;font-weight:700;cursor:pointer}
</style></head><body><div class="box">
<h1>增量商品库 · 渠道选品</h1>
<p>私密入口 · 多月采集动销时序 + Pinterest/国内渠道适配</p>
<form method="post" action="/channel/login">
<input name="password" type="password" placeholder="访问密码" autofocus/>
<button type="submit">进入</button>
</form>
</div></body></html>"""
    )


@router.post("/channel/login")
async def channel_login(request: Request):
    ctype = (request.headers.get("content-type") or "").lower()
    password = ""
    if "application/json" in ctype:
        try:
            body = await request.json()
            password = str((body or {}).get("password") or "")
        except Exception:
            password = ""
    else:
        form = await request.form()
        password = str(form.get("password") or "")

    if not hmac.compare_digest(_token(password), _token()):
        return HTMLResponse(
            "<h3 style='font-family:sans-serif;color:#f07178'>密码错误</h3>"
            "<a href='/channel/'>返回</a>",
            status_code=401,
        )
    resp = RedirectResponse(url="/channel/board/", status_code=302)
    resp.set_cookie(
        key="channel_board_auth",
        value=_token(),
        httponly=True,
        samesite="lax",
        max_age=86400 * 14,
    )
    return resp


@router.get("/channel/board/{path:path}")
@router.get("/channel/board")
@router.get("/channel/board/")
def channel_board_files(request: Request, path: str = ""):
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    if request.url.path.rstrip("/") == "/channel/board" and not (path or "").strip():
        return RedirectResponse(url="/channel/board/", status_code=302)
    root = os.path.join(_boards_root(), "latest")
    if not os.path.isdir(root):
        return HTMLResponse(
            "<h3>看板尚未上传</h3><p>请本机生成后运行 publish_channel_board_cloud.py</p>",
            status_code=404,
        )
    rel = (path or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        rel = "index.html"
    target = os.path.normpath(os.path.join(root, rel))
    if not target.startswith(os.path.normpath(root)):
        raise HTTPException(status_code=400, detail="bad path")
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="not found")
    media = None
    low = rel.lower()
    if low.endswith(".js"):
        media = "application/javascript; charset=utf-8"
    elif low.endswith(".json"):
        media = "application/json; charset=utf-8"
    elif low.endswith(".html"):
        media = "text/html; charset=utf-8"
    return FileResponse(
        target,
        media_type=media,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )
