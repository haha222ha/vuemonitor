# -*- coding: utf-8 -*-
"""加载 UX 文案配置。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

UX_COPY_PATH = Path(__file__).resolve().parents[1] / "config" / "ux_copy.yaml"


@lru_cache(maxsize=1)
def load_ux_copy() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return _fallback()
    if not UX_COPY_PATH.is_file():
        return _fallback()
    return yaml.safe_load(UX_COPY_PATH.read_text(encoding="utf-8")) or _fallback()


def _fallback() -> dict[str, Any]:
    return {
        "ai": {"badge": "AI 辅助生成", "footer": "本内容由 AI 辅助生成，仅供市场研究参考。"},
        "feedback": {"success": "已收到反馈。"},
    }
