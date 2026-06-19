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

ARCHIVE_DAILY = "member_daily_zip"
ARCHIVE_WEEKLY = "member_weekly_zip"
ARCHIVE_MONTHLY = "member_monthly_zip"
