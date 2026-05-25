# AIGC START
"""决策报告展示分类推断（与前端 web-intel/src/utils/reports.ts 规则一致）"""
from __future__ import annotations

import os
import re


def _basename(path: str | None) -> str:
    if not path:
        return ""
    return os.path.basename(path.split("?")[0])


def infer_display_type(report_type: str, title: str, content_html: str | None) -> str:
    fn = _basename(content_html).lower()
    t = title or ""

    if fn.startswith("weekly_"):
        return "weekly"
    if fn.startswith("monthly_"):
        return "monthly"
    if fn.startswith("quarterly_"):
        return "quarterly"
    if fn.startswith("daily_"):
        return "daily"

    if re.search(r"^DIH-|选题|路径决策|副业决策报告", t, re.I) or re.match(r"^DIH-", fn, re.I):
        return "topic"
    if re.search(r"^T20\d{8,}", t) or re.search(r"^T20\d{8,}", fn):
        return "topic"

    if report_type == "topic":
        return "topic"
    if report_type in ("weekly", "monthly", "quarterly", "daily"):
        return report_type
    return report_type or "other"


def extract_topic_id(title: str, content_html: str | None) -> str | None:
    fn = _basename(content_html)
    for src in (title, fn):
        m = re.search(r"T20\d{8,}", src)
        if m:
            return m.group(0)
    return None


def filter_items_for_plan(plan: str, items: list[dict]) -> list[dict]:
    if plan == "weekly":
        return [i for i in items if i.get("display_type") == "weekly"]
    if plan == "monthly":
        return [i for i in items if i.get("display_type") in ("weekly", "monthly", "topic")]
    return items
# AIGC END
