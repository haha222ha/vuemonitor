# -*- coding: utf-8 -*-
"""L6：生成可在线阅读的情报 HTML（无 data.js、无商品表）。"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from services.ux_copy import load_ux_copy


def _bar(value: int, *, label: str, color: str = "#0071e3") -> str:
    v = max(0, min(100, int(value)))
    return (
        f'<div class="metric-row"><span class="metric-label">{html.escape(label)}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{v}%;background:{color}"></div></div>'
        f'<span class="metric-val">{v}</span></div>'
    )


def render_insight_html(
    report: dict[str, Any],
    metrics: dict[str, Any],
    *,
    llm_meta: dict[str, Any] | None = None,
    show_explain: bool = True,
) -> str:
    copy = load_ux_copy()
    ai_copy = copy.get("ai") or {}
    cat = html.escape(str(metrics.get("category") or "市场"))
    report_date = html.escape(str(metrics.get("report_date") or ""))
    stars = int(report.get("opportunity_stars") or 3)
    star_str = "★" * stars + "☆" * (5 - stars)
    star_text = f"机会 {stars}/5"
    pages = report.get("pages") or []
    verdict = ""
    for p in pages:
        if p.get("verdict"):
            verdict = str(p.get("verdict"))
            break

    growth = float(metrics.get("growth_rate_pct") or 0)
    comp = int(metrics.get("competition_index") or 0)
    blue = int(metrics.get("blue_ocean_score") or 0)
    heat = int(metrics.get("heat_score") or 0)

    metric_dashboard = "".join([
        _bar(int(growth), label="增速指数", color="#34c759"),
        _bar(comp, label="竞争指数", color="#ff9500"),
        _bar(blue, label="蓝海指数", color="#0071e3"),
        _bar(heat, label="热度指数", color="#5856d6"),
    ])

    explain_rows = []
    explain_keys = [
        ("category", "类目"), ("sub_category", "子类"), ("window_days", "窗口(天)"),
        ("growth_rate_pct", "增速%"), ("competition_index", "竞争指数"),
        ("blue_ocean_score", "蓝海指数"), ("heat_score", "热度"),
        ("price_band", "价格带"), ("trend_label", "趋势"), ("lifecycle_stage", "生命周期"),
    ]
    for key, label in explain_keys:
        if key in metrics and metrics[key] not in (None, ""):
            explain_rows.append(
                f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(metrics[key]))}</td></tr>"
            )
    explain_html = ""
    if show_explain and explain_rows:
        explain_html = f"""
<details class="explain">
  <summary>{html.escape(str(ai_copy.get("explain_title") or "指标依据"))}</summary>
  <table class="explain-table"><tbody>{''.join(explain_rows)}</tbody></table>
  <p class="explain-note">以上均为类目级聚合指标，不含商品 ID、店铺名称或原始销量明细。</p>
</details>"""

    nav_links = []
    sections = []
    for p in pages:
        pid = int(p.get("page") or 0)
        anchor = f"page-{pid}"
        title = html.escape(str(p.get("title") or ""))
        nav_links.append(f'<a href="#{anchor}">{pid}. {title}</a>')
        body = p.get("body") or p.get("verdict") or ""
        if not body and p.get("growth"):
            body = f"增长 {p.get('growth')} · 竞争 {p.get('competition')} · 机会 {('★' * int(p.get('stars') or 3))}"
        if not body and p.get("focus"):
            body = f"方向：{p.get('focus')} · 价格带 {p.get('price')} · 形式 {p.get('format')}"
        if p.get("action"):
            body = (body + " · " + str(p.get("action"))).strip(" · ")
        sections.append(
            f'<section id="{anchor}" class="page"><h2>{pid}. {title}</h2>'
            f'<p>{html.escape(str(body))}</p></section>'
        )

    # 剥离 top_keywords 等可识别片段(合规 §8.1),不嵌入前端 payload
    safe_metrics = {k: v for k, v in metrics.items() if k != "top_keywords"}
    payload = json.dumps({"report": report, "metrics": safe_metrics}, ensure_ascii=False)
    ai_badge = html.escape(str(ai_copy.get("badge") or "AI 辅助生成"))
    ai_footer = html.escape(str(ai_copy.get("footer") or ""))
    disclaimer = html.escape(str(metrics.get("disclaimer") or ""))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 市场情报 — {cat}</title>
<style>
:root {{ --bg:#f5f7fb; --card:#fff; --primary:#0071e3; --text:#1d1d1f; --muted:#6e6e73; --ok:#248a3d; --warn:#b8860b; }}
* {{ box-sizing:border-box; }}
body {{ font-family: system-ui, "Segoe UI", "PingFang SC", sans-serif; margin:0; background:var(--bg); color:var(--text); line-height:1.65; }}
.wrap {{ max-width:720px; margin:0 auto; padding:20px 16px 48px; }}
.hero {{ background:linear-gradient(135deg,#0071e3,#5856d6); color:#fff; border-radius:16px; padding:24px 20px; margin-bottom:16px; }}
.hero h1 {{ margin:0 0 6px; font-size:20px; font-weight:600; }}
.hero-meta {{ opacity:.92; font-size:14px; }}
.badge {{ display:inline-block; background:rgba(255,255,255,.2); padding:2px 10px; border-radius:999px; font-size:12px; margin-bottom:10px; }}
.stars {{ font-size:26px; letter-spacing:2px; margin:8px 0 4px; }}
.star-text {{ font-size:14px; opacity:.9; }}
.verdict {{ display:inline-block; margin-top:8px; padding:4px 12px; border-radius:8px; background:rgba(255,255,255,.15); font-size:14px; }}
.metrics {{ background:var(--card); border-radius:12px; padding:16px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,.05); }}
.metric-row {{ display:grid; grid-template-columns:72px 1fr 36px; gap:8px; align-items:center; margin-bottom:10px; font-size:13px; }}
.metric-label {{ color:var(--muted); }}
.bar-track {{ height:8px; background:#eef1f6; border-radius:4px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:4px; }}
.metric-val {{ text-align:right; font-weight:600; }}
.nav {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px; }}
.nav a {{ font-size:12px; color:var(--primary); text-decoration:none; padding:4px 10px; background:var(--card); border-radius:999px; border:1px solid #e5e5ea; }}
.page {{ background:var(--card); border-radius:12px; padding:18px; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,.05); scroll-margin-top:12px; }}
.page h2 {{ margin:0 0 10px; font-size:16px; color:var(--primary); }}
.explain {{ background:var(--card); border-radius:12px; padding:12px 16px; margin-bottom:12px; font-size:14px; }}
.explain-table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
.explain-table th {{ text-align:left; color:var(--muted); font-weight:500; padding:4px 8px 4px 0; width:40%; }}
.explain-table td {{ padding:4px 0; }}
.explain-note {{ font-size:12px; color:var(--muted); margin:8px 0 0; }}
.disclaimer {{ font-size:12px; color:var(--muted); margin-top:16px; padding:12px; background:var(--card); border-radius:8px; }}
.feedback {{ margin-top:12px; text-align:center; }}
.feedback a {{ color:var(--primary); font-size:13px; }}
.no-export {{ display:none; }}
@media (max-width:480px) {{ .metric-row {{ grid-template-columns:64px 1fr 32px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <span class="badge">{ai_badge}</span>
    <h1>AI 市场情报报告</h1>
    <div class="hero-meta">{cat} · {report_date}</div>
    <div class="stars" aria-label="{html.escape(star_text)}">{star_str}</div>
    <div class="star-text">{html.escape(star_text)}</div>
    {f'<div class="verdict">{html.escape(verdict)}</div>' if verdict else ''}
    <p style="margin:12px 0 0;opacity:.95;font-size:15px">{html.escape(str(report.get("executive_summary") or ""))}</p>
  </div>
  <div class="metrics">{metric_dashboard}</div>
  {explain_html}
  <nav class="nav" aria-label="报告目录">{''.join(nav_links)}</nav>
  {''.join(sections)}
  <div class="disclaimer">{disclaimer}</div>
  <div class="disclaimer">{ai_footer}</div>
  <div class="feedback"><a href="#feedback" onclick="return false" title="请在会员中心提交">发现内容问题？纠错 / 投诉</a></div>
  <div class="feedback no-export"><a href="#" id="print-hint" style="font-size:12px">导出 PDF 摘要请在会员中心点击「导出 PDF 摘要」</a></div>
</div>
<script type="application/json" id="insight-data" class="no-export">{payload}</script>
</body>
</html>"""


def write_insight_bundle(out_dir: Path, report_date: str, category: str, html_content: str, meta: dict[str, Any]) -> Path:
    bundle = out_dir / f"情报{report_date.replace('-', '')}_{category[:8]}"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "index.html").write_text(html_content, encoding="utf-8")
    (bundle / "insight.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle
