# -*- coding: utf-8 -*-
"""
选品报告 & 详情补全面板 — 统一高增量候选口径（双赛道分档）。

与 gen_report.py 一致:
  虚拟: velocity_1d > 1  OR actual_velocity_1d >= 1
  实体: velocity_1d > 5  OR actual_velocity_1d >= 5
"""
from __future__ import annotations

MIN_V1D_PHYSICAL = 5
MIN_ACTUAL_PHYSICAL = 5
MIN_V1D_VIRTUAL = 1
MIN_ACTUAL_VIRTUAL = 1

ACTIVE_LIFECYCLE_WHERE = "lifecycle IN (0,1,2)"

METRIC_CAP_WHERE = (
    "sold_num <= 200000 "
    "AND (actual_velocity_1d IS NULL OR actual_velocity_1d <= 50000) "
    "AND (velocity_1d IS NULL OR velocity_1d <= 50000)"
)

SCOPE_LABEL = "虚拟 v1d>1/真实≥1；实体 v1d>5/真实≥5（同选品报告）"


def thresholds_for(is_virtual: bool) -> tuple[float, float]:
    if is_virtual:
        return MIN_V1D_VIRTUAL, MIN_ACTUAL_VIRTUAL
    return MIN_V1D_PHYSICAL, MIN_ACTUAL_PHYSICAL


def increment_sql(is_virtual: bool) -> tuple[str, tuple]:
    """单赛道高增量 WHERE（不含 detail_fetched）。"""
    th_v1d, th_actual = thresholds_for(is_virtual)
    iv = 1 if is_virtual else 0
    where = (
        f"is_virtual = {iv} AND {ACTIVE_LIFECYCLE_WHERE} AND {METRIC_CAP_WHERE} "
        f"AND (velocity_1d > ? OR COALESCE(actual_velocity_1d, 0) >= ?)"
    )
    return where, (th_v1d, th_actual)


def combined_increment_sql() -> str:
    """虚拟+实体合并高增量条件。"""
    return (
        f"{ACTIVE_LIFECYCLE_WHERE} AND {METRIC_CAP_WHERE} AND ("
        f"(is_virtual = 1 AND (velocity_1d > {MIN_V1D_VIRTUAL} OR COALESCE(actual_velocity_1d, 0) >= {MIN_ACTUAL_VIRTUAL}))"
        f" OR "
        f"(is_virtual = 0 AND (velocity_1d > {MIN_V1D_PHYSICAL} OR COALESCE(actual_velocity_1d, 0) >= {MIN_ACTUAL_PHYSICAL}))"
        f")"
    )


def candidate_where_clause() -> str:
    """gen_report 参数化 WHERE 模板。"""
    return (
        f"{ACTIVE_LIFECYCLE_WHERE} "
        f"AND (velocity_1d > ? OR actual_velocity_1d >= ?) "
        f"AND sold_num <= 200000 "
        f"AND (actual_velocity_1d IS NULL OR actual_velocity_1d <= 50000) "
        f"AND (velocity_1d IS NULL OR velocity_1d <= 50000)"
    )
