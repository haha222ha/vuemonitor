# -*- coding: utf-8 -*-
"""智能提醒 mock（基于类目指标规则，output/notifications.json）。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from services.metric_engine import aggregate_items_to_insights
from services.subscription_mock import _load_plans_config
from samples.mock_items import MOCK_ITEMS

NOTIF_PATH = Path(__file__).resolve().parents[1] / "output" / "notifications.json"


def _load_notif() -> dict[str, Any]:
    if NOTIF_PATH.is_file():
        try:
            return json.loads(NOTIF_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"items": [], "read_ids": []}


def _save_notif(data: dict[str, Any]) -> None:
    NOTIF_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTIF_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_alerts(report_date: str = "2026-07-12") -> list[dict[str, Any]]:
    cfg = _load_plans_config()
    rules = cfg.get("notification_rules") or {}
    blue_min = int(rules.get("blue_ocean_above") or 75)
    growth_min = float(rules.get("growth_above_pct") or 25)

    insights = aggregate_items_to_insights(report_date, MOCK_ITEMS)
    alerts: list[dict[str, Any]] = []

    now = datetime.now().isoformat()
    for m in insights:
        if m.blue_ocean_score >= blue_min:
            alerts.append({
                "id": f"alert-blue-{m.category}",
                "type": "opportunity",
                "title": f"「{m.category}」蓝海指数突破 {blue_min}",
                "body": f"当前蓝海 {m.blue_ocean_score}，增速 {m.growth_rate_pct:.0f}%，建议查看今日情报。",
                "category": m.category,
                "report_date": report_date,
                "created_at": now,
                "priority": "high" if m.blue_ocean_score >= 85 else "normal",
            })
        if m.growth_rate_pct >= growth_min:
            alerts.append({
                "id": f"alert-growth-{m.category}",
                "type": "trend",
                "title": f"「{m.category}」增速达 {m.growth_rate_pct:.0f}%",
                "body": f"趋势标签：{m.trend_label}，竞争指数 {m.competition_index}。",
                "category": m.category,
                "report_date": report_date,
                "created_at": now,
                "priority": "normal",
            })
        if m.competition_index >= 70:
            alerts.append({
                "id": f"alert-comp-{m.category}",
                "type": "risk",
                "title": f"「{m.category}」竞争偏高",
                "body": f"竞争指数 {m.competition_index}，进入前请评估差异化与供应链。",
                "category": m.category,
                "report_date": report_date,
                "created_at": now,
                "priority": "normal",
            })

    alerts.append({
        "id": "alert-legacy-expiry",
        "type": "account",
        "title": "Legacy 数据包履约剩余 45 天",
        "body": "到期后将切换为 AI 市场情报，不含 data.js 下载。可提前体验 V2 Tab。",
        "category": "",
        "report_date": report_date,
        "created_at": now,
        "priority": "low",
    })
    return alerts


def list_notifications(*, refresh: bool = False) -> dict[str, Any]:
    data = _load_notif()
    if refresh or not data.get("items"):
        data["items"] = _generate_alerts()
        _save_notif(data)
    read_ids = set(data.get("read_ids") or [])
    items = []
    unread = 0
    for it in data["items"]:
        item = dict(it)
        item["read"] = it["id"] in read_ids
        if not item["read"]:
            unread += 1
        items.append(item)
    items.sort(key=lambda x: (0 if x.get("priority") == "high" else 1 if x.get("priority") == "normal" else 2))
    return {"items": items, "unread_count": unread}


def mark_read(notification_id: str) -> dict[str, Any]:
    data = _load_notif()
    read_ids = list(data.get("read_ids") or [])
    if notification_id not in read_ids:
        read_ids.append(notification_id)
    data["read_ids"] = read_ids
    _save_notif(data)
    return list_notifications()


def mark_all_read() -> dict[str, Any]:
    data = _load_notif()
    if not data.get("items"):
        data["items"] = _generate_alerts()
    data["read_ids"] = [it["id"] for it in data["items"]]
    _save_notif(data)
    return list_notifications()
