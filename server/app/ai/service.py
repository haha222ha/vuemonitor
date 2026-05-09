import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ANALYSIS_PROMPTS, get_provider
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.ai import AIAnalysis, AIReport
from app.models.product import Product, ProductFeature
from app.ws.manager import manager


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gate = FeatureGateMiddleware(db)

    async def analyze_product(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        analysis_type: str,
        provider_name: str | None = None,
    ) -> dict:
        if analysis_type not in ANALYSIS_PROMPTS:
            raise BadRequestException(message=f"不支持的分析类型：{analysis_type}")

        from app.models.user import User
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await self.gate.check_gate(user, "gate:ai:analyze")

        product_result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise NotFoundException(message="商品不存在")

        features_result = await self.db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(10)
        )
        features = features_result.scalars().all()

        feature_data = [
            {
                "price": float(f.price) if f.price else None,
                "sales_count": f.sales_count,
                "monthly_sales": f.monthly_sales,
                "rating": float(f.rating) if f.rating else None,
                "review_count": f.review_count,
                "collected_at": f.collected_at.isoformat() if f.collected_at else None,
            }
            for f in features
        ]

        prompt_config = ANALYSIS_PROMPTS[analysis_type]
        prompt = prompt_config["template"].format(
            data=f"商品：{product.product_name}\n平台：{product.platform}\n店铺：{product.shop_name}\n特征数据：{feature_data}"
        )

        provider = get_provider(provider_name)
        ai_result = await provider.analyze(prompt, prompt_config["system"])

        analysis = AIAnalysis(
            user_id=user_id,
            product_id=product_id,
            analysis_type=analysis_type,
            provider=provider_name or "openai",
            model=ai_result["model"],
            input_tokens=ai_result["usage"]["input_tokens"],
            output_tokens=ai_result["usage"]["output_tokens"],
            result=ai_result["result"],
            status="completed",
        )
        self.db.add(analysis)
        await self.db.flush()

        await manager.send_to_user(str(user_id), {
            "type": "ai:analysis_done",
            "data": {"analysis_id": str(analysis.id), "analysis_type": analysis_type, "product_id": str(product_id)},
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "id": str(analysis.id),
            "analysis_type": analysis_type,
            "provider": analysis.provider,
            "model": analysis.model,
            "result": analysis.result,
            "input_tokens": analysis.input_tokens,
            "output_tokens": analysis.output_tokens,
        }

    async def generate_report(
        self,
        user_id: uuid.UUID,
        title: str,
        report_type: str,
        product_ids: list[str],
        provider_name: str | None = None,
    ) -> dict:
        products_data = []
        for pid in product_ids:
            result = await self.db.execute(select(Product).where(Product.id == uuid.UUID(pid)))
            product = result.scalar_one_or_none()
            if product:
                feat_result = await self.db.execute(
                    select(ProductFeature)
                    .where(ProductFeature.product_id == product.id)
                    .order_by(ProductFeature.collected_at.desc())
                    .limit(5)
                )
                features = feat_result.scalars().all()
                products_data.append({
                    "name": product.product_name,
                    "platform": product.platform,
                    "features": [
                        {"price": float(f.price) if f.price else None, "sales_count": f.sales_count}
                        for f in features
                    ],
                })

        prompt_config = ANALYSIS_PROMPTS.get("report", ANALYSIS_PROMPTS["basic_analysis"])
        prompt = prompt_config["template"].format(data=products_data)

        provider = get_provider(provider_name)
        ai_result = await provider.analyze(prompt, prompt_config["system"])

        report = AIReport(
            user_id=user_id,
            title=title,
            report_type=report_type,
            content=ai_result["result"],
            status="completed",
        )
        self.db.add(report)
        await self.db.flush()

        return {
            "id": str(report.id),
            "title": report.title,
            "report_type": report.report_type,
            "status": report.status,
        }
