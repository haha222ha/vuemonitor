# -*- coding: utf-8 -*-
"""加载实验室 .env（不覆盖已存在的环境变量）。"""
from __future__ import annotations

import os
from pathlib import Path


def load_lab_env(root: Path | None = None) -> Path | None:
    root = root or Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)
    return env_path
