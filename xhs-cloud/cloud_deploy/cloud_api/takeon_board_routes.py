# -*- coding: utf-8 -*-
"""私密 · 选题承接复盘看板（密码门 + zip 上传），镜像 psyche board 模式。"""
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

router = APIRouter(tags=["takeon-board"])


def _password() -> str:
    return (
        os.environ.get("XHS_TAKEON_BOARD_PASSWORD")
        or os.environ.get("XHS_PRIVATE_BOARD_PASSWORD")
        or os.environ.get("XHS_PSYCHE_BOARD_PASSWORD")
        or "takeon2026"
    ).strip()


def _token(password: str = "") -> str:
    raw = (password or _password()).strip()
    return hashlib.sha256(f"xhs-takeon-board|{raw}".encode("utf-8")).hexdigest()


def _cookie_ok(request: Request) -> bool:
    got = request.cookies.get("takeon_board_auth") or ""
    return bool(got) and hmac.compare_digest(got, _token())


def _boards_root() -> str:
    from cloud_deploy.cloud_api.config import get_settings

    return os.path.join(get_settings().xhs_data_dir, "takeon_boards")


@router.post("/api/v1/sync/takeon-board-upload")
async def sync_takeon_board_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.reporting.constants import ARCHIVE_TAKEON_BOARD

    filename = os.path.basename(file.filename or "takeon-board.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-takeon-board-")
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
            if "index.html" in files and "takeon_board.json" in files and "data.js" in files:
                report_dir = root
                break
        if not report_dir:
            raise HTTPException(status_code=400, detail="zip 内未找到选题承接看板目录")

        with open(os.path.join(report_dir, "takeon_board.json"), encoding="utf-8") as f:
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
            archive_dir, f"takeon_board_{report_date.replace('-', '')}.zip"
        )
        shutil.copy2(zip_path, dest_zip)
        h = hashlib.sha256()
        with open(dest_zip, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)

        db.init_db()
        db.upsert_report_archive(
            report_date=report_date,
            archive_type=ARCHIVE_TAKEON_BOARD,
            storage_path=dest_zip,
            file_name=os.path.basename(dest_zip),
            file_size=int(os.path.getsize(dest_zip)),
            sha256=h.hexdigest(),
            row_count=int(marker.get("n") or 0),
            meta={
                "report_kind": "takeon_review_board",
                "private": True,
                "view_path": "/takeon/",
                **marker,
            },
        )
        return {
            "ok": True,
            "report_date": report_date,
            "view": "/takeon/",
            "n": marker.get("n"),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/takeon", response_class=HTMLResponse)
@router.get("/takeon/", response_class=HTMLResponse)
def takeon_gate(request: Request):
    if _cookie_ok(request):
        return RedirectResponse(url="/takeon/board/", status_code=302)
    return HTMLResponse(
        """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<title>选题承接看板</title>
<style>
body{font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#f6f3ee;color:#1c1917;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{width:380px;padding:28px;background:#fff;border:1px solid #e7e5e4;border-radius:14px}
h1{font-size:20px;margin:0 0 8px}p{color:#78716c;font-size:13px;line-height:1.5}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #e7e5e4;background:#fafaf9;box-sizing:border-box}
button{margin-top:12px;width:100%;padding:11px;border:0;border-radius:10px;background:#0f766e;color:#fff;font-weight:700;cursor:pointer}
</style></head><body><div class="box">
<h1>选题承接复盘</h1>
<p>私密入口 · 爆品需求 × 怎么接住（开源/自写包/AI/机器人）</p>
<form method="post" action="/takeon/login">
<input name="password" type="password" placeholder="访问密码" autofocus/>
<button type="submit">进入</button>
</form>
</div></body></html>"""
    )


@router.post("/takeon/login")
async def takeon_login(request: Request):
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
            "<h3>密码错误</h3><a href='/takeon/'>返回</a>", status_code=401
        )
    resp = RedirectResponse(url="/takeon/board/", status_code=302)
    resp.set_cookie(
        key="takeon_board_auth",
        value=_token(),
        httponly=True,
        samesite="lax",
        max_age=86400 * 14,
    )
    return resp


@router.get("/takeon/board/{path:path}")
@router.get("/takeon/board")
@router.get("/takeon/board/")
def takeon_board_files(request: Request, path: str = ""):
    if not _cookie_ok(request):
        return RedirectResponse(url="/takeon/", status_code=302)
    if request.url.path.rstrip("/") == "/takeon/board" and not (path or "").strip():
        return RedirectResponse(url="/takeon/board/", status_code=302)
    root = os.path.join(_boards_root(), "latest")
    if not os.path.isdir(root):
        return HTMLResponse(
            "<h3>看板尚未上传</h3><p>请先本地生成并 sync takeon-board-upload</p>",
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
    return FileResponse(target)
