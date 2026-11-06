# -*- coding: utf-8 -*-
"""私密 · 选品作战台：SaaS 会员鉴权（账号/授权码）+ 运维密码兜底；增量库 + 任务台只读镜像。"""
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

from cloud_deploy.cloud_api.auth import (
    resolve_member_token,
    user_from_token,
    verify_sync_key,
)

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


def _ops_cookie_ok(request: Request) -> bool:
    """运维一门一密（兼容旧 cookie）。"""
    got = request.cookies.get("channel_board_auth") or ""
    return bool(got) and hmac.compare_digest(got, _token())


def _member_channel_allowed(user_id: int) -> bool:
    """在期会员默认可进；note 显式 channel_board_enabled=false 则拒。

    设 XHS_CHANNEL_REQUIRE_ENTITLEMENT=1 时，必须 entitlements.channel_board_enabled
    或 products.channel_board.enabled 为真（便于只给指定授权码开通道）。
    """
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.member_entitlements import enrich_member_profile

    profile = db.get_active_member(user_id)
    if not profile:
        return False
    enriched = enrich_member_profile(profile, user_id) or {}
    ent = enriched.get("entitlements") or {}
    if ent.get("channel_board_enabled") is False:
        return False
    products = ent.get("products") if isinstance(ent.get("products"), dict) else {}
    ch = products.get("channel_board") if isinstance(products.get("channel_board"), dict) else {}
    if ch.get("enabled") is False:
        return False
    require = (os.environ.get("XHS_CHANNEL_REQUIRE_ENTITLEMENT") or "").strip() == "1"
    if require:
        return bool(ent.get("channel_board_enabled") or ch.get("enabled"))
    return True


def _member_ok(request: Request) -> bool:
    """SaaS 底座会员会话（与 /member 同一 Cookie / JWT）。"""
    token = resolve_member_token(None, request)
    if not token:
        return False
    try:
        user = user_from_token(token)
        return _member_channel_allowed(int(user["id"]))
    except Exception:
        return False


def _access_ok(request: Request) -> bool:
    return _ops_cookie_ok(request) or _member_ok(request)


# 旧名兼容（内部若有引用）
_cookie_ok = _access_ok


def _boards_root() -> str:
    from cloud_deploy.cloud_api.config import get_settings

    return os.path.join(get_settings().xhs_data_dir, "channel_boards")


def _workbench_root() -> str:
    return os.path.join(_boards_root(), "workbench")


def _cycle_report_root() -> str:
    return os.path.join(_boards_root(), "cycle_report")


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
<p class="lead">记一句就够：<b>左比货 · 中数据包 · 右拍板</b>。中入口 = 会员多用户数据包（在线看 / 下载 / ProductAnalyzer 同步）。</p>
__STAMP__
<div class="grid">
  <a class="card" href="/channel/board/">
    <span class="tag">左 · 增量比货库</span>
    <h2>销量时间矩阵</h2>
    <p>商品行 × 采集日列 · 格内直接销量；顶栏日期悬浮。默认「时间矩阵」，可切卡片。</p>
  </a>
  <a class="card" href="/member#datapacks">
    <span class="tag">中 · 选品数据包</span>
    <h2>在线看 · 下载 · PA</h2>
    <p>多用户会员库：网页在线预览整包，可下 zip；ProductAnalyzer 云端报告库同步同套包到本地打开。</p>
  </a>
  <a class="card" href="/channel/workbench/">
    <span class="tag">右 · 选品任务台</span>
    <h2>今日拍板 · 分类榜</h2>
    <p>先看今日推荐，再锁大类看榜。云端只读快照；人判 / 可搬写入请回本机 8765。</p>
  </a>
</div>
<p class="foot">入口 https://monitor.xhs365.cn/channel/ · 会员账号 / 授权码登录（与 SaaS 底座同一套）</p>
</div></body></html>"""


def _hub_stamp_html() -> str:
    """读 latest 标记，展示导入时间 / 周期漏斗摘要 / 报告浏览包。"""
    latest = os.path.join(_boards_root(), "latest")
    marker: dict[str, Any] = {}
    funnel: dict[str, Any] = {}
    report_marker: dict[str, Any] = {}
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
    for _mk in ("cycle_report_full_cloud.json", "cycle_report_cloud.json"):
        report_marker_path = os.path.join(_cycle_report_root(), "latest", _mk)
        if not os.path.isfile(report_marker_path):
            continue
        try:
            with open(report_marker_path, encoding="utf-8") as f:
                raw = json.load(f) or {}
            if isinstance(raw, dict):
                report_marker = raw
                break
        except Exception:
            pass
    imported = (
        marker.get("cloud_imported_at")
        or marker.get("imported_at")
        or funnel.get("cloud_imported_at")
        or funnel.get("imported_at")
        or report_marker.get("cloud_imported_at")
        or report_marker.get("imported_at")
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
    try:
        cloud_n = int(report_marker.get("cloud_count") or 0)
        full_n = int(report_marker.get("full_count") or report_marker.get("opportunity_pool") or 0)
        if cloud_n or full_n:
            bits.append(f"报告浏览包 Top{cloud_n:,} / 完整入选 {full_n:,}")
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
:root{--bg:#eef3f8;--card:#fff;--text:#101828;--muted:#3d4f63;--line:#c5d0dc;--accent:#14708f;--accent-soft:#e2f3f8;--danger:#b12e3c}
*{box-sizing:border-box}
body{font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:radial-gradient(900px 360px at 12% -10%,rgba(20,112,143,.10),transparent 55%),linear-gradient(180deg,#f7fafc,#eef3f8);color:var(--text);display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px}
.box{width:420px;max-width:100%;padding:28px 24px;background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 10px 28px rgba(16,24,40,.06)}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.06em;color:var(--accent);margin:0 0 6px}
h1{font-size:22px;margin:0 0 8px;letter-spacing:-.02em}
.lead{color:var(--muted);font-size:13px;line-height:1.55;margin:0 0 16px}
.tabs{display:flex;gap:6px;margin:0 0 14px}
.tabs button{flex:1;margin:0;padding:9px 8px;border:1px solid var(--line);border-radius:10px;background:#f8fbfd;color:var(--muted);font-weight:600;font-size:13px;cursor:pointer}
.tabs button.active{background:var(--accent-soft);border-color:rgba(20,112,143,.35);color:#0a4f66}
.pane{display:none}.pane.active{display:block}
label{display:block;font-size:12px;font-weight:600;color:var(--muted);margin:0 0 6px}
input{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:#f8fbfd;color:var(--text);margin:0 0 12px}
.btn{width:100%;padding:11px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:700;cursor:pointer;margin-top:4px}
.btn:disabled{opacity:.6;cursor:wait}
.err{display:none;margin:0 0 12px;padding:10px 12px;border-radius:10px;background:#fdecee;border:1px solid #f3c4cb;color:var(--danger);font-size:13px;line-height:1.4}
.err.show{display:block}
.hint{margin:14px 0 0;font-size:12px;color:var(--muted);line-height:1.5}
.hint a{color:var(--accent);font-weight:600;text-decoration:none}
details{margin-top:16px;border-top:1px solid var(--line);padding-top:12px}
summary{cursor:pointer;color:var(--muted);font-size:12px;font-weight:600}
</style></head><body><div class="box">
<div class="eyebrow">SaaS 会员 · 共用授权</div>
<h1>选品作战台</h1>
<p class="lead">用会员账号或授权码进入；与官网会员中心同一套登录。增量比货库 + 选品任务台（云端只读）。</p>
<div id="err" class="err" role="alert"></div>
<div class="tabs" role="tablist">
  <button type="button" class="active" data-tab="account" id="tabAccount">账号登录</button>
  <button type="button" data-tab="code" id="tabCode">授权码</button>
</div>
<div class="pane active" id="paneAccount">
  <label for="username">用户名</label>
  <input id="username" autocomplete="username" placeholder="会员用户名"/>
  <label for="password">密码</label>
  <input id="password" type="password" autocomplete="current-password" placeholder="登录密码" onkeydown="if(event.key==='Enter')doAccount()"/>
  <button class="btn" type="button" id="btnAccount" onclick="doAccount()">登录进入</button>
</div>
<div class="pane" id="paneCode">
  <label for="authCode">授权码</label>
  <input id="authCode" autocomplete="off" placeholder="XHS-XXXX-XXXX-XXXX" onkeydown="if(event.key==='Enter')doCode()"/>
  <button class="btn" type="button" id="btnCode" onclick="doCode()">授权码进入</button>
</div>
<p class="hint">没有账号？可先到 <a href="/member" target="_blank" rel="noopener">会员中心</a> 开通；客服发的授权码也可直接在此登录。</p>
<details>
  <summary>运维密码（本机内部兜底）</summary>
  <form method="post" action="/channel/login" style="margin-top:12px">
    <label for="opsPassword">访问密码</label>
    <input id="opsPassword" name="password" type="password" placeholder="运维一门一密" autocomplete="off"/>
    <button class="btn" type="submit">密码进入</button>
  </form>
</details>
</div>
<script>
(function(){
  var KEY='xhs_channel_device_id';
  function uid(){
    try{
      var raw=localStorage.getItem(KEY);
      if(!raw||raw.length<8){
        raw=(window.crypto&&crypto.randomUUID)?crypto.randomUUID().replace(/-/g,'').slice(0,32).toUpperCase()
          :(Date.now().toString(36)+Math.random().toString(36).slice(2)).replace(/[^A-Z0-9]/gi,'').slice(0,32).toUpperCase();
        localStorage.setItem(KEY,raw);
      }
      return 'web:'+String(raw).toUpperCase();
    }catch(e){ return 'web:CHANNEL'+String(Date.now()); }
  }
  function showErr(msg){
    var el=document.getElementById('err');
    if(!el) return;
    el.textContent=msg||'登录失败';
    el.classList.add('show');
  }
  function clearErr(){
    var el=document.getElementById('err');
    if(!el) return;
    el.textContent='';
    el.classList.remove('show');
  }
  function setBusy(btn, on){
    if(!btn) return;
    btn.disabled=!!on;
    btn.textContent=on?'登录中…':(btn.id==='btnCode'?'授权码进入':'登录进入');
  }
  document.querySelectorAll('.tabs button').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.tabs button').forEach(function(x){ x.classList.remove('active'); });
      document.querySelectorAll('.pane').forEach(function(x){ x.classList.remove('active'); });
      b.classList.add('active');
      var pane=document.getElementById(b.dataset.tab==='code'?'paneCode':'paneAccount');
      if(pane) pane.classList.add('active');
      clearErr();
    });
  });
  async function postLogin(url, body, btn){
    clearErr();
    setBusy(btn, true);
    try{
      var r=await fetch(url,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body:JSON.stringify(Object.assign({device_id:uid(), device_label:'选品作战台网页'}, body))
      });
      var data=null;
      try{ data=await r.json(); }catch(_e){}
      if(!r.ok){
        var detail=(data&&(data.detail||data.message))||('HTTP '+r.status);
        if(Array.isArray(detail)) detail=detail.map(function(x){return x.msg||JSON.stringify(x);}).join('; ');
        throw new Error(String(detail));
      }
      location.href='/channel/hub/';
    }catch(e){
      showErr(e&&e.message?e.message:'登录失败');
      setBusy(btn, false);
    }
  }
  window.doAccount=function(){
    var u=(document.getElementById('username')||{}).value||'';
    var p=(document.getElementById('password')||{}).value||'';
    if(!u.trim()||!p){ showErr('请输入用户名和密码'); return; }
    postLogin('/api/v1/auth/login',{username:u.trim(),password:p}, document.getElementById('btnAccount'));
  };
  window.doCode=function(){
    var c=(document.getElementById('authCode')||{}).value||'';
    if(c.trim().length<8){ showErr('请输入有效授权码'); return; }
    postLogin('/api/v1/auth/login-code',{auth_code:c.trim()}, document.getElementById('btnCode'));
  };
})();
</script>
</body></html>"""


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


@router.post("/api/v1/sync/channel-cycle-report-upload")
async def sync_channel_cycle_report_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    """周期全量数据包落地页 → /channel/report/（下载 zip；对接 ProductAnalyzer）。

    zip 根下 cycle_report/：index.html + data.js + cycle_report_full_cloud.json
    （或兼容 cycle_report_cloud.json）+ 可选全量 *.zip。
    """
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.reporting.constants import ARCHIVE_CYCLE_REPORT

    filename = os.path.basename(file.filename or "cycle_report_cloud.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-cycle-report-")
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
            has_marker = (
                "cycle_report_full_cloud.json" in files or "cycle_report_cloud.json" in files
            )
            if "index.html" in files and "data.js" in files and has_marker:
                report_dir = root
                break
        if not report_dir:
            raise HTTPException(
                status_code=400,
                detail="zip 内未找到全量包落地（需 index.html + data.js + cycle_report_*cloud.json）",
            )

        marker_path = os.path.join(report_dir, "cycle_report_full_cloud.json")
        if not os.path.isfile(marker_path):
            marker_path = os.path.join(report_dir, "cycle_report_cloud.json")
        with open(marker_path, encoding="utf-8") as f:
            marker = json.load(f) or {}
        if not isinstance(marker, dict):
            marker = {}
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")
        server_imported = datetime.now().isoformat(timespec="seconds")
        marker["imported_at"] = server_imported
        marker["cloud_imported_at"] = server_imported
        marker["report_date"] = report_date
        marker["view_path"] = "/channel/report/"
        marker["product"] = marker.get("product") or "productanalyzer_full_pack"
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False, indent=2)
        # 双写兼容
        compat = os.path.join(report_dir, "cycle_report_cloud.json")
        if os.path.abspath(compat) != os.path.abspath(marker_path):
            with open(compat, "w", encoding="utf-8") as f:
                json.dump(marker, f, ensure_ascii=False, indent=2)

        dl_name = str(marker.get("download_name") or "cycle_report_cloud.zip")
        embedded_zip = os.path.join(report_dir, dl_name)
        fallback_zip = os.path.join(report_dir, "cycle_report_cloud.zip")
        if not os.path.isfile(embedded_zip) and not os.path.isfile(fallback_zip):
            shutil.copy2(zip_path, fallback_zip)

        cr_root = _cycle_report_root()
        dest_live = os.path.join(cr_root, report_date)
        os.makedirs(cr_root, exist_ok=True)
        if os.path.isdir(dest_live):
            shutil.rmtree(dest_live)
        shutil.copytree(report_dir, dest_live)

        latest = os.path.join(cr_root, "latest")
        if os.path.isdir(latest):
            shutil.rmtree(latest)
        shutil.copytree(dest_live, latest)

        archive_dir = get_settings().xhs_report_archive_dir
        os.makedirs(archive_dir, exist_ok=True)
        # hub 私有归档（落地 zip）；真正 PA 用的 member_custom 走 report-upload
        dest_zip = os.path.join(
            archive_dir, f"cycle_report_hub_{report_date.replace('-', '')}.zip"
        )
        src_full = embedded_zip if os.path.isfile(embedded_zip) else fallback_zip
        if os.path.isfile(src_full):
            shutil.copy2(src_full, dest_zip)
        else:
            shutil.copy2(zip_path, dest_zip)
        h = hashlib.sha256()
        with open(dest_zip, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)

        db.init_db()
        db.upsert_report_archive(
            report_date=report_date,
            archive_type=ARCHIVE_CYCLE_REPORT,
            storage_path=dest_zip,
            file_name=os.path.basename(dest_zip),
            file_size=int(os.path.getsize(dest_zip)),
            sha256=h.hexdigest(),
            row_count=int(marker.get("full_count") or marker.get("cloud_count") or 0),
            meta={
                "report_kind": "cycle_report_full_pack",
                "private": True,
                "view_path": "/channel/report/",
                "product": "productanalyzer_full_pack",
                **marker,
            },
        )
        download_url = f"/channel/report/{dl_name}" if os.path.isfile(
            os.path.join(dest_live, dl_name)
        ) else "/channel/report/cycle_report_cloud.zip"
        return {
            "ok": True,
            "report_date": report_date,
            "imported_at": server_imported,
            "view_url": "/channel/report/",
            "hub_url": "/channel/hub/",
            "download_url": download_url,
            "live_dir": dest_live,
            "cloud_count": int(marker.get("cloud_count") or marker.get("full_count") or 0),
            "full_count": int(marker.get("full_count") or 0),
            "source_name": marker.get("source_name") or "",
            "product": "productanalyzer_full_pack",
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


@router.get("/channel/report/{path:path}")
@router.get("/channel/report")
@router.get("/channel/report/")
def channel_cycle_report_files(request: Request, path: str = ""):
    """周期选品报告云浏览瘦包：同套报告 HTML，TopN data.js + zip 下载。"""
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    if request.url.path == "/channel/report" and not (path or "").strip():
        return RedirectResponse(url="/channel/report/", status_code=302)
    root = os.path.join(_cycle_report_root(), "latest")
    if not os.path.isdir(root):
        return HTMLResponse(
            "<h3>周期报告浏览包尚未上传</h3>"
            "<p>请本机运行 <code>python tools/publish_cycle_report_cloud.py</code>（全量数据包 → ProductAnalyzer）</p>"
            "<p><a href='/channel/hub/'>返回入口</a></p>",
            status_code=404,
        )
    rel = (path or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        rel = "index.html"
    target = _safe_file(root, rel)
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="not found")
    low = rel.lower()
    media = _media_type(rel)
    if low.endswith(".zip"):
        media = "application/zip"
    headers = {**_NO_STORE, "X-Channel-Board": "1"}
    if low.endswith(".zip"):
        headers["Content-Disposition"] = f'attachment; filename="{os.path.basename(target)}"'
    return FileResponse(target, media_type=media, headers=headers)
