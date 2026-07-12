# -*- coding: utf-8 -*-
"""
合规发布网关 — 所有对外 JSON/HTML 必须经过此模块。

对标：Policy-First Release Boundary（TrustDS / Google PPI 轻量落地版）
"""
from __future__ import annotations

import re
from typing import Any

# 对外禁止出现的字段名（含变体）
FORBIDDEN_KEYS = frozenset({
    "goods_id", "goodsId", "product_id", "productId", "sku", "sku_id",
    "store_id", "storeId", "shop_id", "shopId", "seller_id",
    "product_title", "goods_title", "商品名称", "店铺名称",
    "store_name", "shop_name", "seller_name", "shopName",
    "url", "link", "product_url", "goods_url", "image_url", "img_url",
    "columns", "items", "REPORT_DATA", "data.js",
})

# 预计算小写集合,避免 _scan_dict 每次迭代重建
FORBIDDEN_KEYS_LOWER = frozenset(x.lower() for x in FORBIDDEN_KEYS)

# HTML 禁止模式（可定位实体）
FORBIDDEN_HTML_PATTERNS = [
    re.compile(r"goods_id\s*[:=]", re.I),
    re.compile(r"store_id\s*[:=]", re.I),
    re.compile(r"REPORT_DATA\s*="),
    re.compile(r"xhslink\.com", re.I),
    re.compile(r"xiaohongshu\.com/goods", re.I),
]

# AI 输出禁止建议（内容安全轻量规则）
FORBIDDEN_ADVICE_PATTERNS = [
    re.compile(r"1\s*[:：]\s*1\s*抄", re.I),
    re.compile(r" guaranteed?\s+profit", re.I),
    re.compile(r"保证.{0,6}收益"),
    re.compile(r"刷单|刷量|伪造销量"),
]


class ComplianceViolation(Exception):
    def __init__(self, message: str, *, field: str = "", rule: str = ""):
        super().__init__(message)
        self.field = field
        self.rule = rule


class ComplianceGate:
    """对外发布前的最后一道关卡。"""

    @classmethod
    def sanitize_dict(cls, data: dict[str, Any], *, path: str = "") -> dict[str, Any]:
        cls._scan_dict(data, path)
        return data

    @classmethod
    def audit_report(cls, report: dict[str, Any], metrics: dict[str, Any]) -> None:
        cls.sanitize_dict(metrics)
        cls.sanitize_dict(report)
        text_blob = " ".join(str(v) for v in _walk_values(report))
        for pat in FORBIDDEN_ADVICE_PATTERNS:
            if pat.search(text_blob):
                raise ComplianceViolation(
                    f"AI 输出含禁止建议类型: {pat.pattern}",
                    rule="content_safety",
                )

    @classmethod
    def audit_html(cls, html: str) -> None:
        for pat in FORBIDDEN_HTML_PATTERNS:
            if pat.search(html):
                raise ComplianceViolation(
                    f"HTML 含禁止模式: {pat.pattern}",
                    rule="html_forbidden",
                )
        if "goods_id" in html.lower() or "store_name" in html.lower():
            raise ComplianceViolation("HTML 含敏感字段名", rule="html_field")

    @classmethod
    def _scan_dict(cls, obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_lower = str(k).lower()
                if key_lower in FORBIDDEN_KEYS_LOWER:
                    raise ComplianceViolation(
                        f"对外数据含禁止字段: {path}.{k}",
                        field=str(k),
                        rule="field_blacklist",
                    )
                cls._scan_dict(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                cls._scan_dict(item, f"{path}[{i}]")


def _walk_values(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_values(v)
    else:
        yield obj


def assert_publishable(
    metrics: dict,
    report: dict,
    html: str,
    *,
    k_min: int = 5,
) -> None:
    """管道发布前调用；失败则 abort publish。"""
    gate = ComplianceGate()
    _check_k_anonymity(metrics, k_min=k_min)
    gate.audit_report(report, metrics)
    gate.audit_html(html)


def _check_k_anonymity(metrics: dict[str, Any], *, k_min: int = 5) -> None:
    """小样本类目可能反推单品，拒绝发布。"""
    if "sample_size" not in metrics:
        return
    n = int(metrics.get("sample_size") or 0)
    if n < k_min:
        raise ComplianceViolation(
            f"样本量 {n} < k={k_min}，存在 re-identification 风险",
            field="sample_size",
            rule="k_anonymity",
        )
