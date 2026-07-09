# -*- coding: utf-8 -*-
"""hwxun 易支付 V1（MD5）对接：mapi 下单 + 异步回调验签。"""
from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin

import requests

from cloud_deploy.cloud_api.config import get_settings


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


def create_wxpay_order(
    *,
    out_trade_no: str,
    amount: str,
    name: str,
    notify_url: str,
    clientip: str,
) -> dict[str, Any]:
    s = get_settings()
    pid = (s.xhs_pay_pid or "").strip()
    key = (s.xhs_pay_key or "").strip()
    api_url = (s.xhs_pay_api_url or "https://pay.hwxun.cn/").strip()
    if not pid or not key:
        raise RuntimeError("未配置 XHS_PAY_PID / XHS_PAY_KEY")

    params = {
        "pid": pid,
        "type": "wxpay",
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
