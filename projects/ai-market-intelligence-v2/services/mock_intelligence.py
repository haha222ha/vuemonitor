# -*- coding: utf-8 -*-
"""
进阶情报 mock 数据（对比 / 时间轴 / 工作流）— 无 PG 实连。

指标均来自 metric_engine 聚合结果 + 确定性扰动，保证可复现。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from services.metric_engine import InsightMetrics, aggregate_items_to_insights
from samples.mock_items import MOCK_ITEMS

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "output" / "workflow_board.json"

RADAR_DIMS = [
    ("growth_rate_pct", "增速"),
    ("blue_ocean_score", "蓝海"),
    ("heat_score", "热度"),
    ("new_product_score", "新品"),
    ("competition_index", "竞争"),
]

# 竞争指数雷达展示时反转(越高越好 → 100-comp)
INVERT_FOR_RADAR = {"competition_index"}


def _insights_by_date(report_date: str) -> dict[str, InsightMetrics]:
    rows = aggregate_items_to_insights(report_date, MOCK_ITEMS)
    return {m.category: m for m in rows}


def _seed(category: str, salt: str = "") -> int:
    h = hashlib.md5(f"{category}:{salt}".encode()).hexdigest()
    return int(h[:8], 16)


def metrics_for_category(category: str, report_date: str = "2026-07-12") -> dict[str, Any] | None:
    pool = _insights_by_date(report_date)
    m = pool.get(category)
    if not m:
        return None
    d = asdict(m)
    d.pop("sample_size", None)
    d["disclaimer"] = m.to_public_dict().get("disclaimer", "")
    return d


def compare_categories(categories: list[str], report_date: str = "2026-07-12") -> dict[str, Any]:
    pool = _insights_by_date(report_date)
    items = []
    for cat in categories[:3]:
        m = pool.get(cat)
        if not m:
            continue
        radar = {}
        for key, label in RADAR_DIMS:
            val = float(getattr(m, key, 0) or 0)
            if key in INVERT_FOR_RADAR:
                val = 100 - val
            radar[label] = int(max(0, min(100, round(val))))
        items.append({
            "category": cat,
            "radar": radar,
            "growth_rate_pct": m.growth_rate_pct,
            "blue_ocean_score": m.blue_ocean_score,
            "competition_index": m.competition_index,
            "heat_score": m.heat_score,
            "trend_label": m.trend_label,
            "price_band": m.price_band,
        })
    ranking = sorted(items, key=lambda x: (-x["blue_ocean_score"], -x["growth_rate_pct"]))
    recommendation = [r["category"] for r in ranking]
    ai_summary = _compare_summary(items, recommendation)
    return {
        "report_date": report_date,
        "categories": items,
        "recommendation_order": recommendation,
        "ai_summary": ai_summary,
        "radar_labels": [label for _, label in RADAR_DIMS],
    }


def _compare_summary(items: list[dict], order: list[str]) -> str:
    if not items:
        return "暂无可用类目对比数据。"
    if len(items) == 1:
        c = items[0]["category"]
        return f"当前仅选择 {c}。建议再选 1～2 个类目进行横向对比。"
    top = order[0] if order else items[0]["category"]
    parts = [f"综合蓝海与增速，相对优先顺序：{' > '.join(order)}。"]
    for it in items:
        if it["category"] == top:
            parts.append(
                f"{top} 蓝海 {it['blue_ocean_score']}、增速 {it['growth_rate_pct']:.0f}%，"
                f"趋势「{it['trend_label']}」，价格带 {it['price_band']}。"
            )
            break
    parts.append("以上为类目级研究参考，不构成对具体商品或店铺的建议。")
    return "".join(parts)


def timeline_for_category(category: str, days: int = 7, end_date: str = "2026-07-12") -> dict[str, Any]:
    """生成 N 日指标时间轴（mock：基于当前值回溯扰动）。"""
    days = max(3, min(30, days))
    base = metrics_for_category(category, end_date)
    if not base:
        return {"category": category, "points": [], "ai_weekly": ""}

    try:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"category": category, "points": [], "ai_weekly": "", "error": "end_date 格式应为 YYYY-MM-DD"}
    points = []
    b_growth = float(base.get("growth_rate_pct") or 0)
    b_blue = int(base.get("blue_ocean_score") or 0)
    b_comp = int(base.get("competition_index") or 0)
    b_heat = int(base.get("heat_score") or 0)

    for i in range(days - 1, -1, -1):
        dt = end - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        jitter = (_seed(category, date_str) % 17) - 8
        points.append({
            "date": date_str,
            "growth_rate_pct": int(max(0, min(100, b_growth + jitter + (i - days // 2)))),
            "blue_ocean_score": int(max(0, min(100, b_blue + jitter // 2 + (days - i) // 2))),
            "competition_index": int(max(0, min(100, b_comp - jitter // 3 + i // 3))),
            "heat_score": int(max(0, min(100, b_heat + jitter // 2))),
        })

    wow_growth = points[-1]["growth_rate_pct"] - points[0]["growth_rate_pct"]
    wow_comp = points[-1]["competition_index"] - points[0]["competition_index"]
    trend_word = "升高" if wow_growth > 3 else "回落" if wow_growth < -3 else "平稳"
    comp_word = "加剧" if wow_comp > 5 else "缓和" if wow_comp < -5 else "稳定"
    ai_weekly = (
        f"近 {days} 天，{category} 增速整体{trend_word}（约 {wow_growth:+d} 点），"
        f"竞争{comp_word}。当前蓝海 {points[-1]['blue_ocean_score']}，"
        f"{'可保持关注' if wow_growth >= 0 else '建议继续观察'}。"
    )
    return {
        "category": category,
        "days": days,
        "end_date": end_date,
        "points": points,
        "ai_weekly": ai_weekly,
    }


DEFAULT_WORKFLOW = {
    "columns": [
        {"id": "idea", "title": "想法", "cards": []},
        {"id": "ai_review", "title": "AI 初评", "cards": []},
        {"id": "validate", "title": "小样本验证", "cards": []},
        {"id": "launch", "title": "上架 / 放弃", "cards": []},
        {"id": "retro", "title": "复盘", "cards": []},
    ],
}


def _load_workflow() -> dict[str, Any]:
    if WORKFLOW_PATH.is_file():
        try:
            return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    board = DEFAULT_WORKFLOW.copy()
    board["columns"] = [dict(c, cards=list(c.get("cards") or [])) for c in DEFAULT_WORKFLOW["columns"]]
    # 预置 demo 卡片
    board["columns"][0]["cards"] = [
        {
            "id": "card-demo-1",
            "title": "美甲穿戴甲 summer 款",
            "category": "美甲美睫",
            "note": "情报报告建议进入，待验证供应链",
            "report_date": "2026-07-12",
            "created_at": "2026-07-10",
        },
    ]
    board["columns"][1]["cards"] = [
        {
            "id": "card-demo-2",
            "title": "小学教辅暑假衔接",
            "category": "小学教辅",
            "note": "AI 初评：适合进入，窗口 2～3 周",
            "report_date": "2026-07-12",
            "created_at": "2026-07-08",
        },
    ]
    _save_workflow(board)
    return board


def _save_workflow(board: dict[str, Any]) -> None:
    WORKFLOW_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKFLOW_PATH.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")


def get_workflow_board() -> dict[str, Any]:
    return _load_workflow()


def add_workflow_card(column_id: str, title: str, category: str = "", note: str = "") -> dict[str, Any]:
    import uuid
    board = _load_workflow()
    card = {
        "id": f"card-{uuid.uuid4().hex[:8]}",
        "title": title[:120],
        "category": category[:32],
        "note": note[:500],
        "report_date": "2026-07-12",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    for col in board["columns"]:
        if col["id"] == column_id:
            col.setdefault("cards", []).append(card)
            _save_workflow(board)
            return card
    raise ValueError(f"unknown column: {column_id}")


def move_workflow_card(card_id: str, to_column_id: str) -> dict[str, Any]:
    board = _load_workflow()
    found = None
    for col in board["columns"]:
        cards = col.get("cards") or []
        for i, c in enumerate(cards):
            if c.get("id") == card_id:
                found = cards.pop(i)
                break
        if found:
            break
    if not found:
        raise ValueError(f"card not found: {card_id}")
    for col in board["columns"]:
        if col["id"] == to_column_id:
            col.setdefault("cards", []).append(found)
            _save_workflow(board)
            return found
    raise ValueError(f"unknown column: {to_column_id}")
