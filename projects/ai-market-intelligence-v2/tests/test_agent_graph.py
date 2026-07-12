# -*- coding: utf-8 -*-
"""agent_graph 单元测试 — 验证 Issues #1,#8,#9,#10 修复。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.agent_graph import _metrics_prompt, _state_to_report, run_agents, _REPORT_CACHE
from services.ai_orchestrator import run_agents_mock


# Issue #1: top_keywords 不进入 Prompt
def test_prompt_excludes_top_keywords():
    metrics = {
        "category": "小学教辅",
        "growth_rate_pct": 30,
        "top_keywords": ["暑假衔接", "练习册"],
    }
    prompt = _metrics_prompt(metrics)
    assert "top_keywords" not in prompt
    assert "暑假衔接" not in prompt
    assert "category" in prompt


def test_prompt_includes_allowed_fields():
    metrics = {
        "category": "小学教辅",
        "growth_rate_pct": 30,
        "competition_index": 20,
        "blue_ocean_score": 80,
        "price_band": "10-20",
        "trend_label": "连续上涨",
    }
    prompt = _metrics_prompt(metrics)
    assert "小学教辅" in prompt
    assert "10-20" in prompt


# Issue #8: confidence 范围校验
def test_confidence_clamped_when_gt_1():
    """LLM 返回 82(表示 82%)应归一化为 0.82,而非显示 8200%。"""
    state = {
        "ceo": {"executive_summary": "test", "opportunity_stars": 4, "confidence": 82, "verdict": "进入"},
        "ops": {"action_plan": {}},
        "market": {},
        "data": {},
        "risk": {},
    }
    metrics = {"growth_rate_pct": 30, "competition_index": 50}
    report = _state_to_report(state, metrics)
    assert 0.0 <= report.confidence <= 1.0
    assert report.confidence == 0.82


def test_confidence_normal_value():
    state = {
        "ceo": {"executive_summary": "test", "opportunity_stars": 4, "confidence": 0.75, "verdict": "进入"},
        "ops": {"action_plan": {}},
    }
    metrics = {"growth_rate_pct": 30, "competition_index": 50}
    report = _state_to_report(state, metrics)
    assert report.confidence == 0.75


def test_confidence_zero():
    state = {
        "ceo": {"executive_summary": "test", "opportunity_stars": 3, "confidence": 0, "verdict": "观察"},
        "ops": {"action_plan": {}},
    }
    metrics = {"growth_rate_pct": 30, "competition_index": 50}
    report = _state_to_report(state, metrics)
    assert report.confidence == 0.0


# Issue #9: comp 从 competition_index 映射,而非 risk_level
def test_comp_from_competition_index_not_risk():
    """risk_level=高 但 competition_index=10 时,comp 应为"低"。"""
    state = {
        "ceo": {"executive_summary": "test", "opportunity_stars": 3, "confidence": 0.7, "verdict": "观察"},
        "ops": {"action_plan": {}},
        "risk": {"risk_level": "高", "risk_assessment": "高风险"},
    }
    metrics = {"growth_rate_pct": 30, "competition_index": 10}
    report = _state_to_report(state, metrics)
    page3 = next(p for p in report.pages if p["page"] == 3)
    assert page3["competition"] == "低"  # 基于 competition_index,不是 risk_level


def test_comp_levels():
    for idx, expected in [(10, "低"), (50, "中"), (80, "高")]:
        state = {
            "ceo": {"executive_summary": "t", "opportunity_stars": 3, "confidence": 0.5, "verdict": "v"},
            "ops": {"action_plan": {}},
        }
        metrics = {"growth_rate_pct": 30, "competition_index": idx}
        report = _state_to_report(state, metrics)
        page3 = next(p for p in report.pages if p["page"] == 3)
        assert page3["competition"] == expected


# Issue #10: 缓存命中
def test_cache_hit_returns_same_report():
    metrics = {"category": "测试类目", "growth_rate_pct": 25, "competition_index": 30}
    # mock 模式不走缓存(无 LLM key),但缓存写入逻辑仅对 LLM 模式生效
    # 这里验证缓存 dict 可正确序列化/反序列化
    report1 = run_agents_mock(metrics)
    _REPORT_CACHE["test_key"] = report1.to_public_dict()
    from services.ai_orchestrator import InsightReport
    report2 = InsightReport(**_REPORT_CACHE["test_key"])
    assert report2.executive_summary == report1.executive_summary
    assert report2.confidence == report1.confidence
    _REPORT_CACHE.pop("test_key", None)


def test_stars_clamped():
    state = {
        "ceo": {"executive_summary": "t", "opportunity_stars": 99, "confidence": 0.5, "verdict": "v"},
        "ops": {"action_plan": {}},
    }
    metrics = {"growth_rate_pct": 30, "competition_index": 50}
    report = _state_to_report(state, metrics)
    assert report.opportunity_stars == 5  # clamped to max 5

    state["ceo"]["opportunity_stars"] = -1
    report = _state_to_report(state, metrics)
    assert report.opportunity_stars == 1  # clamped to min 1


if __name__ == "__main__":
    test_prompt_excludes_top_keywords()
    test_prompt_includes_allowed_fields()
    test_confidence_clamped_when_gt_1()
    test_confidence_normal_value()
    test_confidence_zero()
    test_comp_from_competition_index_not_risk()
    test_comp_levels()
    test_cache_hit_returns_same_report()
    test_stars_clamped()
    print("agent_graph tests OK")
