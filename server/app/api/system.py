from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import AdminUser, CurrentUser
from app.services.feature_flag import feature_flag_service
from app.services.backup_service import backup_service
from app.middleware.tracing import get_trace, get_all_traces, clear_traces
from app.services.error_capture import error_capture
from app.services.sla_monitor import sla_monitor

router = APIRouter(tags=["system"])


class FlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    rollout_pct: int | None = None
    allowed_plans: list[str] | None = None
    description: str | None = None


@router.get("/feature-flags")
async def list_feature_flags(user: CurrentUser):
    flags = await feature_flag_service.get_all_flags()
    return {"code": 0, "data": flags}


@router.get("/feature-flags/{flag_name}/check")
async def check_feature_flag(
    flag_name: str,
    user: CurrentUser,
):
    enabled = await feature_flag_service.is_enabled(
        flag_name, str(user.id), user.plan
    )
    return {"code": 0, "data": {"flag": flag_name, "enabled": enabled}}


@router.put("/feature-flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    req: FlagUpdateRequest,
    admin: AdminUser,
):
    config = {}
    if req.enabled is not None:
        config["enabled"] = req.enabled
    if req.rollout_pct is not None:
        config["rollout_pct"] = req.rollout_pct
    if req.allowed_plans is not None:
        config["allowed_plans"] = req.allowed_plans
    if req.description is not None:
        config["description"] = req.description

    result = await feature_flag_service.set_flag(flag_name, config)
    return {"code": 0, "data": result}


@router.delete("/feature-flags/{flag_name}")
async def delete_feature_flag(
    flag_name: str,
    admin: AdminUser,
):
    success = await feature_flag_service.delete_flag(flag_name)
    return {"code": 0 if success else 404, "message": "已删除" if success else "标志不存在"}


@router.post("/feature-flags/reset")
async def reset_feature_flags(admin: AdminUser):
    flags = await feature_flag_service.reset_to_defaults()
    return {"code": 0, "data": flags}


@router.post("/backups")
async def create_backup(
    admin: AdminUser,
    label: str = Query("manual", max_length=50),
):
    result = await backup_service.create_backup(label)
    return {"code": 0, "data": result}


@router.get("/backups")
async def list_backups(admin: AdminUser):
    backups = await backup_service.list_backups()
    return {"code": 0, "data": {"items": backups, "count": len(backups)}}


@router.post("/backups/{backup_name}/restore")
async def restore_backup(
    backup_name: str,
    admin: AdminUser,
):
    result = await backup_service.restore_backup(backup_name)
    return {"code": 0 if result.get("status") == "success" else 500, "data": result}


@router.post("/backups/cleanup")
async def cleanup_backups(
    admin: AdminUser,
    retention_days: int = Query(30, ge=1, le=365),
):
    removed = await backup_service.cleanup_old_backups(retention_days)
    return {"code": 0, "data": {"removed_count": removed}}


@router.get("/traces")
async def list_traces(
    admin: AdminUser,
    limit: int = Query(50, ge=1, le=200),
):
    traces = get_all_traces(limit)
    return {"code": 0, "data": {"items": traces, "count": len(traces)}}


@router.get("/traces/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    admin: AdminUser,
):
    trace = get_trace(trace_id)
    if not trace:
        return {"code": 404, "message": "Trace not found"}
    return {"code": 0, "data": trace}


@router.delete("/traces")
async def clear_all_traces(admin: AdminUser):
    clear_traces()
    return {"code": 0, "message": "All traces cleared"}


@router.get("/errors")
async def list_errors(
    admin: AdminUser,
    limit: int = Query(50, ge=1, le=200),
    level: str | None = None,
):
    events = error_capture.get_events(limit, level)
    return {"code": 0, "data": {"items": events, "count": len(events)}}


@router.delete("/errors")
async def clear_errors(admin: AdminUser):
    error_capture.clear_events()
    return {"code": 0, "message": "All errors cleared"}


@router.get("/sla")
async def get_sla_config(user: CurrentUser):
    slos = sla_monitor.get_slos()
    return {"code": 0, "data": slos}


@router.put("/sla/{slo_name}")
async def update_sla_config(
    slo_name: str,
    admin: AdminUser,
    target: float | None = None,
    description: str | None = None,
):
    config = {}
    if target is not None:
        config["target"] = target
    if description is not None:
        config["description"] = description
    result = sla_monitor.update_slo(slo_name, config)
    return {"code": 0, "data": result}


@router.get("/client/latest")
async def get_latest_client_version():
    import json
    import os

    downloads_dir = os.environ.get("DOWNLOADS_DIR", "/var/www/xhs365/downloads")
    manifest_path = os.path.join(downloads_dir, "latest.json")

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"code": 0, "data": data}

    return {
        "code": 0,
        "data": {
            "version": "0.1.0",
            "releaseDate": None,
            "platforms": {},
            "downloadBaseUrl": "/downloads",
        },
    }


@router.get("/client/download/{platform}")
async def get_client_download_link(platform: str):
    import json
    import os

    valid_platforms = {"windows", "macos", "linux"}
    if platform not in valid_platforms:
        return {"code": 400, "message": f"不支持的平台: {platform}"}

    downloads_dir = os.environ.get("DOWNLOADS_DIR", "/var/www/xhs365/downloads")
    manifest_path = os.path.join(downloads_dir, "latest.json")

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        platform_data = data.get("platforms", {}).get(platform, {})
        if platform_data:
            return {"code": 0, "data": platform_data}

    return {"code": 404, "message": f"未找到 {platform} 平台的安装包"}


@router.post("/upload-download")
async def upload_download_file(
    admin: AdminUser,
    file: UploadFile = File(...),
):
    import os
    downloads_dir = os.environ.get("DOWNLOADS_DIR", "/opt/vuemonitor/deploy/downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    dest = os.path.join(downloads_dir, file.filename)
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    size = os.path.getsize(dest)
    return {"code": 0, "data": {"filename": file.filename, "size": size, "path": dest}}
