from datetime import datetime

from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class TeamUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)

class TeamMemberResponse(BaseModel):
    user_id: str
    nickname: str
    avatar_url: str | None = None
    role: str
    joined_at: datetime
    model_config = {"from_attributes": True}

class TeamResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    owner_id: str
    invite_code: str
    member_count: int
    members: list[TeamMemberResponse] = []
    shared_products: list[str] = []
    shared_rules: list[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}

class TeamJoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=1)

class TeamMemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")
