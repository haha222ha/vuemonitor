# -*- coding: utf-8 -*-
"""私密 · 选品作战台（一门一密）：增量商品库 + 选品任务台（8765 静态镜像）。"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from cloud_deploy.cloud_api.auth import verify_sync_key

router = APIRouter(tags=["channel-board"])

_NO_STORE = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}


class BoardInventoryUpsertBody(BaseModel):
    batch_id: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    final_batch: bool = False


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


def _workbench_root() -> str:
    return os.path.join(_boards_root(), "workbench")


def _safe_file(root: str, rel: str) -> str:
    rel = (rel or "").strip().lstrip("/").replace("\\", "/")
    if not rel or rel.endswith("/"):
        rel = "index.html"
    target = os.path.normpath(os.path.join(root, rel))
    if not target.startswith(os.path.normpath(root)):
        raise HTTPException(status_code=400, detail="bad path")
    return target


def _media_type(rel: str) -> str | None:
    low = (rel or "").lower()
    if low.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if low.endswith(".json"):
        return "application/json; charset=utf-8"
    if low.endswith(".html"):
        return "text/html; charset=utf-8"
    if low.endswith(".css"):
        return "text/css; charset=utf-8"
    return None


_HUB_HTML_TMPL = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>选品作战台</title>
<style>
:root{--bg:#eef3f8;--card:#fff;--text:#101828;--muted:#3d4f63;--line:#c5d0dc;--accent:#14708f;--accent-soft:#e2f3f8;--accent-deep:#0a4f66}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--text);min-height:100vh;background:
  radial-gradient(900px 360px at 12% -10%,rgba(20,112,143,.10),transparent 55%),
  linear-gradient(180deg,#f7fafc 0%,var(--bg) 40%,#e8eef5 100%)}
.wrap{max-width:920px;margin:0 auto;padding:48px 24px 64px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;margin:0 0 8px}
h1{margin:0 0 8px;font-size:2rem;letter-spacing:-.02em}
.lead{margin:0 0 28px;color:var(--muted);font-size:15px;line-height:1.55;max-width:36rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 20px;box-shadow:0 1px 3px rgba(16,24,40,.06);transition:border-color .15s,box-shadow .15s,transform .15s}
.card:hover{border-color:rgba(20,112,143,.45);box-shadow:0 10px 28px rgba(20,112,143,.12);transform:translateY(-1px)}
.card .tag{display:inline-block;font-size:11px;font-weight:700;color:var(--accent-deep);background:var(--accent-soft);border:1px solid rgba(20,112,143,.25);border-radius:999px;padding:3px 10px;margin-bottom:10px}
.card h2{margin:0 0 8px;font-size:1.25rem}
.card p{margin:0;color:var(--muted);font-size:13px;line-height:1.5}
.stamp{margin:0 0 20px;padding:10px 12px;background:var(--accent-soft);border:1px solid rgba(20,112,143,.22);border-radius:10px;font-size:13px;color:var(--accent-deep);line-height:1.45}
.stamp b{font-family:ui-monospace,Consolas,monospace;font-weight:700}
.foot{margin-top:28px;font-size:12px;color:var(--muted)}
</style></head><body><div class="wrap">
<div class="eyebrow">一门一密 · 私密作战台</div>
<h1>选品作战台</h1>
<p class="lead">记一句就够：<b>左比货 · 右拍板</b>。同一密码；跟品 / 上品 / 日报不进这里。</p>
__STAMP__
<div class="grid">
  <a class="card" href="/channel/board/">
    <span class="tag">左 · 增量比货库</span>
    <h2>销量时间矩阵</h2>
    <p>商品行 × 采集日列 · 格内直接销量；顶栏日期悬浮。默认「时间矩阵」，可切卡片。</p>
  </a>
  <a class="card" href="/channel/workbench/">
    <span class="tag">右 · 选品任务台</span>
    <h2>今日拍板 · 分类榜</h2>
    <p>先看今日推荐，再锁大类看榜。云端只读快照；人判 / 可搬写入请回本机 8765。</p>
  </a>
</div>
<p class="foot">入口 https://monitor.xhs365.cn/channel/ · 密码与原先增量库相同</p>
</div></body></html>"""


def _hub_stamp_html() -> str:
    """读 latest 标记，展示导入时间 / 周期漏斗摘要。"""
    latest = os.path.join(_boards_root(), "latest")
    marker: dict[str, Any] = {}
    funnel: dict[str, Any] = {}
    for name in ("channel_board.json", "cycle_funnel.json"):
        path = os.path.join(latest, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f) or {}
            if name == "channel_board.json" and isinstance(raw, dict):
                marker = raw
            elif isinstance(raw, dict):
                funnel = raw
        except Exception:
            continue
    imported = (
        marker.get("cloud_imported_at")
        or marker.get("imported_at")
        or funnel.get("cloud_imported_at")
        or funnel.get("imported_at")
        or ""
    )
    window = marker.get("cycle_window") or funnel.get("cycle_window") or ""
    cf = marker.get("cycle_funnel") if isinstance(marker.get("cycle_funnel"), dict) else None
    if cf is None and isinstance(funnel.get("cycle_funnel"), dict):
        cf = funnel["cycle_funnel"]
    bits = []
    if imported:
        bits.append(f"导入时间 <b>{imported}</b>")
    if window:
        bits.append(f"周期窗 {window}")
    if isinstance(cf, dict):
        try:
            touched = int(cf.get("touched_virtual") or 0)
            delta = int(cf.get("delta_ge1_unique") or 0)
            pool = int(cf.get("opportunity_pool") or 0)
            if touched or delta or pool:
                bits.append(
                    f"触达虚品 {touched:,} · 正增量 {delta:,} · 入选 {pool:,}"
                )
        except Exception:
            pass
    if not bits:
        return ""
    return f'<div class="stamp">{" · ".join(bits)}</div>'


def _hub_html() -> str:
    return _HUB_HTML_TMPL.replace("__STAMP__", _hub_stamp_html())


def _gate_html() -> str:
    return """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>选品作战台</title>
<style>
body{font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#eef3f8;color:#101828;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;
background-image:radial-gradient(900px 360px at 12% -10%,rgba(20,112,143,.10),transparent 55%),linear-gradient(180deg,#f7fafc,#eef3f8)}
.box{width:400px;padding:28px;background:#fff;border:1px solid #c5d0dc;border-radius:14px;box-shadow:0 10px 28px rgba(16,24,40,.06)}
h1{font-size:20px;margin:0 0 8px}p{color:#3d4f63;font-size:13px;line-height:1.5}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #c5d0dc;background:#f8fbfd;color:#101828;box-sizing:border-box}
button{margin-top:12px;width:100%;padding:11px;border:0;border-radius:10px;background:#14708f;color:#fff;font-weight:700;cursor:pointer}
</style></head><body><div class="box">
<h1>选品作战台</h1>
<p>一门一密 · 增量商品库 + 选品任务台（本机 8765 云端只读镜像）</p>
<form method="post" action="/channel/login">
<input name="password" type="password" placeholder="访问密码" autofocus/>
<button type="submit">进入</button>
</form>
</div></body></html>"""


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
        if not isinstance(marker, dict):
            marker = {}
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")
        # 云端导入时间（服务器钟）：写入标记，供 hub / 面板展示
        server_imported = datetime.now().isoformat(timespec="seconds")
        marker["imported_at"] = server_imported
        marker["cloud_imported_at"] = server_imported
        marker["report_date"] = report_date
        with open(os.path.join(report_dir, "channel_board.json"), "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False, indent=2)
        funnel_path = os.path.join(report_dir, "cycle_funnel.json")
        if os.path.isfile(funnel_path):
            try:
                with open(funnel_path, encoding="utf-8") as f:
                    funnel_obj = json.load(f) or {}
            except Exception:
                funnel_obj = {}
            if isinstance(funnel_obj, dict):
                funnel_obj["imported_at"] = server_imported
                funnel_obj["cloud_imported_at"] = server_imported
                with open(funnel_path, "w", encoding="utf-8") as f:
                    json.dump(funnel_obj, f, ensure_ascii=False, indent=2)

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
                "view_path": "/channel/board/",
                **marker,
            },
        )
        return {
            "ok": True,
            "report_date": report_date,
            "imported_at": server_imported,
            "view_url": "/channel/hub/",
            "live_dir": dest_live,
            "row_count": int(marker.get("items_exported") or 0),
            "cycle_window": marker.get("cycle_window") or "",
            "funnel_kind": marker.get("funnel_kind") or "",
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/api/v1/sync/channel-workbench-upload")
async def sync_channel_workbench_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    """本机 8765 任务台静态包（home_workbench + home_snap）→ /channel/workbench/。"""
    filename = os.path.basename(file.filename or "channel-workbench.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-channel-workbench-")
    zip_path = os.path.join(tmp_dir, filename)
    try:
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(file.file, out)

        extract_root = os.path.join(tmp_dir, "extract")
        os.makedirs(extract_root, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        report_dir = ""
        for root, dirs, files in os.walk(extract_root):
            if "index.html" in files and "snap" in dirs:
                report_dir = root
                break
            if "index.html" in files and "workbench.json" in files:
                report_dir = root
                break
        if not report_dir:
            raise HTTPException(status_code=400, detail="zip 内未找到任务台目录（需 index.html + snap/）")

        marker_path = os.path.join(report_dir, "workbench_cloud.json")
        marker: dict[str, Any] = {}
        if os.path.isfile(marker_path):
            with open(marker_path, encoding="utf-8") as f:
                marker = json.load(f) or {}
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")

        wb_root = _workbench_root()
        dest_live = os.path.join(wb_root, report_date)
        os.makedirs(wb_root, exist_ok=True)
        if os.path.isdir(dest_live):
            shutil.rmtree(dest_live)
        shutil.copytree(report_dir, dest_live)

        latest = os.path.join(wb_root, "latest")
        if os.path.isdir(latest):
            shutil.rmtree(latest)
        shutil.copytree(dest_live, latest)

        return {
            "ok": True,
            "report_date": report_date,
            "view_url": "/channel/workbench/",
            "live_dir": dest_live,
            "hub_url": "/channel/hub/",
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/api/v1/sync/board-inventory-upsert")
def sync_board_inventory_upsert(
    body: BoardInventoryUpsertBody,
    _: None = Depends(verify_sync_key),
):
    """本机 board_inventory_goods → 云端 PG（同构；禁止搬热库全表）。"""
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    if not body.rows and not body.final_batch and not body.meta:
        raise HTTPException(status_code=400, detail="rows 为空")
    if len(body.rows) > 5000:
        raise HTTPException(status_code=400, detail="单批最多 5000 行")

    from cloud_deploy.cloud_api.board_inventory_sync_service import apply_board_inventory_batch
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    init_db()
    conn = _conn()
    try:
        return apply_board_inventory_batch(
            conn,
            body.rows,
            meta=body.meta or None,
            final_batch=bool(body.final_batch),
        )
    finally:
        conn.close()


@router.get("/api/v1/sync/board-inventory-stats")
def sync_board_inventory_stats(_: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.board_inventory_sync_service import board_inventory_stats
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    init_db()
    conn = _conn()
    try:
        return board_inventory_stats(conn)
    finally:
        conn.close()


@router.get("/channel", response_class=HTMLResponse)
@router.get("/channel/", response_class=HTMLResponse)
def channel_gate(request: Request):
    if _cookie_ok(request):
        return RedirectResponse(url="/channel/hub/", status_code=302)
    return HTMLResponse(_gate_html(), headers={**_NO_STORE, "X-Channel-Board": "1"})


@router.get("/channel/hub", response_class=HTMLResponse)
@router.get("/channel/hub/", response_class=HTMLResponse)
def channel_hub(request: Request):
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    return HTMLResponse(_hub_html(), headers={**_NO_STORE, "X-Channel-Board": "1"})


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
            "<h3 style='font-family:sans-serif;color:#b12e3c'>密码错误</h3>"
            "<a href='/channel/'>返回</a>",
            status_code=401,
        )
    resp = RedirectResponse(url="/channel/hub/", status_code=302)
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
    if request.url.path == "/channel/board" and not (path or "").strip():
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
    target = _safe_file(root, rel)
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(
        target,
        media_type=_media_type(rel),
        headers={**_NO_STORE, "X-Channel-Board": "1"},
    )


@router.api_route("/channel/workbench/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@router.api_route("/channel/workbench/api", methods=["GET", "POST"])
def channel_workbench_api_stub(request: Request, path: str = ""):
    """云端任务台只读：动态写/钻 API 一律 stub，避免假绿。"""
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    return JSONResponse(
        {
            "ok": False,
            "cloud_readonly": True,
            "error": "云端任务台为只读静态快照；人判/可搬/钻取请回本机 http://127.0.0.1:8765/",
            "path": path or "",
            "items": [],
            "series": {},
        },
        headers=_NO_STORE,
    )


@router.get("/channel/workbench/{path:path}")
@router.get("/channel/workbench")
@router.get("/channel/workbench/")
def channel_workbench_files(request: Request, path: str = ""):
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    if request.url.path == "/channel/workbench" and not (path or "").strip():
        return RedirectResponse(url="/channel/workbench/", status_code=302)
    root = os.path.join(_workbench_root(), "latest")
    if not os.path.isdir(root):
        return HTMLResponse(
            "<h3>任务台尚未上传</h3>"
            "<p>请本机运行 <code>python tools/publish_channel_workbench_cloud.py</code></p>"
            "<p><a href='/channel/hub/'>返回入口</a></p>",
            status_code=404,
        )
    rel = (path or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        rel = "index.html"
    target = _safe_file(root, rel)
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(
        target,
        media_type=_media_type(rel),
        headers={**_NO_STORE, "X-Channel-Board": "1"},
    )
