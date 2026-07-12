# -*- coding: utf-8 -*-
"""
实验室报告存储 — REQ-TEN-002：按 persona / 日期 / 类目隔离，避免全局 preview.html 覆盖。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from services.lab_session import get_active_persona

_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = _ROOT / "output"

_CATEGORY_RE = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def session_key(persona: str | None = None) -> str:
    return persona or get_active_persona()


def _validate_category(category: str) -> str:
    c = (category or "").strip()
    if not c or not _CATEGORY_RE.match(c):
        raise ValueError(f"invalid category: {category!r}")
    return c


def _validate_date(report_date: str) -> str:
    d = (report_date or "").strip()
    if not _DATE_RE.match(d):
        raise ValueError(f"invalid report_date: {report_date!r}")
    return d


def report_dir(
    report_date: str,
    category: str,
    *,
    persona: str | None = None,
    base: Path | None = None,
) -> Path:
    """output/sessions/{persona}/reports/{date}/{category}/"""
    root = base or OUTPUT
    p = session_key(persona)
    date = _validate_date(report_date)
    cat = _validate_category(category)
    return root / "sessions" / p / "reports" / date / cat


def save_report(
    report_date: str,
    category: str,
    html: str,
    metrics: dict[str, Any],
    report: dict[str, Any],
    *,
    persona: str | None = None,
    llm_meta: dict[str, Any] | None = None,
    base: Path | None = None,
) -> Path:
    root = base or OUTPUT
    p = session_key(persona)
    d = report_dir(report_date, category, persona=p, base=root)
    d.mkdir(parents=True, exist_ok=True)
    index = d / "index.html"
    index.write_text(html, encoding="utf-8")
    meta = {
        "metrics": metrics,
        "report": report,
        "llm_meta": llm_meta or {},
        "persona": p,
        "report_date": report_date,
        "category": category,
    }
    (d / "insight.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    latest = root / "sessions" / p / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(
        json.dumps({"report_date": report_date, "category": category}, ensure_ascii=False),
        encoding="utf-8",
    )
    return index


def resolve_preview_path(
    *,
    persona: str | None = None,
    category: str | None = None,
    report_date: str | None = None,
    base: Path | None = None,
) -> Path | None:
    root = base or OUTPUT
    p = session_key(persona)
    if category and report_date:
        path = report_dir(report_date, category, persona=p, base=root) / "index.html"
        return path if path.is_file() else None
    latest = root / "sessions" / p / "latest.json"
    if not latest.is_file():
        return None
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None
    cat = data.get("category")
    date = data.get("report_date")
    if not cat or not date:
        return None
    return resolve_preview_path(persona=p, category=cat, report_date=date, base=root)


def preview_url(category: str, report_date: str) -> str:
    from urllib.parse import urlencode

    q = urlencode({"category": category, "report_date": report_date})
    return f"/api/v1/insight/report/view?{q}"


def list_session_reports(*, persona: str | None = None, base: Path | None = None) -> list[dict[str, Any]]:
    root = base or OUTPUT
    p = session_key(persona)
    reports_root = root / "sessions" / p / "reports"
    items: list[dict[str, Any]] = []
    if not reports_root.is_dir():
        return items
    for date_dir in sorted(reports_root.iterdir(), reverse=True):
        if not date_dir.is_dir() or not _DATE_RE.match(date_dir.name):
            continue
        for cat_dir in date_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            index = cat_dir / "index.html"
            if not index.is_file():
                continue
            meta: dict[str, Any] = {}
            meta_path = cat_dir / "insight.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            report = meta.get("report") or {}
            metrics = meta.get("metrics") or {}
            items.append(
                {
                    "category": metrics.get("category") or cat_dir.name,
                    "report_date": metrics.get("report_date") or date_dir.name,
                    "stars": report.get("opportunity_stars") or 3,
                    "title": f"{metrics.get('category') or cat_dir.name} 情报",
                    "persona": p,
                }
            )
    return items
