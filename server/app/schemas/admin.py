from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class AdminStatsResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    today_tasks: int = 0
    available_proxies: int = 0
    today_registrations: int = 0
    active_licenses: int = 0
    risk_events_count: int = 0
    system_health: float = 100.0

class SystemMetricsResponse(BaseModel):
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_ws_connections: int = 0
    today_api_requests: int = 0
    today_collect_tasks: int = 0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0

class SystemEventResponse(BaseModel):
    id: str
    type: str
    message: str
    severity: str = "info"
    created_at: datetime
    model_config = {"from_attributes": True}

class AlertRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    condition_type: str
    condition_config: dict[str, Any] = {}
    severity: str = "medium"
    channel_id: Optional[str] = None

class AlertRuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    condition_type: Optional[str] = None
    condition_config: Optional[dict[str, Any]] = None
    severity: Optional[str] = None
    channel_id: Optional[str] = None
    is_active: Optional[bool] = None

class AlertRuleResponse(BaseModel):
    id: str
    name: str
    condition_type: str
    condition_config: dict[str, Any]
    severity: str
    channel: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    model_config = {"from_attributes": True}

class AlertChannelCreateRequest(BaseModel):
    type: str = Field(..., pattern="^(email|webhook|dingtalk|wechat)$")
    config: dict[str, Any]
    is_enabled: bool = True

class AlertChannelUpdateRequest(BaseModel):
    config: Optional[dict[str, Any]] = None
    is_enabled: Optional[bool] = None

class AlertChannelResponse(BaseModel):
    id: str
    type: str
    config: dict[str, Any]
    is_enabled: bool = True
    last_test_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class SecurityAuditEventResponse(BaseModel):
    id: str
    event_type: str
    severity: str
    user_id: Optional[str] = None
    ip: Optional[str] = None
    detail: str
    created_at: datetime
    model_config = {"from_attributes": True}

class SecurityAuditQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    event_type: Optional[str] = None
    severity: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class GdprExportRequestResponse(BaseModel):
    id: str
    user_email: str
    status: str = "pending"
    requested_at: datetime
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class GdprDeletionRequestResponse(BaseModel):
    id: str
    user_email: str
    status: str = "pending"
    retention_days: int = 30
    requested_at: datetime
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class GdprStatsResponse(BaseModel):
    total_export_requests: int = 0
    total_deletion_requests: int = 0
    pending_requests: int = 0
    avg_response_time_hours: float = 0.0

class BenchmarkResponse(BaseModel):
    id: str
    category: str
    platform: str
    avg_price: float = 0.0
    avg_sales: float = 0.0
    avg_rating: float = 0.0
    product_count: int = 0
    updated_at: datetime
    model_config = {"from_attributes": True}

class LicenseGenerateRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|premium|enterprise)$")
    duration_days: int = Field(30, ge=1)
    count: int = Field(1, ge=1, le=100)

class LicenseResponse(BaseModel):
    id: str
    code: str
    plan: str
    duration_days: int
    status: str
    created_at: datetime
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None
    model_config = {"from_attributes": True}

class WeeklyRegistrationItem(BaseModel):
    date: str
    count: int

class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)