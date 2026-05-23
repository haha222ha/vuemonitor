from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    platform: str = Field(..., max_length=20)
    name: str | None = Field(None, max_length=500)

class ProductUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=500)
    is_monitoring: bool | None = None
    category: str | None = Field(None, max_length=100)

class ProductResponse(BaseModel):
    id: str
    name: str
    shop_name: str | None = None
    platform: str
    category: str | None = None
    price: float | None = None
    original_price: float | None = None
    sales: int | None = None
    monthly_sales: int | None = None
    rating: float | None = None
    review_count: int | None = None
    favorite_count: int | None = None
    url: str
    image_url: str | None = None
    last_collected_at: datetime | None = None
    trend: str = "stable"
    is_monitoring: bool = True
    created_at: datetime
    model_config = {"from_attributes": True}

class ProductListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    keyword: str | None = None
    platform: str | None = None
    category: str | None = None
    is_monitoring: bool | None = None

class ProductListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductResponse]

class ProductFeatureSnapshot(BaseModel):
    product_id: str
    price: float | None = None
    sales: int | None = None
    monthly_sales: int | None = None
    rating: float | None = None
    review_count: int | None = None
    favorite_count: int | None = None
    collected_at: datetime
    model_config = {"from_attributes": True}

class ProductBenchmarkComparison(BaseModel):
    product_id: str
    category: str
    platform: str
    rank_percentile: float | None = None
    price_competitiveness: float | None = None
    sales_rank: int | None = None
    rating_rank: int | None = None
    category_avg_price: float | None = None
    category_avg_sales: float | None = None
    category_avg_rating: float | None = None
