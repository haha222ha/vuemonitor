import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.auth import CurrentUser
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.category import ProductCategory
from app.models.product import Product

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=20)
    sort_order: int = Field(0, ge=0)
    parent_id: str | None = None


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=20)
    sort_order: int | None = Field(None, ge=0)
    parent_id: str | None = None
    is_active: bool | None = None


@router.get("")
async def list_categories(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:category")

    result = await db.execute(
        select(ProductCategory)
        .where(ProductCategory.user_id == user.id, ProductCategory.is_active)
        .order_by(ProductCategory.sort_order, ProductCategory.created_at)
    )
    categories = result.scalars().all()

    count_result = await db.execute(
        select(Product.category_id, func.count().label("cnt"))
        .where(Product.user_id == user.id, Product.is_active, Product.category_id.isnot(None))
        .group_by(Product.category_id)
    )
    counts = {str(row.category_id): row.cnt for row in count_result.all()}

    items = []
    for cat in categories:
        items.append({
            "id": str(cat.id),
            "name": cat.name,
            "icon": cat.icon,
            "color": cat.color,
            "sort_order": cat.sort_order,
            "parent_id": str(cat.parent_id) if cat.parent_id else None,
            "product_count": counts.get(str(cat.id), 0),
            "created_at": cat.created_at.isoformat() if cat.created_at else None,
        })

    return {"code": 0, "data": {"categories": items}}


@router.post("", status_code=201)
async def create_category(
    req: CategoryCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:category")

    parent_id = None
    if req.parent_id:
        try:
            parent_id = uuid.UUID(req.parent_id)
        except ValueError:
            raise BadRequestException(message="无效的父分类ID")
        parent = await db.execute(
            select(ProductCategory).where(
                ProductCategory.id == parent_id,
                ProductCategory.user_id == user.id,
            )
        )
        if not parent.scalar_one_or_none():
            raise NotFoundException(message="父分类不存在")

    category = ProductCategory(
        user_id=user.id,
        name=req.name,
        icon=req.icon,
        color=req.color,
        sort_order=req.sort_order,
        parent_id=parent_id,
    )
    db.add(category)
    await db.flush()

    return {
        "code": 0,
        "data": {
            "id": str(category.id),
            "name": category.name,
        },
    }


@router.put("/{category_id}")
async def update_category(
    category_id: str,
    req: CategoryUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:category")

    try:
        cat_uuid = uuid.UUID(category_id)
    except ValueError:
        raise BadRequestException(message="无效的分类ID")

    result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.id == cat_uuid,
            ProductCategory.user_id == user.id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise NotFoundException(message="分类不存在")

    if req.name is not None:
        category.name = req.name
    if req.icon is not None:
        category.icon = req.icon
    if req.color is not None:
        category.color = req.color
    if req.sort_order is not None:
        category.sort_order = req.sort_order
    if req.is_active is not None:
        category.is_active = req.is_active
    if req.parent_id is not None:
        if req.parent_id == "":
            category.parent_id = None
        else:
            try:
                new_parent_id = uuid.UUID(req.parent_id)
            except ValueError:
                raise BadRequestException(message="无效的父分类ID")
            if new_parent_id == cat_uuid:
                raise BadRequestException(message="不能将分类设为自身的子分类")
            category.parent_id = new_parent_id

    await db.flush()

    return {"code": 0, "data": {"id": str(category.id)}}


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:category")

    try:
        cat_uuid = uuid.UUID(category_id)
    except ValueError:
        raise BadRequestException(message="无效的分类ID")

    result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.id == cat_uuid,
            ProductCategory.user_id == user.id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise NotFoundException(message="分类不存在")

    await db.execute(
        Product.__table__.update()
        .where(Product.category_id == cat_uuid, Product.user_id == user.id)
        .values(category_id=None)
    )

    await db.delete(category)
    await db.flush()

    return {"code": 0, "data": {"deleted": True}}


@router.post("/reorder")
async def reorder_categories(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    order: list[str] = [],
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:category")

    for idx, cat_id_str in enumerate(order):
        try:
            cat_uuid = uuid.UUID(cat_id_str)
        except ValueError:
            continue
        result = await db.execute(
            select(ProductCategory).where(
                ProductCategory.id == cat_uuid,
                ProductCategory.user_id == user.id,
            )
        )
        category = result.scalar_one_or_none()
        if category:
            category.sort_order = idx

    await db.flush()

    return {"code": 0, "data": {"reordered": len(order)}}
