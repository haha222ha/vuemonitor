# -*- coding: utf-8 -*-
"""销量/增量合理性校验 — 过滤解析错误、店铺总销误写入等脏数据。"""
from __future__ import annotations

# 单品累计销量展示上限（小红书单品极少超过 20 万）
MAX_PLAUSIBLE_SOLD = 200_000
# 单次观测窗口内增量上限
MAX_PLAUSIBLE_DELTA = 50_000
# 增量占当前销量比例上限（超过则多为「首扫把总销当增量」或脏基准）
MAX_DELTA_SOLD_RATIO = 0.35


def is_dirty_sold_metrics(sold, actual=0, v1d=0, sold_prev=None):
    """
    判断销量/增量是否为脏数据。

    返回 (is_dirty: bool, reason: str)
    """
    sold = int(sold or 0)
    actual = float(actual or 0)
    v1d = float(v1d or 0)

    if sold <= 0:
        return False, ""

    if sold > MAX_PLAUSIBLE_SOLD:
        return True, f"sold>{MAX_PLAUSIBLE_SOLD}"

    if actual > MAX_PLAUSIBLE_DELTA:
        return True, f"actual>{MAX_PLAUSIBLE_DELTA}"

    if v1d > MAX_PLAUSIBLE_DELTA:
        return True, f"v1d>{MAX_PLAUSIBLE_DELTA}"

    if actual > sold or v1d > sold:
        return True, "increment>total_sold"

    if sold > 5000 and actual > 0 and actual >= sold * MAX_DELTA_SOLD_RATIO:
        return True, "actual_ratio_high"

    if sold > 5000 and v1d > 0 and v1d >= sold * MAX_DELTA_SOLD_RATIO:
        return True, "v1d_ratio_high"

    if sold_prev is not None:
        prev = int(sold_prev or 0)
        if prev > MAX_PLAUSIBLE_SOLD:
            return True, "prev_sold_dirty"
        if prev > 0 and sold - prev > MAX_PLAUSIBLE_DELTA:
            return True, "delta_from_prev_high"

    return False, ""


def clamp_sold_for_display(sold):
    """展示层钳制（可选）。"""
    s = int(sold or 0)
    return min(s, MAX_PLAUSIBLE_SOLD) if s > 0 else 0
