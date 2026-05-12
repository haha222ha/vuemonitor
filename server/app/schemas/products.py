from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ProductCreateRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    platform: str = Field(..., max_length=20)
    name: Optional[str] = Field(None, max_length=500)

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=500)
    is_monitoring: Optional[bool] = None
    category: Optional[str] = Field(None, max_length=100)

class ProductResponse(BaseModel):
    id: str
    name: str
    shop_name: Optional[str] = None
    platform: str
    category: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    sales: Optional[int] = None
    monthly_sales: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    favorite_count: Optional[int] = None
    url: str
    image_url: Optional[str] = None
    last_collected_at: Optional[datetime] = None
    trend: str = "stable"
    is_monitoring: bool = True
    created_at: datetime
    model_config = {"from_attributes": True}

class ProductListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    keyword: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    is_monitoring: Optional[bool] = None

class ProductListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductResponse]

class ProductFeatureSnapshot(BaseModel):
    product_id: str
    price: Optional[float] = None
    sales: Optional[int] = None
    monthly_sales: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    favorite_count: Optional[int] = None
    collected_at: datetime
    model_config = {"from_attributes": True}

class ProductBenchmarkComparison(BaseModel):
    product_id: str
    category: str
    platform: str
    rank_percentile: Optional[float] = None
    price_competitiveness: Optional[float] = None
    sales_rank: Optional[int] = None
    rating_rank: Optional[int] = None
    category_avg_price: Optional[float] = None
    category_avg_sales: Optional[float] = None
    category_avg_rating: Optional[float] = None