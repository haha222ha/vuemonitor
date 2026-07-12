# -*- coding: utf-8 -*-
"""
实验室用户分群 — 模拟新会员 / 老会员预览 / 纯 Legacy（REQ-RT-005）。

生产环境由 JWT + memberships + auth_codes.note 替代，本模块仅 Lab。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
SESSION_PATH = _ROOT / "output" / "lab_session.json"
SESSIONS_DIR = _ROOT / "output" / "sessions"

# 与 20-REQUIREMENTS-V2.2-ROLLOUT.md 分群一致
PERSONAS: dict[str, dict[str, Any]] = {
    "insight_standard": {
        "label": "新会员 · V2 Standard",
        "plan_id": "insight_monthly",
        "plan_code": "insight_monthly",
        "portal_route": "insight_only",
        "entitlements": {
            "insight_enabled": True,
            "insight_only": True,
            "insight_categories_per_day": 3,
            "insight_compare": False,
            "insight_timeline_days": 0,
            "insight_workflow": False,
            "insight_pdf_export": False,
            "insight_llm_tokens_per_day": 20_000,
            "legacy_zip_enabled": False,
        },
    },
    "insight_pro": {
        "label": "新会员 · V2 Pro",
        "plan_id": "insight_pro_monthly",
        "plan_code": "insight_pro_monthly",
        "portal_route": "insight_only",
        "entitlements": {
            "insight_enabled": True,
            "insight_only": True,
            "insight_categories_per_day": 5,
            "insight_compare": True,
            "insight_timeline_days": 30,
            "insight_pdf_export": True,
            "insight_workflow": True,
            "insight_llm_tokens_per_day": 40_000,
            "legacy_zip_enabled": False,
        },
    },
    "legacy_preview": {
        "label": "老会员 · V2 预览",
        "plan_id": "monthly",
        "plan_code": "monthly",
        "portal_route": "legacy_with_preview",
        "expires_at": "2026-08-15T00:00:00+00:00",
        "entitlements": {
            "plan_code": "monthly",
            "insight_enabled": True,
            "insight_preview": True,
            "insight_categories_per_day": 1,
            "insight_compare": False,
            "insight_timeline_days": 7,
            "insight_pdf_export": False,
            "legacy_zip_enabled": True,
        },
    },
    "legacy_only": {
        "label": "老会员 · 仅 Legacy",
        "plan_id": "monthly",
        "plan_code": "monthly",
        "portal_route": "legacy_only",
        "expires_at": "2026-08-15T00:00:00+00:00",
        "entitlements": {
            "plan_code": "monthly",
            "insight_enabled": False,
            "legacy_zip_enabled": True,
        },
    },
}

DEFAULT_PERSONA = "insight_pro"


def _load() -> dict[str, Any]:
    if SESSION_PATH.is_file():
        try:
            data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            if data.get("persona") in PERSONAS:
                return data
        except Exception:
            pass
    data = {"persona": DEFAULT_PERSONA, "updated_at": datetime.now(timezone.utc).isoformat()}
    _save(data)
    return data


def _save(data: dict[str, Any]) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    SESSION_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active_persona() -> str:
    return _load().get("persona") or DEFAULT_PERSONA


def set_persona(persona: str) -> dict[str, Any]:
    if persona not in PERSONAS:
        raise ValueError(f"unknown persona: {persona}")
    _save({"persona": persona})
    return get_profile()


def get_persona_config(persona: str | None = None) -> dict[str, Any]:
    key = persona or get_active_persona()
    return dict(PERSONAS.get(key) or PERSONAS[DEFAULT_PERSONA])


def subscription_path(persona: str | None = None) -> Path:
    key = persona or get_active_persona()
    return SESSIONS_DIR / key / "subscription.json"


def list_personas() -> list[dict[str, Any]]:
    active = get_active_persona()
    return [
        {"id": k, "label": v["label"], "active": k == active, "portal_route": v["portal_route"]}
        for k, v in PERSONAS.items()
    ]


def get_profile() -> dict[str, Any]:
    persona = get_active_persona()
    cfg = get_persona_config(persona)
    return {
        "lab_mode": True,
        "persona": persona,
        "persona_label": cfg.get("label"),
        "plan_code": cfg.get("plan_code"),
        "plan_id": cfg.get("plan_id"),
        "portal_route": cfg.get("portal_route"),
        "expires_at": cfg.get("expires_at"),
        "entitlements": dict(cfg.get("entitlements") or {}),
        "available_personas": list_personas(),
    }
