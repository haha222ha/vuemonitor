# -*- coding: utf-8 -*-
"""hwxun 易支付 V1（MD5）对接：mapi 下单 + 异步回调验签。

微信网关：https://pay.hwxun.cn/mapi.php  type=wxpay
支付宝网关：https://xapay.hwxun.cn/mapi.php  type=alipay
商户后台（支付宝云端）：https://xapay.hwxun.cn/user/
"""
from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin

import requests

from cloud_deploy.cloud_api.config import get_settings

PAY_CHANNELS = {
    "wxpay": {
        "type": "wxpay",
        "api_env": "xhs_pay_api_url",
        "default_api": "https://pay.hwxun.cn/",
        "pid_env": "xhs_pay_pid",
        "key_env": "xhs_pay_key",
    },
    "alipay": {
        "type": "alipay",
        "api_env": "xhs_pay_alipay_api_url",
        "default_api": "https://xapay.hwxun.cn/",
        "pid_env": "xhs_pay_alipay_pid",
        "key_env": "xhs_pay_alipay_key",
        "pid_fallback": "xhs_pay_pid",
        "key_fallback": "xhs_pay_key",
    },
}


def _epay_sign(params: dict[str, Any], key: str) -> str:
    items = [(k, str(v)) for k, v in params.items() if k not in ("sign", "sign_type") and v not in (None, "")]
    items.sort(key=lambda x: x[0])
    prestr = "&".join(f"{k}={v}" for k, v in items)
    return hashlib.md5((prestr + key).encode()).hexdigest()


def verify_notify_epay(params: dict[str, Any], key: str) -> bool:
    sign = str(params.get("sign") or "").strip()
    if not sign:
        return False
    expect = _epay_sign(params, key)
    return sign.lower() == expect.lower()


def _channel_credentials(channel: str) -> tuple[str, str, str]:
    """返回 (api_url, pid, key)。"""
    ch = (channel or "wxpay").strip().lower()
    meta = PAY_CHANNELS.get(ch)
    if not meta:
        raise ValueError(f"不支持的支付方式: {channel}")
    s = get_settings()
    api_url = (getattr(s, meta["api_env"], "") or meta["default_api"]).strip()
    pid = (getattr(s, meta["pid_env"], "") or "").strip()
    key = (getattr(s, meta["key_env"], "") or "").strip()
    if not pid and meta.get("pid_fallback"):
        pid = (getattr(s, meta["pid_fallback"], "") or "").strip()
    if not key and meta.get("key_fallback"):
        key = (getattr(s, meta["key_fallback"], "") or "").strip()
    if not pid or not key:
        raise RuntimeError(f"未配置 {meta['pid_env']} / {meta['key_env']}（或微信共用 PID/KEY）")
    return api_url, pid, key


def notify_verify_key_for_order(channel: str) -> str:
    """按订单 channel 取回调验签密钥。"""
    ch = (channel or "wxpay").strip().lower()
    meta = PAY_CHANNELS.get(ch) or PAY_CHANNELS["wxpay"]
    s = get_settings()
    key = (getattr(s, meta["key_env"], "") or "").strip()
    if not key and meta.get("key_fallback"):
        key = (getattr(s, meta["key_fallback"], "") or "").strip()
    return key


def create_epay_order(
    *,
    channel: str,
    out_trade_no: str,
    amount: str,
    name: str,
    notify_url: str,
    clientip: str,
) -> dict[str, Any]:
    ch = (channel or "wxpay").strip().lower()
    meta = PAY_CHANNELS.get(ch)
    if not meta:
        raise ValueError(f"不支持的支付方式: {channel}")
    api_url, pid, key = _channel_credentials(ch)
    params = {
        "pid": pid,
        "type": meta["type"],
        "out_trade_no": out_trade_no,
        "notify_url": notify_url,
        "name": name[:127],
        "money": f"{float(amount):.2f}",
        "clientip": clientip or "127.0.0.1",
        "device": "pc",
    }
    params["sign"] = _epay_sign(params, key)
    params["sign_type"] = "MD5"

    endpoint = urljoin(api_url.rstrip("/") + "/", "mapi.php")
    resp = requests.post(endpoint, data=params, timeout=30)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"支付网关返回非 JSON: {resp.text[:200]}") from e
    if int(data.get("code") or 0) != 1:
        raise RuntimeError(str(data.get("msg") or data.get("message") or "下单失败"))
    return data


def create_wxpay_order(
    *,
    out_trade_no: str,
    amount: str,
    name: str,
    notify_url: str,
    clientip: str,
) -> dict[str, Any]:
    return create_epay_order(
        channel="wxpay",
        out_trade_no=out_trade_no,
        amount=amount,
        name=name,
        notify_url=notify_url,
        clientip=clientip,
    )


def create_alipay_order(
    *,
    out_trade_no: str,
    amount: str,
    name: str,
    notify_url: str,
    clientip: str,
) -> dict[str, Any]:
    return create_epay_order(
        channel="alipay",
        out_trade_no=out_trade_no,
        amount=amount,
        name=name,
        notify_url=notify_url,
        clientip=clientip,
    )
