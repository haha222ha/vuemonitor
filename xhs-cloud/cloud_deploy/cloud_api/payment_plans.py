# -*- coding: utf-8 -*-
"""选品会员在线购买套餐（Web / PC 共用）。"""
from __future__ import annotations

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

PLAN_BY_CODE = {p["plan_code"]: p for p in PAYMENT_PLANS}


def get_plan(plan_code: str) -> dict | None:
    return PLAN_BY_CODE.get(str(plan_code or "").strip())
