# -*- coding: utf-8 -*-
"""L0 预生成 — 真 LLM 单轮报告（T0 降本：1 次调用/类目；失败降级 mock）。"""
from __future__ import annotations

import json
import os
from typing import Any

from cloud_deploy.reporting.insight_ai_mock import InsightReport, run_agents_mock, _stars
from cloud_deploy.reporting.insight_llm_client import LLMError, chat_json_with_usage, llm_configured

# 进程内当日 token 计数（Shadow timer 单进程足够）
_daily_tokens: dict[str, int] = {}


def _budget_exceeded(budget: int) -> bool:
    from datetime import date

    day = date.today().isoformat()
    return _daily_tokens.get(day, 0) >= budget


def _record_usage(usage) -> None:
    from datetime import date

    day = date.today().isoformat()
    total = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
    _daily_tokens[day] = _daily_tokens.get(day, 0) + total


def should_use_llm() -> bool:
    flag = os.environ.get("INSIGHT_USE_LLM", "").strip().lower() in ("1", "true", "yes")
    return flag and llm_configured()


def _metrics_prompt(metrics: dict[str, Any]) -> str:
    keys = (
        "report_date",
        "category",
        "sub_category",
        "window_days",
        "growth_rate_pct",
        "competition_index",
        "blue_ocean_score",
        "heat_score",
        "new_product_score",
        "lifecycle_stage",
        "season_score",
        "price_band",
        "trend_label",
        "sample_size",
        "trend_7d",
        "price_distribution",
        "similar_categories",
        "user_context",
    )
    allowed = {k: metrics[k] for k in keys if k in metrics}
    return json.dumps(allowed, ensure_ascii=False)


def _build_pages(metrics: dict[str, Any], parsed: dict[str, Any], stars: int) -> list[dict[str, Any]]:
    cat = metrics.get("category") or "目标类目"
    growth = float(metrics.get("growth_rate_pct") or 0)
    comp = int(metrics.get("competition_index") or 50)
    band = metrics.get("price_band") or "待定"
    trend_body = parsed.get("trend_summary") or ""
    risk = parsed.get("risk_assessment") or ""
    action = parsed.get("action_plan") or {}
    return [
        {"page": 1, "title": "本周趋势评分", "stars": stars},
        {"page": 2, "title": "AI 总结", "body": trend_body},
        {
            "page": 3,
            "title": "市场机会",
            "growth": f"{growth:.0f}%",
            "competition": "低" if comp < 40 else "中" if comp < 70 else "高",
            "stars": stars,
        },
        {"page": 4, "title": "AI 建议", "focus": cat, "price": band, "action": action},
        {"page": 5, "title": "风险提示", "body": risk},
        {
            "page": 6,
            "title": "总结",
            "verdict": parsed.get("verdict") or ("适合进入" if action.get("enter") else "继续观察"),
        },
    ]


def run_agents_llm(metrics: dict[str, Any], *, budget_tokens: int = 200_000) -> InsightReport:
    if not should_use_llm():
        return run_agents_mock(metrics)
    if _budget_exceeded(budget_tokens):
        print("[insight-ai-llm] daily budget exceeded, fallback mock", flush=True)
        return run_agents_mock(metrics)

    system = (
        "你是电商市场研究顾问。仅基于类目级聚合指标 JSON 分析，禁止引用具体商品 ID、店铺名、链接。"
        "输出 JSON 字段：executive_summary, trend_summary, metric_interpretation, "
        "action_plan(含 enter/category_focus/price_band/content_format/timeline_days), "
        "risk_assessment, opportunity_stars(1-5整数), confidence(0-1), verdict。"
    )
    user = f"类目级指标：\n{_metrics_prompt(metrics)}"

    try:
        parsed, usage = chat_json_with_usage(system, user, temperature=0.25)
        _record_usage(usage)
    except LLMError as e:
        print(f"[insight-ai-llm] LLM failed, fallback mock: {e}", flush=True)
        return run_agents_mock(metrics)

    blue = int(metrics.get("blue_ocean_score") or 50)
    stars = int(parsed.get("opportunity_stars") or _stars(blue))
    stars = max(1, min(5, stars))
    confidence = float(parsed.get("confidence") or 0.7)
    confidence = max(0.0, min(1.0, confidence))

    action = parsed.get("action_plan")
    if not isinstance(action, dict):
        action = {"enter": False, "category_focus": metrics.get("category"), "timeline_days": 14}

    return InsightReport(
        executive_summary=str(parsed.get("executive_summary") or ""),
        trend_summary=str(parsed.get("trend_summary") or ""),
        metric_interpretation=str(parsed.get("metric_interpretation") or ""),
        action_plan=action,
        risk_assessment=str(parsed.get("risk_assessment") or ""),
        opportunity_stars=stars,
        confidence=confidence,
        pages=_build_pages(metrics, parsed, stars),
    )


def run_agents_auto(metrics: dict[str, Any], *, budget_tokens: int = 200_000) -> InsightReport:
    """INSIGHT_USE_LLM=1 且 Key 已配置时走 LLM，否则 mock。"""
    if should_use_llm():
        return run_agents_llm(metrics, budget_tokens=budget_tokens)
    return run_agents_mock(metrics)
