# -*- coding: utf-8 -*-
"""顾问输出合规裁剪。"""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEYS = frozenset({
    "goods_id",
    "product_id",
    "store_id",
    "shop_id",
    "store_name",
    "shop_name",
    "goods_url",
    "product_url",
})

_GOODS_ID_RE = re.compile(r"\b\d{15,20}\b")


def sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    """移除 context 中不应进入 LLM 的标识字段（浅层）。"""
    if not isinstance(context, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in context.items():
        if k in _SENSITIVE_KEYS:
            continue
        if isinstance(v, list):
            out[k] = [sanitize_context(x) if isinstance(x, dict) else x for x in v[:200]]
        elif isinstance(v, dict):
            out[k] = sanitize_context(v)
        else:
            out[k] = v
    return out


def validate_advisory_output(advice: dict[str, Any]) -> None:
    """发布前扫描 advice 是否含 goods_id / 店铺名等。"""
    blob = str(advice)
    if _GOODS_ID_RE.search(blob):
        raise ValueError("advice 含疑似 goods_id")
    for key in _SENSITIVE_KEYS:
        if f'"{key}"' in blob or f"'{key}'" in blob:
            raise ValueError(f"advice 含敏感字段 {key}")
