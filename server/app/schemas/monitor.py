from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class MonitorRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    condition_type: str = Field(..., pattern="^(price_drop|sales_surge|rating_drop|out_of_stock|custom)$")
    condition_config: dict[str, Any] = {}
    action_type: str = Field("notify", pattern="^(notify|ai_analysis|export)$")
    is_active: bool = True
    product_ids: list[str] = []

class MonitorRuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    condition_type: Optional[str] = None
    condition_config: Optional[dict[str, Any]] = None
    action_type: Optional[str] = None
    is_active: Optional[bool] = None
    product_ids: Optional[list[str]] = None

class MonitorRuleResponse(BaseModel):
    id: str
    name: str
    condition_type: str
    condition_config: dict[str, Any]
    action_type: str
    is_active: bool
    product_ids: list[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class CollectStatusResponse(BaseModel):
    status: str = "idle"
    concurrency: int = 0
    queue_size: int = 0
    memory_usage: float = 0.0
    active_tasks: int = 0