# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from datetime import datetime

CRAWLER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if CRAWLER_ROOT not in sys.path:
    sys.path.insert(0, CRAWLER_ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.auth import (
    change_member_password,
    current_member,
    create_token,
    login_member,
    login_member_by_code,
    refresh_member_token,
    security,
    verify_agent_access,
    verify_sync_key,
)
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


class LoginCodeBody(BaseModel):
    auth_code: str = Field(..., min_length=8, max_length=64)


class ChangePasswordBody(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)
    current_password: str = Field(default="")


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    auth_code: str = Field(..., min_length=8, max_length=64)


class ActivateBody(BaseModel):
    auth_code: str = Field(..., min_length=8, max_length=64)


class WatchlistUpsertBody(BaseModel):
    goods_ids: list[str] = Field(default_factory=list, max_length=500)
    items: list[dict] = Field(default_factory=list, max_length=500)
    source: str = ""


class WatchlistDeleteBody(BaseModel):
    goods_ids: list[str] = Field(..., min_length=1, max_length=500)


class BatchDownloadBody(BaseModel):
    archive_type: str = "member_daily_zip"
    report_dates: list[str] = Field(..., min_length=1, max_length=50)


_MEMBER_ARCHIVE_TYPES = frozenset(
    {"member_daily_zip", "member_weekly_zip", "member_monthly_zip", "member_custom_zip"}
)


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


class PremiumUpsertBody(BaseModel):
    client_id: str = ""
    sync_version: int = 0
    rows: list[dict]


class PremiumSnapshotsBackfillBody(BaseModel):
    client_id: str = ""
    goods_id: str
    goods_daily: list[dict] = Field(default_factory=list)
    store_daily: list[dict] = Field(default_factory=list)


class PremiumCatalogBody(BaseModel):
    local_ids: list[str] = Field(default_factory=list)
    since_date: str = ""


class PeriodReportTriggerBody(BaseModel):
    scope: str = Field(..., pattern="^(weekly|monthly)$")
    end_date: str = ""
    page: int = 0
    page_size: int = 5000


class PremiumFetchBody(BaseModel):
    goods_ids: list[str] = Field(default_factory=list)


class PremiumDailyFetchBody(BaseModel):
    goods_ids: list[str] = Field(default_factory=list)
    since_date: str = ""
    max_rows: int = 25000


class PremiumBatchSyncBody(BaseModel):
    batch_id: str = ""
    rows: list[dict]
    final_batch: bool = False


class AgentScanRow(BaseModel):
    goods_id: str
    status: str
    sold: int | None = None
    engine: str = "playwright"
    message: str = ""
    ms: int = 0
    deal_price: float | None = None
    detail: dict = Field(default_factory=dict)


class AgentScanUploadBody(BaseModel):
    batch_id: str = ""
    agent_id: str = ""
    scan_date: str = ""
    rows: list[AgentScanRow] = Field(default_factory=list)


@app.get("/api/v1/agent/risk-worklist")
def agent_risk_worklist(
    limit: int = 100,
    scan_date: str = "",
    include_pending: int = 0,
    agent_id: str = "",
    min_age_hours: float = 2.0,
    _: None = Depends(verify_agent_access),
):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from datetime import date

    from cloud_deploy.cloud_api.agent_service import (
        DEFAULT_CLAIM_TTL_MINUTES,
        list_risk_worklist,
    )
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    limit = max(1, min(int(limit), 1000))
    day = (scan_date or date.today().isoformat())[:10]
    init_db()
    conn = _conn()
    try:
        return list_risk_worklist(
            conn,
            day,
            limit,
            include_pending=bool(include_pending),
            agent_id=agent_id.strip(),
            min_age_hours=max(0.0, float(min_age_hours)),
            claim_ttl_minutes=DEFAULT_CLAIM_TTL_MINUTES,
        )
    finally:
        conn.close()


@app.post("/api/v1/agent/scan-results")
def agent_scan_results(body: AgentScanUploadBody, _: None = Depends(verify_agent_access)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    if not body.rows:
        raise HTTPException(status_code=400, detail="rows 为空")
    if len(body.rows) > 500:
        raise HTTPException(status_code=400, detail="单批最多 500 条")
    from cloud_deploy.cloud_api.agent_service import apply_local_scan_batch
    from cloud_deploy.cloud_api.database_pg import _conn, init_db

    init_db()
    conn = _conn()
    try:
        payload = [r.model_dump() for r in body.rows]
        return apply_local_scan_batch(
            conn,
            payload,
            agent_id=body.agent_id,
            batch_id=body.batch_id,
        )
    finally:
        conn.close()


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


@app.post("/api/v1/auth/login-code")
def login_with_code(body: LoginCodeBody):
    return login_member_by_code(body.auth_code)


@app.post("/api/v1/auth/register")
def register(body: RegisterBody):
    try:
        profile = db.register_with_auth_code(body.username, body.password, body.auth_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"开通失败: {e}") from e
    try:
        token = create_token(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录令牌生成失败: {e}") from e
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


@app.post("/api/v1/auth/refresh")
def refresh_token(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
    access_token: str = "",
):
    token = (cred.credentials if cred else None) or (access_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    return refresh_member_token(token)


@app.get("/api/v1/member/profile")
def member_profile(user: dict = Depends(current_member)):
    profile = db.get_member_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="用户不存在")
    return profile


@app.post("/api/v1/member/change-password")
def member_change_password(body: ChangePasswordBody, user: dict = Depends(current_member)):
    current = body.current_password.strip() or None
    change_member_password(user["id"], body.new_password, current_password=current)
    return {"message": "密码已更新，下次可使用新密码登录"}


@app.get("/api/v1/member/reports")
def member_reports(
    archive_type: str = "member_daily_zip",
    user: dict = Depends(current_member),
):
    return {"items": db.list_archives(archive_type=archive_type), "user": user["username"]}


@app.get("/api/v1/member/library")
def member_library(user: dict = Depends(current_member)):
    """全部历史报告库（日报 + 周报 + 月报）。"""
    import logging

    logger = logging.getLogger(__name__)
    try:
        library = db.list_report_library()
        profile = db.get_member_profile(user["id"])
        return {"membership": profile, "library": library}
    except Exception as e:
        logger.exception("member_library failed for user_id=%s", user.get("id"))
        raise HTTPException(status_code=500, detail=f"报告库加载失败: {e}") from e


@app.get("/api/v1/member/watchlist")
def member_watchlist(
    limit: int = 500,
    user: dict = Depends(current_member),
):
    items = db.list_member_watchlist(user["id"], limit=min(max(limit, 1), 2000))
    return {"items": items, "count": len(items)}


@app.post("/api/v1/member/watchlist")
def member_watchlist_upsert(body: WatchlistUpsertBody, user: dict = Depends(current_member)):
    items = body.items or []
    if body.goods_ids and not items:
        items = [{"goods_id": gid.strip()} for gid in body.goods_ids if str(gid).strip()]
    if not items:
        raise HTTPException(status_code=400, detail="缺少 goods_ids 或 items")
    result = db.upsert_member_watchlist(user["id"], items, source=body.source or "")
    return {"message": "收藏已同步", **result}


@app.delete("/api/v1/member/watchlist")
def member_watchlist_delete(body: WatchlistDeleteBody, user: dict = Depends(current_member)):
    removed = db.delete_member_watchlist(user["id"], body.goods_ids)
    return {"message": f"已移除 {removed} 项", "removed": removed}


@app.get("/api/v1/member/reports/{report_date}/download")
def download_report(
    report_date: str,
    archive_type: str = "member_daily_zip",
    access_token: str = "",
    request: Request = None,
    cred: HTTPAuthorizationCredentials | None = Depends(security),
):
    from cloud_deploy.cloud_api.auth import member_from_token

    token = (cred.credentials if cred else None) or (access_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    user = member_from_token(token)
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


@app.get("/member/preview", response_class=HTMLResponse)
def member_preview_page():
    path = os.path.join(_ASSETS, "member_preview.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="预览页未部署")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/api/v1/member/reports/{report_date}/view/{file_path:path}")
def member_report_view_file(
    report_date: str,
    file_path: str,
    archive_type: str = "member_daily_zip",
    access_token: str = "",
    request: Request = None,
    cred: HTTPAuthorizationCredentials | None = Depends(security),
):
    from cloud_deploy.cloud_api.auth import member_from_token
    from cloud_deploy.cloud_api.member_report_preview import guess_media_type, resolve_member_report_file

    if archive_type not in _MEMBER_ARCHIVE_TYPES:
        raise HTTPException(status_code=400, detail="无效的报告类型")
    token = (cred.credentials if cred else None) or (access_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    user = member_from_token(token)
    try:
        path = resolve_member_report_file(report_date, archive_type, file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e) or "文件不存在") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    ip = request.client.host if request and request.client else ""
    db.log_download(user["id"], report_date, archive_type, ip)
    return FileResponse(path, media_type=guess_media_type(path))


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@app.post("/api/v1/member/reports/batch-download")
def batch_download_reports(
    body: BatchDownloadBody,
    request: Request = None,
    user: dict = Depends(current_member),
):
    """将会员选中的多份报告 zip 再打包为一个 zip 下载。"""
    if body.archive_type not in _MEMBER_ARCHIVE_TYPES:
        raise HTTPException(status_code=400, detail="无效的报告类型")

    seen: set[str] = set()
    ordered_dates: list[str] = []
    for raw in body.report_dates:
        date = str(raw).strip()[:10]
        if not date or date in seen:
            continue
        seen.add(date)
        ordered_dates.append(date)

    if not ordered_dates:
        raise HTTPException(status_code=400, detail="未选择有效报告")

    entries: list[tuple[str, str]] = []
    missing: list[str] = []
    ip = request.client.host if request and request.client else ""
    for date in ordered_dates:
        path = db.get_archive_path(date, body.archive_type)
        if not path or not os.path.isfile(path):
            missing.append(date)
            continue
        entries.append((date, path))

    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"以下报告不存在: {', '.join(missing)}",
        )
    if not entries:
        raise HTTPException(status_code=404, detail="没有可下载的报告")

    fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="member_batch_")
    os.close(fd)
    used_names: set[str] = set()
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for date, path in entries:
                base = os.path.basename(path)
                arcname = base
                if arcname in used_names:
                    stem, ext = os.path.splitext(base)
                    arcname = f"{stem}_{date}{ext or '.zip'}"
                used_names.add(arcname)
                zout.write(path, arcname=arcname)
                db.log_download(user["id"], date, body.archive_type, ip)
    except Exception:
        _remove_temp_file(tmp_path)
        raise

    type_short = body.archive_type.replace("member_", "").replace("_zip", "")
    stamp = datetime.now().strftime("%Y%m%d")
    out_name = f"reports_{type_short}_{len(entries)}份_{stamp}.zip"
    return FileResponse(
        tmp_path,
        media_type="application/zip",
        filename=out_name,
        background=BackgroundTask(_remove_temp_file, tmp_path),
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
    try:
        items = db.list_auth_codes(limit=limit, status=status or None)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e
    return {"items": items}


@app.post("/api/v1/admin/auth-codes/{code}/revoke")
def admin_revoke_code(code: str, _: None = Depends(verify_sync_key)):
    try:
        return db.revoke_auth_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e


@app.get("/api/v1/admin/stats")
def admin_stats(_: None = Depends(verify_sync_key)):
    try:
        stats = db.get_admin_stats()
        archives = db.list_archives()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库未就绪: {e}") from e
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
    from cloud_deploy.reporting.constants import ARCHIVE_DAILY, ARCHIVE_MONTHLY, ARCHIVE_WEEKLY

    daily_archives = db.list_archives(archive_type=ARCHIVE_DAILY)
    weekly_archives = db.list_archives(archive_type=ARCHIVE_WEEKLY)
    monthly_archives = db.list_archives(archive_type=ARCHIVE_MONTHLY)
    archives = daily_archives
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
        "latest": daily_archives[0] if daily_archives else None,
        "library": {
            "daily": daily_archives[:5],
            "weekly": weekly_archives[:5],
            "monthly": monthly_archives[:5],
        },
        "latest_weekly": weekly_archives[0] if weekly_archives else None,
        "latest_monthly": monthly_archives[0] if monthly_archives else None,
        "monitor_pool_active": pool_size,
        "sold_history_pending_backfill": pending_backfill,
        "sold_snapshots_pending_backfill": pending_snapshots,
    }


@app.post("/api/v1/sync/trigger-period-report")
def sync_trigger_period_report(body: PeriodReportTriggerBody, _: None = Depends(verify_sync_key)):
    """本地编排触发云端周报/月报（PG 聚合 → 同日报 HTML 模板 → zip 登记）。"""
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.scripts.cloud_period_report import generate_period_report

    try:
        result = generate_period_report(body.scope, body.end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    latest = result.get("report_date") or result.get("end_date") or ""
    return {
        "ok": True,
        "scope": body.scope,
        "report_date": latest,
        "row_count": result.get("row_count"),
        "file_name": result.get("file_name"),
        "output_dir": result.get("output_dir"),
        "archive_type": result.get("archive_type"),
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


@app.post("/api/v1/sync/report-upload")
async def sync_report_upload(
    request: Request,
    file: UploadFile = File(...),
    _: None = Depends(verify_sync_key),
):
    """方案 B：本地 gen_report 打包 zip 上传 → 解压 ingest → 会员可下载。"""
    from cloud_deploy.cloud_api.ingest_guard import ingest_force_enabled

    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少上传文件")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    max_mb = int(os.environ.get("XHS_REPORT_UPLOAD_MAX_MB", "200") or 200)
    if len(raw) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件超过 {max_mb}MB 限制")
    force = ingest_force_enabled(header_value=request.headers.get("X-Upload-Force", ""))
    try:
        from cloud_deploy.cloud_api.report_upload_service import ingest_report_upload_bytes

        return ingest_report_upload_bytes(raw, filename=file.filename or "report.zip", force=force)
    except zipfile.BadZipFile as e:
        raise HTTPException(status_code=400, detail=f"无效 zip: {e}") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ingest 失败: {e}") from e


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
    from cloud_deploy.cloud_api.retention_policy import (
        retention_policy_summary,
        snapshot_prune_enabled,
    )
    from cloud_deploy.cloud_api.sync_service import prune_sold_snapshots

    if not snapshot_prune_enabled():
        return {
            "deleted_rows": 0,
            "skipped": "retention_disabled",
            **retention_policy_summary(),
        }

    init_db()
    conn = _conn()
    try:
        deleted = prune_sold_snapshots(conn)
        return {"deleted_rows": deleted, **retention_policy_summary()}
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-upsert")
def sync_premium_upsert(body: PremiumUpsertBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_upsert

    init_db()
    conn = _conn()
    try:
        result = apply_premium_upsert(conn, body.rows, client_id=body.client_id)
        conn.commit()
        return result
    finally:
        conn.close()


@app.get("/api/v1/sync/premium-changes")
def sync_premium_changes(
    since: int = 0,
    limit: int = 500,
    _: None = Depends(verify_sync_key),
):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import get_premium_changes

    init_db()
    conn = _conn()
    try:
        return get_premium_changes(conn, since=since, limit=limit)
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-snapshots-backfill")
def sync_premium_snapshots_backfill(
    body: PremiumSnapshotsBackfillBody,
    _: None = Depends(verify_sync_key),
):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_snapshots_backfill

    init_db()
    conn = _conn()
    try:
        result = apply_snapshots_backfill(
            conn, body.goods_id, body.goods_daily, body.store_daily
        )
        conn.commit()
        return result
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-catalog")
def sync_premium_catalog(body: PremiumCatalogBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_catalog

    init_db()
    conn = _conn()
    try:
        return apply_premium_catalog(
            conn,
            body.local_ids,
            since_date=body.since_date,
            page=body.page,
            page_size=body.page_size,
        )
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-fetch")
def sync_premium_fetch(body: PremiumFetchBody, _: None = Depends(verify_sync_key)):
    """按 goods_id 拉取云精品行（本地缺的 cloud_only 商品）。"""
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import fetch_premium_goods_by_ids

    init_db()
    conn = _conn()
    try:
        rows = fetch_premium_goods_by_ids(conn, body.goods_ids[:2000])
        return {"rows": rows, "count": len(rows)}
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-daily-fetch")
def sync_premium_daily_fetch(body: PremiumDailyFetchBody, _: None = Depends(verify_sync_key)):
    """按 goods_id 批量拉取云 premium_goods_daily 日快照。"""
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import fetch_premium_goods_daily_by_ids

    init_db()
    conn = _conn()
    try:
        return fetch_premium_goods_daily_by_ids(
            conn,
            body.goods_ids[:500],
            since_date=body.since_date,
            max_rows=body.max_rows,
        )
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-daily-upsert")
def sync_premium_daily_upsert(body: PremiumBatchSyncBody, _: None = Depends(verify_sync_key)):
    """批量推送 premium_goods_daily 日快照（本地历史 → 云 PG）。"""
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    if not body.rows:
        raise HTTPException(status_code=400, detail="rows 为空")
    if len(body.rows) > 2000:
        raise HTTPException(status_code=400, detail="单批最多 2000 行")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_goods_daily_batch

    init_db()
    conn = _conn()
    try:
        n = apply_premium_goods_daily_batch(conn, body.rows)
        conn.commit()
        return {
            "batch_id": body.batch_id,
            "rows_upserted": n,
            "final_batch": body.final_batch,
        }
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
