# -*- coding: utf-8 -*-
"""metric_engine 单元测试 — 验证 Issues #3,#4,#5,#6,#7 修复。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.metric_engine import (
    _price_band,
    _season_score,
    _infer_category,
    aggregate_items_to_insights,
)


# Issue #3: _price_band 不再有 no-op replace
def test_price_band_returns_clean_label():
    assert _price_band(5) == "0-10"
    assert _price_band(15.9) == "10-20"
    assert _price_band(30) == "20-50"
    assert _price_band(80) == "50-100"
    assert _price_band(200) == "100+"
    assert _price_band(0) == "未知"
    assert _price_band(-1) == "未知"


# Issue #6: season_score 不再硬编码为 3
def test_season_score_varies_by_category_and_month():
    # 教辅:暑假(7月)=5
    assert _season_score("小学教辅", "2026-07-12") == 5
    # 教辅:开学季(9月)=4
    assert _season_score("小学教辅", "2026-09-01") == 4
    # 教辅:淡季(3月)=2
    assert _season_score("小学教辅", "2026-03-15") == 2
    # 美甲:冬季(12月)=4
    assert _season_score("美甲美睫", "2026-12-01") == 4
    # 未覆盖类目:默认 3
    assert _season_score("未知类目", "2026-07-12") == 3
    # 日期格式异常:默认 7 月
    assert _season_score("小学教辅", "invalid") == 5


# Issue #7: sub_category 不再为空
def test_sub_category_is_populated():
    items = [
        {"title": "小学语文暑假衔接", "price": 15, "actual_v1d": 10, "gr": 0.2, "is_new": True},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    assert len(insights) == 1
    assert insights[0].sub_category == "K12"


def test_sub_category_for_pet():
    items = [
        {"title": "宠物猫粮", "price": 50, "actual_v1d": 5, "gr": 0.1},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    assert insights[0].sub_category == "宠物"


# Issue #4: growth_rate_pct 统一为小数 * 100
def test_growth_rate_pct_from_decimal():
    items = [
        {"title": "小学语文教辅", "price": 15, "actual_v1d": 10, "gr": 0.28},
        {"title": "小学数学教辅", "price": 15, "actual_v1d": 10, "gr": 0.32},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    # avg_gr = 0.30 → growth_pct = 30
    assert insights[0].growth_rate_pct == 30.0


def test_growth_rate_pct_clamped_to_100():
    items = [
        {"title": "小学语文教辅", "price": 15, "actual_v1d": 10, "gr": 1.5},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    # gr=1.5 → 150 → clamped to 100
    assert insights[0].growth_rate_pct == 100.0


# Issue #5: competition_index 不再仅基于 n/2.5
def test_competition_includes_price_diversity():
    items = [
        {"title": "小学语文教辅", "price": 10, "actual_v1d": 10, "gr": 0.2},
        {"title": "小学数学教辅", "price": 20, "actual_v1d": 10, "gr": 0.2},
        {"title": "小学英语教辅", "price": 30, "actual_v1d": 10, "gr": 0.2},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    # n=3, price_diversity=3 → 3*0.3 + 3*5 = 0.9 + 15 = 15.9 ≈ 16
    assert insights[0].competition_index > 10  # 不再是 n/2.5=1.2


def test_infer_category():
    cat, sub = _infer_category("小学语文暑假衔接练习册")
    assert cat == "小学教辅"
    assert sub == "K12"

    cat, sub = _infer_category("美甲穿戴甲片")
    assert cat == "美甲美睫"
    assert sub == "美业"

    cat, sub = _infer_category("随机商品")
    assert cat == "综合类目"
    assert sub == "其他"


def test_aggregate_multiple_categories():
    items = [
        {"title": "小学语文教辅", "price": 15, "actual_v1d": 10, "gr": 0.28},
        {"title": "美甲穿戴甲片", "price": 30, "actual_v1d": 50, "gr": 0.35},
    ]
    insights = aggregate_items_to_insights("2026-07-12", items)
    assert len(insights) == 2
    # 按 blue_ocean_score 降序排列
    assert insights[0].blue_ocean_score >= insights[1].blue_ocean_score


if __name__ == "__main__":
    test_price_band_returns_clean_label()
    test_season_score_varies_by_category_and_month()
    test_sub_category_is_populated()
    test_sub_category_for_pet()
    test_growth_rate_pct_from_decimal()
    test_growth_rate_pct_clamped_to_100()
    test_competition_includes_price_diversity()
    test_infer_category()
    test_aggregate_multiple_categories()
    print("metric_engine tests OK")
