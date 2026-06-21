# -*- coding: utf-8 -*-
"""与桌面 gen_report（snapshot_phase1）对齐的 21 列常量。"""

REPORT_COLUMNS = [
    "goods_id", "title", "price", "sold", "actual_v1d", "v1d",
    "actual_gr", "actual_vsr", "vsr",
    "burst", "pool", "first_seen", "store_id", "store_name",
    "shop_sales", "shop_fans", "shop_fsr", "goods_fsr",
    "behavior", "is_virtual", "anomaly",
]

COL = {name: i for i, name in enumerate(REPORT_COLUMNS)}

DEFAULT_MIN_V1D = 5
DEFAULT_MIN_ACTUAL = 5
DEFAULT_MIN_V1D_VIRTUAL = 1
DEFAULT_MIN_ACTUAL_VIRTUAL = 1

REPORT_DISCLAIMER = (
    "本报告基于公开可见信息与系统扫描快照，指标含估算成分，非平台官方数据。"
    "仅供内部选品参考，禁止转售与违规用途。"
)

FIELD_GUIDE = [
    {"field": "商品ID", "key": "goods_id", "desc": "平台唯一标识，用于搜索与溯源。"},
    {"field": "商品名称", "key": "title", "desc": "抓取时的标题快照。"},
    {"field": "价格", "key": "price", "desc": "成交价（券后/活动价）。"},
    {"field": "销量", "key": "sold", "desc": "累计已售快照。"},
    {"field": "真实增量", "key": "actual_v1d", "desc": "自上次有效快照起的销量差值。"},
    {"field": "预估日增量", "key": "v1d", "desc": "按扫描间隔折算的日均估值。"},
    {"field": "真实日增速", "key": "actual_gr", "desc": "真实增量 / 基线销量 %。"},
    {"field": "真实增销比", "key": "actual_vsr", "desc": "真实增量 / 当前销量。"},
    {"field": "预估增销比", "key": "vsr", "desc": "预估日增量 / 当前销量。"},
    {"field": "店铺", "key": "store_name", "desc": "所属店铺名称。"},
    {"field": "池子", "key": "pool", "desc": "监控池分层：NEW/WATCH/ACCEL/BURST 等。"},
]

ARCHIVE_DAILY = "member_daily_zip"
ARCHIVE_WEEKLY = "member_weekly_zip"
ARCHIVE_MONTHLY = "member_monthly_zip"


def item_at(item: list, key: str, default=None):
    idx = COL.get(key)
    if idx is None or not isinstance(item, (list, tuple)) or idx >= len(item):
        return default
    val = item[idx]
    return default if val is None else val
