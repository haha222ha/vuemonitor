# -*- coding: utf-8
"""云端监控守护入口（PG 写入，不调用 xhs_full_sold_daemon）。"""
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
    cfg["batch_size"] = int(os.environ.get("XHS_DAEMON_BATCH_SIZE", cfg.get("batch_size", 20)))
    cfg["web_cooldown_seconds"] = int(
        os.environ.get("XHS_DAEMON_COOLDOWN_SEC", cfg.get("web_cooldown_seconds", 120))
    )
    return cfg


def main():
    bootstrap()
    from cloud_deploy.daemon.cloud_daemon import start_cloud_daemon

    cfg = _load_config()
    daemon = start_cloud_daemon(cfg, print)
    print(f"[xhs-daemon] cloud PG 模式: {cfg}", flush=True)

    def _on_sig(_sig, _frame):
        print("[xhs-daemon] 停止", flush=True)
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
