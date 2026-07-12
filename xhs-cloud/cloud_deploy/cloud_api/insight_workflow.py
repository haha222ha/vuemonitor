# -*- coding: utf-8 -*-
"""工作流进货回填（REQ-RET-020 骨架）。"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _table_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = 'member_insight_workflow'
            LIMIT 1
            """
        )
        return cur.fetchone() is not None


def list_workflow(conn, user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
    if not _table_exists(conn):
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, category, report_date, status, outcome, note, remind_at, updated_at
            FROM member_insight_workflow
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(
                {
                    "id": row.get("id"),
                    "category": row.get("category"),
                    "report_date": str(row.get("report_date") or "")[:10] or None,
                    "status": row.get("status"),
                    "outcome": row.get("outcome"),
                    "note": row.get("note"),
                    "remind_at": str(row.get("remind_at") or "")[:10] or None,
                }
            )
        else:
            out.append(
                {
                    "id": row[0],
                    "category": row[1],
                    "report_date": str(row[2] or "")[:10] or None,
                    "status": row[3],
                    "outcome": row[4],
                    "note": row[5],
                    "remind_at": str(row[6] or "")[:10] or None,
                }
            )
    return out


def upsert_workflow(
    conn,
    user_id: int,
    *,
    category: str,
    report_date: str | None = None,
    status: str = "stocked",
    outcome: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if not _table_exists(conn):
        raise RuntimeError("workflow 表未迁移")
    category = (category or "").strip()
    remind = (date.today() + timedelta(days=30)).isoformat()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO member_insight_workflow
                (user_id, category, report_date, status, outcome, note, remind_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s::date)
            RETURNING id
            """,
            (
                user_id,
                category,
                (report_date or None)[:10] if report_date else None,
                status,
                outcome,
                note,
                remind,
            ),
        )
        row = cur.fetchone()
        wid = row[0] if row and not isinstance(row, dict) else (row or {}).get("id")
    conn.commit()
    return {"id": wid, "category": category, "status": status, "remind_at": remind}
