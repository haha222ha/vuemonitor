# -*- coding: utf-8 -*-
"""实验室权益 — 桥接 cloud-stubs/entitlements_v2.py"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "entitlements_v2",
    _ROOT / "cloud-stubs" / "entitlements_v2.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_mod)

merge_entitlements = _mod.merge_entitlements
can_insight_generate = _mod.can_insight_generate
can_insight_compare = _mod.can_insight_compare
can_insight_timeline = _mod.can_insight_timeline
can_insight_workflow = _mod.can_insight_workflow
can_insight_pdf = _mod.can_insight_pdf
llm_token_budget = _mod.llm_token_budget
portal_route = _mod.portal_route
PLAN_ENTITLEMENT_DEFAULTS = _mod.PLAN_ENTITLEMENT_DEFAULTS
EXPERIENCE_ENTITLEMENTS_INSIGHT = _mod.EXPERIENCE_ENTITLEMENTS_INSIGHT
EXPERIENCE_ENTITLEMENTS_V2_ONLY = _mod.EXPERIENCE_ENTITLEMENTS_V2_ONLY
PREVIEW_ENTITLEMENTS_LEGACY = _mod.PREVIEW_ENTITLEMENTS_LEGACY
LEGACY_ONLY_ENTITLEMENTS = _mod.LEGACY_ONLY_ENTITLEMENTS
ENTITLEMENT_FIELD_GUIDE = _mod.ENTITLEMENT_FIELD_GUIDE
