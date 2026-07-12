# -*- coding: utf-8 -*-
"""类目树加载与标题推断（Q1-A）。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "config" / "category_taxonomy.yaml"

_BUILTIN_RULES: list[tuple[str, str, str]] = [
    (r"小学|语文|数学|英语|教辅|暑假|衔接", "小学教辅", "K12"),
    (r"美甲|穿戴甲|甲片", "美甲美睫", "美业"),
    (r"收纳|置物|整理", "家居收纳", "家居"),
    (r"宠物|猫|狗", "宠物用品", "宠物"),
]


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    fallback = {"category": "综合类目", "sub_category": "其他"}
    rules: list[tuple[str, str, str]] = []
    if not _TAXONOMY_PATH.is_file():
        return {"fallback": fallback, "rules": _BUILTIN_RULES}
    try:
        import yaml

        raw = yaml.safe_load(_TAXONOMY_PATH.read_text(encoding="utf-8")) or {}
        fallback = raw.get("fallback") or fallback
        for item in raw.get("rules") or []:
            if not isinstance(item, dict):
                continue
            pat = str(item.get("pattern") or "").strip()
            cat = str(item.get("category") or "").strip()
            sub = str(item.get("sub_category") or "").strip()
            if pat and cat:
                rules.append((pat, cat, sub or "其他"))
    except Exception:
        rules = list(_BUILTIN_RULES)
    if not rules:
        rules = list(_BUILTIN_RULES)
    return {"fallback": fallback, "rules": rules}


def infer_category(
    title: str,
    *,
    behavior: str = "",
    is_virtual: bool | None = None,
) -> tuple[str, str]:
    """标题 + 可选行为标签 → (category, sub_category)。"""
    t = (title or "").strip()
    ctx = f"{t} {behavior or ''}"
    tax = load_taxonomy()
    for pattern, cat, sub in tax["rules"]:
        if re.search(pattern, ctx, flags=re.IGNORECASE):
            return cat, sub
    fb = tax.get("fallback") or {}
    cat = str(fb.get("category") or "综合类目")
    sub = str(fb.get("sub_category") or "其他")
    if is_virtual is True and cat == "综合类目":
        return "虚拟综合", "虚拟"
    return cat, sub
