from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class TeamUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class TeamMemberResponse(BaseModel):
    user_id: str
    nickname: str
    avatar_url: Optional[str] = None
    role: str
    joined_at: datetime
    model_config = {"from_attributes": True}

class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
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