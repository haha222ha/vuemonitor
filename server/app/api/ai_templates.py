import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.auth import CurrentUser
from app.models.ai import AIReportTemplate

router = APIRouter(prefix="/ai/templates", tags=["AI报告模板"])

DEFAULT_TEMPLATES = [
    {
        "name": "商品分析报告",
        "description": "全面分析商品的价格、销量、评分等核心指标",
        "report_type": "product_analysis",
        "metrics": ["price", "sales_count", "monthly_sales", "rating", "review_count", "favorite_count"],
        "chart_types": ["line", "bar", "radar"],
        "output_format": "pdf",
        "prompt_template": "请对以下商品进行全面分析，包括价格趋势、销量变化、竞争力评估和优化建议：\n\n商品数据：{data}",
        "sections": [
            {"title": "概览", "type": "summary"},
            {"title": "价格分析", "type": "price_analysis"},
            {"title": "销量趋势", "type": "sales_trend"},
            {"title": "竞争对比", "type": "benchmark"},
            {"title": "优化建议", "type": "recommendations"},
        ],
        "is_default": True,
        "is_active": True,
    },
    {
        "name": "竞品对比报告",
        "description": "横向对比多个竞品的关键指标",
        "report_type": "competitor_comparison",
        "metrics": ["price", "sales_count", "rating", "review_count"],
        "chart_types": ["radar", "bar", "table"],
        "output_format": "pdf",
        "prompt_template": "请对比以下竞品数据，分析各商品的优劣势和市场定位：\n\n竞品数据：{data}",
        "sections": [
            {"title": "对比概览", "type": "comparison_overview"},
            {"title": "价格对比", "type": "price_comparison"},
            {"title": "销量对比", "type": "sales_comparison"},
            {"title": "优劣势分析", "type": "swot"},
            {"title": "策略建议", "type": "strategy"},
        ],
        "is_default": True,
        "is_active": True,
    },
    {
        "name": "趋势预警报告",
        "description": "分析商品指标变化趋势并预警异常波动",
        "report_type": "trend_alert",
        "metrics": ["price", "sales_count", "price_change_pct", "sales_change_pct"],
        "chart_types": ["line", "gauge"],
        "output_format": "pdf",
        "prompt_template": "请分析以下商品的趋势数据，识别异常波动并提供预警：\n\n趋势数据：{data}",
        "sections": [
            {"title": "趋势概览", "type": "trend_overview"},
            {"title": "价格趋势", "type": "price_trend"},
            {"title": "销量趋势", "type": "sales_trend"},
            {"title": "异常检测", "type": "anomaly_detection"},
            {"title": "预警建议", "type": "alert_recommendations"},
        ],
        "is_default": True,
        "is_active": True,
    },
]


@router.get("")
async def list_templates(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    report_type: str | None = None,
):
    query = select(AIReportTemplate).where(
        (AIReportTemplate.user_id == user.id) | (AIReportTemplate.is_default == True)
    )
    if report_type:
        query = query.where(AIReportTemplate.report_type == report_type)
    query = query.order_by(AIReportTemplate.is_default.desc(), AIReportTemplate.created_at.desc())
    result = await db.execute(query)
    templates = result.scalars().all()

    return {
        "code": 0,
        "data": [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "report_type": t.report_type,
                "metrics": t.metrics,
                "chart_types": t.chart_types,
                "output_format": t.output_format,
                "prompt_template": t.prompt_template,
                "sections": t.sections,
                "is_default": t.is_default,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
    }


@router.post("")
async def create_template(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    name: str = Query(..., max_length=200),
    description: str | None = None,
    report_type: str = Query(..., max_length=50),
    metrics: list[str] | None = None,
    chart_types: list[str] | None = None,
    output_format: str = "pdf",
    prompt_template: str | None = None,
    sections: list[dict] | None = None,
):
    template = AIReportTemplate(
        user_id=user.id,
        name=name,
        description=description,
        report_type=report_type,
        metrics=metrics or [],
        chart_types=chart_types or [],
        output_format=output_format,
        prompt_template=prompt_template,
        sections=sections or [],
        is_default=False,
        is_active=True,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {"code": 0, "data": {"id": str(template.id), "name": template.name}}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReportTemplate).where(AIReportTemplate.id == uuid.UUID(template_id))
    )
    template = result.scalar_one_or_none()
    if not template or (not template.is_default and template.user_id != user.id):
        raise NotFoundException(message="模板不存在")
    return {
        "code": 0,
        "data": {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "metrics": template.metrics,
            "chart_types": template.chart_types,
            "output_format": template.output_format,
            "prompt_template": template.prompt_template,
            "sections": template.sections,
            "is_default": template.is_default,
            "is_active": template.is_active,
        },
    }


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    name: str | None = None,
    description: str | None = None,
    metrics: list[str] | None = None,
    chart_types: list[str] | None = None,
    output_format: str | None = None,
    prompt_template: str | None = None,
    sections: list[dict] | None = None,
    is_active: bool | None = None,
):
    result = await db.execute(
        select(AIReportTemplate).where(
            AIReportTemplate.id == uuid.UUID(template_id), AIReportTemplate.user_id == user.id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise NotFoundException(message="模板不存在")
    if name is not None: template.name = name
    if description is not None: template.description = description
    if metrics is not None: template.metrics = metrics
    if chart_types is not None: template.chart_types = chart_types
    if output_format is not None: template.output_format = output_format
    if prompt_template is not None: template.prompt_template = prompt_template
    if sections is not None: template.sections = sections
    if is_active is not None: template.is_active = is_active
    await db.commit()
    return {"code": 0, "data": {"id": str(template.id), "updated": True}}


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIReportTemplate).where(
            AIReportTemplate.id == uuid.UUID(template_id), AIReportTemplate.user_id == user.id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise NotFoundException(message="模板不存在")
    await db.delete(template)
    await db.commit()
    return {"code": 0, "data": {"deleted": True}}


@router.post("/init-defaults")
async def init_default_templates(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(AIReportTemplate).where(AIReportTemplate.is_default == True)
    )
    if existing.scalars().first():
        return {"code": 0, "data": {"message": "默认模板已存在"}}

    for tpl_data in DEFAULT_TEMPLATES:
        template = AIReportTemplate(
            user_id=user.id,
            is_default=True,
            **tpl_data,
        )
        db.add(template)
    await db.commit()
    return {"code": 0, "data": {"created": len(DEFAULT_TEMPLATES)}}
