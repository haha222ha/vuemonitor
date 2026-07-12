# -*- coding: utf-8 -*-
"""会员套餐 + 关注列表 mock（实验室，output/subscription.json）。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from services.lab_session import get_active_persona, get_persona_config, subscription_path
from services.plan_entitlements import current_entitlements, entitlements_for_plan

SUB_PATH_LEGACY = Path(__file__).resolve().parents[1] / "output" / "subscription.json"
PLANS_PATH = Path(__file__).resolve().parents[1] / "config" / "plans.yaml"


def _load_plans_config() -> dict[str, Any]:
    fallback = {
        "default_plan": "insight_pro_monthly",
        "plans": {
            "insight_monthly": {
                "display": "AI 选品情报",
                "price_label": "¥129/月",
                "entitlements": {
                    "insight_categories_per_day": 3,
                    "insight_compare": False,
                    "insight_timeline_days": 0,
                    "insight_workflow": False,
                    "insight_pdf_export": False,
                    "insight_llm_tokens_per_day": 20_000,
                },
            },
            "insight_pro_monthly": {
                "display": "AI 选品情报 Pro",
                "price_label": "¥299/月",
                "entitlements": {
                    "insight_categories_per_day": 5,
                    "insight_compare": True,
                    "insight_timeline_days": 30,
                    "insight_workflow": True,
                    "insight_pdf_export": True,
                    "insight_llm_tokens_per_day": 40_000,
                },
            },
            "insight_team_monthly": {
                "display": "AI 选品情报 团队版",
                "price_label": "¥899/月",
                "entitlements": {
                    "insight_categories_per_day": 20,
                    "insight_compare": True,
                    "insight_timeline_days": 30,
                    "insight_workflow": True,
                    "insight_pdf_export": True,
                    "insight_llm_tokens_per_day": 150_000,
                },
            },
        },
        "notification_rules": {"blue_ocean_above": 75, "growth_above_pct": 25},
    }
    try:
        import yaml
    except ImportError:
        return fallback
    if not PLANS_PATH.is_file():
        return fallback
    data = yaml.safe_load(PLANS_PATH.read_text(encoding="utf-8")) or {}
    if not data.get("plans"):
        return fallback
    return data


def _default_state() -> dict[str, Any]:
    cfg = _load_plans_config()
    plan_id = cfg.get("default_plan") or "insight_pro_monthly"
    return {
        "plan_id": plan_id,
        "watchlist": ["美甲美睫", "小学教辅"],
        "daily_generated": {},  # date -> [categories]
        "updated_at": datetime.now().isoformat(),
    }


def _sub_path() -> Path:
    return subscription_path()


def _load_sub() -> dict[str, Any]:
    path = _sub_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg = _load_plans_config()
    persona_cfg = get_persona_config()
    plan_id = persona_cfg.get("plan_id") or cfg.get("default_plan") or "insight_pro_monthly"
    state = {
        "plan_id": plan_id,
        "watchlist": ["美甲美睫", "小学教辅"],
        "daily_generated": {},
        "updated_at": datetime.now().isoformat(),
    }
    _save_sub(state)
    return state


def _save_sub(state: dict[str, Any]) -> None:
    path = _sub_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_plan_info() -> dict[str, Any]:
    cfg = _load_plans_config()
    sub = _load_sub()
    persona_cfg = get_persona_config()
    plan_id = sub.get("plan_id") or persona_cfg.get("plan_id") or cfg.get("default_plan") or "insight_pro_monthly"
    plans = cfg.get("plans") or {}
    plan = plans.get(plan_id)
    if not plan and plan_id == "monthly":
        plan = {"display": "Legacy 月卡", "entitlements": {}}
    plan = plan or plans.get("insight_pro_monthly") or {}
    ent = current_entitlements(plan_id)
    today = datetime.now().strftime("%Y-%m-%d")
    used = len(sub.get("daily_generated", {}).get(today, []))
    limit = int(ent.get("insight_categories_per_day") or 1)
    # 前端兼容字段（来自 entitlements）
    plan_view = {
        **plan,
        "display": plan.get("display") or plan_id,
        "categories_per_day": limit,
        "compare_enabled": bool(ent.get("insight_compare")),
        "pdf_export": bool(ent.get("insight_pdf_export")),
        "workflow_enabled": bool(ent.get("insight_workflow")),
        "timeline_days_max": int(ent.get("insight_timeline_days") or 0),
    }
    return {
        "plan_id": plan_id,
        "plan": plan_view,
        "entitlements": ent,
        "watchlist": sub.get("watchlist") or [],
        "usage_today": {
            "date": today,
            "generated_count": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "categories": sub.get("daily_generated", {}).get(today, []),
        },
        "persona": get_active_persona(),
        "available_plans": {
            k: {"display": v.get("display"), "price_label": v.get("price_label")}
            for k, v in plans.items()
        },
    }


def set_plan(plan_id: str) -> dict[str, Any]:
    cfg = _load_plans_config()
    if plan_id not in (cfg.get("plans") or {}):
        raise ValueError(f"unknown plan: {plan_id}")
    sub = _load_sub()
    sub["plan_id"] = plan_id
    _save_sub(sub)
    return get_plan_info()


def update_watchlist(categories: list[str]) -> dict[str, Any]:
    sub = _load_sub()
    ent = current_entitlements(sub.get("plan_id"))
    max_w = int(ent.get("insight_categories_per_day") or 5) * 2
    sub["watchlist"] = list(dict.fromkeys(categories))[:max_w]
    _save_sub(sub)
    return get_plan_info()


def can_generate(category: str, report_date: str | None = None) -> tuple[bool, str]:
    info = get_plan_info()
    today = report_date or datetime.now().strftime("%Y-%m-%d")
    sub = _load_sub()
    day_list = sub.setdefault("daily_generated", {}).setdefault(today, [])
    if category in day_list:
        return True, "already_generated"
    remaining = info["usage_today"]["remaining"]
    if remaining <= 0:
        return False, f"今日套餐额度已用完（{info['usage_today']['limit']} 类目/日），请明日再试或升级套餐"
    return True, "ok"


def record_generation(category: str, report_date: str | None = None) -> None:
    sub = _load_sub()
    today = report_date or datetime.now().strftime("%Y-%m-%d")
    day_list = sub.setdefault("daily_generated", {}).setdefault(today, [])
    if category not in day_list:
        day_list.append(category)
    _save_sub(sub)


def check_feature(feature: str) -> bool:
    ent = current_entitlements(get_plan_info().get("plan_id"))
    mapping = {
        "compare_enabled": ent.get("insight_compare"),
        "pdf_export": ent.get("insight_pdf_export"),
        "workflow_enabled": ent.get("insight_workflow"),
    }
    return bool(mapping.get(feature))
