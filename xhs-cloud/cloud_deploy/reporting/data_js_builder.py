# -*- coding: utf-8
"""生成 data.js 与报告目录。"""
from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from datetime import datetime
from typing import Any

from cloud_deploy.reporting.constants import (
    DEFAULT_MIN_ACTUAL,
    DEFAULT_MIN_ACTUAL_VIRTUAL,
    DEFAULT_MIN_V1D,
    DEFAULT_MIN_V1D_VIRTUAL,
    REPORT_COLUMNS,
    REPORT_DISCLAIMER,
)


def _agg(items: list) -> dict:
    physical = virtual = 0
    pool_map: Counter = Counter()
    for item in items:
        if item[24] == 1:
            virtual += 1
        elif item[24] == 0:
            physical += 1
        pool_map[item[14] or "WATCH"] += 1
    return {"physical_v1d": physical, "virtual_v1d": virtual, "pool_map": dict(pool_map)}


def build_report_payload(
    items: list,
    report_date: str,
    *,
    scope: str = "daily",
    scope_label: str = "",
    min_v1d=DEFAULT_MIN_V1D,
    min_actual=DEFAULT_MIN_ACTUAL,
    min_v1d_virtual=DEFAULT_MIN_V1D_VIRTUAL,
    min_actual_virtual=DEFAULT_MIN_ACTUAL_VIRTUAL,
    source: str = "cloud_gen_report",
    period_start: str = "",
    period_end: str = "",
) -> dict[str, Any]:
    now = datetime.now()
    agg = _agg(items)
    prices = sorted([item[2] for item in items if item[2] > 0])
    median_price = round(prices[len(prices) // 2], 1) if prices else 0
    avg_price = round(sum(prices) / len(prices), 1) if prices else 0
    avg_v1d = round(sum(item[7] for item in items) / len(items), 1) if items else 0
    actual_values = [item[6] for item in items if item[6] > 0]
    avg_actual_v1d = round(sum(actual_values) / len(actual_values), 1) if actual_values else 0

    filter_label = scope_label or (
        f"实体 v1d>{min_v1d}/真实>={min_actual}；"
        f"虚拟 v1d>{min_v1d_virtual}/真实>={min_actual_virtual}"
    )

    meta = {
        "date": report_date,
        "scope": scope,
        "period_start": period_start or report_date,
        "period_end": period_end or report_date,
        "filter_mode": "v1d_or_actual_split",
        "filter_label": filter_label,
        "min_v1d": min_v1d,
        "min_actual": min_actual,
        "min_v1d_virtual": min_v1d_virtual,
        "min_actual_virtual": min_actual_virtual,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "physical_v1d": agg["physical_v1d"],
        "virtual_v1d": agg["virtual_v1d"],
        "avg_price": avg_price,
        "median_price": median_price,
        "avg_v1d": avg_v1d,
        "avg_actual_v1d": avg_actual_v1d,
        "source": source,
        "disclaimer": REPORT_DISCLAIMER,
        "pool_new": agg["pool_map"].get("NEW", 0),
        "pool_watch": agg["pool_map"].get("WATCH", 0),
        "pool_accel": agg["pool_map"].get("ACCEL", 0),
        "pool_burst": agg["pool_map"].get("BURST", 0),
    }
    return {
        "meta": meta,
        "columns": REPORT_COLUMNS,
        "items": items,
        "charts": {},
        "top_keywords": [],
        "top_stores": [],
    }


def write_report_dir(
    output_dir: str,
    payload: dict,
    html_template: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    js_path = os.path.join(output_dir, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("var REPORT_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")

    html_dst = os.path.join(output_dir, "index_with_gr.html")
    if html_template and os.path.isfile(html_template):
        shutil.copy2(html_template, html_dst)
    elif not os.path.isfile(html_dst):
        with open(html_dst, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><meta charset=utf-8><title>选品报告</title></head>"
                    "<body><p>请配置 XHS_HTML_TEMPLATE 指向 index_with_gr.html</p>"
                    "<script src=data.js></script></body></html>")

    readme = os.path.join(output_dir, "README.txt")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(payload["meta"].get("disclaimer", "") + "\n解压后打开 index_with_gr.html\n")
    return output_dir


def resolve_output_dir(report_root: str, report_date: str, scope: str = "daily") -> str:
    d = report_date.replace("-", "")[4:]  # MMDD
    if scope == "daily":
        name = f"全量{d}"
    elif scope == "weekly":
        name = f"周报{d}"
    else:
        name = f"月报{report_date[:7].replace('-', '')}"
    return os.path.join(report_root, name)
