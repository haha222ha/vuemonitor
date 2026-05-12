from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class AIAnalysisRequest(BaseModel):
    product_id: str
    analysis_type: str = Field("comprehensive", pattern="^(comprehensive|price|competition|trend|risk)$")
    options: dict[str, Any] = {}

class AIAnalysisResponse(BaseModel):
    id: str
    product_id: str
    analysis_type: str
    result: dict[str, Any]
    score: Optional[float] = None
    summary: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class AIReportRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=1)
    report_type: str = Field("comprehensive", pattern="^(comprehensive|price|competition|trend)$")

class AIReportResponse(BaseModel):
    id: str
    title: str
    content: str
    format: str = "markdown"
    created_at: datetime
    model_config = {"from_attributes": True}

class AITemplateResponse(BaseModel):
    id: str
    name: str
    analysis_type: str
    prompt_template: str
    is_default: bool = False
    model_config = {"from_attributes": True}