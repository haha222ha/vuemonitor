# -*- coding: utf-8 -*-
"""L1 insight_report_cache — LLM 批处理去重（REQ-CACHE-002）。"""
from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "agent-v1"


def _table_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = 'insight_report_cache'
            LIMIT 1
            """
        )
        return cur.fetchone() is not None


def get_cached_report(
    conn,
    metrics_hash: str,
    prompt_version: str = PROMPT_VERSION,
) -> dict[str, Any] | None:
    if not metrics_hash or not _table_exists(conn):
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT report_json FROM insight_report_cache
            WHERE metrics_hash = %s AND prompt_version = %s
            LIMIT 1
            """,
            (metrics_hash, prompt_version),
        )
        row = cur.fetchone()
    if not row:
        return None
    raw = row[0] if not isinstance(row, dict) else row.get("report_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


def upsert_cached_report(
    conn,
    metrics_hash: str,
    report_json: dict[str, Any],
    *,
    prompt_version: str = PROMPT_VERSION,
    llm_tokens_used: int = 0,
) -> None:
    if not metrics_hash or not report_json or not _table_exists(conn):
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO insight_report_cache (metrics_hash, prompt_version, report_json, llm_tokens_used)
            VALUES (%s, %s, %s::jsonb, %s)
            ON CONFLICT (metrics_hash, prompt_version) DO UPDATE SET
                report_json = EXCLUDED.report_json,
                llm_tokens_used = EXCLUDED.llm_tokens_used,
                created_at = NOW()
            """,
            (
                metrics_hash,
                prompt_version,
                json.dumps(report_json, ensure_ascii=False),
                int(llm_tokens_used or 0),
            ),
        )
    conn.commit()
