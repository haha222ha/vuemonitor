# -*- coding: utf-8 -*-
"""
云侧 AI 顾问预生成 — 拾取 data/incoming/advisor/*.ready → advisor_published。

用法:
  python cloud_deploy/scripts/advisor_cloud_generate.py
  python cloud_deploy/scripts/advisor_cloud_generate.py --date 2026-07-12
  python cloud_deploy/scripts/advisor_cloud_generate.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _cloud_root() -> str:
    return os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")


def _incoming_dir() -> str:
    return os.path.join(_cloud_root(), os.environ.get("XHS_ADVISOR_INCOMING_SUBDIR", "data/incoming/advisor"))


def _publish_dir() -> str:
    return os.path.join(_cloud_root(), os.environ.get("XHS_ADVISOR_PUBLISH_DIR", "data/advisor_published"))


def _work_dir() -> str:
    return os.path.join(_cloud_root(), os.environ.get("XHS_ADVISOR_WORK_DIR", "data/advisor_work"))


def _load_context(report_date: str) -> dict | None:
    path = os.path.join(_incoming_dir(), f"context_{report_date}.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("context"), dict):
        return data["context"]
    if isinstance(data, dict):
        return data
    return None


def _try_rank_engine_generate(report_date: str, context: dict) -> dict | None:
    try:
        from cloud_deploy.rank_engine.ai_advisor import AiAdvisor

        return AiAdvisor().run_batch(target_date=report_date, context=context)
    except ImportError:
        return None
    except Exception as e:
        print(f"[advisor] rank_engine failed: {e}", file=sys.stderr)
        return None


def _stub_advice(report_date: str, context: dict) -> dict:
    summary = str(context.get("market_summary") or context.get("summary") or "市场数据已接收，AI 全文生成待 rank_engine 部署。")
    directions = []
    for block in context.get("directions") or context.get("direction_blocks") or []:
        if not isinstance(block, dict):
            continue
        key = str(block.get("key") or block.get("direction") or "")
        if not key:
            continue
        directions.append({
            "key": key,
            "title": block.get("title") or key,
            "summary": (block.get("summary") or "")[:200],
            "content": block.get("content") or block.get("summary") or "",
        })
    return {
        "report_date": report_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "daily_overview": {
            "title": "今日市场观察",
            "summary": summary[:240],
            "content": summary,
        },
        "direction_advices": directions[:8],
        "disclaimer": "仅供参考，不构成投资建议。",
    }


def _write_publish_bundle(report_date: str, advice: dict) -> str:
    out = os.path.join(_publish_dir(), report_date)
    os.makedirs(out, exist_ok=True)
    advice_path = os.path.join(out, "advice.json")
    with open(advice_path, "w", encoding="utf-8") as f:
        json.dump(advice, f, ensure_ascii=False, indent=2)

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>AI 选品顾问 {report_date}</title></head><body>
<h1>{advice.get('daily_overview', {}).get('title', '今日市场观察')}</h1>
<pre style="white-space:pre-wrap;font-family:sans-serif;line-height:1.7">{
        (advice.get('daily_overview') or {}).get('content', '')
    }</pre>
<p style="color:#666;font-size:12px">{advice.get('disclaimer', '')}</p>
</body></html>"""
    with open(os.path.join(out, "advisor.html"), "w", encoding="utf-8") as f:
        f.write(html)

    manifest = {
        "report_date": report_date,
        "summary": (advice.get("daily_overview") or {}).get("summary", ""),
        "archive_type": "member_ai_advisor_zip",
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(out, "report_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return out


def _pack_zip(report_date: str, publish_dir: str) -> str:
    work = os.path.join(_work_dir(), report_date)
    os.makedirs(work, exist_ok=True)
    zip_path = os.path.join(work, f"ai_advisor_{report_date}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("advice.json", "advisor.html", "report_manifest.json"):
            full = os.path.join(publish_dir, name)
            if os.path.isfile(full):
                zf.write(full, arcname=name)
    return zip_path


def process_one(report_date: str, *, dry_run: bool = False) -> dict:
    if not _DATE_RE.match(report_date):
        return {"report_date": report_date, "status": "error", "detail": "invalid date"}

    ready = os.path.join(_incoming_dir(), f"context_{report_date}.ready")
    if not os.path.isfile(ready):
        return {"report_date": report_date, "status": "skipped", "detail": "no .ready marker"}

    context = _load_context(report_date)
    if not context:
        return {"report_date": report_date, "status": "error", "detail": "context missing"}

    if dry_run:
        return {"report_date": report_date, "status": "dry-run", "detail": "context loaded"}

    advice = _try_rank_engine_generate(report_date, context) or _stub_advice(report_date, context)
    publish_dir = _write_publish_bundle(report_date, advice)
    zip_path = _pack_zip(report_date, publish_dir)

    from cloud_deploy.scripts.register_advisor_archive import register_advisor_zip

    reg = register_advisor_zip(zip_path, report_date)
    try:
        os.remove(ready)
    except OSError:
        pass
    return {
        "report_date": report_date,
        "status": "published",
        "publish_dir": publish_dir,
        "zip": reg.get("path"),
    }


def process_pending(report_date: str | None = None, *, dry_run: bool = False) -> list[dict]:
    incoming = _incoming_dir()
    if not os.path.isdir(incoming):
        return []

    dates: list[str] = []
    if report_date:
        dates = [report_date]
    else:
        for name in sorted(os.listdir(incoming)):
            if not name.startswith("context_") or not name.endswith(".ready"):
                continue
            d = name[len("context_") : -len(".ready")]
            if _DATE_RE.match(d):
                dates.append(d)

    out = []
    for d in dates:
        out.append(process_one(d, dry_run=dry_run))
    return out


def main() -> int:
    bootstrap()
    from cloud_deploy.scripts.insight_llm_runtime import apply_admin_insight_llm

    apply_admin_insight_llm(log_prefix="advisor")
    ap = argparse.ArgumentParser(description="AI 顾问云侧预生成")
    ap.add_argument("--date", default="", help="仅处理指定日期 YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true", help="只验证 context，不写发布目录")
    args = ap.parse_args()
    results = process_pending(report_date=args.date or None, dry_run=args.dry_run)
    if not results:
        print("[advisor] no pending context")
        return 0
    for r in results:
        print(r)
    failed = [r for r in results if r.get("status") == "error"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
