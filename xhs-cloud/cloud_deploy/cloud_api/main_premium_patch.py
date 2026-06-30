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

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from cloud_deploy.cloud_api import database as db
from cloud_deploy.cloud_api.auth import current_member, login_member, verify_sync_key
from cloud_deploy.cloud_api.config import get_settings

app = FastAPI(title="XHS 选品云服务", version="1.0.0")


@app.on_event("startup")
def _startup():
    db.init_db()
    db.ensure_admin()


class LoginBody(BaseModel):
    username: str
    password: str


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


class PremiumBatchSyncBody(BaseModel):
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


class BatchDownloadBody(BaseModel):
    archive_type: str = "member_daily_zip"
    report_dates: list[str] = Field(..., min_length=1, max_length=50)


_MEMBER_ARCHIVE_TYPES = frozenset(
    {"member_daily_zip", "member_weekly_zip", "member_monthly_zip"}
)


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/login")
def login(body: LoginBody):
    return login_member(body.username, body.password)


@app.get("/api/v1/member/reports")
def member_reports(
    archive_type: str = "member_daily_zip",
    user: dict = Depends(current_member),
):
    return {"items": db.list_archives(archive_type=archive_type), "user": user["username"]}


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


@app.post("/api/v1/member/reports/batch-download")
def batch_download_reports(
    body: BatchDownloadBody,
    request: Request = None,
    user: dict = Depends(current_member),
):
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


@app.post("/api/v1/sync/premium-goods")
def sync_premium_goods(body: PremiumBatchSyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_goods_batch

    init_db()
    conn = _conn()
    try:
        n = apply_premium_goods_batch(conn, body.rows)
        conn.commit()
        return {"batch_id": body.batch_id, "rows_upserted": n, "final_batch": body.final_batch}
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-goods-daily")
def sync_premium_goods_daily(body: PremiumBatchSyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_goods_daily_batch

    init_db()
    conn = _conn()
    try:
        n = apply_premium_goods_daily_batch(conn, body.rows)
        conn.commit()
        return {"batch_id": body.batch_id, "rows_upserted": n, "final_batch": body.final_batch}
    finally:
        conn.close()


@app.post("/api/v1/sync/premium-store-daily")
def sync_premium_store_daily(body: PremiumBatchSyncBody, _: None = Depends(verify_sync_key)):
    if not os.environ.get("XHS_DATABASE_URL", "").startswith("postgres"):
        raise HTTPException(status_code=503, detail="未配置 XHS_DATABASE_URL")
    from cloud_deploy.cloud_api.database_pg import _conn, init_db
    from cloud_deploy.cloud_api.premium_sync_service import apply_premium_store_daily_batch

    init_db()
    conn = _conn()
    try:
        n = apply_premium_store_daily_batch(conn, body.rows)
        conn.commit()
        return {"batch_id": body.batch_id, "rows_upserted": n, "final_batch": body.final_batch}
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
        return apply_premium_catalog(conn, body.local_ids, since_date=body.since_date)
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
