# -*- coding: utf-8 -*-
"""选品会员 hwxun 支付：下单、回调履约、订单查询。"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.config import get_settings
from cloud_deploy.cloud_api.hwxun_pay import create_wxpay_order, verify_notify_epay
from cloud_deploy.cloud_api.payment_plans import get_plan


def _notify_url() -> str:
    base = (get_settings().xhs_pay_notify_base or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("未配置 XHS_PAY_NOTIFY_BASE")
    return f"{base}/api/v1/payment/notify/hwxun"


def _gen_order_no() -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"XHSP{ts}{secrets.token_hex(3).upper()}"


def list_public_plans() -> list[dict]:
    from cloud_deploy.cloud_api.payment_plans import list_active_plans

    return [
        {
            "plan_code": p["plan_code"],
            "label": p["label"],
            "duration_days": p["duration_days"],
            "amount": p["amount"],
            "price_yuan": p["price_yuan"],
            "summary": p["summary"],
            **({"is_test": True} if p.get("is_test") else {}),
        }
        for p in list_active_plans()
    ]


def create_order(
    *,
    plan_code: str,
    user_id: int | None,
    client_ip: str,
) -> dict:
    plan = get_plan(plan_code)
    if not plan:
        raise ValueError("无效套餐")
    order_no = _gen_order_no()
    expires_at = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    db.insert_payment_order(
        order_no=order_no,
        user_id=user_id,
        plan_code=plan["plan_code"],
        duration_days=int(plan["duration_days"]),
        amount=plan["amount"],
        channel="wxpay",
        client_ip=client_ip,
        expires_at=expires_at,
    )
    gw = create_wxpay_order(
        out_trade_no=order_no,
        amount=plan["amount"],
        name=f"选品报告会员-{plan['label']}",
        notify_url=_notify_url(),
        clientip=client_ip,
    )
    qrcode = str(gw.get("qrcode") or gw.get("code_url") or "").strip()
    payurl = str(gw.get("payurl") or gw.get("url") or "").strip()
    gateway_trade_no = str(gw.get("trade_no") or "").strip()
    if not qrcode and not payurl:
        raise RuntimeError("支付网关未返回二维码")
    db.update_payment_order_gateway(
        order_no,
        qrcode=qrcode,
        payurl=payurl,
        gateway_trade_no=gateway_trade_no,
    )
    return {
        "order_no": order_no,
        "plan_code": plan["plan_code"],
        "plan_label": plan["label"],
        "amount": plan["amount"],
        "duration_days": plan["duration_days"],
        "qrcode": qrcode,
        "payurl": payurl,
        "expires_at": expires_at,
        "status": "pending",
    }


def get_order_public(order_no: str) -> dict | None:
    row = db.get_payment_order(order_no)
    if not row:
        return None
    db.expire_stale_payment_order(order_no)
    row = db.get_payment_order(order_no) or row
    plan = get_plan(row["plan_code"]) or {}
    fulfilled = bool(row.get("fulfilled_user_id"))
    out = {
        "order_no": row["order_no"],
        "plan_code": row["plan_code"],
        "plan_label": plan.get("label") or row["plan_code"],
        "amount": row["amount"],
        "duration_days": row["duration_days"],
        "status": row["status"],
        "expires_at": row["expires_at"],
        "paid_at": row.get("paid_at"),
        "qrcode": row.get("qrcode") or "",
        "payurl": row.get("payurl") or "",
        "fulfilled": fulfilled,
    }
    if row["status"] == "paid":
        if fulfilled:
            out["message"] = "支付成功，会员已生效"
            out["next_action"] = "none"
        else:
            out["message"] = "支付成功，请设置账号或登录已有账号以完成开通"
            out["next_action"] = "complete_account"
    return out


def complete_paid_order(
    order_no: str,
    *,
    mode: str,
    username: str,
    password: str,
) -> dict:
    """支付成功后：新用户注册开通，或老用户登录绑定续期（不再暴露授权码）。"""
    row = db.get_payment_order(order_no)
    if not row:
        raise ValueError("订单不存在")
    if row["status"] != "paid":
        raise ValueError("订单尚未支付")
    if row.get("fulfilled_user_id"):
        uid = int(row["fulfilled_user_id"])
        profile = db.get_member_profile(uid) or {}
        return {
            "membership": profile,
            "message": "该订单已完成开通",
            "username": profile.get("username") or "",
        }
    code = (row.get("auth_code") or "").strip()
    if not code:
        raise ValueError("订单处理中，请稍后刷新或联系客服")

    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        raise ValueError("请填写用户名和密码")
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")

    mode = (mode or "").strip().lower()
    if mode == "register":
        profile = db.register_with_auth_code(username, password, code)
        msg = f"开通成功，会员已生效 {row['duration_days']} 天"
    elif mode == "login":
        profile = db.renew_with_credentials(username, password, code)
        stack = profile.get("renew_stack") or {}
        if stack.get("stacked"):
            msg = (
                f"续费成功：已叠加剩余 {stack.get('previous_days_remaining', 0)} 天 + "
                f"新购 {stack.get('days_added', 0)} 天"
            )
        else:
            msg = profile.get("message") or f"会员已延长 {stack.get('days_added', row['duration_days'])} 天"
    else:
        raise ValueError("无效操作，请选择新用户开通或已有账号登录")

    db.mark_payment_order_fulfilled(order_no, int(profile["id"]))
    return {
        "membership": profile,
        "message": msg,
        "username": profile.get("username") or username,
    }


def claim_paid_order(order_no: str, user_id: int) -> dict:
    row = db.get_payment_order(order_no)
    if not row:
        raise ValueError("订单不存在")
    if row["status"] != "paid":
        raise ValueError("订单尚未支付")
    if row.get("fulfilled_user_id"):
        if int(row["fulfilled_user_id"]) == user_id:
            profile = db.get_member_profile(user_id) or {}
            return {"membership": profile, "message": "该订单已履约"}
        raise ValueError("该订单已被其他账号使用")
    code = row.get("auth_code")
    if not code:
        raise ValueError("订单缺少授权码，请联系客服")
    profile = db.renew_with_auth_code(user_id, code)
    db.mark_payment_order_fulfilled(order_no, user_id)
    stack = profile.get("renew_stack") or {}
    if stack.get("stacked"):
        msg = (
            f"续费成功：已叠加剩余 {stack.get('previous_days_remaining', 0)} 天 + "
            f"新授权 {stack.get('days_added', 0)} 天"
        )
    else:
        msg = f"会员已延长 {stack.get('days_added', row['duration_days'])} 天"
    return {"membership": profile, "message": msg}


def handle_hwxun_notify(params: dict) -> str:
    key = (get_settings().xhs_pay_key or "").strip()
    if not key:
        return "fail"
    if not verify_notify_epay(params, key):
        return "fail"
    trade_status = str(params.get("trade_status") or "").upper()
    if trade_status != "TRADE_SUCCESS":
        return "success"
    order_no = str(params.get("out_trade_no") or "").strip()
    money = str(params.get("money") or "").strip()
    gateway_trade_no = str(params.get("trade_no") or "").strip()
    if not order_no:
        return "fail"
    row = db.get_payment_order(order_no)
    if not row:
        return "fail"
    if row["status"] == "paid":
        return "success"
    if f"{float(row['amount']):.2f}" != f"{float(money):.2f}":
        return "fail"
    paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = json.dumps({"order_no": order_no, "source": "hwxun_wxpay"}, ensure_ascii=False)
    codes = db.generate_auth_codes(
        count=1,
        plan_code=row["plan_code"],
        duration_days=int(row["duration_days"]),
        max_activations=1,
        note=note,
    )
    auth_code = codes[0] if codes else ""
    db.mark_payment_order_paid(
        order_no,
        gateway_trade_no=gateway_trade_no,
        auth_code=auth_code,
        paid_at=paid_at,
    )
    user_id = row.get("user_id")
    if user_id and auth_code:
        try:
            db.renew_with_auth_code(int(user_id), auth_code)
            db.mark_payment_order_fulfilled(order_no, int(user_id))
        except Exception:
            pass
    return "success"
