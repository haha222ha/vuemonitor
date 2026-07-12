# -*- coding: utf-8 -*-
"""
Shadow 情报日报生成 — 合并目标: xhs-cloud/cloud_deploy/scripts/cloud_insight_report.py

用法:
  python cloud_insight_report.py --date 2026-07-12
  python cloud_insight_report.py --date 2026-07-12 --shadow   # 不写入 report_archives
"""
from __future__ import annotations

import argparse
import os
import sys

CRAWLER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if CRAWLER_ROOT not in sys.path:
    sys.path.insert(0, CRAWLER_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--shadow", action="store_true", help="仅写 data/insight_shadow，不发布")
    args = ap.parse_args()

    # Phase 2: 从 PG 读 raw_product_snapshots → insight_metrics → AI → HTML
    # 实验室参考: projects/ai-market-intelligence-v2/services/*
    out = os.path.join(
        os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud"),
        "data",
        "insight_shadow" if args.shadow else "report_archives",
        f"insight_{args.date.replace('-', '')}",
    )
    os.makedirs(out, exist_ok=True)
    print(f"TODO: wire metric_engine + insight_ai → {out}")
    print("Copy implementation from projects/ai-market-intelligence-v2/services/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
