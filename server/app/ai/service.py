import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ANALYSIS_PROMPTS, get_provider
from app.core.cache import cache_get, cache_set
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.ai import AIAnalysis, AIReport
from app.models.product import Product, ProductFeature
from app.ws.manager import manager

logger = logging.getLogger(__name__)

_AI_CACHE_TTL = 3600


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
            gate_key = f"gate:ai:{analysis_type}" if analysis_type in ("basic_analysis",) else "gate:ai:trend_score"
            if analysis_type in ("prediction",):
                gate_key = "gate:ai:prediction"
            elif analysis_type in ("risk_warning",):
                gate_key = "gate:ai:risk_warning"
            elif analysis_type in ("report",):
                gate_key = "gate:ai:report"
            elif analysis_type in ("batch_analysis",):
                gate_key = "gate:ai:batch_analysis"
            elif analysis_type in ("note_optimization",):
                gate_key = "gate:ai:trend_score"
            await self.gate.check_gate(user, gate_key)

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
                "favorite_count": f.favorite_count,
                "collected_at": f.collected_at.isoformat() if f.collected_at else None,
            }
            for f in features
        ]

        cache_key = f"ai:{analysis_type}:{product_id}:{hash(str(feature_data))}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        prompt_config = ANALYSIS_PROMPTS[analysis_type]
        prompt = prompt_config["template"].format(
            data=f"商品：{product.product_name}\n平台：小红书\n店铺：{product.shop_name}\n分类：{product.category}\n特征数据：{json.dumps(feature_data, ensure_ascii=False)}"
        )

        ai_result = None
        providers_to_try = [provider_name] if provider_name else ["openai", "deepseek"]

        for prov_name in providers_to_try:
            try:
                provider = get_provider(prov_name)
                ai_result = await provider.analyze(prompt, prompt_config["system"])
                break
            except Exception as e:
                logger.warning(f"AI provider {prov_name} failed: {e}, trying next...")
                continue

        if ai_result is None:
            analysis = AIAnalysis(
                user_id=user_id,
                product_id=product_id,
                analysis_type=analysis_type,
                provider="fallback",
                model="rule-based",
                input_tokens=0,
                output_tokens=0,
                result=self._rule_based_analysis(product, features, analysis_type),
                status="completed",
            )
            self.db.add(analysis)
            await self.db.flush()

            result = {"id": str(analysis.id), "analysis_type": analysis_type, "result": analysis.result, "provider": "fallback", "model": "rule-based"}
            return result

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

        if user:
            await self.gate.record_usage(user.id, gate_key, {"analysis_type": analysis_type, "product_id": str(product_id)})

        await self.db.flush()

        result = {
            "id": str(analysis.id),
            "analysis_type": analysis_type,
            "result": ai_result["result"],
            "provider": provider_name or "openai",
            "model": ai_result["model"],
            "usage": ai_result["usage"],
        }

        await cache_set(cache_key, result, _AI_CACHE_TTL)

        await manager.send_to_user(str(user_id), {
            "type": "ai:analysis_completed",
            "data": {"analysis_id": str(analysis.id), "product_id": str(product_id), "analysis_type": analysis_type},
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        return result

    def _rule_based_analysis(self, product: Product, features: list, analysis_type: str) -> dict:
        if not features:
            return {"summary": "暂无足够数据进行分析", "confidence": 0}

        latest = features[0]
        result = {"note_name": product.product_name, "platform": "xhs"}

        if analysis_type == "basic_analysis":
            engagement = "low"
            if latest.favorite_count and latest.favorite_count > 1000:
                engagement = "high"
            elif latest.favorite_count and latest.favorite_count > 100:
                engagement = "medium"
            result.update({
                "summary": f"商品「{product.product_name}」互动表现{engagement}",
                "engagement_assessment": engagement,
                "strengths": ["数据已采集"] if latest.favorite_count else [],
                "weaknesses": [],
                "suggestion": "建议采集更多数据后进行AI深度分析",
            })
        elif analysis_type == "trend_score":
            score = 50
            if latest.favorite_count and latest.favorite_count > 500:
                score = 70
            if latest.review_count and latest.review_count > 50:
                score += 10
            result.update({
                "trend_score": min(score, 100),
                "trend_direction": "stable",
                "traffic_stage": "growing" if score > 60 else "cold_start",
                "key_factors": ["收藏数", "评论数"],
                "prediction": "需要更多历史数据才能准确预测",
            })
        else:
            result.update({
                "message": "规则引擎暂不支持此分析类型，请配置AI服务后重试",
                "confidence": 0,
            })

        return result

    async def get_analysis_history(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        analysis_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        query = select(AIAnalysis).where(AIAnalysis.user_id == user_id)

        if product_id:
            query = query.where(AIAnalysis.product_id == product_id)
        if analysis_type:
            query = query.where(AIAnalysis.analysis_type == analysis_type)

        query = query.order_by(AIAnalysis.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        analyses = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "product_id": str(a.product_id) if a.product_id else None,
                "analysis_type": a.analysis_type,
                "provider": a.provider,
                "model": a.model,
                "result": a.result,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in analyses
        ]
