# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

CRAWLER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if CRAWLER_ROOT not in sys.path:
    sys.path.insert(0, CRAWLER_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.auth import current_member, create_token, login_member, verify_sync_key
from cloud_deploy.cloud_api.config import get_settings

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

app = FastAPI(title="XHS 选品云服务", version="1.1.0")


@app.on_event("startup")
def _startup():
    db.init_db()
    db.ensure_admin()


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    auth_code: str = Field(..., min_length=8, max_length=64)


class ActivateBody(BaseModel):
    auth_code: str = Field(..., min_length=8, max_length=64)


class GenerateCodesBody(BaseModel):
    count: int = Field(default=1, ge=1, le=100)
    plan_code: str = "monthly"
    duration_days: int = Field(default=30, ge=1, le=3650)
    max_activations: int = Field(default=1, ge=1, le=1000)
    note: str = ""


class DailyReportSyncBody(BaseModel):
    report_date: str
    meta: dict = Field(default_factory=dict)
    items: list
    source: str = "local_gen_report"


class SoldHistorySyncBody(BaseModel):
    batch_id: str = ""
    rows: list[dict]
    final_batch: bool = False


class SoldSnapshotsSyncBody(BaseModel):
    batch_id: str = ""
    rows: list[dict]
    final_batch: bool = False


@app.get("/", response_class=HTMLResponse)
@app.get("/member", response_class=HTMLResponse)
def member_portal_page():
    path = os.path.join(_ASSETS, "member_portal.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="会员看板未部署")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/login")
def login(body: LoginBody):
    return login_member(body.username, body.password)


@app.post("/api/v1/auth/register")
def register(body: RegisterBody):
    try:
        profile = db.register_with_auth_code(body.username, body.password, body.auth_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    token = create_token(profile)
    return {
        "access_token": token,
        "token_type": "bearer",
        "membership": profile,
    }


@app.post("/api/v1/auth/activate")
def activate_code(body: ActivateBody, user: dict = Depends(current_member)):
    try:
        profile = db.renew_with_auth_code(user["id"], body.auth_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"membership": profile, "message": "续费成功"}


@app.get("/api/v1/member/profile")
def member_profile(user: dict = Depends(current_member)):
    profile = db.get_member_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    return profile


@app.get("/api/v1/member/reports")
def member_reports(
    archive_type: str = "member_daily_zip",
    user: dict = Depends(current_member),
):
    return {"items": db.list_archives(archive_type=archive_type), "user": user["username"]}


@app.get("/api/v1/member/library")
def member_library(user: dict = Depends(current_member)):
    """全部历史报告库（日报 + 周报 + 月报）。"""
    library = db.list_report_library()
    profile = db.get_member_profile(user["id"])
    return {"membership": profile, "library": library}


@app.get("/api/v1/member/reports/{report_date}/download")
def download_report(
    report_date: str,
    archive_type: str = "member_daily_zip",
    request: Request = None,
    user: dict = Depends(current_member),
):
    path = db.get_archive_path(report_date, archive_type)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="报告不存在")
    ip = request.client.host if request and request.client else ""
    db.log_download(user["id"], report_date, archive_type, ip)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=os.path.basename(path),
    )


@app.post("/api/v1/admin/auth-codes")
def admin_generate_codes(body: GenerateCodesBody, _: None = Depends(verify_sync_key)):
    codes = db.generate_auth_codes(
        count=body.count,
        plan_code=body.plan_code,
        duration_days=body.duration_days,
        max_activations=body.max_activations,
        note=body.note,
    )
    return {
        "codes": codes,
        "plan_code": body.plan_code,
        "duration_days": body.duration_days,
        "max_activations": body.max_activations,
    }


@app.get("/api/v1/admin/auth-codes")
def admin_list_codes(
    _: None = Depends(verify_sync_key),
    limit: int = 100,
    status: str | None = None,
):
    return {"items": db.list_auth_codes(limit=limit, status=status or None)}


@app.get("/api/v1/admin/stats")
def admin_stats(_: None = Depends(verify_sync_key)):
    stats = db.get_admin_stats()
    archives = db.list_archives()
    pool_size = 0
    pending_backfill = 0
    pending_snapshots = 0
    if os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        try:
            from cloud_deploy.cloud_api.database_pg import _conn

            conn = _conn()
            with conn.cursor() as c:
                c.execute("SET search_path TO xhs_monitor, public")
                c.execute("SELECT COUNT(*) FROM monitor_goods WHERE monitor_status='active'")
                pool_size = c.fetchone()[0]
                c.execute(
                    "SELECT COUNT(*) FROM goods_sync_state WHERE sold_daily_backfill_done=FALSE"
                )
                pending_backfill = c.fetchone()[0]
                c.execute(
                    "SELECT COUNT(*) FROM goods_sync_state WHERE sold_snapshots_backfill_done=FALSE"
                )
                pending_snapshots = c.fetchone()[0]
            conn.close()
        except Exception:
            pass
    return {
        **stats,
        "archive_count_sync": len(archives),
        "latest_archive": archives[0] if archives else None,
        "monitor_pool_active": pool_size,
        "sold_history_pending_backfill": pending_backfill,
        "sold_snapshots_pending_backfill": pending_snapshots,
    }


@app.get("/api/v1/sync/status")
def sync_status(_: None = Depends(verify_sync_key)):
    archives = db.list_archives()
    pool_size = 0
    pending_backfill = 0
    pending_snapshots = 0
    if os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        try:
            from cloud_deploy.cloud_api.database_pg import _conn

            conn = _conn()
            with conn.cursor() as c:
                c.execute("SET search_path TO xhs_monitor, public")
                c.execute("SELECT COUNT(*) FROM monitor_goods WHERE monitor_status='active'")
                pool_size = c.fetchone()[0]
                c.execute(
                    "SELECT COUNT(*) FROM goods_sync_state WHERE sold_daily_backfill_done=FALSE"
                )
                pending_backfill = c.fetchone()[0]
                c.execute(
                    "SELECT COUNT(*) FROM goods_sync_state WHERE sold_snapshots_backfill_done=FALSE"
                )
                pending_snapshots = c.fetchone()[0]
            conn.close()
        except Exception:
            pass
    return {
        "archive_count": len(archives),
        "latest": archives[0] if archives else None,
        "monitor_pool_active": pool_size,
        "sold_history_pending_backfill": pending_backfill,
        "sold_snapshots_pending_backfill": pending_snapshots,
    }


@app.post("/api/v1/sync/daily-report")
def sync_daily_report(body: DailyReportSyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.sync_service import apply_daily_report

    init_db()
    conn = _conn()
    try:
        return apply_daily_report(conn, body.report_date, body.meta, body.items, source=body.source)
    finally:
        conn.close()


@app.post("/api/v1/sync/sold-history")
def sync_sold_history(body: SoldHistorySyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.sync_service import apply_sold_history_batch

    init_db()
    conn = _conn()
    try:
        n = apply_sold_history_batch(conn, body.rows)
        return {"batch_id": body.batch_id, "rows_upserted": n, "final_batch": body.final_batch}
    finally:
        conn.close()


@app.post("/api/v1/sync/sold-snapshots")
def sync_sold_snapshots(body: SoldSnapshotsSyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.sync_service import apply_sold_snapshots_batch

    init_db()
    conn = _conn()
    try:
        n = apply_sold_snapshots_batch(conn, body.rows)
        return {"batch_id": body.batch_id, "rows_upserted": n, "final_batch": body.final_batch}
    finally:
        conn.close()


@app.post("/api/v1/sync/prune-snapshots")
def sync_prune_snapshots(_: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.sync_service import prune_sold_snapshots

    init_db()
    conn = _conn()
    try:
        deleted = prune_sold_snapshots(conn)
        return {"deleted_rows": deleted}
    finally:
        conn.close()


def main():
    s = get_settings()
    import uvicorn

    uvicorn.run(
        "cloud_deploy.cloud_api.main:app",
        host=s.xhs_cloud_host,
        port=s.xhs_cloud_port,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
