# -*- coding: utf-8 -*-
"""mock_intelligence 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.mock_intelligence import compare_categories, timeline_for_category, get_workflow_board


def test_compare():
    r = compare_categories(["美甲美睫", "小学教辅"])
    assert len(r["categories"]) == 2
    assert len(r["recommendation_order"]) == 2
    assert r["ai_summary"]


def test_timeline():
    r = timeline_for_category("美甲美睫", days=7)
    assert len(r["points"]) == 7
    assert r["ai_weekly"]


def test_workflow():
    b = get_workflow_board()
    assert len(b["columns"]) == 5


if __name__ == "__main__":
    test_compare()
    test_timeline()
    test_workflow()
    print("mock_intelligence tests OK")
