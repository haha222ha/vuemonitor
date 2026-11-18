# -*- coding: utf-8 -*-
"""私密 · 选品作战台：SaaS 会员鉴权（账号/授权码）+ 运维密码兜底；增量库 + 任务台只读镜像。"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta

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
# data.js 动辄上百 MB；禁止再对静态资源套 no-store，否则每次点开都整包重下
_STATIC_CACHE = {"Cache-Control": "private, max-age=86400"}

# Cloudflare Free/Pro 单请求约 100MB；分片默认 16MB，留足余量
_DEFAULT_CHUNK_SIZE = 16 * 1024 * 1024
_MAX_CHUNK_SIZE = 32 * 1024 * 1024
_SESSION_TTL_HOURS = 24


class BoardInventoryUpsertBody(BaseModel):
    batch_id: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    final_batch: bool = False


class UploadSessionInitBody(BaseModel):
    # channel_board | channel_workbench | cycle_report | member_custom_zip
    kind: str = "channel_board"
    filename: str = "channel_board.zip"
    size: int = Field(..., ge=1)
    sha256: str = ""
    # 线上 nginx 默认约 12MB；未拉高 client_max_body_size 前分片用 8MB
    chunk_size: int = Field(default=8 * 1024 * 1024, ge=1024 * 1024, le=_MAX_CHUNK_SIZE)


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


def _vertical_landing_html() -> str:
    """④ 垂类入口：云端先给可导航落地页；深挖写回仍回本机 8765/vertical。"""
    return """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>垂类多卖家 · 选品作战台</title>
<style>
:root{--bg:#eef3f8;--card:#fff;--text:#101828;--muted:#3d4f63;--line:#c5d0dc;--accent:#14708f;--accent-soft:#e2f3f8;--accent-deep:#0a4f66}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--text);min-height:100vh;background:linear-gradient(180deg,#f7fafc,var(--bg))}
.wrap{max-width:720px;margin:0 auto;padding:40px 24px 64px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;margin:0 0 8px}
h1{margin:0 0 10px;font-size:1.75rem}
.lead{color:var(--muted);line-height:1.55;margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:0 0 14px;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.card h2{margin:0 0 8px;font-size:1.05rem}
.card p,.card li{margin:0;color:var(--muted);font-size:13px;line-height:1.55}
.card ul{margin:8px 0 0;padding-left:1.2rem}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}
.nav a{display:inline-block;padding:9px 14px;border-radius:999px;border:1px solid rgba(20,112,143,.28);background:var(--accent-soft);color:var(--accent-deep);font-weight:700;font-size:13px;text-decoration:none}
.nav a.primary{background:var(--accent);color:#fff;border-color:transparent}
</style></head><body><div class="wrap">
<div class="eyebrow">四看板 · ① 垂类多卖家</div>
<h1>垂类搜词 · 多卖家对照</h1>
<p class="lead">云端这一页是导航与口径说明。带热库搜词挂载的深挖表仍在本机任务台 <code>/vertical/</code>（8765），避免云端直连热库。</p>
<div class="card">
  <h2>本入口做什么</h2>
  <ul>
    <li>锁一个垂类词 → 看多卖家表与增长曲线</li>
    <li>挂词组 <code>vertical_niche_probe</code>；本机命令：<code>python tools/pin_vertical_niche_keywords.py --niche … --apply</code></li>
    <li>与增量比货 / 任务台 / 周期包同一视觉世界，不另起主题</li>
  </ul>
</div>
<div class="card">
  <h2>接下来去哪</h2>
  <div class="nav">
    <a class="primary" href="/channel/hub/">回四看板入口</a>
    <a href="/channel/board/">② 增量比货库</a>
    <a href="/channel/workbench/">③ 选品任务台</a>
    <a href="/channel/report/">④ 周期完整包</a>
  </div>
</div>
</div></body></html>"""


def _safe_file(root: str, rel: str) -> str:
    rel = (rel or "").strip().lstrip("/").replace("\\", "/")
    if not rel or rel.endswith("/"):
        rel = "index.html"
    target = os.path.normpath(os.path.join(root, rel))
    if not target.startswith(os.path.normpath(root)):
        raise HTTPException(status_code=400, detail="bad path")
    return target


def _header_ascii(value: str, *, limit: int = 120) -> str:
    """HTTP 响应头必须 latin-1；中文包名改成百分号编码，避免 500。"""
    from urllib.parse import quote

    s = str(value or "").strip() or "cycle"
    try:
        s.encode("latin-1")
        return s[:limit]
    except UnicodeEncodeError:
        return quote(s, safe=":/._-+=@")[:limit]


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
<title>选品作战台 · 四看板</title>
<style>
:root{--bg:#eef3f8;--elev:#fff;--text:#101828;--muted:#3d4f63;--line:#c5d0dc;--accent:#14708f;--accent-soft:#e2f3f8;--accent-deep:#0a4f66;--v1:#0a4f66;--v2:#14708f;--v3:#0d7a5f;--v4:#8a5a12;--ease:cubic-bezier(.4,0,.2,1);--dur:180ms}
*{box-sizing:border-box}html,body{height:100%;margin:0;overflow:hidden}
body{font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased}
#app{display:flex;flex-direction:column;height:100%}
.topbar{flex-shrink:0;padding:8px 16px;background:rgba(255,255,255,.92);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line);z-index:10}
.top-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:6px}
.brand{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;min-width:0}
.brand .eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;margin:0}
.brand h1{margin:0;font-size:1.05rem;letter-spacing:-.02em;font-weight:780}
.stamp{margin:0;padding:4px 8px;border-radius:8px;background:var(--accent-soft);border:1px solid rgba(20,112,143,.22);font-size:11px;color:var(--accent-deep);line-height:1.35;max-width:22rem}
.stamp:empty{display:none}.stamp b{font-family:ui-monospace,Consolas,monospace;font-weight:700}
.kbd-hint{font-size:11px;color:var(--muted);white-space:nowrap}
.kbd-hint kbd{display:inline-block;padding:1px 5px;margin:0 1px;border:1px solid var(--line);border-radius:4px;background:#f4f7fb;font-size:10px;font-family:ui-monospace,Consolas,monospace}
.view-menu{display:inline-flex;flex-wrap:wrap;gap:4px;padding:4px;background:#e4ebf3;border:1px solid var(--line);border-radius:12px;max-width:100%}
.view-menu button{appearance:none;border:1px solid transparent;background:transparent;color:var(--muted);padding:7px 14px;font-size:13px;font-weight:650;cursor:pointer;border-radius:9px;font-family:inherit;white-space:nowrap;transition:color var(--dur) var(--ease),background var(--dur) var(--ease),border-color var(--dur) var(--ease),box-shadow var(--dur) var(--ease)}
.view-menu button:hover{color:var(--text);background:rgba(255,255,255,.55)}
.view-menu button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.view-menu button.active{background:var(--elev);color:var(--accent-deep);font-weight:780;border-color:rgba(20,112,143,.22);box-shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.04)}
.view-menu button[data-view="workbench"].active{color:var(--v3);border-color:rgba(13,122,95,.28)}
.view-menu button[data-view="ops"].active{color:var(--v2);border-color:rgba(20,112,143,.28)}
.view-menu button[data-view="vertical"].active{color:var(--v1);border-color:rgba(10,79,102,.28)}
.view-menu button[data-view="cycle"].active{color:var(--v4);border-color:rgba(138,90,18,.28)}
.hint{font-size:11px;color:var(--muted);padding:6px 0 0;line-height:1.4}
.frame-wrap{flex:1;min-height:0;position:relative;background:#e8eef5}
.frame-wrap iframe{position:absolute;inset:0;width:100%;height:100%;border:0;background:var(--elev);opacity:0;pointer-events:none;transition:opacity var(--dur) var(--ease)}
.frame-wrap iframe.is-active{opacity:1;pointer-events:auto}.frame-wrap iframe.is-loading{opacity:.35}
.foot-mini{position:absolute;right:12px;bottom:8px;z-index:5;font-size:11px;color:var(--muted);background:rgba(255,255,255,.85);padding:4px 8px;border-radius:6px;border:1px solid var(--line)}
.foot-mini a{color:var(--accent);font-weight:700;text-decoration:none}
@media (prefers-reduced-motion:reduce){.view-menu button,.frame-wrap iframe{transition:none}}
</style></head><body>
<div id="app">
  <div class="topbar">
    <div class="top-row">
      <div class="brand">
        <div class="eyebrow">一门一密</div>
        <h1>选品作战台</h1>
      </div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end">
        __STAMP__
        <div class="kbd-hint">快捷 <kbd>1</kbd>–<kbd>4</kbd> · <kbd>←</kbd><kbd>→</kbd></div>
      </div>
    </div>
    <div class="view-menu" role="tablist" aria-label="四看板菜单" id="viewMenu"></div>
    <div class="hint" id="hint"></div>
  </div>
  <div class="frame-wrap" id="frameWrap">
    <div class="foot-mini">数据包：<a href="/member#datapacks">会员中心</a></div>
  </div>
</div>
<script>
(function(){
  var PATHS={workbench:"/channel/workbench/?embed=1",ops:"/channel/board/?embed=1&ledger=1",vertical:"/channel/board/vertical_niche.html?embed=1",cycle:"/channel/report/?embed=1"};
  var TABS=[
    {id:"workbench",label:"1 任务台",hint:"今日拍板 · 云端只读；人判/可搬请回本机 8765"},
    {id:"ops",label:"2 比货",hint:"全量静态分片 · 非瘦包 · 约 34 万底账"},
    {id:"vertical",label:"3 垂类",hint:"原独立垂类页 · 任意搜词"},
    {id:"cycle",label:"4 周期包",hint:"周期包列表 · 点开选品报告"}
  ];
  var TAB_IDS=TABS.map(function(t){return t.id});
  var ALIAS={workbench:"workbench",home:"workbench",task:"workbench",ops:"ops",board:"ops",matrix:"ops",vertical:"vertical",niche:"vertical",cycle:"cycle",report:"cycle","1":"workbench","2":"ops","3":"vertical","4":"cycle"};
  var loaded={},view="workbench",buttons={},frames={};
  var menu=document.getElementById("viewMenu"),wrap=document.getElementById("frameWrap"),hintEl=document.getElementById("hint");
  function resolveView(raw){var k=String(raw||"").replace(/^#/,"").toLowerCase();return ALIAS[k]||null}
  function initialView(){try{var q=new URLSearchParams(location.search).get("view")||new URLSearchParams(location.search).get("tab");var a=resolveView(q);if(a)return a;var b=resolveView(location.hash);if(b)return b}catch(e){}return "workbench"}
  function isTypingTarget(el){if(!el||!el.tagName)return false;var tag=el.tagName.toUpperCase();return tag==="INPUT"||tag==="TEXTAREA"||tag==="SELECT"||!!el.isContentEditable}
  function ensureFrame(id){
    if(frames[id])return frames[id];
    var iframe=document.createElement("iframe");
    iframe.setAttribute("data-view",id);
    iframe.title=(TABS.find(function(t){return t.id===id})||{}).label||id;
    iframe.src="about:blank";
    iframe.addEventListener("load",function(){
      iframe.classList.remove("is-loading");
      try{var win=iframe.contentWindow;if(win&&!win.__hubKeysBound){win.addEventListener("keydown",onHubKey);win.__hubKeysBound=true}}catch(e){}
    });
    wrap.insertBefore(iframe, wrap.firstChild);
    frames[id]=iframe;
    return iframe;
  }
  function switchView(id){
    if(!PATHS[id])id="workbench";
    view=id;
    if(!loaded[id]){loaded[id]=true;var fr=ensureFrame(id);fr.classList.add("is-loading");fr.src=PATHS[id]}
    else{ensureFrame(id)}
    TAB_IDS.forEach(function(tid){
      var btn=buttons[tid],fr=frames[tid];
      if(btn){var on=tid===id;btn.classList.toggle("active",on);btn.setAttribute("aria-selected",on?"true":"false")}
      if(fr)fr.classList.toggle("is-active",tid===id);
    });
    var tab=TABS.find(function(t){return t.id===id});
    if(hintEl)hintEl.textContent=tab?tab.hint:"";
    try{var url=new URL(location.href);url.searchParams.set("view",id);url.hash="";history.replaceState(null,"",url.toString())}catch(e){}
  }
  function stepView(delta){var i=TAB_IDS.indexOf(view);if(i<0)i=0;switchView(TAB_IDS[(i+delta+TAB_IDS.length)%TAB_IDS.length])}
  function onHubKey(e){if(e.defaultPrevented||e.altKey||e.ctrlKey||e.metaKey||isTypingTarget(e.target))return;var k=e.key;if(k>="1"&&k<="4"){var id=ALIAS[k];if(id){e.preventDefault();switchView(id)}return}if(k==="ArrowLeft"){e.preventDefault();stepView(-1);return}if(k==="ArrowRight"){e.preventDefault();stepView(1)}}
  TABS.forEach(function(t){
    var btn=document.createElement("button");
    btn.type="button";btn.setAttribute("role","tab");btn.setAttribute("data-view",t.id);btn.textContent=t.label;
    btn.addEventListener("click",function(){switchView(t.id)});
    menu.appendChild(btn);buttons[t.id]=btn;
  });
  window.addEventListener("keydown",onHubKey);
  window.addEventListener("hashchange",function(){var v=resolveView(location.hash);if(v)switchView(v)});
  switchView(initialView());
})();
</script>
</body></html>"""

_CYCLE_EMBED_SNIPPET = """<script>(function(){
try{
  var emb=/(?:\\?|&)embed=1(?:&|$)/.test(location.search)||(window.self!==window.top);
  if(!emb)return;
  document.documentElement.classList.add('hub-embed');
  var css=document.createElement('style');
  css.textContent=[
    'html.hub-embed header .nav,html.hub-embed .nav,html.hub-embed .hub-nav{display:none!important}',
    'html.hub-embed header{padding:8px 16px!important}',
    'html.hub-embed header h1,.hub-embed .topbar h1{font-size:1.05rem!important}',
    'html.hub-embed header .sub,html.hub-embed .topbar .lead,html.hub-embed .view-tabs,html.hub-embed .hint{display:none!important}',
    'html.hub-embed .topbar{padding:6px 12px 0!important}',
    '.cycle-back-list{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:10px;padding:8px 12px;background:rgba(238,243,248,.96);border-bottom:1px solid #c5d0dc;font:650 12px/1.4 Segoe UI,PingFang SC,Microsoft YaHei,sans-serif}',
    '.cycle-back-list a{color:#0a4f66;text-decoration:none}',
    '.cycle-back-list a:hover{text-decoration:underline}'
  ].join('');
  document.head.appendChild(css);
  if(/\\/channel\\/report\\/p\\//.test(location.pathname||'')){
    var bar=document.createElement('div');
    bar.className='cycle-back-list';
    bar.innerHTML='<a href=\"/channel/report/?embed=1\">← 周期包列表</a><span style=\"color:#3d4f63\">当前报告</span>';
    document.body.insertBefore(bar, document.body.firstChild);
  }
}catch(_){}
})();</script>"""


def _inject_cycle_embed_chrome(raw: bytes) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="ignore")
    if "hub-embed" in text and "CYCLE_EMBED" in text:
        return text.encode("utf-8")
    snip = "<!--CYCLE_EMBED-->" + _CYCLE_EMBED_SNIPPET
    low = text.lower()
    idx = low.find("</head>")
    if idx >= 0:
        text = text[:idx] + snip + text[idx:]
    else:
        text = snip + text
    return text.encode("utf-8")


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
    """优先读看板 latest/hub.html（本机 publish 即可改入口）；缺则用内置模板。"""
    latest_hub = os.path.join(_boards_root(), "latest", "hub.html")
    if os.path.isfile(latest_hub):
        try:
            with open(latest_hub, encoding="utf-8") as f:
                text = f.read()
            stamp = _hub_stamp_html()
            if stamp and "__STAMP__" in text:
                text = text.replace("__STAMP__", stamp)
            elif stamp and 'id="hint"' in text and "stamp" not in text[:800].lower():
                # 静态 hub 无 stamp 槽时不硬塞，避免破坏布局
                pass
            return text
        except Exception:
            pass
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


def _sessions_root() -> str:
    from cloud_deploy.cloud_api.config import get_settings

    return os.path.join(get_settings().xhs_data_dir, "upload_sessions")


def _session_dir(upload_id: str) -> str:
    safe = "".join(c for c in (upload_id or "") if c.isalnum() or c in "-_")
    if not safe or safe != upload_id:
        raise HTTPException(status_code=400, detail="invalid upload_id")
    return os.path.join(_sessions_root(), safe)


def _read_session_meta(upload_id: str) -> dict[str, Any]:
    meta_path = os.path.join(_session_dir(upload_id), "meta.json")
    if not os.path.isfile(meta_path):
        raise HTTPException(status_code=404, detail="upload session 不存在或已过期")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    if not isinstance(meta, dict):
        raise HTTPException(status_code=400, detail="session meta 损坏")
    return meta


def _write_session_meta(upload_id: str, meta: dict[str, Any]) -> None:
    meta_path = os.path.join(_session_dir(upload_id), "meta.json")
    tmp = meta_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, meta_path)


def _list_received_chunks(upload_id: str, chunk_count: int) -> list[int]:
    root = _session_dir(upload_id)
    got: list[int] = []
    for i in range(int(chunk_count)):
        if os.path.isfile(os.path.join(root, "chunks", f"{i:06d}.part")):
            got.append(i)
    return got


def _assemble_session_zip(upload_id: str, meta: dict[str, Any]) -> str:
    root = _session_dir(upload_id)
    chunk_count = int(meta.get("chunk_count") or 0)
    size = int(meta.get("size") or 0)
    want_sha = str(meta.get("sha256") or "").strip().lower()
    missing = [i for i in range(chunk_count) if i not in set(_list_received_chunks(upload_id, chunk_count))]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"缺分片 {len(missing)} 个，首个 index={missing[0]}",
        )
    out_zip = os.path.join(root, meta.get("filename") or "assembled.zip")
    h = hashlib.sha256()
    written = 0
    with open(out_zip, "wb") as out:
        for i in range(chunk_count):
            part = os.path.join(root, "chunks", f"{i:06d}.part")
            with open(part, "rb") as inp:
                while True:
                    buf = inp.read(1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
                    h.update(buf)
                    written += len(buf)
    if written != size:
        raise HTTPException(
            status_code=400,
            detail=f"拼装大小不符：got={written} want={size}",
        )
    digest = h.hexdigest()
    if want_sha and want_sha != digest:
        raise HTTPException(
            status_code=400,
            detail=f"sha256 不符：got={digest} want={want_sha}",
        )
    meta["assembled_sha256"] = digest
    meta["assembled_at"] = datetime.now().isoformat(timespec="seconds")
    _write_session_meta(upload_id, meta)
    return out_zip


def _ingest_channel_board_zip(zip_path: str) -> dict[str, Any]:
    """解压全量看板 zip → channel_boards/{date} + latest + archive（与单次 upload 同口径）。"""
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.reporting.constants import ARCHIVE_CHANNEL_BOARD

    if not str(zip_path).lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")
    if not os.path.isfile(zip_path):
        raise HTTPException(status_code=400, detail="zip 不存在")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-channel-board-")
    try:
        extract_root = os.path.join(tmp_dir, "extract")
        os.makedirs(extract_root, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        report_dir = ""
        for root, _dirs, files in os.walk(extract_root):
            has_marker = "index.html" in files and "channel_board.json" in files
            has_boot_js = "channel_board_data.js" in files
            has_shards = os.path.isfile(os.path.join(root, "shards", "manifest.json"))
            if has_marker and (has_boot_js or has_shards):
                report_dir = root
                break
        if not report_dir:
            raise HTTPException(
                status_code=400,
                detail="zip 内未找到增量商品库看板目录（需 index.html + channel_board.json + boot js 或 shards/）",
            )

        with open(os.path.join(report_dir, "channel_board.json"), encoding="utf-8") as f:
            marker = json.load(f)
        if not isinstance(marker, dict):
            marker = {}
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")
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
        latest = os.path.join(boards_root, "latest")
        overlay = bool(marker.get("overlay"))
        # overlay=true：只覆盖 zip 内文件，保留已有 shards/facets（修壳/JS 不必重传 500MB+）
        if overlay and os.path.isdir(latest):
            for root, _dirs, files in os.walk(report_dir):
                for name in files:
                    src = os.path.join(root, name)
                    rel = os.path.relpath(src, report_dir)
                    dst = os.path.join(latest, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
            dest_live = latest
            # 同步一份到日期目录（有则合并，无则跳过）
            dest_date = os.path.join(boards_root, report_date)
            if os.path.isdir(dest_date):
                for root, _dirs, files in os.walk(report_dir):
                    for name in files:
                        src = os.path.join(root, name)
                        rel = os.path.relpath(src, report_dir)
                        dst = os.path.join(dest_date, rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
        else:
            dest_live = os.path.join(boards_root, report_date)
            os.makedirs(boards_root, exist_ok=True)
            if os.path.isdir(dest_live):
                shutil.rmtree(dest_live)
            shutil.copytree(report_dir, dest_live)

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
            "sha256": h.hexdigest(),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/api/v1/sync/channel-board-upload")
async def sync_channel_board_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    """兼容旧客户端：单次整包上传（≤CF 限额时可用）。大包请走 upload-session 分片。"""
    filename = os.path.basename(file.filename or "channel-board.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-channel-board-")
    zip_path = os.path.join(tmp_dir, filename)
    try:
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        return _ingest_channel_board_zip(zip_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/api/v1/sync/upload-session")
async def sync_upload_session_init(
    body: UploadSessionInitBody,
    _: None = Depends(verify_sync_key),
):
    """开分片续传会话（绕过 Cloudflare 单请求 100MB 上限）。"""
    kind = (body.kind or "channel_board").strip()
    if kind not in (
        "channel_board",
        "channel_workbench",
        "cycle_report",
        "member_custom_zip",
    ):
        raise HTTPException(
            status_code=400,
            detail="kind 仅支持 channel_board|channel_workbench|cycle_report|member_custom_zip",
        )
    filename = os.path.basename(body.filename or f"{kind}.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")
    chunk_size = int(body.chunk_size or _DEFAULT_CHUNK_SIZE)
    chunk_size = max(1024 * 1024, min(chunk_size, _MAX_CHUNK_SIZE))
    size = int(body.size)
    chunk_count = (size + chunk_size - 1) // chunk_size
    upload_id = uuid.uuid4().hex
    root = _session_dir(upload_id)
    os.makedirs(os.path.join(root, "chunks"), exist_ok=True)
    meta = {
        "ok": True,
        "upload_id": upload_id,
        "kind": kind,
        "filename": filename,
        "size": size,
        "sha256": str(body.sha256 or "").strip().lower(),
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expires_at": (datetime.now() + timedelta(hours=_SESSION_TTL_HOURS)).isoformat(
            timespec="seconds"
        ),
        "received": [],
    }
    _write_session_meta(upload_id, meta)
    return {
        "ok": True,
        "upload_id": upload_id,
        "kind": kind,
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
        "size": size,
        "expires_at": meta["expires_at"],
    }


@router.put("/api/v1/sync/upload-session/{upload_id}/chunk/{index}")
async def sync_upload_session_chunk(
    upload_id: str,
    index: int,
    request: Request,
    _: None = Depends(verify_sync_key),
):
    """上传第 index 片（0-based）；body=原始字节。"""
    meta = _read_session_meta(upload_id)
    chunk_count = int(meta.get("chunk_count") or 0)
    chunk_size = int(meta.get("chunk_size") or _DEFAULT_CHUNK_SIZE)
    if index < 0 or index >= chunk_count:
        raise HTTPException(status_code=400, detail=f"index 越界 0..{chunk_count-1}")
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="空分片")
    is_last = index == chunk_count - 1
    if not is_last and len(raw) != chunk_size:
        raise HTTPException(
            status_code=400,
            detail=f"非末片长度须={chunk_size}，got={len(raw)}",
        )
    if is_last:
        expect = int(meta["size"]) - chunk_size * (chunk_count - 1)
        if len(raw) != expect:
            raise HTTPException(
                status_code=400,
                detail=f"末片长度须={expect}，got={len(raw)}",
            )
    part_path = os.path.join(_session_dir(upload_id), "chunks", f"{index:06d}.part")
    tmp = part_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, part_path)
    received = _list_received_chunks(upload_id, chunk_count)
    meta["received"] = received
    meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_session_meta(upload_id, meta)
    return {
        "ok": True,
        "upload_id": upload_id,
        "index": index,
        "bytes": len(raw),
        "received_n": len(received),
        "chunk_count": chunk_count,
    }


@router.get("/api/v1/sync/upload-session/{upload_id}")
async def sync_upload_session_status(
    upload_id: str,
    _: None = Depends(verify_sync_key),
):
    meta = _read_session_meta(upload_id)
    chunk_count = int(meta.get("chunk_count") or 0)
    received = _list_received_chunks(upload_id, chunk_count)
    missing = [i for i in range(chunk_count) if i not in set(received)]
    return {
        "ok": True,
        "upload_id": upload_id,
        "kind": meta.get("kind"),
        "size": meta.get("size"),
        "chunk_size": meta.get("chunk_size"),
        "chunk_count": chunk_count,
        "received": received,
        "missing": missing,
        "complete": not missing,
    }


@router.post("/api/v1/sync/upload-session/{upload_id}/commit")
async def sync_upload_session_commit(
    upload_id: str,
    _: None = Depends(verify_sync_key),
):
    """拼装分片并按 kind 落盘。

    - channel_board → /channel/board/
    - cycle_report → /channel/report/（选品报告整包解压打开）
    - member_custom_zip → report_archives + 会员预览解压缓存
    """
    meta = _read_session_meta(upload_id)
    kind = str(meta.get("kind") or "channel_board")
    zip_path = _assemble_session_zip(upload_id, meta)
    try:
        if kind == "channel_board":
            result = _ingest_channel_board_zip(zip_path)
        elif kind == "cycle_report":
            result = _ingest_cycle_report_zip(zip_path)
        elif kind == "member_custom_zip":
            from cloud_deploy.cloud_api.report_upload_service import ingest_report_zip_file

            result = ingest_report_zip_file(zip_path, force=True)
            if isinstance(result, dict):
                result["ok"] = True
                result["view_url"] = "/channel/report/"
                result["archive_type"] = result.get("archive_type") or "member_custom_zip"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"kind={kind} 暂请用对应单次 upload",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"commit ingest 失败 kind={kind}: {e}") from e
    result["upload_id"] = upload_id
    result["via"] = "upload-session"
    result["kind"] = kind
    # 成功才清会话；失败保留分片便于续传/重 commit
    shutil.rmtree(_session_dir(upload_id), ignore_errors=True)
    return result


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


def _ingest_cycle_report_zip(zip_path: str) -> dict[str, Any]:
    """选品报告整包 → /channel/report/（解压打开；同套 index.html + data.js）。"""
    from cloud_deploy.cloud_api import database as db
    from cloud_deploy.cloud_api.config import get_settings
    from cloud_deploy.reporting.constants import ARCHIVE_CYCLE_REPORT

    if not str(zip_path).lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")
    if not os.path.isfile(zip_path):
        raise HTTPException(status_code=400, detail="zip 不存在")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-cycle-report-")
    try:
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
        # 兼容：顶层就是选品报告目录（无 marker 时补写）
        if not report_dir:
            for root, _dirs, files in os.walk(extract_root):
                if "index.html" in files and "data.js" in files:
                    report_dir = root
                    break
        if not report_dir:
            raise HTTPException(
                status_code=400,
                detail="zip 内未找到选品报告（需 index.html + data.js）",
            )

        marker_path = os.path.join(report_dir, "cycle_report_full_cloud.json")
        if not os.path.isfile(marker_path):
            marker_path = os.path.join(report_dir, "cycle_report_cloud.json")
        marker: dict[str, Any] = {}
        if os.path.isfile(marker_path):
            with open(marker_path, encoding="utf-8") as f:
                marker = json.load(f) or {}
        if not isinstance(marker, dict):
            marker = {}
        report_date = str(marker.get("report_date") or "")[:10]
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")
        server_imported = datetime.now().isoformat(timespec="seconds")
        pack_id = _cycle_pack_id({**marker, "report_date": report_date})
        marker["imported_at"] = server_imported
        marker["cloud_imported_at"] = server_imported
        marker["report_date"] = report_date
        marker["pack_id"] = pack_id
        marker["view_path"] = f"/channel/report/p/{pack_id}/"
        marker["product"] = marker.get("product") or "productanalyzer_full_pack"
        marker["pack_kind"] = marker.get("pack_kind") or "selection_report_full"
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False, indent=2)
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
        dest_live = os.path.join(cr_root, pack_id)
        os.makedirs(cr_root, exist_ok=True)
        if os.path.isdir(dest_live):
            shutil.rmtree(dest_live)
        shutil.copytree(report_dir, dest_live)

        latest = os.path.join(cr_root, "latest")
        if os.path.isdir(latest):
            shutil.rmtree(latest)
        shutil.copytree(dest_live, latest)

        # 同逻辑包名的旧日期目录 / 续传分片目录一并清掉，只留这一份
        _prune_cycle_pack_siblings(pack_id, keep_dirs={pack_id, "latest"})

        archive_dir = get_settings().xhs_report_archive_dir
        os.makedirs(archive_dir, exist_ok=True)
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
                "view_path": f"/channel/report/p/{pack_id}/",
                "product": "productanalyzer_full_pack",
                **marker,
            },
        )
        download_url = (
            f"/channel/report/p/{pack_id}/{dl_name}"
            if os.path.isfile(os.path.join(dest_live, dl_name))
            else f"/channel/report/p/{pack_id}/cycle_report_cloud.zip"
        )
        return {
            "ok": True,
            "report_date": report_date,
            "pack_id": pack_id,
            "imported_at": server_imported,
            "view_url": f"/channel/report/p/{pack_id}/",
            "list_url": "/channel/report/",
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


@router.post("/api/v1/sync/channel-cycle-report-upload")
async def sync_channel_cycle_report_upload(
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    """周期/选品报告整包 → /channel/report/（小包直传；大包请走 upload-session kind=cycle_report）。"""
    filename = os.path.basename(file.filename or "cycle_report_cloud.zip")
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 zip")

    tmp_dir = tempfile.mkdtemp(prefix="xhs-cycle-report-")
    zip_path = os.path.join(tmp_dir, filename)
    try:
        with open(zip_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        return _ingest_cycle_report_zip(zip_path)
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


@router.get("/channel/api/vertical-niche")
def channel_vertical_niche_api(
    request: Request,
    q: str = "",
    niche: str = "",
    goods_id: str = "",
    limit: int = 80,
):
    """原独立垂类看板合同：任意搜词 → PG。hub 只做导航，业务不另起炉灶。"""
    if not _cookie_ok(request):
        raise HTTPException(status_code=401, detail="未登录")
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    try:
        from cloud_deploy.cloud_api.database_pg import init_db
        from cloud_deploy.cloud_api.vertical_niche_query import query_vertical_niche

        init_db()
        payload = query_vertical_niche(
            q=q or "",
            niche=niche or "",
            goods_id=goods_id or "",
            limit=int(limit or 80),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"vertical-niche 失败: {e}") from e
    code = 200 if (payload or {}).get("ok", True) else 400
    return JSONResponse(payload, status_code=code, headers={**_NO_STORE, "X-Channel-Board": "1"})


@router.get("/channel/vertical")
@router.get("/channel/vertical/")
@router.get("/channel/vertical/{path:path}")
def channel_vertical_landing(request: Request, path: str = ""):
    """四看板①：导航到原 vertical_niche 页（不另做空壳业务页）。"""
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    rel = (path or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        target = "/channel/board/vertical_niche.html"
        q = request.url.query
        if q:
            target = f"{target}?{q}"
        elif (request.query_params.get("embed") or "") == "1":
            target = f"{target}?embed=1"
        return RedirectResponse(url=target, status_code=302)
    return RedirectResponse(url="/channel/board/vertical_niche.html", status_code=302)


_CYCLE_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CYCLE_CORE_NAME_RE = re.compile(r"(周期\d+)", re.UNICODE)
_CYCLE_PART_SUFFIX_RE = re.compile(
    r"(_部分|_partial|_part|_chunk|_续传|_分片)\d*$",
    re.IGNORECASE | re.UNICODE,
)


def _cycle_slug(raw: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", (raw or "").strip(), flags=re.UNICODE)
    slug = slug.strip("._")[:80] or "cycle"
    if slug.lower() in {"latest", "p", "api", "list"}:
        slug = f"pack_{slug}"
    return slug


def _cycle_canonical_source_name(raw: str) -> str:
    """把续传/分片文件名收成同一逻辑包：周期13075_部分2341 → 周期13075。"""
    s = str(raw or "").strip()
    if not s:
        return ""
    # 标题里常带「周期全量 · 周期13075」
    m = _CYCLE_CORE_NAME_RE.search(s)
    if m:
        return m.group(1)
    s = _CYCLE_PART_SUFFIX_RE.sub("", s).strip("._")
    return s or str(raw or "").strip()


def _cycle_pack_id(marker: dict[str, Any] | None = None, *, dir_name: str = "") -> str:
    """周期包目录名：按源文件名合并（同周期=同一包），不用上传日期拆多份。"""
    marker = marker or {}
    src = str(marker.get("source_name") or "").strip()
    title = str(marker.get("title") or marker.get("filter_label") or "").strip()
    raw = _cycle_canonical_source_name(src) or _cycle_canonical_source_name(title)
    if not raw:
        # 旧目录名若是日期，不要当 pack_id；交给调用方用 marker/date 兜底
        if dir_name and not _CYCLE_DATE_DIR_RE.match(dir_name) and dir_name != "latest":
            raw = _cycle_canonical_source_name(dir_name) or dir_name
    if not raw:
        date = str(marker.get("report_date") or "")[:10]
        raw = date or dir_name or "cycle"
    return _cycle_slug(raw)


def _cycle_pack_is_openable(root: str) -> bool:
    if not os.path.isdir(root):
        return False
    if not os.path.isfile(os.path.join(root, "data.js")):
        return False
    return any(
        os.path.isfile(os.path.join(root, name))
        for name in ("index.html", "index_with_gr.html", "index_vue.html")
    )


def _read_cycle_pack_marker(root: str) -> dict[str, Any]:
    for name in ("cycle_report_full_cloud.json", "cycle_report_cloud.json"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                obj = json.load(f) or {}
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}


def _cycle_pack_mtime(root: str) -> float:
    try:
        return float(os.path.getmtime(os.path.join(root, "data.js")))
    except OSError:
        try:
            return float(os.path.getmtime(root))
        except OSError:
            return 0.0


def _iter_cycle_pack_dirs(*, include_latest: bool = True) -> list[tuple[str, str, dict[str, Any]]]:
    """返回 [(dir_name, root, marker), ...]。"""
    cr_root = _cycle_report_root()
    if not os.path.isdir(cr_root):
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for name in os.listdir(cr_root):
        if name in {"p", "api"} or name.startswith("."):
            continue
        if name == "latest" and not include_latest:
            continue
        root = os.path.join(cr_root, name)
        if not _cycle_pack_is_openable(root):
            continue
        out.append((name, root, _read_cycle_pack_marker(root)))
    return out


def _prune_cycle_pack_siblings(pack_id: str, *, keep_dirs: set[str] | None = None) -> None:
    """删除同一逻辑包名下的多余目录（旧按日归档 / 续传分片）。"""
    pack_id = (pack_id or "").strip()
    if not pack_id:
        return
    keep = set(keep_dirs or set()) | {pack_id, "latest", "p", "api"}
    cr_root = _cycle_report_root()
    if not os.path.isdir(cr_root):
        return
    for name, root, marker in _iter_cycle_pack_dirs(include_latest=True):
        if name in keep:
            continue
        logical = _cycle_pack_id(marker, dir_name=name)
        if logical != pack_id and name != pack_id:
            continue
        try:
            shutil.rmtree(root)
        except OSError:
            pass


def _consolidate_cycle_packs() -> None:
    """把旧「按日期目录」迁到包名目录；同名只留最新，续传分片按文件名合并。"""
    cr_root = _cycle_report_root()
    if not os.path.isdir(cr_root):
        return
    groups: dict[str, list[tuple[float, str, str, dict[str, Any]]]] = {}
    for name, root, marker in _iter_cycle_pack_dirs(include_latest=False):
        pid = _cycle_pack_id(marker, dir_name=name)
        groups.setdefault(pid, []).append((_cycle_pack_mtime(root), name, root, marker))

    # 已是「一包一名目录」且无旁支时跳过，避免列表请求反复搬文件
    dirty = False
    for pack_id, rows in groups.items():
        if len(rows) > 1 or rows[0][1] != pack_id:
            dirty = True
            break
    if not dirty:
        return

    newest_overall: tuple[float, str] | None = None
    for pack_id, rows in groups.items():
        rows.sort(key=lambda x: x[0], reverse=True)
        mtime, keep_name, keep_root, keep_marker = rows[0]
        dest = os.path.join(cr_root, pack_id)
        try:
            keep_marker = dict(keep_marker or {})
            keep_marker["pack_id"] = pack_id
            if not keep_marker.get("source_name"):
                keep_marker["source_name"] = pack_id
            mk_path = os.path.join(keep_root, "cycle_report_full_cloud.json")
            if not os.path.isfile(mk_path):
                mk_path = os.path.join(keep_root, "cycle_report_cloud.json")
            with open(mk_path, "w", encoding="utf-8") as f:
                json.dump(keep_marker, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        if os.path.abspath(keep_root) != os.path.abspath(dest):
            if os.path.isdir(dest):
                try:
                    if _cycle_pack_mtime(dest) <= mtime:
                        shutil.rmtree(dest)
                    else:
                        keep_root = dest
                        keep_name = pack_id
                        mtime = _cycle_pack_mtime(dest)
                except OSError:
                    shutil.rmtree(dest, ignore_errors=True)
            if os.path.abspath(keep_root) != os.path.abspath(dest) and not os.path.isdir(dest):
                try:
                    shutil.move(keep_root, dest)
                    keep_root = dest
                    keep_name = pack_id
                except OSError:
                    try:
                        shutil.copytree(keep_root, dest)
                        shutil.rmtree(keep_root, ignore_errors=True)
                        keep_root = dest
                        keep_name = pack_id
                    except OSError:
                        pass

        for _, name, root, _marker in rows[1:]:
            if name in {"latest", pack_id}:
                continue
            if os.path.abspath(root) == os.path.abspath(keep_root):
                continue
            try:
                shutil.rmtree(root)
            except OSError:
                pass

        if _cycle_pack_is_openable(dest if os.path.isdir(dest) else keep_root):
            use_root = dest if os.path.isdir(dest) else keep_root
            use_mtime = _cycle_pack_mtime(use_root)
            if newest_overall is None or use_mtime >= newest_overall[0]:
                newest_overall = (use_mtime, use_root)

    # 只在发生合并时刷新 latest（整包复制成本高，不做无谓刷新）
    if newest_overall and dirty:
        src_latest = newest_overall[1]
        latest = os.path.join(cr_root, "latest")
        try:
            if os.path.isdir(latest):
                shutil.rmtree(latest)
            shutil.copytree(src_latest, latest)
        except OSError:
            pass


def _peek_cycle_data_meta(root: str) -> dict[str, Any]:
    """轻量读 data.js 头部 meta：出报时刻 / 周期窗口说明。"""
    path = os.path.join(root, "data.js")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(131072)
    except Exception:
        return {}
    out: dict[str, Any] = {}
    m = re.search(r'"date"\s*:\s*"([^"]+)"', head)
    if m:
        out["date"] = m.group(1)[:10]
    m = re.search(r'"time"\s*:\s*"([^"]+)"', head)
    if m:
        out["time"] = m.group(1).strip()[:19]
    m = re.search(r'"count"\s*:\s*(\d+)', head)
    if m:
        out["count"] = int(m.group(1))
    def _unquote_js(s: str) -> str:
        return (
            s.replace(r"\/", "/")
            .replace(r"\"", '"')
            .replace(r"\n", "\n")
            .replace(r"\\", "\\")
        )

    m = re.search(r'"filter_label"\s*:\s*"((?:\\.|[^"\\])*)"', head)
    if m:
        out["filter_label"] = _unquote_js(m.group(1))
    m = re.search(r'"scan_label"\s*:\s*"((?:\\.|[^"\\])*)"', head)
    if m:
        out["scan_label"] = _unquote_js(m.group(1))
    # 「近39日」/「周期#13075」等窗口线索
    blob = str(out.get("filter_label") or "") + " " + str(out.get("scan_label") or "")
    wm = re.search(r"近\s*(\d+)\s*日", blob)
    if wm:
        out["window_days"] = int(wm.group(1))
        out["period_label"] = f"近{wm.group(1)}日销量增量窗口"
    cm = re.search(r"周期#?\s*(\d+)", blob)
    if cm:
        out["cycle_no"] = cm.group(1)
    return out


def _cycle_pack_list_item(name: str, root: str, marker: dict[str, Any] | None = None) -> dict[str, Any]:
    marker = marker if isinstance(marker, dict) else _read_cycle_pack_marker(root)
    pack_id = _cycle_pack_id(marker, dir_name=name)
    src = str(marker.get("source_name") or "").strip()
    cycle_name = _cycle_canonical_source_name(src) or pack_id
    meta = _peek_cycle_data_meta(root)

    report_date = (
        str(meta.get("date") or marker.get("report_date") or "")[:10]
    )
    report_time = str(meta.get("time") or "").strip()
    if not report_time and report_date:
        built = str(marker.get("built_at") or "")[:19].replace("T", " ")
        report_time = built or report_date

    count = int(marker.get("full_count") or marker.get("cloud_count") or meta.get("count") or 0)
    period_label = str(meta.get("period_label") or "").strip()
    if not period_label:
        fl = str(meta.get("filter_label") or marker.get("filter_label") or "")
        wm = re.search(r"近\s*(\d+)\s*日", fl)
        period_label = f"近{wm.group(1)}日销量增量窗口" if wm else "关键词周期累计增量"
    cycle_no = str(meta.get("cycle_no") or "")
    if not cycle_no:
        cm = re.search(r"(\d+)", cycle_name)
        cycle_no = cm.group(1) if cm else ""

    # 展示名：出报时间优先，方便对照哪天的包
    if report_date:
        title = f"{report_date} 出报 · 周期#{cycle_no or cycle_name}"
    else:
        title = f"周期#{cycle_no or cycle_name}"

    summary = period_label
    if report_time:
        summary = f"{period_label} · 出报 {report_time}"

    return {
        "pack_id": pack_id,
        "dir_name": name,
        "title": title,
        "summary": summary,
        "period_label": period_label,
        "cycle_no": cycle_no,
        "source_name": src or cycle_name,
        "report_date": report_date,
        "report_time": report_time,
        "full_count": count,
        "imported_at": str(marker.get("imported_at") or marker.get("cloud_imported_at") or ""),
        "view_url": f"/channel/report/p/{pack_id}/",
        "mtime": _cycle_pack_mtime(root),
    }


def _list_cycle_report_packs() -> list[dict[str, Any]]:
    """按逻辑包名去重：同周期/同文件名只展示最新一份。"""
    try:
        _consolidate_cycle_packs()
    except Exception:
        pass

    items_by_id: dict[str, dict[str, Any]] = {}
    for name, root, marker in _iter_cycle_pack_dirs(include_latest=False):
        it = _cycle_pack_list_item(name, root, marker)
        pid = str(it.get("pack_id") or "")
        if not pid:
            continue
        prev = items_by_id.get(pid)
        if not prev or float(it.get("mtime") or 0) >= float(prev.get("mtime") or 0):
            items_by_id[pid] = it

    if not items_by_id:
        latest = os.path.join(_cycle_report_root(), "latest")
        if _cycle_pack_is_openable(latest):
            marker = _read_cycle_pack_marker(latest)
            it = _cycle_pack_list_item("latest", latest, marker)
            items_by_id[str(it["pack_id"])] = it

    items = list(items_by_id.values())
    items.sort(key=lambda x: (x.get("mtime") or 0), reverse=True)
    return items


def _resolve_cycle_pack_root(pack_id: str) -> tuple[str, str]:
    """按逻辑包名解析；兼容旧日期目录，同名多份取最新。"""
    pack_id = (pack_id or "").strip().strip("/")
    if not pack_id or ".." in pack_id or "/" in pack_id or "\\" in pack_id:
        raise HTTPException(status_code=400, detail="无效 pack_id")
    cr_root = _cycle_report_root()
    root = os.path.join(cr_root, pack_id)
    if _cycle_pack_is_openable(root):
        return root, f"cycle_report:{pack_id}"

    candidates: list[tuple[float, str, str]] = []
    for name, cand, marker in _iter_cycle_pack_dirs(include_latest=True):
        logical = _cycle_pack_id(marker, dir_name=name)
        mid = str(marker.get("pack_id") or "")
        if name == pack_id or mid == pack_id or logical == pack_id:
            candidates.append((_cycle_pack_mtime(cand), name, cand))
        elif name == "latest" and pack_id == "latest":
            candidates.append((_cycle_pack_mtime(cand), name, cand))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _mt, name, cand = candidates[0]
        return cand, f"cycle_report:{name}"
    raise HTTPException(status_code=404, detail=f"周期包不存在: {pack_id}")


def _cycle_report_catalog_html(*, embed: bool = False) -> str:
    items = _list_cycle_report_packs()
    rows = []
    for it in items:
        n = int(it.get("full_count") or 0)
        count_s = f"{n:,}" if n else "—"
        date_s = it.get("report_date") or "—"
        time_s = (it.get("report_time") or date_s or "")[:19]
        period = it.get("period_label") or "关键词周期累计增量"
        imported = (it.get("imported_at") or "")[:19].replace("T", " ")
        open_url = it["view_url"] + ("?embed=1" if embed else "")
        rows.append(
            "<article class='card'>"
            f"<div class='tag'>出报 {_html_escape(date_s)}</div>"
            f"<h2>{_html_escape(it.get('title') or it['pack_id'])}</h2>"
            f"<p class='desc'>{_html_escape(period)}"
            f"{(' · 出报时刻 ' + _html_escape(time_s)) if time_s else ''}</p>"
            f"<div class='meta'>入选 <b>{count_s}</b>"
            f"{(' · 入库 ' + _html_escape(imported)) if imported else ''}"
            f" · 包名 {_html_escape(it.get('source_name') or it['pack_id'])}</div>"
            f"<a class='btn' href='{_html_escape(open_url)}'>打开报告</a>"
            "</article>"
        )
    body_cards = (
        "".join(rows)
        if rows
        else (
            "<div class='empty'><h2>还没有周期包</h2>"
            "<p>本机运行 <code>python tools/publish_cycle_report_cloud.py</code> "
            "上传选品报告 zip 后，会出现在这里。</p></div>"
        )
    )
    embed_cls = " hub-embed" if embed else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN" class="{embed_cls.strip()}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>周期包列表</title>
<style>
:root{{--bg:#eef3f8;--card:#fff;--text:#101828;--muted:#3d4f63;--line:#c5d0dc;--accent:#14708f;--accent-soft:#e2f3f8;--accent-deep:#0a4f66}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--text);background:linear-gradient(180deg,#f7fafc,#eef3f8);min-height:100vh}}
.wrap{{max-width:920px;margin:0 auto;padding:28px 20px 48px}}
.hub-embed .wrap{{padding:12px 14px 28px}}
.eyebrow{{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;margin:0 0 6px}}
h1{{margin:0 0 8px;font-size:1.45rem;letter-spacing:-.02em}}
.hub-embed h1{{font-size:1.15rem}}
.sub{{margin:0 0 18px;color:var(--muted);font-size:13px;line-height:1.5}}
.grid{{display:grid;gap:12px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 18px 16px;box-shadow:0 1px 2px rgba(16,24,40,.04)}}
.tag{{display:inline-block;font-size:11px;font-weight:700;color:var(--accent-deep);background:var(--accent-soft);border:1px solid rgba(20,112,143,.22);border-radius:999px;padding:3px 10px;margin-bottom:8px}}
.card h2{{margin:0 0 6px;font-size:1.08rem;letter-spacing:-.01em}}
.desc{{margin:0 0 10px;font-size:13px;color:var(--muted);line-height:1.5}}
.meta{{font-size:12px;color:var(--muted);margin-bottom:14px;line-height:1.45}}
.meta b{{color:var(--text);font-variant-numeric:tabular-nums}}
.btn{{display:inline-block;padding:9px 14px;border-radius:10px;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;font-size:13px}}
.btn:hover{{background:var(--accent-deep)}}
.empty{{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:28px 20px;text-align:center}}
.empty h2{{margin:0 0 8px;font-size:1.05rem}}
.empty p{{margin:0;color:var(--muted);font-size:13px;line-height:1.55}}
code{{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#f0f5f8;padding:1px 6px;border-radius:6px}}
.foot{{margin-top:18px;font-size:12px;color:var(--muted)}}
.foot a{{color:var(--accent);font-weight:650;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">选品作战台 · ④</div>
  <h1>周期包列表</h1>
  <p class="sub">按出报时间命名；同周期包名自动合并为最新一份，并标注数据时间窗口。</p>
  <div class="grid">{body_cards}</div>
  <div class="foot"><a href="/channel/hub/">返回四看板</a> · 共 {len(items)} 份</div>
</div>
<script>
(function(){{
  // 鼠标悬停/触摸「打开报告」时预热 data.js（约百兆）；配合可缓存头，点开更快
  function warm(href){{
    try{{
      var u=new URL(href, location.href);
      u.search="";
      if(!/\\/p\\//.test(u.pathname)) return;
      u.pathname=u.pathname.replace(/\\/?$/,"/")+"data.js";
      if(window.__cycleWarm===u.href) return;
      window.__cycleWarm=u.href;
      fetch(u.href, {{credentials:"same-origin", cache:"force-cache", priority:"low"}}).catch(function(){{}});
    }}catch(_){{}}
  }}
  document.querySelectorAll("a.btn").forEach(function(a){{
    a.addEventListener("mouseenter", function(){{ warm(a.href); }}, {{once:true}});
    a.addEventListener("touchstart", function(){{ warm(a.href); }}, {{once:true, passive:true}});
  }});
  // 只有一份时：列表出现后稍候自动预热，接近以前「进④就加载」的体感
  var only=document.querySelectorAll("a.btn");
  if(only.length===1){{
    setTimeout(function(){{ warm(only[0].href); }}, 400);
  }}
}})();
</script>
</body>
</html>"""


def _html_escape(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _serve_cycle_pack_file(
    request: Request,
    *,
    root: str,
    source: str,
    rel: str,
) -> FileResponse | HTMLResponse:
    rel = (rel or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        for name in ("index.html", "index_with_gr.html", "index_vue.html"):
            if os.path.isfile(os.path.join(root, name)):
                rel = name
                break
        else:
            rel = "index.html"

    try:
        target = _safe_file(root, rel)
    except Exception:
        target = ""
    if not target or not os.path.isfile(target):
        alt_map = {
            "index.html": ("index_with_gr.html", "index_vue.html"),
            "_view_table.html": ("index_with_gr.html",),
            "_view_cards.html": ("index_vue.html",),
        }
        found = ""
        for name in alt_map.get(rel, ()):
            cand = os.path.join(root, name)
            if os.path.isfile(cand):
                found = cand
                rel = name
                break
        if not found:
            raise HTTPException(status_code=404, detail="not found")
        target = found

    low = rel.lower()
    media = _media_type(rel)
    if low.endswith(".zip"):
        media = "application/zip"
    is_html = low.endswith((".html", ".htm"))
    headers = {
        "X-Channel-Board": "1",
        "X-Cycle-Report-Source": _header_ascii(source, limit=80),
    }
    if is_html:
        headers.update(_NO_STORE)
    else:
        # data.js / 静态资源：按文件 mtime 做 ETag，浏览器可复用，避免每次点开重下百兆
        headers.update(_STATIC_CACHE)
        try:
            st = os.stat(target)
            headers["ETag"] = f'W/"{int(st.st_mtime)}-{st.st_size}"'
            headers["Last-Modified"] = (
                __import__("email.utils", fromlist=["formatdate"]).formatdate(
                    st.st_mtime, usegmt=True
                )
            )
        except OSError:
            pass
        # 条件请求：未变更直接 304，秒开
        inm = (request.headers.get("if-none-match") or "").strip()
        if inm and headers.get("ETag") and inm == headers["ETag"]:
            from fastapi.responses import Response

            return Response(status_code=304, headers=headers)
    if low.endswith(".zip"):
        from urllib.parse import quote as _q

        fname = os.path.basename(target)
        ascii_name = "cycle_report.zip"
        headers["Content-Disposition"] = (
            f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{_q(fname)}"
        )

    embed = (request.query_params.get("embed") or "") == "1"
    if embed and is_html:
        try:
            with open(target, "rb") as f:
                raw = f.read()
            return HTMLResponse(
                _inject_cycle_embed_chrome(raw).decode("utf-8", errors="ignore"),
                media_type=media or "text/html; charset=utf-8",
                headers=headers,
            )
        except Exception:
            pass
    return FileResponse(target, media_type=media, headers=headers)


@router.get("/channel/report/{path:path}")
@router.get("/channel/report")
@router.get("/channel/report/")
def channel_cycle_report_files(request: Request, path: str = ""):
    """④ 周期包：先列表自选；/p/{pack_id}/ 打开对应选品报告整包。"""
    if not _cookie_ok(request):
        return RedirectResponse(url="/channel/", status_code=302)
    if request.url.path == "/channel/report" and not (path or "").strip():
        return RedirectResponse(url="/channel/report/", status_code=302)

    rel = (path or "").strip().lstrip("/")
    embed = (request.query_params.get("embed") or "") == "1"

    # JSON 列表
    if rel in {"api/list", "api/list.json", "list.json"}:
        return JSONResponse(
            {"ok": True, "items": _list_cycle_report_packs()},
            headers=_NO_STORE,
        )

    # 目录页
    if not rel or rel in {"list", "index", "index.html"}:
        return HTMLResponse(
            _cycle_report_catalog_html(embed=embed),
            headers={**_NO_STORE, "X-Channel-Board": "1", "X-Cycle-Report-Source": "catalog"},
        )

    # /p/{pack_id}/...
    if rel == "p" or rel.startswith("p/"):
        rest = rel[1:].lstrip("/") if rel.startswith("p") else ""
        if not rest:
            return RedirectResponse(url="/channel/report/", status_code=302)
        pack_id, _, file_rel = rest.partition("/")
        root, source = _resolve_cycle_pack_root(pack_id)
        return _serve_cycle_pack_file(request, root=root, source=source, rel=file_rel)

    # 兼容：旧直链 /channel/report/data.js → 最新包
    latest = os.path.join(_cycle_report_root(), "latest")
    if _cycle_pack_is_openable(latest):
        return _serve_cycle_pack_file(
            request, root=latest, source="cycle_report_latest", rel=rel
        )

    return HTMLResponse(
        "<h3>周期选品报告尚未上传</h3>"
        "<p>请本机运行 <code>python tools/publish_cycle_report_cloud.py</code> 上传后，"
        "本页会列出可选周期包。</p>"
        "<p><a href='/channel/hub/'>返回入口</a></p>",
        status_code=404,
    )
