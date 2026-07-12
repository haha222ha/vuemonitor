# -*- coding: utf-8 -*-
"""会员 V2 权益解析 — PR-1 合并骨架，供 profile / insight API / legacy_gate 共用。"""
from __future__ import annotations

from fastapi import HTTPException

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.entitlements_v2 import merge_entitlements, portal_route
from cloud_deploy.cloud_api.legacy_gate import insight_enabled, legacy_zip_enabled

LEGACY_ZIP_DENIED = "当前套餐不含 Legacy 数据包下载，请开通 AI 选品情报或联系客服"


def resolve_entitlements(user_id: int, profile: dict | None) -> dict:
    """合并 auth_codes.note 与 memberships.plan_code 为规范 entitlements。"""
    profile = profile or {}
    raw = db.get_member_entitlements(user_id)
    plan = (profile.get("plan_code") or (raw or {}).get("plan_code") or "").strip()
    if raw is None:
        raw = {"plan_code": plan} if plan else {}
    else:
        raw = dict(raw)
        raw.setdefault("plan_code", plan)
    return merge_entitlements(raw, plan or None)


def enrich_member_profile(profile: dict | None, user_id: int) -> dict | None:
    """扩展 GET /api/v1/member/profile — Doc 21 PR-1 验收字段。"""
    if not profile:
        return profile
    ent = resolve_entitlements(user_id, profile)
    plan = profile.get("plan_code") or ent.get("plan_code") or ""
    expires = profile.get("expires_at")
    out = dict(profile)
    out["entitlements"] = ent
    out["portal_route"] = portal_route(ent)
    out["legacy_zip_enabled"] = legacy_zip_enabled(
        plan_code=plan,
        expires_at=expires,
        entitlements=ent,
    )
    out["insight_enabled"] = insight_enabled(
        plan_code=plan,
        expires_at=expires,
        entitlements=ent,
    )
    return out


def assert_legacy_zip_allowed(user_id: int) -> None:
    """Legacy zip 下载/批量下载/报告内文件查看门控。"""
    profile = db.get_member_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    enriched = enrich_member_profile(profile, user_id)
    if not enriched or not enriched.get("legacy_zip_enabled"):
        raise HTTPException(status_code=403, detail=LEGACY_ZIP_DENIED)


def assert_insight_allowed(user_id: int) -> dict:
    """情报 API 门控；返回 entitlements。"""
    profile = db.get_member_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    enriched = enrich_member_profile(profile, user_id)
    if not enriched or not enriched.get("insight_enabled"):
        raise HTTPException(status_code=403, detail="当前账号不含 AI 选品情报权益")
    return enriched.get("entitlements") or {}
