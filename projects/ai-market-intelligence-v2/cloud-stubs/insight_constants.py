# -*- coding: utf-8 -*-
"""V2 archive types — merge into cloud_deploy/reporting/constants.py"""
ARCHIVE_INSIGHT_DAILY = "insight_daily_html"
ARCHIVE_INSIGHT_WEEKLY = "insight_weekly_html"

INSIGHT_ARCHIVE_TYPES = frozenset({ARCHIVE_INSIGHT_DAILY, ARCHIVE_INSIGHT_WEEKLY})

INSIGHT_DISCLAIMER = (
    "本报告为 AI 归纳的市场趋势情报，基于类目级统计与公开信息分析，"
    "不包含可定位具体商品或店铺的数据，不构成投资建议或平台官方意见。"
)
