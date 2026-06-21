#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
本地 risk 静默采集 Agent — 开机自启、拉工单、Playwright 采集、HTTP 回传云端。

无需开放 PG 5432；通过云端 API（X-Agent-Key 鉴权）拉取 risk 列表并上传结果。

环境变量（本地 .env 或 install 脚本写入）:
  XHS_CLOUD_API_URL=https://xhs365.cn
  XHS_LOCAL_AGENT_KEY=与服务器 .env 一致的长随机串
  XHS_CRAWLER_ROOT=D:\vuemonitor\xhs-cloud\cloud_deploy\crawler_runtime
  XHS_ENABLE_PLAYWRIGHT=1
  XHS_LOCAL_AGENT_ID=home-pc-1          # 可选，标识本机
  XHS_LOCAL_AGENT_BATCH=80              # 每轮拉取条数
  XHS_LOCAL_AGENT_CONCURRENCY=5         # Playwright 进程并发
  XHS_LOCAL_AGENT_IDLE_SEC=300          # 无工单时休眠秒数
  XHS_LOCAL_AGENT_COOLDOWN_SEC=15       # 每轮上传后冷却
  XHS_LOCAL_AGENT_LOG_DIR=%LOCALAPPDATA%\xhs-local-agent

用法:
  python tools/local_risk_agent.py run          # 前台运行（调试）
  python tools/local_risk_agent.py run-once   # 跑一轮后退出
  python tools/local_risk_agent.py status     # 检查 API 连通与待处理 risk 数

Windows 静默安装（开机自启）:
  powershell -ExecutionPolicy Bypass -File tools/install_local_risk_agent.ps1
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_XHS_ROOT = os.environ.get("XHS_CLOUD_PKG_ROOT", os.path.dirname(_TOOLS))
if _XHS_ROOT not in sys.path:
    sys.path.insert(0, _XHS_ROOT)

CLOUD_ROOT = os.path.join(_XHS_ROOT, "cloud_deploy")
CRAWLER_DEFAULT = os.path.join(_XHS_ROOT, "cloud_deploy", "crawler_runtime")


def _log_dir() -> Path:
    base = os.environ.get("XHS_LOCAL_AGENT_LOG_DIR", "").strip()
    if not base:
        base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "xhs-local-agent")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        with open(_log_dir() / "agent.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if os.environ.get("XHS_LOCAL_AGENT_FOREGROUND", "").strip().lower() in ("1", "true", "yes"):
        print(line, flush=True)


def _api_base() -> str:
    return os.environ.get("XHS_CLOUD_API_URL", "http://127.0.0.1:8080").rstrip("/")


def _agent_key() -> str:
    return os.environ.get("XHS_LOCAL_AGENT_KEY", os.environ.get("XHS_CLOUD_SYNC_KEY", "")).strip()


def _agent_id() -> str:
    return os.environ.get("XHS_LOCAL_AGENT_ID", os.environ.get("COMPUTERNAME", "local-agent"))


def _api_request(method: str, path: str, body: dict | None = None, timeout: int = 120) -> dict:
    key = _agent_key()
    if not key:
        raise RuntimeError("未配置 XHS_LOCAL_AGENT_KEY")
    url = f"{_api_base()}{path}"
    data = None
    headers = {"X-Agent-Key": key, "User-Agent": "xhs-local-risk-agent/1.0"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    except URLError as e:
        raise RuntimeError(f"网络错误: {e}") from e


def fetch_worklist(limit: int, scan_date: str = "") -> dict:
    q = f"?limit={int(limit)}"
    if scan_date:
        q += f"&scan_date={scan_date}"
    return _api_request("GET", f"/api/v1/agent/risk-worklist{q}")


def upload_results(rows: list[dict], batch_id: str, scan_date: str) -> dict:
    return _api_request(
        "POST",
        "/api/v1/agent/scan-results",
        {
            "batch_id": batch_id,
            "agent_id": _agent_id(),
            "scan_date": scan_date,
            "rows": rows,
        },
        timeout=180,
    )


def _worker_init(crawler: str, cloud_root: str) -> None:
    if cloud_root not in sys.path:
        sys.path.insert(0, cloud_root)
    if crawler and os.path.isdir(crawler) and crawler not in sys.path:
        sys.path.insert(0, crawler)
    os.environ["XHS_ENABLE_PLAYWRIGHT"] = "1"


def _worker_fetch(payload: tuple[str, str]) -> dict:
    goods_id, crawler = payload
    cloud_root = os.environ.get("_RISK_AGENT_CLOUD_ROOT", _XHS_ROOT)
    _worker_init(crawler, cloud_root)
    from cloud_deploy.cloud_api.agent_service import slim_detail

    from xhs_full_sold_fetch import fetch_sold_detail

    t0 = time.time()
    gid = str(goods_id)
    try:
        detail, status, meta = fetch_sold_detail(
            gid,
            engine="playwright",
            fallback_chain=("playwright",),
            auto_fallback=False,
        )
    except Exception as exc:
        return {
            "goods_id": gid,
            "status": "fail",
            "sold": None,
            "message": str(exc)[:200],
            "engine": "playwright",
            "ms": int((time.time() - t0) * 1000),
            "detail": {},
        }
    meta = dict(meta or {})
    sold = None
    detail_out = None
    if status == "ok" and detail:
        sold = int(detail.get("real_sales") or detail.get("product_sales") or 0)
        detail_out = slim_detail(detail)
    return {
        "goods_id": gid,
        "status": status,
        "sold": sold,
        "message": str(meta.get("message") or "")[:200],
        "engine": str(meta.get("won_engine") or meta.get("engine") or "playwright"),
        "ms": int((time.time() - t0) * 1000),
        "detail": detail_out or {},
    }


def scan_batch(items: list[dict], concurrency: int, crawler: str) -> list[dict]:
    os.environ["_RISK_AGENT_CLOUD_ROOT"] = _XHS_ROOT
    work = [(str(i["goods_id"]), crawler) for i in items]
    results: list[dict] = []
    with ProcessPoolExecutor(
        max_workers=max(1, concurrency),
        initializer=_worker_init,
        initargs=(crawler, _XHS_ROOT),
    ) as pool:
        futs = {pool.submit(_worker_fetch, w): w[0] for w in work}
        for fut in as_completed(futs):
            results.append(fut.result())
    return results


def run_once() -> dict:
    batch_size = max(10, min(500, int(os.environ.get("XHS_LOCAL_AGENT_BATCH", "80"))))
    concurrency = max(1, min(8, int(os.environ.get("XHS_LOCAL_AGENT_CONCURRENCY", "5"))))
    crawler = os.environ.get("XHS_CRAWLER_ROOT", CRAWLER_DEFAULT).strip()
    scan_date = date.today().isoformat()

    wl = fetch_worklist(batch_size, scan_date)
    items = wl.get("items") or []
    pending = int(wl.get("pending_risk") or 0)
    if not items:
        _log(f"无 risk 工单 pending={pending}")
        return {"pending_risk": pending, "scanned": 0, "ok": 0}

    _log(f"开始采集 {len(items)} 条 pending={pending} 并发={concurrency}")
    t0 = time.time()
    results = scan_batch(items, concurrency, crawler)
    ok = sum(1 for r in results if r.get("status") == "ok")
    _log(f"采集完成 ok={ok}/{len(results)} 耗时={time.time()-t0:.1f}s 上传中...")

    up = upload_results(results, str(uuid.uuid4()), scan_date)
    _log(f"上传完成 {up}")
    summary = {
        "pending_risk": pending,
        "scanned": len(results),
        "ok": ok,
        "upload": up,
        "wall_s": round(time.time() - t0, 1),
    }
    try:
        with open(_log_dir() / "last_run.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return summary


def run_daemon() -> None:
    idle_sec = max(30, int(os.environ.get("XHS_LOCAL_AGENT_IDLE_SEC", "300")))
    cooldown = max(0, int(os.environ.get("XHS_LOCAL_AGENT_COOLDOWN_SEC", "15")))
    _log(f"Agent 启动 id={_agent_id()} api={_api_base()}")
    while True:
        try:
            summary = run_once()
            if int(summary.get("scanned") or 0) == 0:
                time.sleep(idle_sec)
            else:
                time.sleep(cooldown)
        except KeyboardInterrupt:
            _log("收到退出信号")
            break
        except Exception as exc:
            _log(f"本轮异常: {exc}")
            time.sleep(min(idle_sec, 120))


def cmd_status() -> None:
    try:
        wl = fetch_worklist(1)
        print(json.dumps({"api": _api_base(), "agent_id": _agent_id(), **wl}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"连接失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main():
    import argparse

    ap = argparse.ArgumentParser(description="本地 risk Playwright Agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="守护循环")
    sub.add_parser("run-once", help="跑一轮")
    sub.add_parser("status", help="检查 API 与待处理数")
    args = ap.parse_args()

    env_file = os.environ.get("XHS_LOCAL_AGENT_ENV", "")
    if env_file and os.path.isfile(env_file):
        from cloud_deploy.scripts.bootstrap_env import bootstrap

        bootstrap(env_file)

    if args.cmd == "run":
        run_daemon()
    elif args.cmd == "run-once":
        run_once()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
