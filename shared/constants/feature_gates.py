from typing import Literal

PlanTier = Literal["free", "pro", "premium", "enterprise"]

PLAN_HIERARCHY: dict[PlanTier, int] = {
    "free": 0,
    "pro": 1,
    "premium": 2,
    "enterprise": 3,
}


def is_plan_sufficient(user_plan: PlanTier, required_plan: PlanTier) -> bool:
    return PLAN_HIERARCHY.get(user_plan, 0) >= PLAN_HIERARCHY.get(required_plan, 0)


PLAN_LIMITS: dict[PlanTier, dict] = {
    "free": {"maxProducts": 3, "maxConcurrency": 1, "dailyCollectLimit": 20, "maxScheduleTasks": 0, "aiCallsPerDay": 3},
    "pro": {"maxProducts": 50, "maxConcurrency": 5, "dailyCollectLimit": 500, "maxScheduleTasks": 20, "aiCallsPerDay": 50},
    "premium": {"maxProducts": 500, "maxConcurrency": 8, "dailyCollectLimit": 2000, "maxScheduleTasks": 100, "aiCallsPerDay": 200},
    "enterprise": {"maxProducts": -1, "maxConcurrency": 10, "dailyCollectLimit": -1, "maxScheduleTasks": -1, "aiCallsPerDay": -1},
}

PLAN_FEATURES_MAP: dict[str, list[str]] = {
    "free": ["gate:monitor:add", "gate:monitor:manual_refresh", "gate:ai:basic_analysis"],
    "pro": [
        "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
        "gate:monitor:history", "gate:monitor:export",
        "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:ai:report",
        "gate:collect:playwright", "gate:collect:author_full", "gate:sync:cloud",
    ],
    "premium": [
        "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
        "gate:monitor:history", "gate:monitor:export",
        "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:ai:prediction",
        "gate:ai:risk_warning", "gate:ai:report", "gate:ai:batch_analysis",
        "gate:collect:playwright", "gate:collect:author_full", "gate:sync:cloud",
    ],
    "enterprise": [
        "gate:monitor:add", "gate:monitor:manual_refresh", "gate:monitor:auto_refresh",
        "gate:monitor:history", "gate:monitor:export",
        "gate:ai:basic_analysis", "gate:ai:trend_score", "gate:ai:prediction",
        "gate:ai:risk_warning", "gate:ai:report", "gate:ai:batch_analysis",
        "gate:collect:playwright", "gate:collect:author_full", "gate:sync:cloud",
    ],
}
