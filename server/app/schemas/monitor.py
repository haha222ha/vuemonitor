from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MonitorRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    condition_type: str = Field(..., pattern="^(price_drop|sales_surge|rating_drop|out_of_stock|custom)$")
    condition_config: dict[str, Any] = {}
    action_type: str = Field("notify", pattern="^(notify|ai_analysis|export)$")
    is_active: bool = True
    product_ids: list[str] = []

class MonitorRuleUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    condition_type: str | None = None
    condition_config: dict[str, Any] | None = None
    action_type: str | None = None
    is_active: bool | None = None
    product_ids: list[str] | None = None

class MonitorRuleResponse(BaseModel):
    id: str
    name: str
    condition_type: str
    condition_config: dict[str, Any]
    action_type: str
    is_active: bool
    product_ids: list[str]
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class CollectStatusResponse(BaseModel):
    status: str = "idle"
    concurrency: int = 0
    queue_size: int = 0
    memory_usage: float = 0.0
    active_tasks: int = 0
