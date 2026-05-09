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
    "free": {"maxProducts": 3, "maxConcurrency": 2, "dailyCollectLimit": 50},
    "pro": {"maxProducts": 50, "maxConcurrency": 8, "dailyCollectLimit": 500},
    "premium": {"maxProducts": -1, "maxConcurrency": 16, "dailyCollectLimit": 2000},
    "enterprise": {"maxProducts": -1, "maxConcurrency": 32, "dailyCollectLimit": -1},
}
