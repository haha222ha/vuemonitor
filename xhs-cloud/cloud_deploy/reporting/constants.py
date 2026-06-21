# -*- coding: utf-8 -*-
"""与 gen_report 对齐的常量（独立副本，不 import gen_report）。"""

REPORT_COLUMNS = [
    "goods_id", "title", "price", "sold", "v1h", "v6h", "actual_v1d", "v1d",
    "actual_gr", "gr", "actual_vsr", "vsr", "acc", "burst",
    "pool", "first_seen", "store_id", "store_name", "shelf_time",
    "shop_sales", "shop_fans", "shop_fsr", "goods_fsr",
    "behavior", "is_virtual", "base_hours", "base_at", "anomaly",
]

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
    {"field": "真实日增量", "key": "actual_v1d", "desc": "相对昨日销量的真实增量。"},
    {"field": "预估日增量", "key": "v1d", "desc": "系统估算日增量（本地报告含24h缩放）。"},
    {"field": "实际日增速", "key": "actual_gr", "desc": "真实日增量 / 基线销量 %。"},
    {"field": "实际增销比", "key": "actual_vsr", "desc": "真实日增量 / 当前销量。"},
    {"field": "店铺", "key": "store_name", "desc": "所属店铺名称。"},
    {"field": "池子", "key": "pool", "desc": "监控池分层：NEW/WATCH/ACCEL/BURST 等。"},
]

ARCHIVE_DAILY = "member_daily_zip"
ARCHIVE_WEEKLY = "member_weekly_zip"
ARCHIVE_MONTHLY = "member_monthly_zip"
