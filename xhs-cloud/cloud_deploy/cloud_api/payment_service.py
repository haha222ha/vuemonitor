# -*- coding: utf-8 -*-
"""选品会员 hwxun 支付：下单、回调履约、订单查询。"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.config import get_settings
from cloud_deploy.cloud_api.hwxun_pay import channel_merchant_credentials, create_epay_order, verify_notify_epay
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


def list_payment_channels() -> list[dict]:
    """返回已配置凭证的支付方式（微信/支付宝 PID 独立）。"""
    labels = {"wxpay": "微信扫码", "alipay": "支付宝扫码"}
    out: list[dict] = []
    for ch in ("wxpay", "alipay"):
        try:
            channel_merchant_credentials(ch)
            out.append({"channel": ch, "label": labels[ch]})
        except RuntimeError:
            continue
    return out


def create_order(
    *,
    plan_code: str,
    user_id: int | None,
    client_ip: str,
    channel: str = "wxpay",
) -> dict:
    plan = get_plan(plan_code)
    if not plan:
        raise ValueError("无效套餐")
    pay_channel = (channel or "wxpay").strip().lower()
    if pay_channel not in ("wxpay", "alipay"):
        raise ValueError("支付方式仅支持 wxpay 或 alipay")
    order_no = _gen_order_no()
    expires_at = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    db.insert_payment_order(
        order_no=order_no,
        user_id=user_id,
        plan_code=plan["plan_code"],
        duration_days=int(plan["duration_days"]),
        amount=plan["amount"],
        channel=pay_channel,
        client_ip=client_ip,
        expires_at=expires_at,
    )
    gw = create_epay_order(
        channel=pay_channel,
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
        "channel": pay_channel,
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
        "channel": row.get("channel") or "wxpay",
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
            "auth_code": (row.get("auth_code") or "").strip(),
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
        "auth_code": code,
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
            return {
                "membership": profile,
                "message": "该订单已履约",
                "auth_code": (row.get("auth_code") or "").strip(),
            }
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
    return {"membership": profile, "message": msg, "auth_code": (code or "").strip()}


def handle_hwxun_notify(params: dict) -> str:
    order_no = str(params.get("out_trade_no") or "").strip()
    row = db.get_payment_order(order_no) if order_no else None
    ch = (row or {}).get("channel") or params.get("type") or "wxpay"
    try:
        expect_pid, key = channel_merchant_credentials(str(ch))
    except RuntimeError:
        return "fail"
    notify_pid = str(params.get("pid") or "").strip()
    if notify_pid and notify_pid != expect_pid:
        return "fail"
    if not verify_notify_epay(params, key):
        return "fail"
    trade_status = str(params.get("trade_status") or "").strip().upper()
    # 无 trade_status 时不可返回 success，否则网关认为已通知成功而不再重试
    if not trade_status:
        return "fail"
    if trade_status != "TRADE_SUCCESS":
        return "success"
    order_no = str(params.get("out_trade_no") or "").strip()
    money = str(params.get("money") or "").strip()
    gateway_trade_no = str(params.get("trade_no") or "").strip()
    if not order_no:
        return "fail"
    if not row:
        row = db.get_payment_order(order_no)
    if not row:
        return "fail"
    if row["status"] == "paid":
        return "success"
    if f"{float(row['amount']):.2f}" != f"{float(money):.2f}":
        return "fail"
    paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ch = row.get("channel") or "wxpay"
    note = json.dumps({"order_no": order_no, "source": f"hwxun_{ch}"}, ensure_ascii=False)
    codes = db.generate_auth_codes(
        count=1,
        plan_code=row["plan_code"],
        duration_days=int(row["duration_days"]),
        max_activations=1,
        note=note,
    )
    auth_code = codes[0] if codes else ""
    ok = db.mark_payment_order_paid(
        order_no,
        gateway_trade_no=gateway_trade_no,
        auth_code=auth_code,
        paid_at=paid_at,
    )
    if not ok:
        ok = db.mark_payment_order_paid_force(
            order_no,
            gateway_trade_no=gateway_trade_no,
            auth_code=auth_code,
            paid_at=paid_at,
        )
    if not ok:
        return "fail"
    user_id = row.get("user_id")
    if user_id and auth_code:
        try:
            db.renew_with_auth_code(int(user_id), auth_code)
            db.mark_payment_order_fulfilled(order_no, int(user_id))
        except Exception:
            pass
    return "success"
