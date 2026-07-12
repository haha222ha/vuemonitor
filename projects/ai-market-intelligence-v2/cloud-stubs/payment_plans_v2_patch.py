# -*- coding: utf-8 -*-
"""
V2 套餐定义 — 合并到 xhs-cloud/cloud_deploy/cloud_api/payment_plans.py

用法（Phase 3）:
  from cloud_deploy.cloud_api.payment_plans_v2_patch import INSIGHT_PAYMENT_PLANS
  PAYMENT_PLANS = PAYMENT_PLANS + INSIGHT_PAYMENT_PLANS  # 或 tuple 拼接

支付通道、回调、二维码生成 **不改**，仅新增 plan_code。
"""
from __future__ import annotations

INSIGHT_PAYMENT_PLANS: tuple[dict, ...] = (
    {
        "plan_code": "insight_monthly",
        "label": "AI 选品情报",
        "duration_days": 30,
        "amount": "129.00",
        "price_yuan": 129,
        "summary": "30 天 AI 选品分析 · 3 类目/日 · 无对比/PDF",
        "product_line": "v2",
        "entitlements_template": {
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
    {
        "plan_code": "insight_pro_monthly",
        "label": "AI 选品情报 Pro",
        "duration_days": 30,
        "amount": "299.00",
        "price_yuan": 299,
        "summary": "主推：5 类目/日 · 对比 · 时间轴 · 工作流",
        "product_line": "v2",
        "recommended": True,
        "entitlements_template": {
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
    {
        "plan_code": "insight_team_monthly",
        "label": "AI 选品情报 团队版",
        "duration_days": 30,
        "amount": "899.00",
        "price_yuan": 899,
        "summary": "5 席位 · 20 类目/日",
        "product_line": "v2",
        "entitlements_template": {
            "insight_enabled": True,
            "insight_only": True,
            "insight_categories_per_day": 20,
            "insight_compare": True,
            "insight_timeline_days": 30,
            "insight_pdf_export": True,
            "insight_workflow": True,
            "insight_team_seats": 5,
            "insight_llm_tokens_per_day": 150_000,
            "legacy_zip_enabled": False,
        },
    },
)

# dual_monthly / 纯 Legacy 套餐：T0 后不再销售（见 docs/19-LEGACY-SUNSET-AND-V2-LAUNCH.md）
# 现网 monthly/quarterly/… 仅用于在期老用户履约，不出现在 list_active_plans()

# 免费/低价体验：走授权码 plan_code=experience + note JSON，不走在线标价
# 见 entitlements_v2.EXPERIENCE_ENTITLEMENTS_INSIGHT

INSIGHT_PLAN_BY_CODE = {p["plan_code"]: p for p in INSIGHT_PAYMENT_PLANS}


def list_active_plans_v2_only() -> list[dict]:
    """T0 上线后替换 list_active_plans() 的返回值。"""
    plans = list(INSIGHT_PAYMENT_PLANS)
    return [p for p in plans if p.get("product_line") == "v2"]


def list_active_plans_legacy_hidden() -> list[dict]:
    """兼容：仅 V2 在售；Legacy 套餐不展示。"""
    return list_active_plans_v2_only()


def entitlements_note_for_plan(plan_code: str) -> str:
    """支付回调生成授权码时写入 auth_codes.note。"""
    import json
    tpl = INSIGHT_PLAN_BY_CODE.get(plan_code, {}).get("entitlements_template") or {}
    return json.dumps({"entitlements": {**tpl, "plan_code": plan_code}}, ensure_ascii=False)
