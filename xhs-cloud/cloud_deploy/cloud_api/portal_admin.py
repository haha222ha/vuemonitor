# -*- coding: utf-8 -*-
"""统一运营后台（admin.xhs365.cn/admin）公共底座。

鉴权复用 xhs-cloud 会员 JWT；仅 plan_code=admin 或配置的管理员账号可进入。
自用运营栈目录只经鉴权接口返回，不出现在公开货架。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.auth import current_member, issue_member_token
from cloud_deploy.cloud_api.config import get_settings

router = APIRouter(prefix="/api/v1/portal/admin", tags=["portal-admin"])

_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900

DEFAULT_OPS_STACK: list[dict] = [
    {
        "slug": "member",
        "name": "选品会员中心",
        "description": "选品 AI 顾问、报告与会员登录（www）。",
        "badge": "底座",
        "cta_label": "进入",
        "cta_url": "https://www.xhs365.cn/member",
        "external_url": "https://www.xhs365.cn/member",
    },
    {
        "slug": "insight",
        "name": "选品 AI 顾问",
        "description": "内部选品报告与顾问能力（自用）。注意：monitor.xhs365.cn 现网是心象测，不是选品。",
        "badge": "自用",
        "cta_label": "打开",
        "cta_url": "https://admin.xhs365.cn/member",
        "external_url": "https://www.xhs365.cn/member",
    },
    {
        "slug": "admin",
        "name": "统一运营后台",
        "description": "授权码、分销、反馈、自用运营栈入口。",
        "badge": "自用",
        "cta_label": "打开后台",
        "cta_url": "https://admin.xhs365.cn/admin/",
        "external_url": "https://admin.xhs365.cn/admin/",
    },
    {
        "slug": "psy",
        "name": "心象测（对外 SaaS）",
        "description": "心理测评 C/B 端。monitor.xhs365.cn 现网也指向心象测前端，勿当选品站。",
        "badge": "SaaS",
        "cta_label": "打开心象测",
        "cta_url": "https://psy.xhs365.cn",
        "external_url": "https://psy.xhs365.cn",
    },
    {
        "slug": "xianyu-ops",
        "name": "闲鱼自动经营",
        "description": "IM 发卡、多店矩阵、采购上架——自用运营栈。",
        "badge": "自用",
        "cta_label": "打开矩阵后台",
        "cta_url": "https://xy.xhs365.cn",
        "external_url": "https://xy.xhs365.cn",
    },
    {
        "slug": "list",
        "name": "上架审核台",
        "description": "小红书→闲鱼批次审核（自用）。",
        "badge": "自用",
        "cta_label": "打开审核台",
        "cta_url": "https://list.xhs365.cn",
        "external_url": "https://list.xhs365.cn",
    },
    {
        "slug": "hub",
        "name": "Source Hub",
        "description": "双源任务领取与 ingest（自用）。",
        "badge": "自用",
        "cta_label": "打开 Hub",
        "cta_url": "https://hub.xhs365.cn",
        "external_url": "https://hub.xhs365.cn",
    },
    {
        "slug": "hub-xianyu",
        "name": "闲鱼矩阵看板",
        "description": "Hub 子页：闲鱼数据参谋",
        "badge": "自用",
        "cta_label": "打开",
        "cta_url": "https://hub.xhs365.cn/board/xianyu/",
        "external_url": "https://hub.xhs365.cn",
    },
    {
        "slug": "hub-xhs",
        "name": "小红书筛选",
        "description": "Hub 子页：人工筛选入口",
        "badge": "自用",
        "cta_label": "打开",
        "cta_url": "https://hub.xhs365.cn/board/xhs-review/",
        "external_url": "https://hub.xhs365.cn",
    },
]

DEFAULT_AUTH_PRODUCTS: list[dict] = [
    {
        "product": "assess",
        "label": "选品会员",
        "activate_url_template": "https://www.xhs365.cn/member/?code={code}",
        "skus": [
            {"sku": "monthly", "label": "月卡", "duration_days": 30, "plan_code": "monthly"},
            {"sku": "quarterly", "label": "季卡", "duration_days": 90, "plan_code": "quarterly"},
            {"sku": "yearly", "label": "年卡", "duration_days": 365, "plan_code": "yearly"},
            {"sku": "admin", "label": "管理员（内部）", "duration_days": 3650, "plan_code": "admin", "reserved": True},
        ],
    }
]

DEFAULT_PORTAL_LINKS: dict[str, str] = {
    "assess_site": "https://www.xhs365.cn/member",
    "assess_activate": "https://www.xhs365.cn/member",
    "assess_activate_template": "https://www.xhs365.cn/member/?code={code}",
    "monitor_site": "https://www.xhs365.cn/member",
    "admin_site": "https://admin.xhs365.cn/admin/",
    "psy_site": "https://psy.xhs365.cn",
    "psy_admin": "https://psy.xhs365.cn/admin",
}


class PortalLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    device_id: str = Field(default="web:admin-portal", min_length=8, max_length=160)
    device_label: str = Field(default="admin-portal", max_length=64)


class GeneratePortalCodesBody(BaseModel):
    product: str = "assess"
    sku: str = "monthly"
    count: int = Field(default=1, ge=1, le=100)
    max_activations: int = Field(default=1, ge=1, le=1000)
    channel: str = ""
    remark: str = ""


class PatchNoteBody(BaseModel):
    status: str
    admin_note: str = ""


class ContactBody(BaseModel):
    wechat_qr_url: str = ""
    wechat_label: str = "扫码联系客服"
    contact_text: str = ""


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _rate_limit_login(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < _LOCKOUT_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(status_code=403, detail=f"登录尝试过多，请{_LOCKOUT_SECONDS}秒后重试")
    _login_attempts[ip] = attempts


def _record_login_fail(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < _LOCKOUT_SECONDS]
    attempts.append(now)
    _login_attempts[ip] = attempts


def _is_admin_user(user: dict) -> bool:
    s = get_settings()
    plan = (user.get("plan_code") or "").strip().lower()
    username = (user.get("username") or "").strip()
    if plan == "admin":
        return True
    if username and username == (s.xhs_cloud_admin_user or "").strip():
        return True
    return False


def current_portal_admin(user: dict = Depends(current_member)) -> dict:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="需要管理员账号")
    return user


def _ops_stack_items() -> list[dict]:
    raw = (os.environ.get("OPS_STACK_JSON") or "").strip()
    if not raw:
        return list(DEFAULT_OPS_STACK)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
        if isinstance(data, dict) and isinstance(data.get("apps"), list):
            return data["apps"]
    except json.JSONDecodeError:
        pass
    return list(DEFAULT_OPS_STACK)


def _portal_links() -> dict[str, str]:
    raw = (os.environ.get("PORTAL_LINKS_JSON") or "").strip()
    links = dict(DEFAULT_PORTAL_LINKS)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                links.update({str(k): str(v) for k, v in parsed.items()})
        except json.JSONDecodeError:
            pass
    return links


def _auth_products() -> list[dict]:
    raw = (os.environ.get("PORTAL_AUTH_PRODUCTS_JSON") or "").strip()
    if not raw:
        return list(DEFAULT_AUTH_PRODUCTS)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("products"), list):
            return data["products"]
    except json.JSONDecodeError:
        pass
    return list(DEFAULT_AUTH_PRODUCTS)


def _sku_meta(product: str, sku: str) -> dict:
    for p in _auth_products():
        if p.get("product") != product:
            continue
        for s in p.get("skus") or []:
            if s.get("sku") == sku:
                return s
    raise HTTPException(status_code=400, detail=f"未知 SKU: {product}/{sku}")


@router.post("/login")
def portal_login(body: PortalLoginRequest, request: Request):
    ip = _client_ip(request)
    _rate_limit_login(ip)
    username = body.username.strip()
    auth_fn = getattr(db, "authenticate_user", None) or db.authenticate
    auth_user = auth_fn(username, body.password)
    if not auth_user:
        _record_login_fail(ip)
        raise HTTPException(status_code=403, detail="管理员账号或密码错误")

    profile = db.get_member_profile(auth_user["id"]) or {}
    user = {
        "id": auth_user["id"],
        "username": auth_user["username"],
        "plan_code": profile.get("plan_code") or auth_user.get("plan_code") or "",
    }
    if not _is_admin_user(user):
        _record_login_fail(ip)
        raise HTTPException(status_code=403, detail="需要管理员账号")

    _login_attempts.pop(ip, None)
    device_id = (body.device_id or "web:admin-portal").strip()
    device_label = (body.device_label or "admin-portal").strip()
    token = issue_member_token(user["id"], user["username"], device_id, device_label)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": "admin",
        "plan_code": user.get("plan_code") or "admin",
    }


@router.get("/me")
def portal_me(admin: dict = Depends(current_portal_admin)):
    profile = db.get_member_profile(admin["id"]) or admin
    return {
        "id": str(admin["id"]),
        "username": admin.get("username") or profile.get("username"),
        "role": "admin",
        "plan": profile.get("plan_code") or admin.get("plan_code") or "admin",
        "plan_code": profile.get("plan_code") or admin.get("plan_code") or "admin",
        "days_remaining": profile.get("days_remaining"),
    }


@router.get("/ops-stack")
def portal_ops_stack(admin: dict = Depends(current_portal_admin)):
    items = _ops_stack_items()
    return {"items": items, "apps": items, "total": len(items)}


@router.get("/status")
def portal_status(admin: dict = Depends(current_portal_admin)):
    try:
        stats = db.get_admin_stats()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e
    products = _auth_products()
    return {
        "online": True,
        "portal_links": _portal_links(),
        "products": products,
        "stats": stats,
    }


@router.get("/auth-products")
def portal_auth_products(admin: dict = Depends(current_portal_admin)):
    return {"products": _auth_products()}


@router.get("/auth-codes")
def portal_list_codes(
    admin: dict = Depends(current_portal_admin),
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = None,
    product: str | None = None,
):
    try:
        items = db.list_auth_codes(limit=limit, status=status or None)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e
    if product:
        # note JSON meta.product 过滤（兼容旧纯文本 note）
        filtered = []
        for row in items:
            note = row.get("note") or ""
            meta_product = ""
            try:
                j = json.loads(note)
                meta_product = (j.get("meta") or {}).get("product") or ""
            except Exception:
                meta_product = ""
            if meta_product == product or (not meta_product and product == "assess"):
                filtered.append(row)
        items = filtered
    return {"items": items, "total": len(items)}


@router.post("/auth-codes")
def portal_generate_codes(
    body: GeneratePortalCodesBody,
    admin: dict = Depends(current_portal_admin),
):
    sku = _sku_meta(body.product, body.sku)
    if sku.get("reserved"):
        raise HTTPException(status_code=400, detail="该 SKU 仅内部保留，不可批量生成")
    plan_code = sku.get("plan_code") or body.sku
    duration_days = int(sku.get("duration_days") or 30)
    note_obj = {
        "meta": {
            "product": body.product,
            "sku": body.sku,
            "channel": (body.channel or "").strip(),
            "remark": (body.remark or "").strip(),
            "by": admin.get("username") or "admin",
        }
    }
    note = json.dumps(note_obj, ensure_ascii=False)
    try:
        codes = db.generate_auth_codes(
            count=body.count,
            plan_code=plan_code,
            duration_days=duration_days,
            max_activations=body.max_activations,
            note=note,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"生成失败: {e}") from e

    links = _portal_links()
    tpl = ""
    for p in _auth_products():
        if p.get("product") == body.product:
            tpl = p.get("activate_url_template") or ""
            break
    tpl = tpl or links.get("assess_activate_template") or ""
    export_lines = []
    for code in codes:
        link = tpl.replace("{code}", code) if tpl else code
        export_lines.append(f"{code}\t{link}")
    return {
        "codes": codes,
        "export_tsv": "\n".join(export_lines),
        "label": sku.get("label") or plan_code,
        "plan_code": plan_code,
        "duration_days": duration_days,
        "max_activations": body.max_activations,
    }


@router.post("/auth-codes/{code}/revoke")
def portal_revoke_code(code: str, admin: dict = Depends(current_portal_admin)):
    try:
        return db.revoke_auth_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e


@router.get("/member-feedback")
def portal_member_feedback(
    admin: dict = Depends(current_portal_admin),
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = None,
):
    # 表未就绪时返回空列表，避免运营台整页不可用
    _ = admin, limit, status
    return {"items": [], "total": 0}


@router.patch("/member-feedback/{item_id}")
def portal_patch_feedback(
    item_id: int,
    body: PatchNoteBody,
    admin: dict = Depends(current_portal_admin),
):
    _ = item_id, body, admin
    raise HTTPException(status_code=501, detail="会员反馈表尚未启用")


@router.get("/member-keyword-requests")
def portal_keyword_requests(
    admin: dict = Depends(current_portal_admin),
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = None,
):
    _ = admin, limit, status
    return {"items": [], "total": 0}


@router.patch("/member-keyword-requests/{item_id}")
def portal_patch_keyword(
    item_id: int,
    body: PatchNoteBody,
    admin: dict = Depends(current_portal_admin),
):
    _ = item_id, body, admin
    raise HTTPException(status_code=501, detail="关键词申请表尚未启用")


@router.get("/member-contact")
def portal_get_contact(admin: dict = Depends(current_portal_admin)):
    _ = admin
    raw = (os.environ.get("PORTAL_MEMBER_CONTACT_JSON") or "").strip()
    config: dict[str, Any] = {
        "wechat_qr_url": "",
        "wechat_label": "扫码联系客服",
        "contact_text": "",
    }
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                config.update(parsed)
        except json.JSONDecodeError:
            pass
    return {"config": config}


@router.put("/member-contact")
def portal_put_contact(body: ContactBody, admin: dict = Depends(current_portal_admin)):
    _ = admin
    # 无持久化表时仅回显；生产可改写 ENV 文件或落库
    return {
        "config": {
            "wechat_qr_url": body.wechat_qr_url,
            "wechat_label": body.wechat_label,
            "contact_text": body.contact_text,
        },
        "persisted": False,
        "detail": "当前未配置联系方式持久化，请在 ENV PORTAL_MEMBER_CONTACT_JSON 维护",
    }


@router.post("/member-contact/upload")
async def portal_upload_contact(admin: dict = Depends(current_portal_admin)):
    _ = admin
    raise HTTPException(status_code=501, detail="联系方式上传未启用，请直接填写 URL")


@router.get("/dist/overview")
def portal_dist_overview(
    admin: dict = Depends(current_portal_admin),
    limit: int = Query(default=100, ge=1, le=500),
    link_status: str | None = None,
):
    _ = admin, limit, link_status
    links = _portal_links()
    return {
        "stats": {
            "distributors": 0,
            "quota_remaining": 0,
            "links_total": 0,
            "results_total": 0,
            "quota_used": 0,
            "quota_total": 0,
            "orders_paid": 0,
            "orders_total": 0,
            "links_by_test": [],
        },
        "orders": [],
        "links": [],
        "distributors": [],
        "portal_links": links,
    }
