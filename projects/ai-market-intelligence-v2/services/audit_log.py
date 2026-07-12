# -*- coding: utf-8 -*-
"""实验室合规/LLM 审计日志（JSONL，Phase 2 可迁 PG compliance_audit_log）。

注意: 当前按天单文件追加,无轮转。Phase 2 上线前应接入 RotatingFileHandler
或改为按天滚动 + 保留 N 天策略,避免日志文件无限增长。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_DIR = Path(__file__).resolve().parents[1] / "output" / "audit"


def append_audit(event: str, payload: dict[str, Any]) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = AUDIT_DIR / f"audit_{day}.jsonl"
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def log_publish(
    *,
    report_date: str,
    category: str,
    llm_meta: dict[str, Any] | None = None,
    k_min: int = 5,
    sample_size: int = 0,
) -> Path:
    return append_audit(
        "insight_publish",
        {
            "report_date": report_date,
            "category": category,
            "sample_size": sample_size,
            "k_min": k_min,
            "llm": llm_meta or {},
        },
    )
