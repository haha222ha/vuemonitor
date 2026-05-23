from datetime import datetime

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    content: str
    is_read: bool = False
    product_id: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}

class NotificationListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    type: str | None = None
    is_read: bool | None = None

class UnreadCountResponse(BaseModel):
    count: int
