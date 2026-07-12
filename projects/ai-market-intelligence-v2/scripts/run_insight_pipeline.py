# -*- coding: utf-8 -*-
"""
实验室管道：mock/PG 内部商品 → 指标 → AI 报告 → HTML

用法:
  cd projects/ai-market-intelligence-v2
  python scripts/run_insight_pipeline.py --date 2026-07-12
  python scripts/run_insight_pipeline.py --source pg   # 需 INSIGHT_PG_DSN
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataclasses import asdict

from services.audit_log import log_publish
from services.env_loader import load_lab_env
from services.agent_graph import run_agents
from services.compliance_gate import assert_publishable
from services.llm_client import describe_config
from services.metric_engine import aggregate_items_to_insights
from services.metric_engine_pg import load_items as load_items_pg, pg_configured
from services.report_builder import render_insight_html, write_insight_bundle
from samples.mock_items import MOCK_ITEMS


def _resolve_items(report_date: str, source: str) -> tuple[list[dict], str]:
    if source == "pg":
        if not pg_configured():
            raise SystemExit("INSIGHT_PG_DSN 未配置，无法 --source pg")
        rows = load_items_pg(report_date)
        if not rows:
            raise SystemExit(f"PG 无 {report_date} 数据")
        return rows, "pg"
    return MOCK_ITEMS, "sample"


def main() -> int:
    load_lab_env(ROOT)
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-07-12")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--source", default=os.environ.get("INSIGHT_DATA_SOURCE", "sample"), choices=("sample", "pg"))
    ap.add_argument("--k-min", type=int, default=int(os.environ.get("INSIGHT_K_ANONYMITY", "5")))
    args = ap.parse_args()

    items, data_source = _resolve_items(args.date, args.source)
    out_root = Path(args.out)
    insights = aggregate_items_to_insights(args.date, items)
    if not insights:
        print("no insights")
        return 1

    # 为每个类目生成报告(不再只处理 top 1)
    summaries = []
    for insight in insights:
        internal_metrics = asdict(insight)
        public_metrics = insight.to_public_dict()
        report_obj = run_agents(public_metrics)
        report = report_obj.to_public_dict()
        html = render_insight_html(report, public_metrics, llm_meta=report_obj.llm_meta)
        assert_publishable(internal_metrics, report, html, k_min=args.k_min)
        bundle = write_insight_bundle(
            out_root,
            args.date,
            insight.category,
            html,
            {
                "metrics": public_metrics,
                "report": report,
                "meta": {
                    "data_source": data_source,
                    "llm": describe_config(),
                    "llm_usage": report_obj.llm_meta.get("usage"),
                },
            },
        )

        log_publish(
            report_date=args.date,
            category=insight.category,
            llm_meta={**report_obj.llm_meta, "provider": describe_config()},
            k_min=args.k_min,
            sample_size=insight.sample_size,
        )

        summaries.append({
            "category": insight.category,
            "metrics": public_metrics,
            "report": report,
            "bundle": str(bundle),
        })
        print(f"OK bundle={bundle}")

    summary_path = out_root / "latest.json"
    summary_path.write_text(
        json.dumps(
            {
                "summaries": summaries,
                "data_source": data_source,
                "llm_config": describe_config(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"OK summary={summary_path} ({len(summaries)} categories)")
    print(f"OK llm={describe_config().get('provider')} model={describe_config().get('default_model')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
