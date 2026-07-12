# -*- coding: utf-8 -*-
"""情报 HTML 渲染与 bundle 写入。"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any


def render_insight_html(report: dict[str, Any], metrics: dict[str, Any]) -> str:
    cat = html.escape(str(metrics.get("category") or "市场"))
    report_date = html.escape(str(metrics.get("report_date") or ""))
    stars = int(report.get("opportunity_stars") or 3)
    star_str = "★" * stars + "☆" * (5 - stars)
    body_parts = []
    for p in report.get("pages") or []:
        title = html.escape(str(p.get("title") or ""))
        if p.get("body"):
            body_parts.append(f"<section><h2>{title}</h2><p>{html.escape(str(p['body']))}</p></section>")
        elif p.get("verdict"):
            body_parts.append(
                f"<section><h2>{title}</h2><p>{html.escape(str(p.get('verdict')))}</p></section>"
            )
    sections = "\n".join(body_parts) or f"<p>{html.escape(report.get('executive_summary') or '')}</p>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{cat} · AI 选品情报 {report_date}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;padding:20px;background:#f5f5f7;color:#1d1d1f}}
.wrap{{max-width:720px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
h1{{font-size:22px;margin:0 0 8px}} .meta{{color:#6e6e73;font-size:13px;margin-bottom:20px}}
.stars{{color:#ff9500;font-size:18px;margin:8px 0 16px}} section{{margin-bottom:20px}}
h2{{font-size:16px;margin:0 0 8px}} p{{line-height:1.65;font-size:14px;margin:0}}
.disclaimer{{font-size:12px;color:#6e6e73;margin-top:24px;padding-top:16px;border-top:1px solid #eee}}
</style></head><body><div class="wrap">
<h1>{cat}</h1>
<div class="meta">报告日期 {report_date} · 类目级聚合情报</div>
<div class="stars">{star_str} 机会 {stars}/5</div>
{sections}
<p class="disclaimer">{html.escape(metrics.get('disclaimer') or '')}</p>
</div></body></html>"""


def write_insight_bundle(
    base_dir: str | Path,
    report_date: str,
    category: str,
    html_content: str,
    meta: dict[str, Any],
) -> Path:
    day = report_date.replace("-", "")
    bundle = Path(base_dir) / f"insight_{day}" / category
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "index.html").write_text(html_content, encoding="utf-8")
    (bundle / "insight.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle


def pg_items_to_rows(items: list) -> list[dict[str, Any]]:
    """28 列 report item → insight 聚合输入（仅管道内使用）。"""
    from cloud_deploy.reporting.constants import item_at

    rows: list[dict[str, Any]] = []
    for it in items:
        title = (item_at(it, "title") or "").strip()
        if not title:
            continue
        gr = float(item_at(it, "gr") or item_at(it, "actual_gr") or 0)
        if gr > 1.5:
            gr = gr / 100.0
        pool = str(item_at(it, "pool") or "")
        rows.append(
            {
                "title": title,
                "price": float(item_at(it, "price") or 0),
                "actual_v1d": float(item_at(it, "actual_v1d") or 0),
                "gr": gr,
                "first_seen_days": 99,
                "is_new": pool.upper() == "NEW",
            }
        )
    return rows
