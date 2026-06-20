# -*- coding: utf-8 -*-
"""爬虫路径（云端精简模块）。"""
from __future__ import annotations

import os

APP_DIR = os.environ.get("XHS_CRAWLER_ROOT", "").strip() or os.path.dirname(
    os.path.abspath(__file__)
)
DATA_DIR = os.path.join(APP_DIR, "crawl_data")


def ensure_data_dirs() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return DATA_DIR


def dp_user_data_dir(profile_id: int = 77) -> str:
    path = os.path.join(ensure_data_dirs(), f"dp_profile_{int(profile_id)}")
    os.makedirs(path, exist_ok=True)
    return path
