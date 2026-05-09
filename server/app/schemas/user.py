from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserUpdateRequest(BaseModel):
    nickname: str | None = Field(None, min_length=2, max_length=50)
    avatar_url: str | None = None


class AdminUserUpdateRequest(BaseModel):
    nickname: str | None = None
    plan: str | None = None
    plan_expires_at: datetime | None = None
    role: str | None = None
    is_active: bool | None = None


class UserListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    keyword: str | None = None
    plan: str | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[dict]
