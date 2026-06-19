# -*- coding: utf-8 -*-
"""会员授权码管理 CLI。

用法:
  cd /opt/xhs-cloud
  export PYTHONPATH=/opt/xhs-cloud
  ./venv/bin/python cloud_deploy/scripts/manage_auth_codes.py generate --plan monthly --days 30 --count 5
  ./venv/bin/python cloud_deploy/scripts/manage_auth_codes.py list
"""
from __future__ import annotations

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()


def main() -> None:
    from cloud_deploy.cloud_api.database import generate_auth_codes, init_db, list_auth_codes

    init_db()

    ap = argparse.ArgumentParser(description="选品会员授权码管理")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="生成授权码")
    g.add_argument("--plan", default="monthly", choices=["weekly", "monthly", "yearly"])
    g.add_argument("--days", type=int, default=30, help="会员有效天数")
    g.add_argument("--count", type=int, default=1, help="生成数量")
    g.add_argument("--max-activations", type=int, default=1, help="每码最多激活次数")
    g.add_argument("--note", default="", help="备注（渠道/订单号）")

    sub.add_parser("list", help="列出最近授权码")

    args = ap.parse_args()

    if args.cmd == "generate":
        codes = generate_auth_codes(
            count=args.count,
            plan_code=args.plan,
            duration_days=args.days,
            max_activations=args.max_activations,
            note=args.note,
        )
        print(f"已生成 {len(codes)} 个授权码（{args.plan} / {args.days}天）:")
        for c in codes:
            print(c)
    elif args.cmd == "list":
        items = list_auth_codes(100)
        if not items:
            print("暂无授权码")
            return
        for it in items:
            print(
                f"{it['code']}  {it['plan_label']}  {it['duration_days']}天  "
                f"已用{it['current_activations']}/{it['max_activations']}  "
                f"{it['status']}  {it['note']}"
            )


if __name__ == "__main__":
    main()
