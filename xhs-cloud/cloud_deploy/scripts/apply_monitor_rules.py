# -*- coding: utf-8
"""运行监控池规则引擎。"""
from __future__ import annotations

import argparse
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)


def run(goods_id: str = "") -> dict:
    from cloud_deploy.scripts.bootstrap_env import bootstrap

    bootstrap()
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.rules.rule_engine import evaluate_rules

    init_db()
    conn = _conn()
    try:
        result = evaluate_rules(conn, goods_id or None)
    finally:
        conn.close()
    print(f"[apply-rules] {result}", flush=True)
    return result


def main():
    ap = argparse.ArgumentParser(description="监控池规则评估")
    ap.add_argument("--goods-id", default="")
    args = ap.parse_args()
    run(args.goods_id)


if __name__ == "__main__":
    main()
