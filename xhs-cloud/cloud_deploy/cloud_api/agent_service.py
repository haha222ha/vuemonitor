# -*- coding: utf-8 -*-
"""本地 Agent 拉取 risk 工单 + 回传扫描结果（服务端 PG 写入）。"""
from __future__ import annotations

from collections import Counter
from datetime import date

from cloud_deploy.cloud_api.sync_service import mark_scan_result, record_cloud_scan


def list_risk_worklist(conn, scan_date: str, limit: int, include_pending: bool = False) -> dict:
    day_start = scan_date
    with conn.cursor() as c:
        c.execute("SET search_path TO xhs_monitor, public")
        pending = None
        if include_pending:
            c.execute(
                """SELECT COUNT(*) FROM monitor_goods
                   WHERE monitor_status IN ('active', 'idle')
                     AND last_scan_status = 'risk'
                     AND last_scan_at >= %s::date
                     AND last_scan_at < (%s::date + INTERVAL '1 day')""",
                (day_start, day_start),
            )
            pending = int(c.fetchone()[0] or 0)
        c.execute(
            """SELECT goods_id, title
               FROM monitor_goods
               WHERE monitor_status IN ('active', 'idle')
                 AND last_scan_status = 'risk'
                 AND last_scan_at >= %s::date
                 AND last_scan_at < (%s::date + INTERVAL '1 day')
               ORDER BY priority_score DESC NULLS LAST
               LIMIT %s""",
            (day_start, day_start, limit),
        )
        items = [{"goods_id": str(r[0]), "title": r[1] or ""} for r in c.fetchall()]
    return {
        "scan_date": scan_date,
        "pending_risk": pending,
        "items": items,
    }


def slim_detail(detail: dict | None) -> dict:
    if not isinstance(detail, dict):
        return {}
    keys = (
        "deal_price",
        "product_price",
        "product_name",
        "title",
        "shop_id",
        "store_id",
        "shop_name",
        "store_name",
        "real_sales",
        "product_sales",
    )
    return {k: detail[k] for k in keys if k in detail and detail[k] not in (None, "")}


def apply_local_scan_row(conn, row: dict, data_source: str = "local_playwright") -> str:
    gid = str(row.get("goods_id") or "")
    if not gid:
        return "skip"
    status = str(row.get("status") or "fail")
    engine = str(row.get("engine") or "playwright")[:32]
    detail = slim_detail(row.get("detail"))

    if status == "ok" and row.get("sold") is not None:
        deal_price = row.get("deal_price")
        if deal_price is None:
            try:
                deal_price = float(detail.get("deal_price") or detail.get("product_price") or 0)
            except (TypeError, ValueError):
                deal_price = None
        record_cloud_scan(
            conn,
            gid,
            int(row["sold"]),
            data_source=data_source,
            deal_price=deal_price,
            detail=detail or None,
        )
        mark_scan_result(conn, gid, "ok", engine=engine)
        return "ok"
    if status == "frozen":
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                "UPDATE monitor_goods SET monitor_status='delisted', updated_at=NOW() WHERE goods_id=%s",
                (gid,),
            )
        conn.commit()
        mark_scan_result(conn, gid, "frozen", engine=engine)
        return "frozen"
    mark_scan_result(conn, gid, status if status in ("risk", "fail") else "fail", engine=engine)
    return status if status in ("risk", "fail") else "fail"


def apply_local_scan_batch(
    conn,
    rows: list[dict],
    *,
    agent_id: str = "",
    batch_id: str = "",
    data_source: str = "local_playwright",
) -> dict:
    outcomes = Counter()
    for row in rows:
        try:
            outcomes[apply_local_scan_row(conn, row, data_source=data_source)] += 1
        except Exception:
            outcomes["error"] += 1
    note = f"local_agent:{agent_id or 'unknown'}:{batch_id or '-'}"
    try:
        from cloud_deploy.cloud_api.sync_service import record_daemon_batch_stats

        record_daemon_batch_stats(
            conn,
            len(rows),
            outcomes.get("ok", 0),
            outcomes.get("fail", 0) + outcomes.get("error", 0),
            outcomes.get("risk", 0),
            outcomes.get("frozen", 0),
            0,
            note[:512],
        )
    except Exception:
        pass
    return {
        "batch_id": batch_id,
        "agent_id": agent_id,
        "received": len(rows),
        "ok": outcomes.get("ok", 0),
        "risk": outcomes.get("risk", 0),
        "fail": outcomes.get("fail", 0),
        "frozen": outcomes.get("frozen", 0),
        "error": outcomes.get("error", 0),
        "scan_date": date.today().isoformat(),
    }
