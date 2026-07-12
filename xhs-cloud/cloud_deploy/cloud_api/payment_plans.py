# -*- coding: utf-8 -*-
"""选品会员在线购买套餐（Web / PC 共用）。"""
from __future__ import annotations

import os

PAYMENT_PLANS: tuple[dict, ...] = (
    {
        "plan_code": "monthly",
        "label": "月度会员",
        "duration_days": 30,
        "amount": "99.00",
        "price_yuan": 99,
        "summary": "30 天，全部报告下载",
    },
    {
        "plan_code": "quarterly",
        "label": "季度会员",
        "duration_days": 90,
        "amount": "269.00",
        "price_yuan": 269,
        "summary": "90 天，全部报告下载",
    },
    {
        "plan_code": "halfyear",
        "label": "半年会员",
        "duration_days": 183,
        "amount": "469.00",
        "price_yuan": 469,
        "summary": "183 天，全部报告下载",
    },
    {
        "plan_code": "yearly",
        "label": "年度会员",
        "duration_days": 365,
        "amount": "799.00",
        "price_yuan": 799,
        "summary": "365 天，全部报告下载",
    },
)

# 仅当 XHS_PAY_ENABLE_TEST_PLAN=1 时在 API/页面展示，用于 1 元联调
PAYMENT_TEST_PLAN: dict = {
    "plan_code": "pay_test",
    "label": "支付测试",
    "duration_days": 1,
    "amount": "1.00",
    "price_yuan": 1,
    "summary": "1 元联调（1 天会员，验证支付回调）",
    "is_test": True,
}


def test_plan_enabled() -> bool:
    return os.environ.get("XHS_PAY_ENABLE_TEST_PLAN", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def list_active_plans() -> list[dict]:
    if v2_launch_enabled():
        from cloud_deploy.cloud_api.payment_plans_v2 import list_active_plans_v2_only

        plans = list_active_plans_v2_only()
        if test_plan_enabled():
            return [PAYMENT_TEST_PLAN, *plans]
        return plans
    plans = list(PAYMENT_PLANS)
    if test_plan_enabled():
        plans = [PAYMENT_TEST_PLAN, *plans]
    return plans


def v2_launch_enabled() -> bool:
    """T0 上线后设为 1：支付页仅展示 insight_* SKU。"""
    return os.environ.get("XHS_V2_LAUNCH", "").strip().lower() in ("1", "true", "yes", "on")


PLAN_BY_CODE = {p["plan_code"]: p for p in PAYMENT_PLANS}
PLAN_BY_CODE[PAYMENT_TEST_PLAN["plan_code"]] = PAYMENT_TEST_PLAN


def get_plan(plan_code: str) -> dict | None:
    code = str(plan_code or "").strip()
    if code == PAYMENT_TEST_PLAN["plan_code"] and not test_plan_enabled():
        return None
    plan = PLAN_BY_CODE.get(code)
    if plan:
        return plan
    from cloud_deploy.cloud_api.payment_plans_v2 import INSIGHT_PLAN_BY_CODE

    return INSIGHT_PLAN_BY_CODE.get(code)
