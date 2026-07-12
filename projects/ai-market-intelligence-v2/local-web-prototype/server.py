# -*- coding: utf-8 -*-
"""
本地验证 API（实验室，端口 8765）

  cd projects/ai-market-intelligence-v2
  python local-web-prototype/server.py

浏览器: http://127.0.0.1:8765
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.audit_log import append_audit, log_publish
from services.env_loader import load_lab_env
from services.agent_graph import run_agents
from services.compliance_gate import assert_publishable
from services.llm_client import describe_config, llm_configured
from services.metric_engine import aggregate_items_to_insights
from services.report_builder import render_insight_html
from services.ux_copy import load_ux_copy
from services.mock_intelligence import (
    add_workflow_card,
    compare_categories,
    get_workflow_board,
    move_workflow_card,
    timeline_for_category,
)
from services.notification_mock import list_notifications, mark_all_read, mark_read
from services.report_export import render_print_summary
from services.insight_watchlist_lab import get_watchlist, put_watchlist
from services.team_mock import get_team_mock
from services.entitlements_lab import (
    merge_entitlements,
    can_insight_generate,
    can_insight_compare,
    can_insight_timeline,
    can_insight_workflow,
    can_insight_pdf,
    portal_route,
)
from services.lab_session import get_profile, set_persona, list_personas
from services.llm_budget import check_budget, record_usage, get_daily_usage
from services.report_storage import (
    list_session_reports,
    preview_url,
    resolve_preview_path,
    save_report,
)
from services.subscription_mock import (
    can_generate,
    check_feature,
    get_plan_info,
    record_generation,
    set_plan,
)
from samples.mock_items import MOCK_ITEMS

load_lab_env(ROOT)

app = FastAPI(title="Insight Lab API", version="0.2.0")

STATIC = Path(__file__).parent
OUTPUT = ROOT / "output"
K_MIN = int(os.environ.get("INSIGHT_K_ANONYMITY", "5"))

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(value: str, field: str = "date") -> str:
    """校验日期参数格式为 YYYY-MM-DD,防止非法输入穿透到下游。"""
    if not _DATE_RE.match(value or ""):
        raise HTTPException(400, f"{field} 格式应为 YYYY-MM-DD")
    return value


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "lab": "ai-market-intelligence-v2",
        "llm_configured": llm_configured(),
        "llm": describe_config(),
    }


@app.get("/api/v1/llm/config")
def llm_config():
    return describe_config()


@app.get("/api/v1/member/profile")
def member_profile():
    """REQ-RT-004：门户路由 + 权益（Lab persona 模拟生产 JWT 用户）。"""
    prof = get_profile()
    ent = merge_entitlements(prof.get("entitlements"), prof.get("plan_code"))
    plan = get_plan_info()
    return {
        **prof,
        "entitlements": ent,
        "portal_route": portal_route(ent),
        "legacy_zip_enabled": bool(ent.get("legacy_zip_enabled")),
        "insight_enabled": bool(ent.get("insight_enabled")),
        "usage_today": plan.get("usage_today"),
        "llm_usage_today": get_daily_usage(),
    }


class PersonaSwitchRequest(BaseModel):
    persona: str


@app.get("/api/v1/lab/personas")
def lab_personas():
    return {"items": list_personas(), "lab_mode": True}


@app.post("/api/v1/lab/persona")
def lab_persona_switch(body: PersonaSwitchRequest):
    try:
        return set_persona(body.persona)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/v1/member/plan")
def member_plan():
    return get_plan_info()


class PlanSwitchRequest(BaseModel):
    plan_id: str


@app.post("/api/v1/member/plan")
def member_plan_switch(body: PlanSwitchRequest):
    try:
        return set_plan(body.plan_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class InsightWatchlistBody(BaseModel):
    categories: list[str]

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        for c in v:
            if c and not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", str(c).strip()):
                raise ValueError(f"非法类目: {c}")
        return [str(c).strip() for c in v if str(c).strip()]


@app.get("/api/v1/member/insight/watchlist")
def insight_watchlist_get():
    """类目关注 — 契约同 cloud-stubs/insight_watchlist.py"""
    return get_watchlist()


@app.put("/api/v1/member/insight/watchlist")
def insight_watchlist_put(body: InsightWatchlistBody):
    plan = get_plan_info()
    max_w = int((plan.get("plan") or {}).get("categories_per_day") or 5) * 2
    return put_watchlist(body.categories, max_items=max_w)


@app.get("/api/v1/member/entitlements")
def member_entitlements():
    """模拟 get_member_entitlements() 输出（生产读 auth_codes.note）。"""
    prof = get_profile()
    ent = merge_entitlements(prof.get("entitlements"), prof.get("plan_code"))
    return {**ent, "portal_route": portal_route(ent)}


_DEMO_SAMPLES = {
    "美甲美睫": "情报20260712_美甲美睫",
    "小学教辅": "情报20260712_小学教辅",
    "家居收纳": "情报20260712_家居收纳",
}


@app.get("/demo/insight")
def demo_insight_landing():
    path = STATIC / "insight-demo.html"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/api/v1/demo/insight/samples")
def demo_insight_samples():
    """D2 拉新：公开样例列表（无需登录）。"""
    items = []
    for category, folder in _DEMO_SAMPLES.items():
        p = OUTPUT / folder / "index.html"
        if p.is_file():
            items.append({"slug": category, "category": category, "report_date": "2026-07-12"})
    return {"items": items, "public": True, "note": "静态缓存，非实时 LLM"}


@app.get("/demo/insight/sample/{slug}", response_class=HTMLResponse)
def demo_insight_sample(slug: str):
    if slug not in _DEMO_SAMPLES:
        raise HTTPException(404, "样例不存在")
    path = OUTPUT / _DEMO_SAMPLES[slug] / "index.html"
    if not path.is_file():
        raise HTTPException(404, "样例文件缺失，请先运行 insight 管道生成")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/member/insight")
def member_insight_page():
    """REQ-RT-003：V2 独立门户（Lab 模拟生产 /member/insight）。"""
    path = STATIC / "insight_portal.html"
    if not path.is_file():
        raise HTTPException(404, "insight_portal.html missing")
    return FileResponse(path)


@app.get("/api/v1/member/team")
def member_team():
    plan = get_plan_info()
    if plan.get("plan_id") != "insight_team_monthly":
        raise HTTPException(403, "当前套餐非 Team 版")
    return get_team_mock()


@app.get("/api/v1/payment/bridge")
def payment_bridge():
    """实验室不 mock 支付；返回现网入口。"""
    return {
        "message": "扫码支付请使用现网选品报告中心",
        "portal_url": "https://monitor.xhs365.cn/member",
        "plans_api": "/api/v1/payment/plans",
        "note": "合并 V2 套餐后现网 plans 将含 insight_* SKU",
    }


@app.get("/api/v1/notifications")
def notifications_list(refresh: bool = False):
    return list_notifications(refresh=refresh)


class NotifReadRequest(BaseModel):
    id: str


@app.post("/api/v1/notifications/read")
def notifications_read(body: NotifReadRequest):
    return mark_read(body.id)


@app.post("/api/v1/notifications/read-all")
def notifications_read_all():
    return mark_all_read()


@app.get("/api/v1/ux/copy")
def ux_copy():
    return load_ux_copy()


@app.get("/api/v1/insight/library")
def insight_library():
    """情报库列表（实验室：当前 persona 隔离目录 + 公开 demo 目录）。"""
    items = list_session_reports()
    if OUTPUT.is_dir():
        for p in sorted(OUTPUT.glob("情报*"), reverse=True):
            if not p.is_dir():
                continue
            insight_json = p / "insight.json"
            meta = {}
            if insight_json.is_file():
                import json
                try:
                    meta = json.loads(insight_json.read_text(encoding="utf-8"))
                except Exception:
                    pass
            report = meta.get("report") or {}
            metrics = meta.get("metrics") or {}
            items.append({
                "category": metrics.get("category") or p.name.split("_")[-1],
                "report_date": metrics.get("report_date") or "2026-07-12",
                "stars": report.get("opportunity_stars") or 3,
                "title": f"{metrics.get('category', '类目')} 情报",
                "public_demo": True,
            })
    if not items:
        insights = aggregate_items_to_insights("2026-07-12", MOCK_ITEMS)
        items = [
            {
                "category": m.category,
                "report_date": "2026-07-12",
                "stars": 3,
                "title": f"{m.category} 情报",
            }
            for m in insights[:3]
        ]
    return {"items": items[:20]}


class FeedbackRequest(BaseModel):
    type: str = "correction"
    content: str
    category: str = ""
    report_date: str = "2026-07-12"

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("content 不能为空")
        return v.strip()[:2000]


@app.post("/api/v1/feedback")
def submit_feedback(body: FeedbackRequest):
    """投诉/纠错 stub（写入 audit JSONL，无真实工单系统）。"""
    import uuid
    ticket_id = f"FB-LAB-{uuid.uuid4().hex[:8].upper()}"
    append_audit(
        "user_feedback",
        {
            "ticket_id": ticket_id,
            "type": body.type,
            "category": body.category,
            "report_date": body.report_date,
            "content_preview": body.content[:200],
        },
    )
    copy = load_ux_copy()
    msg = (copy.get("feedback") or {}).get("success") or "已收到"
    return {"status": "received", "ticket_id": ticket_id, "message": msg, "sla_days": 15}


def _current_ent():
    prof = get_profile()
    return merge_entitlements(prof.get("entitlements"), prof.get("plan_code"))


@app.get("/api/v1/insight/compare")
def insight_compare(categories: str = "", report_date: str = "2026-07-12"):
    ent = _current_ent()
    if not can_insight_compare(ent):
        raise HTTPException(403, "当前套餐不支持类目对比，请升级 V2-Pro")
    _validate_date(report_date, "report_date")
    cats = [c.strip() for c in categories.split(",") if c.strip()]
    if len(cats) < 1:
        insights = aggregate_items_to_insights(report_date, MOCK_ITEMS)
        cats = [m.category for m in insights[:2]]
    if len(cats) < 2:
        raise HTTPException(400, "请至少选择 2 个类目")
    for c in cats:
        if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", c):
            raise HTTPException(400, f"非法类目名: {c}")
    return compare_categories(cats, report_date)


@app.get("/api/v1/insight/timeline")
def insight_timeline(category: str, days: int = 7, end_date: str = "2026-07-12"):
    ent = _current_ent()
    ok, msg = can_insight_timeline(ent, days=days)
    if not ok:
        raise HTTPException(403, msg)
    _validate_date(end_date, "end_date")
    if not category or not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", category):
        raise HTTPException(400, "category 无效")
    days = max(3, min(30, days))
    result = timeline_for_category(category, days=days, end_date=end_date)
    if not result.get("points"):
        raise HTTPException(404, "类目不存在")
    return result


@app.get("/api/v1/workflow/board")
def workflow_board():
    if not can_insight_workflow(_current_ent()):
        raise HTTPException(403, "当前套餐不支持决策工作流，请升级 V2-Pro")
    return get_workflow_board()


class WorkflowCardCreate(BaseModel):
    column_id: str = "idea"
    title: str
    category: str = ""
    note: str = ""

    @field_validator("title")
    @classmethod
    def title_ok(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title 不能为空")
        return v[:120]


class WorkflowCardMove(BaseModel):
    card_id: str
    to_column: str


@app.post("/api/v1/workflow/card")
def workflow_add_card(body: WorkflowCardCreate):
    if not can_insight_workflow(_current_ent()):
        raise HTTPException(403, "当前套餐不支持决策工作流，请升级 V2-Pro")
    try:
        card = add_workflow_card(body.column_id, body.title, body.category, body.note)
        return {"status": "ok", "card": card}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/v1/workflow/card/move")
def workflow_move_card(body: WorkflowCardMove):
    if not can_insight_workflow(_current_ent()):
        raise HTTPException(403, "当前套餐不支持决策工作流，请升级 V2-Pro")
    try:
        card = move_workflow_card(body.card_id, body.to_column)
        return {"status": "ok", "card": card}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/v1/insight/categories")
def list_categories(date: str = "2026-07-12"):
    insights = aggregate_items_to_insights(date, MOCK_ITEMS)
    return {
        "report_date": date,
        "items": [
            {
                "category": m.category,
                "growth_rate_pct": m.growth_rate_pct,
                "blue_ocean_score": m.blue_ocean_score,
                "competition_index": m.competition_index,
            }
            for m in insights
        ],
    }


class GenerateReportRequest(BaseModel):
    report_date: str = "2026-07-12"
    category: str = ""

    @field_validator("report_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("report_date 格式应为 YYYY-MM-DD")
        return v

    @field_validator("category")
    @classmethod
    def sanitize_category(cls, v: str) -> str:
        # 防止路径遍历:仅允许中文/字母/数字
        if v and not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", v):
            raise ValueError("category 含非法字符")
        return v


@app.post("/api/v1/insight/report/generate")
def generate_report(body: GenerateReportRequest):
    date = body.report_date
    category = body.category
    prof = get_profile()
    ent = merge_entitlements(prof.get("entitlements"), prof.get("plan_code"))
    if not ent.get("insight_enabled"):
        raise HTTPException(403, "当前账号不含 AI 选品情报权益，请开通 V2 套餐或联系客服获取预览码")

    plan = get_plan_info()
    already = int((plan.get("usage_today") or {}).get("generated_count") or 0)
    ok_ent, reason_ent = can_insight_generate(ent, already_today=already)
    if not ok_ent:
        raise HTTPException(403, reason_ent)

    ok_budget, reason_budget = check_budget(plan.get("plan_id"), entitlements=ent)
    if not ok_budget:
        raise HTTPException(503, reason_budget)

    insights = aggregate_items_to_insights(date, MOCK_ITEMS)
    match = next((m for m in insights if m.category == category), insights[0] if insights else None)
    if not match:
        raise HTTPException(404, "无可用类目")
    ok, reason = can_generate(match.category, date)
    if not ok:
        raise HTTPException(403, reason)
    internal = asdict(match)
    metrics = match.to_public_dict()
    report_obj = run_agents(metrics)
    report = report_obj.to_public_dict()
    html = render_insight_html(report, metrics, llm_meta=report_obj.llm_meta)
    assert_publishable(internal, report, html, k_min=K_MIN)
    record_generation(match.category, date)
    log_publish(
        report_date=date,
        category=match.category,
        llm_meta=report_obj.llm_meta,
        k_min=K_MIN,
        sample_size=match.sample_size,
    )
    usage = (report_obj.llm_meta or {}).get("usage") or {}
    record_usage(usage, category=match.category)
    save_report(
        date,
        match.category,
        html,
        metrics,
        report,
        llm_meta=report_obj.llm_meta,
    )
    plan = get_plan_info()
    return {
        "metrics": metrics,
        "report": report,
        "preview_url": preview_url(match.category, date),
        "print_url": f"/api/v1/insight/report/print?category={match.category}&report_date={date}",
        "llm": describe_config(),
        "mode": "llm" if llm_configured() else "mock",
        "usage": plan.get("usage_today"),
        "llm_usage_today": get_daily_usage(),
    }


@app.get("/api/v1/insight/report/print", response_class=HTMLResponse)
def print_report(category: str, report_date: str = "2026-07-12"):
    _validate_date(report_date, "report_date")
    if not can_insight_pdf(_current_ent()):
        raise HTTPException(403, "当前套餐不支持 PDF 摘要导出，请升级 V2-Pro")
    if not category or not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", category):
        raise HTTPException(400, "category 无效")
    insights = aggregate_items_to_insights(report_date, MOCK_ITEMS)
    match = next((m for m in insights if m.category == category), None)
    if not match:
        raise HTTPException(404, "类目不存在")
    metrics = match.to_public_dict()
    report = run_agents(metrics).to_public_dict()
    html = render_print_summary(report, metrics)
    return HTMLResponse(html)


@app.get("/api/v1/insight/report/view", response_class=HTMLResponse)
def insight_report_view(category: str, report_date: str = "2026-07-12"):
    _validate_date(report_date, "report_date")
    if not category or not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9]+$", category):
        raise HTTPException(400, "category 无效")
    path = resolve_preview_path(category=category, report_date=report_date)
    if not path:
        raise HTTPException(404, "报告不存在，请先生成")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/preview/latest", response_class=HTMLResponse)
def preview_latest():
    path = resolve_preview_path()
    if not path:
        raise HTTPException(404, "请先在首页生成报告")
    return HTMLResponse(path.read_text(encoding="utf-8"))


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
