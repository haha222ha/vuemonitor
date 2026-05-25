import uuid
import hashlib
import json
import logging
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.config import get_settings
from app.middleware.auth import CurrentUser
from app.api.intelligence.plan_utils import get_effective_membership
from app.models.intelligence import IntelMembership

logger = logging.getLogger(__name__)

sync_bearer = HTTPBearer()

INTEL_SYNC_API_KEY = getattr(get_settings(), "INTEL_SYNC_API_KEY", "")


async def verify_sync_token(credentials: HTTPAuthorizationCredentials = Depends(sync_bearer)):
    if not INTEL_SYNC_API_KEY:
        raise HTTPException(status_code=403, detail="sync api not configured")
    if credentials.credentials != INTEL_SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid sync token")
    return True


async def get_intel_membership(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> IntelMembership:
    membership = await get_effective_membership(user.id, db)
    if not membership:
        raise HTTPException(status_code=403, detail="no active intel membership")
    return membership


async def get_intel_plan(membership: IntelMembership = Depends(get_intel_membership)) -> str:
    return membership.plan


def compute_item_checksum(item: dict) -> str:
    clean = {k: v for k, v in item.items() if k != "_checksum"}
    serialized = json.dumps(clean, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


class SyncRequest(BaseModel):
    sync_batch_id: str = Field(..., max_length=100)
    key_field: str = Field(default="title", max_length=50)
    items: list[dict] = Field(..., max_length=50)