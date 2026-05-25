import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.content_filter import is_demo_content
from app.api.intelligence.deps import get_intel_plan, verify_sync_token
from app.core.database import get_db
from app.models.intelligence import IntelligenceReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["intel-reports"])

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


@router.get("")
async def list_reports(
    plan: str = Depends(get_intel_plan),
    report_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntelligenceReport)

    if plan == "free":
        return {"plan": "free", "count": 0, "items": [], "message": "free tier does not include reports"}
    elif plan == "weekly":
        stmt = stmt.where(IntelligenceReport.report_type == "weekly")
    elif plan == "monthly":
        stmt = stmt.where(IntelligenceReport.report_type.in_(["weekly", "monthly"]))
    elif plan in ("yearly", "enterprise"):
        pass

    if report_type:
        stmt = stmt.where(IntelligenceReport.report_type == report_type)

    stmt = stmt.order_by(IntelligenceReport.report_date.desc())

    result = await db.execute(stmt)
    reports = [r for r in result.scalars().all() if not is_demo_content(r.title)]

    return {
        "plan": plan,
        "count": len(reports),
        "items": [
            {
                "id": str(r.id), "report_type": r.report_type,
                "title": r.title, "week_number": r.week_number,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "content_json": r.content_json, "content_html": r.content_html,
                "file_path": r.content_html, "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
    }


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    report_type: str = Form("weekly"),
    title: str = Form(...),
    week_number: str | None = Form(None),
    report_date: str = Form(...),
    _auth: bool = Depends(verify_sync_token),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="no filename")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".html", ".htm", ".pdf"):
        raise HTTPException(status_code=400, detail="only .html/.htm/.pdf files allowed")

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{report_type}_{file_id}{ext}"
    file_path = os.path.join(REPORTS_DIR, safe_name)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="file too large (max 10MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        report_date_dt = datetime.fromisoformat(report_date).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        report_date_dt = datetime.now(timezone.utc)

    report = IntelligenceReport(
        report_type=report_type,
        title=title,
        week_number=week_number,
        report_date=report_date_dt,
        content_html=f"/static/reports/{safe_name}",
    )
    db.add(report)
    await db.flush()
    await db.commit()

    logger.info(f"Report uploaded: {safe_name} ({len(content)} bytes)")

    return {
        "status": "ok",
        "id": str(report.id),
        "filename": safe_name,
        "url": f"/static/reports/{safe_name}",
        "size": len(content),
    }


@router.get("/files/{filename}")
async def serve_report_file(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="file not found")
    ext = os.path.splitext(filename)[1].lower()
    media_type = "text/html" if ext in (".html", ".htm") else "application/pdf"
    return FileResponse(file_path, media_type=media_type)
