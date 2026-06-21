#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
本地 risk 静默采集 Agent — 开机自启、拉工单、Playwright 采集、HTTP 回传云端。

无需开放 PG 5432；通过云端 API（X-Agent-Key 鉴权）拉取 risk 列表并上传结果。

环境变量（本地 .env 或 install 脚本写入）:
  XHS_CLOUD_API_URL=https://monitor.xhs365.cn
  XHS_LOCAL_AGENT_KEY=与服务器 .env 一致的长随机串
  XHS_CRAWLER_ROOT=D:\vuemonitor\xhs-cloud\cloud_deploy\crawler_runtime
  XHS_ENABLE_PLAYWRIGHT=1
  XHS_LOCAL_AGENT_ID=home-pc-1          # 可选，标识本机
  XHS_LOCAL_AGENT_BATCH=80              # 每轮拉取条数
  XHS_LOCAL_AGENT_CONCURRENCY=5         # Playwright 进程/标签并发
  XHS_LOCAL_AGENT_MODE=multi_browser    # multi_browser | single_browser | api_then_browser
  XHS_LOCAL_AGENT_IDLE_SEC=300          # 无工单时休眠秒数
  XHS_LOCAL_AGENT_COOLDOWN_SEC=15       # 每轮上传后冷却
  XHS_LOCAL_AGENT_LOG_DIR=%LOCALAPPDATA%\xhs-local-agent

用法:
  python tools/local_risk_agent.py run          # 前台运行（调试）
  python tools/local_risk_agent.py run-once   # 跑一轮后退出
  python tools/local_risk_agent.py status     # 检查 API 连通与待处理 risk 数
  python tools/local_risk_agent.py compare    # 三种模式对比测试（不上传）

Windows 静默安装（开机自启）:
  powershell -ExecutionPolicy Bypass -File tools/install_local_risk_agent.ps1
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from local_risk_agent_modes import (
    MODE_API_THEN_BROWSER,
    MODE_LABELS,
    MODE_MULTI_BROWSER,
    MODE_SINGLE_BROWSER,
    compare_modes,
    scan_batch,
)

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_XHS_ROOT = os.environ.get("XHS_CLOUD_PKG_ROOT", os.path.dirname(_TOOLS))
if _XHS_ROOT not in sys.path:
    sys.path.insert(0, _XHS_ROOT)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

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
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e
        except (TimeoutError, URLError) as e:
            last_err = e
            if attempt < 2:
                _log(f"请求超时，{5 * (attempt + 1)}s 后重试 ({attempt + 1}/3)...")
                time.sleep(5 * (attempt + 1))
                continue
    raise RuntimeError(f"网络超时: {last_err}") from last_err


def fetch_worklist(limit: int, scan_date: str = "", include_pending: bool = False) -> dict:
    q = f"?limit={int(limit)}"
    if scan_date:
        q += f"&scan_date={scan_date}"
    if include_pending:
        q += "&include_pending=1"
    return _api_request("GET", f"/api/v1/agent/risk-worklist{q}", timeout=180)


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


def _agent_mode() -> str:
    mode = os.environ.get("XHS_LOCAL_AGENT_MODE", MODE_MULTI_BROWSER).strip().lower()
    aliases = {
        "a": MODE_MULTI_BROWSER,
        "multi": MODE_MULTI_BROWSER,
        "c": MODE_SINGLE_BROWSER,
        "single": MODE_SINGLE_BROWSER,
        "tabs": MODE_SINGLE_BROWSER,
        "d": MODE_API_THEN_BROWSER,
        "api": MODE_API_THEN_BROWSER,
        "api_pw": MODE_API_THEN_BROWSER,
    }
    return aliases.get(mode, mode)


def _load_env_file() -> None:
    env_file = os.environ.get("XHS_LOCAL_AGENT_ENV", "").strip()
    if not env_file:
        default_env = Path(__file__).resolve().parent / "local_agent.env"
        if default_env.is_file():
            env_file = str(default_env)
    if env_file and os.path.isfile(env_file):
        from cloud_deploy.scripts.bootstrap_env import bootstrap

        bootstrap(env_file)


def run_once() -> dict:
    batch_size = max(10, min(500, int(os.environ.get("XHS_LOCAL_AGENT_BATCH", "80"))))
    concurrency = max(1, min(10, int(os.environ.get("XHS_LOCAL_AGENT_CONCURRENCY", "5"))))
    crawler = os.environ.get("XHS_CRAWLER_ROOT", CRAWLER_DEFAULT).strip()
    scan_date = date.today().isoformat()

    wl = fetch_worklist(batch_size, scan_date, include_pending=False)
    items = wl.get("items") or []
    pending = wl.get("pending_risk")
    if not items:
        _log(f"无 risk 工单 pending={pending if pending is not None else '?'}")
        return {"pending_risk": pending or 0, "scanned": 0, "ok": 0}

    mode = _agent_mode()
    if mode not in MODE_LABELS:
        _log(f"未知模式 {mode}，回退 multi_browser")
        mode = MODE_MULTI_BROWSER

    _log(
        f"开始采集 {len(items)} 条 mode={mode} "
        f"({MODE_LABELS.get(mode, mode)}) 并发={concurrency}"
    )
    t0 = time.time()
    results = scan_batch(items, concurrency, crawler, _XHS_ROOT, mode, log_fn=_log)
    ok = sum(1 for r in results if r.get("status") == "ok")
    _log(f"采集完成 ok={ok}/{len(results)} 耗时={time.time()-t0:.1f}s 上传中...")

    up = upload_results(results, str(uuid.uuid4()), scan_date)
    _log(f"上传完成 {up}")
    summary = {
        "pending_risk": pending if pending is not None else 0,
        "mode": mode,
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
    _log(f"Agent 启动 id={_agent_id()} mode={_agent_mode()} api={_api_base()}")
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
        wl = fetch_worklist(1, include_pending=True)
        print(json.dumps({"api": _api_base(), "agent_id": _agent_id(), **wl}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"连接失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def cmd_compare() -> None:
    batch_size = max(10, min(100, int(os.environ.get("XHS_LOCAL_AGENT_BATCH", "80"))))
    concurrency = max(1, min(10, int(os.environ.get("XHS_LOCAL_AGENT_CONCURRENCY", "5"))))
    crawler = os.environ.get("XHS_CRAWLER_ROOT", CRAWLER_DEFAULT).strip()
    scan_date = date.today().isoformat()

    wl = fetch_worklist(batch_size, scan_date, include_pending=False)
    items = wl.get("items") or []
    if not items:
        print("无 risk 工单可对比")
        raise SystemExit(1)

    print(f"对比模式: 每模式最多 {os.environ.get('XHS_LOCAL_AGENT_COMPARE_N', '15')} 条")
    reports = compare_modes(items, concurrency, crawler, _XHS_ROOT, log_fn=_log)
    out = _log_dir() / "mode_compare.json"
    out.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    print(f"\n报告已保存: {out}")


def main():
    import argparse

    ap = argparse.ArgumentParser(description="本地 risk Playwright Agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="守护循环")
    sub.add_parser("run-once", help="跑一轮")
    sub.add_parser("status", help="检查 API 与待处理数")
    sub.add_parser("compare", help="A/C/D 三模式对比（不上传）")
    args = ap.parse_args()

    _load_env_file()

    if args.cmd == "run":
        run_daemon()
    elif args.cmd == "run-once":
        run_once()
    elif args.cmd == "compare":
        cmd_compare()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
