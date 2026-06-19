# -*- coding: utf-8 -*-
"""云端 ⑥ 挂机补缺守护进程入口（无 GUI）。"""
from __future__ import annotations

import json
import os
import signal
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_DEPLOY = os.path.dirname(SCRIPT_DIR)
CRAWLER_ROOT = os.path.dirname(CLOUD_DEPLOY)
sys.path.insert(0, CRAWLER_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap


def _load_config() -> dict:
    cfg_path = os.environ.get(
        "XHS_DAEMON_CONFIG",
        os.path.join(CLOUD_DEPLOY, "config", "daemon.json"),
    )
    cfg = {}
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["web_detail_concurrency"] = int(
        os.environ.get("XHS_DAEMON_CONCURRENCY", cfg.get("web_detail_concurrency", 2))
    )
    cfg["batch_size"] = int(os.environ.get("XHS_DAEMON_BATCH_SIZE", cfg.get("batch_size", 400)))
    cfg["web_cooldown_seconds"] = int(
        os.environ.get("XHS_DAEMON_COOLDOWN_SEC", cfg.get("web_cooldown_seconds", 120))
    )
    return cfg


def main():
    bootstrap()

    from xhs_full_sold_daemon import start_full_sold_daemon, stop_full_sold_daemon

    cfg = _load_config()
    print(f"[xhs-daemon] 启动配置: {cfg}", flush=True)

    def _on_sig(_sig, _frame):
        print("[xhs-daemon] 收到停止信号", flush=True)
        stop_full_sold_daemon()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)

    start_full_sold_daemon(config=cfg, log_func=print, web_log_func=print)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
