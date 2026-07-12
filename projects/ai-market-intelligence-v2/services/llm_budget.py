# -*- coding: utf-8 -*-
"""日 LLM Token 预算 — REQ-LLM-010 / REQ-LLM-011"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
USAGE_PATH = _ROOT / "output" / "llm_usage.json"
PLANS_PATH = _ROOT / "config" / "plans.yaml"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _budget_limit(plan_id: str | None = None, entitlements: dict | None = None) -> int:
    if entitlements:
        tok = int(entitlements.get("insight_llm_tokens_per_day") or 0)
        if tok > 0:
            return tok
    env = os.environ.get("INSIGHT_LLM_BUDGET_TOKENS_PER_DAY", "").strip()
    if env.isdigit():
        return int(env)
    try:
        import yaml
        if PLANS_PATH.is_file():
            cfg = yaml.safe_load(PLANS_PATH.read_text(encoding="utf-8")) or {}
            lb = cfg.get("llm_budget") or {}
            if plan_id == "insight_team_monthly":
                return int(lb.get("tokens_per_day_team") or 800_000)
            return int(lb.get("tokens_per_day_default") or 200_000)
    except Exception:
        pass
    return 200_000


def _load() -> dict[str, Any]:
    if USAGE_PATH.is_file():
        try:
            return json.loads(USAGE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"days": {}}


def _save(data: dict[str, Any]) -> None:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USAGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_daily_usage(date: str | None = None) -> dict[str, Any]:
    date = date or _today()
    data = _load()
    day = data.get("days", {}).get(date) or {}
    return {
        "date": date,
        "total_tokens": int(day.get("total_tokens") or 0),
        "requests": int(day.get("requests") or 0),
    }


def check_budget(
    plan_id: str | None = None,
    *,
    date: str | None = None,
    entitlements: dict | None = None,
) -> tuple[bool, str]:
    date = date or _today()
    used = get_daily_usage(date)["total_tokens"]
    limit = _budget_limit(plan_id, entitlements)
    if used >= limit:
        return False, f"今日 LLM Token 预算已用尽（{used}/{limit}），请明日再试或联系运营"
    return True, "ok"


def record_usage(
    usage: dict[str, Any] | None,
    *,
    date: str | None = None,
    category: str = "",
) -> dict[str, Any]:
    date = date or _today()
    u = usage or {}
    prompt = int(u.get("prompt_tokens") or 0)
    completion = int(u.get("completion_tokens") or 0)
    total = prompt + completion
    if total <= 0:
        return get_daily_usage(date)

    data = _load()
    days = data.setdefault("days", {})
    day = days.setdefault(date, {"total_tokens": 0, "requests": 0, "events": []})
    day["total_tokens"] = int(day.get("total_tokens") or 0) + total
    day["requests"] = int(day.get("requests") or 0) + 1
    events = day.setdefault("events", [])
    events.append({
        "at": datetime.now().isoformat(),
        "tokens": total,
        "category": category,
        "model": u.get("model") or "",
    })
    # 保留最近 50 条
    day["events"] = events[-50:]
    _save(data)
    return get_daily_usage(date)
