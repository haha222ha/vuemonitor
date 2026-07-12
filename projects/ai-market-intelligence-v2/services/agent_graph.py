# -*- coding: utf-8 -*-
"""
LangGraph 多 Agent 编排 + 真 LLM 对接（OpenAI 兼容 API）。

图结构：market → data → risk → ops → ceo（串行，便于审计；Phase 2 可改并行）

无 API Key 时降级 run_agents_mock。
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, TypedDict

from services.ai_orchestrator import InsightReport, run_agents_mock
from services.agent_validate import AgentOutputError, validate_agent_output
from services.llm_client import LLMError, chat_json_with_usage, describe_config, llm_configured
from services.metric_engine import metrics_fingerprint

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "prompts" / "agents.yaml"

# Prompt 版本号(变更 prompt 后需递增,使缓存失效)
PROMPT_VERSION = "agent-v1"

# 进程内缓存:key = "{prompt_version}:{metrics_fingerprint}" → report dict
_REPORT_CACHE: dict[str, dict[str, Any]] = {}


class AgentState(TypedDict, total=False):
    metrics: dict[str, Any]
    market: dict[str, Any]
    data: dict[str, Any]
    risk: dict[str, Any]
    ops: dict[str, Any]
    ceo: dict[str, Any]
    errors: list[str]
    llm_provider: str
    llm_usage: list[dict[str, Any]]


def _load_prompts() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return _prompts_fallback()
    if not PROMPTS_PATH.is_file():
        return _prompts_fallback()
    raw = PROMPTS_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    shared = data.get("shared_rules") or ""
    agents = data.get("agents") or {}
    for cfg in agents.values():
        if isinstance(cfg, dict) and "system" in cfg:
            cfg["system"] = str(cfg["system"]).replace("{shared_rules}", shared)
    return agents


def _prompts_fallback() -> dict[str, Any]:
    base = "你是市场研究顾问。仅基于类目级指标JSON分析。禁止商品ID店铺名链接。输出JSON。"
    return {
        "market": {"system": base + ' 输出{"trend_summary":"","market_drivers":[]}'},
        "data": {"system": base + ' 输出{"metric_interpretation":"","data_highlights":[]}'},
        "risk": {"system": base + ' 输出{"risk_assessment":"","risk_level":"中"}'},
        "ops": {"system": base + ' 输出{"action_plan":{"enter":false,"category_focus":"","price_band":"","content_format":[],"timeline_days":14}}'},
        "ceo": {"system": base + ' 输出{"executive_summary":"","opportunity_stars":3,"confidence":0.7,"verdict":"继续观察"}'},
    }


def _metrics_prompt(metrics: dict[str, Any]) -> str:
    # top_keywords 不进入 Prompt:其来源为商品标题分词,可能含可识别片段(合规 §8.1)
    allowed = {
        k: metrics[k]
        for k in (
            "report_date", "category", "sub_category", "window_days",
            "growth_rate_pct", "competition_index", "blue_ocean_score",
            "heat_score", "new_product_score", "lifecycle_stage",
            "season_score", "price_band", "trend_label",
        )
        if k in metrics
    }
    return json.dumps(allowed, ensure_ascii=False)


def _run_agent(
    name: str,
    prompts: dict,
    metrics: dict,
    prior: dict | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    cfg = prompts.get(name) or {}
    system = cfg.get("system") or ""
    user = f"类目级指标：\n{_metrics_prompt(metrics)}"
    if prior:
        user += f"\n\n前序分析摘要：\n{json.dumps(prior, ensure_ascii=False)[:2000]}"
    parsed, usage = chat_json_with_usage(system, user, agent=name)
    validated = validate_agent_output(name, parsed)
    return validated, {
        "agent": name,
        "model": usage.model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    }


def _parallel_first_pass(
    prompts: dict,
    metrics: dict,
) -> tuple[dict, dict, dict, list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    results: dict[str, dict] = {}
    usage_log: list[dict[str, Any]] = []

    def task(name: str):
        return name, *_run_agent(name, prompts, metrics)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(task, n): n for n in ("market", "data", "risk")}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                _, data, usage = fut.result()
                results[name] = data
                if usage:
                    usage_log.append(usage)
            except Exception as e:
                errors.append(f"{name}:{e}")
                results[name] = {}
    return (
        results.get("market", {}),
        results.get("data", {}),
        results.get("risk", {}),
        errors,
        usage_log,
    )


def _sum_usage(usage_log: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "calls": len(usage_log),
        "prompt_tokens": sum(u.get("prompt_tokens") or 0 for u in usage_log),
        "completion_tokens": sum(u.get("completion_tokens") or 0 for u in usage_log),
        "agents": usage_log,
    }


def _build_graph(prompts: dict):
    from langgraph.graph import END, START, StateGraph

    def node_parallel(state: AgentState) -> AgentState:
        m, d, r, errs, ulog = _parallel_first_pass(prompts, state["metrics"])
        errors = list(state.get("errors") or []) + errs
        usage = list(state.get("llm_usage") or []) + ulog
        return {"market": m, "data": d, "risk": r, "errors": errors, "llm_usage": usage}

    def node_ops(state: AgentState) -> AgentState:
        errors = list(state.get("errors") or [])
        usage = list(state.get("llm_usage") or [])
        prior = {"market": state.get("market"), "data": state.get("data"), "risk": state.get("risk")}
        try:
            ops, u = _run_agent("ops", prompts, state["metrics"], prior)
            if u:
                usage.append(u)
        except Exception as e:
            errors.append(f"ops:{e}")
            ops = {}
        return {"ops": ops, "errors": errors, "llm_usage": usage}

    def node_ceo(state: AgentState) -> AgentState:
        errors = list(state.get("errors") or [])
        usage = list(state.get("llm_usage") or [])
        prior = {
            "market": state.get("market"),
            "data": state.get("data"),
            "risk": state.get("risk"),
            "ops": state.get("ops"),
        }
        ceo: dict[str, Any] = {}
        try:
            ceo, u = _run_agent("ceo", prompts, state["metrics"], prior)
            if u:
                usage.append(u)
        except Exception as e:
            errors.append(f"ceo:{e}")
            ceo = {}
        # ceo 为最低成功集：失败则整链降级
        if not ceo.get("executive_summary"):
            errors.append("ceo:missing_executive_summary")
        return {"ceo": ceo, "errors": errors, "llm_usage": usage}

    g = StateGraph(AgentState)
    g.add_node("parallel", node_parallel)
    g.add_node("ops", node_ops)
    g.add_node("ceo", node_ceo)
    g.add_edge(START, "parallel")
    g.add_edge("parallel", "ops")
    g.add_edge("ops", "ceo")
    g.add_edge("ceo", END)
    return g.compile()


def _state_to_report(state: AgentState, metrics: dict[str, Any]) -> InsightReport:
    market = state.get("market") or {}
    data = state.get("data") or {}
    risk = state.get("risk") or {}
    ops = state.get("ops") or {}
    ceo = state.get("ceo") or {}

    trend_summary = market.get("trend_summary") or ""
    metric_interpretation = data.get("metric_interpretation") or ""
    risk_assessment = risk.get("risk_assessment") or ""
    action_plan = ops.get("action_plan") or {}
    executive_summary = ceo.get("executive_summary") or ""
    stars = max(1, min(5, int(ceo.get("opportunity_stars") or 3)))
    conf_val = ceo.get("confidence")
    raw_conf = float(conf_val) if conf_val is not None else 0.7
    # 若 LLM 返回 >1 的值(如 82 表示 82%),自动归一化到 [0, 1]
    confidence = max(0.0, min(1.0, raw_conf / 100 if raw_conf > 1 else raw_conf))
    verdict = ceo.get("verdict") or "继续观察"
    growth = float(metrics.get("growth_rate_pct") or 0)
    # 竞争度从 competition_index 映射,而非 risk_level(风险≠竞争)
    comp_idx = int(metrics.get("competition_index") or 50)
    comp = "低" if comp_idx < 40 else "中" if comp_idx < 70 else "高"

    pages = [
        {"page": 1, "title": "本周趋势评分", "stars": stars},
        {"page": 2, "title": "AI 总结", "body": trend_summary},
        {"page": 3, "title": "市场机会", "growth": f"{growth:.0f}%", "competition": comp, "stars": stars},
        {
            "page": 4,
            "title": "AI 建议",
            "focus": action_plan.get("category_focus") or metrics.get("category"),
            "price": action_plan.get("price_band") or metrics.get("price_band"),
            "format": "、".join(action_plan.get("content_format") or [])[:80],
        },
        {"page": 5, "title": "风险提示", "body": risk_assessment},
        {"page": 6, "title": "总结", "verdict": verdict, "action": f"置信度 {confidence:.0%}"},
    ]
    if state.get("errors"):
        executive_summary += f"（Agent 部分降级: {len(state['errors'])}）"

    return InsightReport(
        executive_summary=executive_summary,
        trend_summary=trend_summary,
        metric_interpretation=metric_interpretation,
        action_plan=action_plan,
        risk_assessment=risk_assessment,
        opportunity_stars=stars,
        confidence=confidence,
        pages=pages,
        llm_meta={
            "prompt_version": PROMPT_VERSION,
            "usage": _sum_usage(state.get("llm_usage") or []),
            "errors": state.get("errors") or [],
        },
    )


def os_fallback_mock_enabled() -> bool:
    import os
    v = (os.environ.get("INSIGHT_LLM_FALLBACK_MOCK") or "1").strip().lower()
    return v not in ("0", "false", "no")


def run_agents(metrics: dict[str, Any], *, force_mock: bool = False) -> InsightReport:
    if force_mock:
        return run_agents_mock(metrics)
    if not llm_configured():
        return run_agents_mock(metrics)

    # 缓存命中检查(相同指标 + prompt 版本 → 相同报告,Master Spec §8.5)
    cache_key = f"{PROMPT_VERSION}:{metrics_fingerprint(metrics)}"
    if cache_key in _REPORT_CACHE:
        return InsightReport(**_REPORT_CACHE[cache_key])

    try:
        prompts = _load_prompts()
        cfg = describe_config()
        graph = _build_graph(prompts)
        final_state = graph.invoke({
            "metrics": metrics,
            "errors": [],
            "llm_provider": cfg.get("provider") or "packy_deepseek",
            "llm_usage": [],
        })
        report = _state_to_report(final_state, metrics)
        if not report.executive_summary and not report.trend_summary:
            return run_agents_mock(metrics)
        if any(str(e).startswith("ceo:") for e in (final_state.get("errors") or [])):
            if os_fallback_mock_enabled():
                return run_agents_mock(metrics)
            raise LLMError("CEO Agent 未成功完成")
        _REPORT_CACHE[cache_key] = report.to_internal_dict()
        return report
    except (LLMError, ImportError, AgentOutputError):
        if os_fallback_mock_enabled():
            return run_agents_mock(metrics)
        raise
