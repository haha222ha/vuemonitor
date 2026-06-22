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
  XHS_LOCAL_AGENT_BATCH=800             # 每轮拉取条数（最大 1000，需服务端同步放开 limit）
  XHS_LOCAL_AGENT_CONCURRENCY=5         # Playwright 进程/标签并发
  XHS_LOCAL_AGENT_MODE=api_only         # api_only(E) | multi_browser(A) | single_browser(C) | api_then_browser(D)
  XHS_LOCAL_AGENT_IDLE_SEC=300          # 无工单时休眠秒数
  XHS_LOCAL_AGENT_COOLDOWN_SEC=15       # 每批上传后冷却
  XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC=3600  # 整轮 risk 扫完后冷却（默认1小时）
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
    MODE_API_ONLY,
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
        p = _log_dir() / "agent.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
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


def _batch_cap() -> int:
    return max(100, min(1000, int(os.environ.get("XHS_LOCAL_AGENT_BATCH_MAX", "1000"))))


def _batch_size(default: int = 800) -> int:
    return max(10, min(_batch_cap(), int(os.environ.get("XHS_LOCAL_AGENT_BATCH", str(default)))))


def _upload_timeout(row_count: int) -> int:
    custom = int(os.environ.get("XHS_LOCAL_AGENT_UPLOAD_TIMEOUT", "0") or 0)
    if custom > 0:
        return max(60, min(900, custom))
    return max(180, min(900, 120 + row_count))


def fetch_worklist(limit: int, scan_date: str = "", include_pending: bool = False) -> dict:
    q = f"?limit={int(limit)}&agent_id={_agent_id()}"
    if scan_date:
        q += f"&scan_date={scan_date}"
    if include_pending:
        q += "&include_pending=1"
    min_age = os.environ.get("XHS_LOCAL_AGENT_MIN_AGE_HOURS", "2").strip()
    if min_age:
        q += f"&min_age_hours={min_age}"
    return _api_request("GET", f"/api/v1/agent/risk-worklist{q}", timeout=180)


def upload_results(rows: list[dict], batch_id: str, scan_date: str) -> dict:
    timeout = _upload_timeout(len(rows))
    return _api_request(
        "POST",
        "/api/v1/agent/scan-results",
        {
            "batch_id": batch_id,
            "agent_id": _agent_id(),
            "scan_date": scan_date,
            "rows": rows,
        },
        timeout=timeout,
    )


def _agent_mode() -> str:
    mode = os.environ.get("XHS_LOCAL_AGENT_MODE", MODE_API_ONLY).strip().lower()
    aliases = {
        "a": MODE_MULTI_BROWSER,
        "multi": MODE_MULTI_BROWSER,
        "c": MODE_SINGLE_BROWSER,
        "single": MODE_SINGLE_BROWSER,
        "tabs": MODE_SINGLE_BROWSER,
        "d": MODE_API_THEN_BROWSER,
        "api_pw": MODE_API_THEN_BROWSER,
        "e": MODE_API_ONLY,
        "api": MODE_API_ONLY,
        "api_only": MODE_API_ONLY,
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


def _load_cycle_state() -> dict:
    path = _log_dir() / "cycle_state.json"
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"start_pending": 0, "batches": 0, "items": 0, "scan_date": ""}


def _save_cycle_state(state: dict) -> None:
    try:
        path = _log_dir() / "cycle_state.json"
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _reset_cycle_state(pending: int, scan_date: str) -> dict:
    state = {"start_pending": max(0, int(pending)), "batches": 0, "items": 0, "scan_date": scan_date}
    _save_cycle_state(state)
    return state


def _sleep_with_log(seconds: int, reason: str) -> None:
    seconds = max(0, int(seconds))
    if seconds <= 0:
        return
    hours, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hours:
        eta = f"{hours}h{mins}m"
    elif mins:
        eta = f"{mins}m{secs}s"
    else:
        eta = f"{secs}s"
    _log(f"{reason}，整轮冷却 {eta}...")
    left = seconds
    while left > 0:
        chunk = min(left, 60)
        time.sleep(chunk)
        left -= chunk
        if left > 0 and left % 600 == 0:
            _log(f"整轮冷却中，剩余约 {left // 60} 分钟...")


def run_once() -> dict:
    batch_size = _batch_size()
    concurrency = max(1, min(10, int(os.environ.get("XHS_LOCAL_AGENT_CONCURRENCY", "5"))))
    crawler = os.environ.get("XHS_CRAWLER_ROOT", CRAWLER_DEFAULT).strip()
    scan_date = date.today().isoformat()

    wl = fetch_worklist(batch_size, scan_date, include_pending=True)
    items = wl.get("items") or []
    pending = int(wl.get("pending_risk") or 0)
    if not items:
        _log(f"无 risk 工单 pending={pending}")
        return {
            "pending_risk": pending,
            "scanned": 0,
            "ok": 0,
            "batch_size": batch_size,
            "tail_batch": True,
            "scan_date": scan_date,
        }

    mode = _agent_mode()
    if mode not in MODE_LABELS:
        _log(f"未知模式 {mode}，回退 api_only")
        mode = MODE_API_ONLY

    _log(
        f"开始采集 {len(items)} 条 pending={pending} mode={mode} "
        f"({MODE_LABELS.get(mode, mode)}) 并发={concurrency}"
    )
    t0 = time.time()
    results = scan_batch(items, concurrency, crawler, _XHS_ROOT, mode, log_fn=_log)
    ok = sum(1 for r in results if r.get("status") == "ok")
    _log(f"采集完成 ok={ok}/{len(results)} 耗时={time.time()-t0:.1f}s 上传中...")

    up = upload_results(results, str(uuid.uuid4()), scan_date)
    _log(f"上传完成 {up}")
    summary = {
        "pending_risk": pending,
        "mode": mode,
        "scanned": len(results),
        "ok": ok,
        "upload": up,
        "wall_s": round(time.time() - t0, 1),
        "batch_size": batch_size,
        "tail_batch": len(items) < batch_size,
        "scan_date": scan_date,
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
    cycle_cooldown = max(60, int(os.environ.get("XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC", "3600")))
    batch_size = _batch_size()
    _log(
        f"Agent 启动 id={_agent_id()} mode={_agent_mode()} api={_api_base()} "
        f"批间={cooldown}s 整轮={cycle_cooldown}s"
    )
    cycle = _load_cycle_state()
    while True:
        try:
            summary = run_once()
            scanned = int(summary.get("scanned") or 0)
            pending = int(summary.get("pending_risk") or 0)
            scan_date = str(summary.get("scan_date") or date.today().isoformat())
            tail_batch = bool(summary.get("tail_batch"))

            if cycle.get("scan_date") != scan_date or not cycle.get("start_pending"):
                cycle = _reset_cycle_state(pending, scan_date)
                if pending:
                    _log(f"新轮次开始 pending={pending} 预计约 {max(1, (pending + batch_size - 1) // batch_size)} 批")

            if scanned == 0:
                if pending <= 0:
                    _sleep_with_log(cycle_cooldown, "今日 risk 已全部处理")
                    cycle = _reset_cycle_state(0, scan_date)
                else:
                    time.sleep(idle_sec)
                continue

            cycle["batches"] = int(cycle.get("batches") or 0) + 1
            cycle["items"] = int(cycle.get("items") or 0) + scanned
            _save_cycle_state(cycle)

            start_pending = int(cycle.get("start_pending") or pending or 0)
            batches_planned = max(1, (start_pending + batch_size - 1) // batch_size) if start_pending else 0
            cycle_done = (
                pending <= 0
                or tail_batch
                or (batches_planned and int(cycle["batches"]) >= batches_planned)
            )

            if cycle_done:
                _log(
                    f"本轮完成 已扫 {cycle['items']} 条 / 轮初 pending≈{start_pending} "
                    f"剩余 pending={pending}"
                )
                _sleep_with_log(cycle_cooldown, "整轮 risk 采集结束")
                cycle = _reset_cycle_state(pending, scan_date)
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
    batch_size = max(10, min(100, _batch_size()))
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
