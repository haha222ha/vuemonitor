# -*- coding: utf-8 -*-
"""Standard vs Pro 权益差异化（G1 验收）"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_standard_no_compare_or_pdf():
    ent = _load("entitlements_v2", "cloud-stubs/entitlements_v2.py")
    std = ent.merge_entitlements({"plan_code": "insight_monthly", "insight_enabled": True})
    pro = ent.merge_entitlements({"plan_code": "insight_pro_monthly", "insight_enabled": True})
    assert std["insight_compare"] is False
    assert std["insight_pdf_export"] is False
    assert std["insight_workflow"] is False
    assert std["insight_timeline_days"] == 0
    assert pro["insight_compare"] is True
    assert pro["insight_pdf_export"] is True
    assert pro["insight_workflow"] is True
    assert pro["insight_timeline_days"] == 30


def test_llm_token_budget_by_tier():
    ent = _load("entitlements_v2", "cloud-stubs/entitlements_v2.py")
    std = ent.merge_entitlements({"plan_code": "insight_monthly"})
    team = ent.merge_entitlements({"plan_code": "insight_team_monthly"})
    assert ent.llm_token_budget(std) == 20_000
    assert ent.llm_token_budget(team) == 150_000
    assert team["insight_llm_tokens_per_day"] > std["insight_llm_tokens_per_day"]


def test_payment_plans_standard_template():
    pp = _load("payment_plans_v2_patch", "cloud-stubs/payment_plans_v2_patch.py")
    tpl = pp.INSIGHT_PLAN_BY_CODE["insight_monthly"]["entitlements_template"]
    assert tpl["insight_compare"] is False
    assert tpl["insight_pdf_export"] is False
    assert tpl.get("insight_llm_tokens_per_day") == 20_000
