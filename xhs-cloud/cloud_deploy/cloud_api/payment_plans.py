# -*- coding: utf-8 -*-
"""选品会员在线购买套餐（Web / PC 共用）。

定价（2026-07）：体验 9.9/3天 · 月 39 · 季 99 · 半年 188 · 年 299
"""
from __future__ import annotations

import json
import os

# 统一 AI 会员权益（支付 / 授权码 / 会员阅读）
AI_MEMBER_ENTITLEMENTS: dict = {
    "insight_enabled": True,
    "insight_only": True,
    "insight_categories_per_day": 5,
    "insight_compare": True,
    "insight_timeline_days": 30,
    "insight_workflow": True,
    "insight_pdf_export": True,
    "insight_llm_tokens_per_day": 40_000,
    "advisor_read": True,
    "advisor_directions_per_day": 28,
    "advisor_history_days": 365,
    "advisor_chat_daily": 10,
    "legacy_zip_enabled": False,
}

# 体验卡：3 天 · 只读预生成，不含动态 LLM / 顾问对话
EXPERIENCE_3D_ENTITLEMENTS: dict = {
    "insight_enabled": True,
    "insight_only": True,
    "insight_categories_per_day": 3,
    "insight_compare": False,
    "insight_timeline_days": 7,
    "insight_workflow": False,
    "insight_pdf_export": False,
    "insight_llm_tokens_per_day": 0,
    "advisor_read": True,
    "advisor_directions_per_day": 8,
    "advisor_history_days": 30,
    "advisor_chat_daily": 0,
    "legacy_zip_enabled": False,
}

PAYMENT_PLANS: tuple[dict, ...] = (
    {
        "plan_code": "experience_3d",
        "label": "体验卡",
        "duration_days": 3,
        "amount": "9.90",
        "price_yuan": 9.9,
        "summary": "3 天 · 预生成报告阅读",
        "entitlements_template": EXPERIENCE_3D_ENTITLEMENTS,
    },
    {
        "plan_code": "monthly",
        "label": "月度会员",
        "duration_days": 30,
        "amount": "39.00",
        "price_yuan": 39,
        "summary": "30 天 · AI 选品顾问 + 类目情报",
        "entitlements_template": AI_MEMBER_ENTITLEMENTS,
    },
    {
        "plan_code": "quarterly",
        "label": "季度会员",
        "duration_days": 90,
        "amount": "99.00",
        "price_yuan": 99,
        "summary": "90 天 · 约合 ¥33/月",
        "entitlements_template": AI_MEMBER_ENTITLEMENTS,
    },
    {
        "plan_code": "halfyear",
        "label": "半年会员",
        "duration_days": 183,
        "amount": "188.00",
        "price_yuan": 188,
        "summary": "183 天 · 约合 ¥31/月",
        "entitlements_template": AI_MEMBER_ENTITLEMENTS,
    },
    {
        "plan_code": "yearly",
        "label": "年度会员",
        "duration_days": 365,
        "amount": "299.00",
        "price_yuan": 299,
        "summary": "365 天 · 最划算 · 约合 ¥25/月",
        "recommended": True,
        "entitlements_template": AI_MEMBER_ENTITLEMENTS,
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


def v2_launch_enabled() -> bool:
    """T0 上线后设为 1：支付页仅展示 AI 套餐（与 PAYMENT_PLANS 一致）。"""
    return os.environ.get("XHS_V2_LAUNCH", "").strip().lower() in ("1", "true", "yes", "on")


def list_active_plans() -> list[dict]:
    plans = list(PAYMENT_PLANS)
    if test_plan_enabled():
        plans = [PAYMENT_TEST_PLAN, *plans]
    return plans


PLAN_BY_CODE = {p["plan_code"]: p for p in PAYMENT_PLANS}
PLAN_BY_CODE[PAYMENT_TEST_PLAN["plan_code"]] = PAYMENT_TEST_PLAN


def entitlements_note_for_payment_plan(plan_code: str) -> str | None:
    """支付回调写入 auth_codes.note。"""
    plan = PLAN_BY_CODE.get(str(plan_code or "").strip())
    if not plan:
        return None
    tpl = plan.get("entitlements_template")
    if not tpl:
        return None
    payload = {"entitlements": {**tpl, "plan_code": plan["plan_code"]}}
    return json.dumps(payload, ensure_ascii=False)


def get_plan(plan_code: str) -> dict | None:
    code = str(plan_code or "").strip()
    if code == PAYMENT_TEST_PLAN["plan_code"] and not test_plan_enabled():
        return None
    plan = PLAN_BY_CODE.get(code)
    if plan:
        return plan
    from cloud_deploy.cloud_api.payment_plans_v2 import INSIGHT_PLAN_BY_CODE

    return INSIGHT_PLAN_BY_CODE.get(code)
