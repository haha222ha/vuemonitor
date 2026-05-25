import hashlib
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import SyncRequest, compute_item_checksum, verify_sync_token
from app.core.database import get_db
from app.models.intelligence import (
    IntelSyncBatch,
    IntelligenceOpportunity,
    IntelligencePlatformSignal,
    IntelligenceRisk,
    IntelligenceTrend,
    IntelligenceUserEmotion,
    IntelligenceXhsTopic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["intel-sync"], dependencies=[Depends(verify_sync_token)])


def _filter_item_for_model(item: dict, model_class) -> dict:
    valid_keys = set(c.name for c in model_class.__table__.columns)
    dt_columns = {
        c.name for c in model_class.__table__.columns
        if hasattr(c, "type") and c.type.__class__.__name__ == "DateTime"
    }
    filtered = {}
    extra = {}
    for k, v in item.items():
        if k in valid_keys:
            if k in dt_columns and isinstance(v, str):
                try:
                    v = datetime.fromisoformat(v).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass
            filtered[k] = v
        else:
            extra[k] = v
    if extra and "source_data" in valid_keys:
        existing = filtered.get("source_data", {})
        if isinstance(existing, dict):
            existing.update(extra)
        else:
            existing = extra
        filtered["source_data"] = existing
    return filtered


def _records_match(existing, incoming: dict, key_field: str) -> bool:
    existing_checksum = hashlib.sha256(
        json.dumps({
            k: str(v) if not isinstance(v, (dict, list)) else json.dumps(v, sort_keys=True, ensure_ascii=False)
            for k, v in existing.items()
            if k not in ("_checksum", "id", "created_at", "updated_at")
        }, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    incoming_checksum = hashlib.sha256(
        json.dumps({
            k: str(v) if not isinstance(v, (dict, list)) else json.dumps(v, sort_keys=True, ensure_ascii=False)
            for k, v in incoming.items()
            if k not in ("_checksum", "id", "created_at", "updated_at")
        }, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    return existing_checksum == incoming_checksum


async def _upsert_batch(
    db: AsyncSession,
    model_class,
    table_name: str,
    key_field: str,
    items: list[dict],
    batch_id: str,
) -> dict:
    results = []
    created = updated = skipped = errors = 0

    for item in items:
        try:
            key_value = item.get(key_field)
            if not key_value:
                errors += 1
                results.append({"action": "error", "status": "missing_key", "detail": "key field missing"})
                continue

            client_checksum = item.pop("_checksum", "")
            item = _filter_item_for_model(item, model_class)
            stmt = select(model_class).where(getattr(model_class, key_field) == key_value)
            query_result = await db.execute(stmt)
            existing = query_result.scalar_one_or_none()

            if existing:
                if _records_match({
                    c.name: getattr(existing, c.name) for c in model_class.__table__.columns
                }, item, key_field):
                    skipped += 1
                    results.append({
                        "action": "skipped",
                        "title": key_value,
                        "id": str(existing.id),
                        "status": "ok",
                        "client_checksum": client_checksum,
                    })
                    continue

                for field_name, value in item.items():
                    if hasattr(existing, field_name) and field_name not in ("id", "created_at"):
                        setattr(existing, field_name, value)

                updated += 1
                record_id = str(existing.id)
                results.append({
                    "action": "updated",
                    "title": key_value,
                    "id": record_id,
                    "status": "ok",
                    "client_checksum": client_checksum,
                })
            else:
                instance = model_class(**item)
                db.add(instance)
                await db.flush()
                created += 1
                record_id = str(instance.id)
                results.append({
                    "action": "created",
                    "title": key_value,
                    "id": record_id,
                    "status": "ok",
                    "client_checksum": client_checksum,
                })

        except Exception as e:
            logger.error(f"Upsert item error: {e}", exc_info=True)
            errors += 1
            results.append({"action": "error", "title": item.get(key_field, "unknown"), "status": "error", "detail": str(e)[:200]})

    await db.flush()

    summary = {
        "total": len(items),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }

    sync_batch = IntelSyncBatch(
        batch_id=batch_id,
        sync_table=table_name,
        total_items=len(items),
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
        error_count=errors,
        status="success" if errors == 0 else "partial_success",
        detail_log=summary,
    )
    db.add(sync_batch)

    return {
        "batch_id": batch_id,
        "status": "success" if errors == 0 else "partial_success",
        "summary": summary,
        "items": results,
    }


@router.post("/trends")
async def sync_trends(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligenceTrend, "intelligence_trends", "title", req.items, req.sync_batch_id)


@router.post("/opportunities")
async def sync_opportunities(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligenceOpportunity, "intelligence_opportunities", "name", req.items, req.sync_batch_id)


@router.post("/risks")
async def sync_risks(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligenceRisk, "intelligence_risks", "name", req.items, req.sync_batch_id)


@router.post("/topics")
async def sync_topics(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligenceXhsTopic, "intelligence_xhs_topics", "title", req.items, req.sync_batch_id)


@router.post("/signals")
async def sync_signals(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligencePlatformSignal, "intelligence_platform_signals", "platform", req.items, req.sync_batch_id)


@router.post("/emotions")
async def sync_emotions(req: SyncRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(IntelSyncBatch).where(IntelSyncBatch.batch_id == req.sync_batch_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"status": "duplicate", "batch_id": req.sync_batch_id, "message": "batch already processed"}
    return await _upsert_batch(db, IntelligenceUserEmotion, "intelligence_user_emotions", "keyword", req.items, req.sync_batch_id)