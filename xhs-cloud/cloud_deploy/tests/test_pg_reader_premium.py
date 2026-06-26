# -*- coding: utf-8 -*-
"""pg_reader 精品库报告行转换（无 PG）。"""
from cloud_deploy.reporting.constants import item_at
from cloud_deploy.reporting.pg_reader import merge_items_by_goods_id, premium_row_to_item


def test_premium_row_from_daily_snap():
    row = {
        "goods_id": "g1",
        "title": "测试商品",
        "deal_price": 19.9,
        "sold_num": 100,
        "pgd_sold": 120,
        "prev_sold": 100,
        "pgd_actual_delta": 20,
        "pgd_velocity": 25,
        "tier": "A",
        "store_id": "s1",
        "store_name": "店",
        "shop_fans": 1000,
        "shop_sales": 5000,
        "is_virtual": 0,
    }
    item = premium_row_to_item(row)
    assert item is not None
    assert item_at(item, "goods_id") == "g1"
    assert float(item_at(item, "actual_v1d")) == 20.0
    assert item_at(item, "pool") == "ACCEL"


def test_premium_row_rejects_zero_actual():
    row = {"goods_id": "g2", "sold_num": 50, "prev_sold": 50, "pgd_actual_delta": 0}
    assert premium_row_to_item(row) is None


def test_merge_items_by_goods_id():
    base = [["g1", "A", 0, 0, 0, 0, 10, 10] + [0] * 20]
    extra = [["g2", "B", 0, 0, 0, 0, 8, 8] + [0] * 20]
    merged = merge_items_by_goods_id(base, extra)
    ids = {item_at(it, "goods_id") for it in merged}
    assert ids == {"g1", "g2"}
