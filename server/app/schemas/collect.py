from datetime import datetime

from pydantic import BaseModel, Field


class CollectTaskCreateRequest(BaseModel):
    task_type: str = Field(..., pattern="^(product|shop|category|author)$")
    platform: str = Field(..., max_length=20)
    target_type: str = Field("product_id", pattern="^(product_id|shop_id|category_url|author_id)$")
    target_ids: list[str] = Field(..., min_length=1)

class CollectTaskResponse(BaseModel):
    id: str
    task_type: str
    platform: str
    target_type: str
    target_ids: list[str]
    status: str = "pending"
    progress: float = 0.0
    result_summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    model_config = {"from_attributes": True}

class CollectTaskListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    status: str | None = None
    platform: str | None = None
    task_type: str | None = None
