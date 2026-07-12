# -*- coding: utf-8 -*-
"""
L3/L4：从内部商品快照聚合为类目级指标（V2 实验室参考实现）。

输入：内部 rows（含 goods_id/title/store_name — 仅在本模块内使用，不得写入输出）
输出：InsightMetrics（无商品/店铺可定位字段）
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InsightMetrics:
    report_date: str
    category: str
    sub_category: str = ""
    window_days: int = 7
    sample_size: int = 0
    growth_rate_pct: float = 0.0
    competition_index: int = 0
    blue_ocean_score: int = 0
    heat_score: int = 0
    new_product_score: int = 0
    lifecycle_stage: str = "成长"
    season_score: int = 3
    price_band: str = ""
    trend_label: str = "平稳"
    top_keywords: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("sample_size", None)
        d["disclaimer"] = (
            "本报告基于公开市场趋势归纳，不构成对特定商品或店铺的建议。"
            "禁止将本报告用于定位、抄款或批量转售原始数据。"
        )
        return d


def _clamp(n: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def _infer_category(title: str) -> tuple[str, str]:
    t = (title or "").strip()
    rules = [
        (r"小学|语文|数学|英语|教辅|暑假|衔接", "小学教辅", "K12"),
        (r"美甲|穿戴甲|甲片", "美甲美睫", "美业"),
        (r"收纳|置物|整理", "家居收纳", "家居"),
        (r"宠物|猫|狗", "宠物用品", "宠物"),
    ]
    for pattern, cat, sub in rules:
        if re.search(pattern, t):
            return cat, sub
    return "综合类目", "其他"


def _price_band(price: float) -> str:
    if price <= 0:
        return "未知"
    bands = [(10, "0-10"), (20, "10-20"), (50, "20-50"), (100, "50-100"), (99999, "100+")]
    for upper, label in bands:
        if price <= upper:
            return label
    return "100+"


# 类目 × 月份 → 季节指数(1-5);Phase 2 应迁移至 config/category_taxonomy.yaml
_SEASON_RULES: dict[str, dict] = {
    "教辅": {"peak": (6, 7, 8), "high": (1, 2, 9), "peak_v": 5, "high_v": 4, "low_v": 2},
    "美甲": {"peak": (11, 12, 1), "high": (), "peak_v": 4, "high_v": 3, "low_v": 3},
}


def _season_score(category: str, report_date: str) -> int:
    try:
        month = int(str(report_date).split("-")[1])
    except (ValueError, IndexError):
        month = 7
    for key, rule in _SEASON_RULES.items():
        if key in category:
            if month in rule["peak"]:
                return rule["peak_v"]
            if month in rule["high"]:
                return rule["high_v"]
            return rule["low_v"]
    return 3


def _extract_keywords(titles: list[str], limit: int = 8) -> list[str]:
    freq: dict[str, int] = defaultdict(int)
    stop = {"的", "了", "和", "与", "款", "新", "包邮", "现货"}
    for title in titles:
        for part in re.split(r"[\s/|·\-—]+", title):
            part = part.strip()
            if 2 <= len(part) <= 8 and part not in stop:
                freq[part] += 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in ranked[:limit]]


def aggregate_items_to_insights(
    report_date: str,
    items: list[dict[str, Any]],
    *,
    window_days: int = 7,
) -> list[InsightMetrics]:
    """
    items 内部格式（实验室/mock）:
      { "title", "price", "actual_v1d", "v1d", "gr", "first_seen_days", "is_new" }
    生产环境从 PG 读取，在本函数入口前不得序列化 goods_id/store_name 到下游。
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    cat_sub_map: dict[str, str] = {}
    for it in items:
        cat, sub = _infer_category(str(it.get("title") or ""))
        buckets[cat].append(it)
        cat_sub_map[cat] = sub

    out: list[InsightMetrics] = []
    for category, rows in buckets.items():
        n = len(rows)
        if n == 0:
            continue
        actuals = [float(r.get("actual_v1d") or 0) for r in rows]
        growths = [float(r.get("gr") or 0) for r in rows]
        prices = [float(r.get("price") or 0) for r in rows if float(r.get("price") or 0) > 0]
        new_cnt = sum(1 for r in rows if r.get("is_new") or int(r.get("first_seen_days") or 99) <= 3)

        avg_actual = sum(actuals) / max(n, 1)
        avg_gr = sum(growths) / max(n, 1)
        # gr 统一为小数格式(0.28 = 28%),始终乘 100 转百分比
        growth_pct = _clamp(avg_gr * 100, 0, 100)

        # 竞争指数:样本量 + 价格离散度(Phase 2 应接入类目级基准数据)
        price_diversity = len({round(p) for p in prices}) if prices else 1
        competition = _clamp(n * 0.3 + price_diversity * 5, 0, 100)
        blue_ocean = _clamp(100 - competition * 0.6 + growth_pct * 0.4, 0, 100)
        heat = _clamp(avg_actual * 2 + growth_pct * 0.5, 0, 100)
        new_score = _clamp(new_cnt / max(n, 1) * 100 + 20, 0, 100)

        if growth_pct >= 30:
            trend = "连续上涨"
            lifecycle = "成长"
        elif growth_pct >= 10:
            trend = "温和上涨"
            lifecycle = "成长"
        elif growth_pct <= 3:
            trend = "平稳"
            lifecycle = "成熟"
        else:
            trend = "波动"
            lifecycle = "成熟"

        band = "综合"
        if prices:
            lo, hi = min(prices), max(prices)
            band = f"{int(lo)}-{int(hi)}" if hi - lo > 5 else _price_band(lo)

        titles = [str(r.get("title") or "") for r in rows]
        out.append(
            InsightMetrics(
                report_date=report_date,
                category=category,
                sub_category=cat_sub_map.get(category, ""),
                window_days=window_days,
                sample_size=n,
                growth_rate_pct=float(growth_pct),
                competition_index=competition,
                blue_ocean_score=blue_ocean,
                heat_score=heat,
                new_product_score=new_score,
                lifecycle_stage=lifecycle,
                season_score=_season_score(category, report_date),
                price_band=band,
                trend_label=trend,
                top_keywords=_extract_keywords(titles),
            )
        )
    out.sort(key=lambda x: (-x.blue_ocean_score, -x.growth_rate_pct))
    return out


def metrics_fingerprint(metrics: dict[str, Any]) -> str:
    raw = repr(sorted(metrics.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
