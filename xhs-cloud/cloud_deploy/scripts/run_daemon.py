# -*- coding: utf-8
"""云端监控守护入口。

模式（XHS_DAEMON_MODE）:
  full_sold  — ⑥补缺挂机（默认，对齐主面板，写 PG）
  lite       — 简化版 cloud_daemon（仅 fetch + record_cloud_scan）
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap


def _load_config() -> dict:
    cfg_path = os.environ.get(
        "XHS_DAEMON_CONFIG",
        os.path.join(CLOUD_ROOT, "cloud_deploy", "config", "daemon.json"),
    )
    cfg = {}
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["web_detail_concurrency"] = int(
        os.environ.get("XHS_DAEMON_CONCURRENCY", cfg.get("web_detail_concurrency", 2))
    )
    cfg["batch_size"] = int(os.environ.get("XHS_DAEMON_BATCH_SIZE", cfg.get("batch_size", 400)))
    cfg["shop_engine"] = os.environ.get("XHS_DAEMON_ENGINE", cfg.get("shop_engine", "api"))
    cfg["seed_batch_size"] = int(
        os.environ.get("XHS_DAEMON_SEED_BATCH_SIZE", cfg.get("seed_batch_size", 0))
    )
    cfg["web_cooldown_seconds"] = int(
        os.environ.get("XHS_DAEMON_COOLDOWN_SEC", cfg.get("web_cooldown_seconds", 0))
    )
    env_full = os.environ.get("XHS_DAEMON_FULL_POOL", "").strip().lower()
    if env_full:
        full_pool = env_full in ("1", "true", "yes")
    else:
        full_pool = bool(cfg.get("full_pool"))
    if full_pool:
        cfg["full_pool"] = True
        cfg["skip_today"] = False
        cfg["min_sold"] = 0
        os.environ.setdefault("XHS_PG_SEED_MODE", "full")
    if "XHS_DAEMON_SKIP_TODAY" in os.environ:
        cfg["skip_today"] = os.environ["XHS_DAEMON_SKIP_TODAY"].strip().lower() in (
            "1",
            "true",
            "yes",
        )
    if "XHS_DAEMON_MIN_SOLD" in os.environ:
        cfg["min_sold"] = int(os.environ["XHS_DAEMON_MIN_SOLD"])
    elif "min_sold" in cfg:
        cfg["min_sold"] = int(cfg["min_sold"])
    return cfg


def _run_lite(cfg: dict) -> None:
    from cloud_deploy.daemon.cloud_daemon import start_cloud_daemon

    daemon = start_cloud_daemon(cfg, print)
    print(f"[xhs-daemon] lite 模式: {cfg}", flush=True)

    def _on_sig(_sig, _frame):
        print("[xhs-daemon] 停止", flush=True)
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    while True:
        time.sleep(60)


def main():
    bootstrap()
    mode = os.environ.get("XHS_DAEMON_MODE", "full_sold").strip().lower()
    cfg = _load_config()
    if mode == "lite":
        _run_lite(cfg)
    else:
        from cloud_deploy.daemon.crawler_bridge import run_full_sold_daemon_loop

        run_full_sold_daemon_loop(cfg)


if __name__ == "__main__":
    main()
