# -*- coding: utf-8 -*-
"""从 plans.yaml / persona 解析实验室权益"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from services.entitlements_lab import merge_entitlements
from services.lab_session import get_persona_config

PLANS_PATH = Path(__file__).resolve().parents[1] / "config" / "plans.yaml"


def _load_plans_config() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    if not PLANS_PATH.is_file():
        return {}
    return yaml.safe_load(PLANS_PATH.read_text(encoding="utf-8")) or {}


def entitlements_for_plan(plan_id: str) -> dict[str, Any]:
    cfg = _load_plans_config()
    plan = (cfg.get("plans") or {}).get(plan_id) or {}
    ent = dict(plan.get("entitlements") or {})
    ent["plan_code"] = plan_id
    ent.setdefault("insight_enabled", plan_id.startswith("insight_"))
    ent.setdefault("insight_only", plan_id.startswith("insight_"))
    ent.setdefault("legacy_zip_enabled", False)
    return merge_entitlements(ent, plan_id)


def current_entitlements(plan_id: str | None = None) -> dict[str, Any]:
    persona = get_persona_config()
    pid = plan_id or persona.get("plan_id") or "insight_pro_monthly"
    raw = dict(persona.get("entitlements") or {})
    if persona.get("plan_id") == pid and raw:
        raw.setdefault("plan_code", pid)
        return merge_entitlements(raw, pid)
    return entitlements_for_plan(pid)
