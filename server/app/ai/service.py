import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ANALYSIS_PROMPTS, get_provider, get_available_providers
from app.core.cache import cache_get, cache_set
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.ai import AIAnalysis, AIReport
from app.models.product import Product, ProductFeature
from app.ws.manager import manager

logger = logging.getLogger(__name__)

_AI_CACHE_TTL = 3600

_GATE_KEY_MAP = {
    "basic_analysis": "gate:ai:basic_analysis",
    "trend_score": "gate:ai:trend_score",
    "prediction": "gate:ai:prediction",
    "risk_warning": "gate:ai:risk_warning",
    "competitor_analysis": "gate:ai:trend_score",
    "product_selection": "gate:ai:prediction",
    "report": "gate:ai:report",
    "product_optimization": "gate:ai:trend_score",
    "batch_analysis": "gate:ai:batch_analysis",
    "note_optimization": "gate:ai:trend_score",
}


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
            gate_key = _GATE_KEY_MAP.get(analysis_type, "gate:ai:basic_analysis")
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
        providers_to_try = [provider_name] if provider_name else get_available_providers()
        if not providers_to_try:
            providers_to_try = ["deepseek", "openai"]

        for prov_name in providers_to_try:
            try:
                provider = get_provider(prov_name)
                ai_result = await provider.analyze_with_retry(prompt, prompt_config["system"])
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

    async def generate_report(
        self,
        user_id: uuid.UUID,
        title: str,
        report_type: str,
        product_ids: list[str],
        provider_name: str | None = None,
    ) -> dict:
        from app.models.user import User
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await self.gate.check_gate(user, "gate:ai:report")

        product_uuids = [uuid.UUID(pid) for pid in product_ids]

        products_result = await self.db.execute(
            select(Product).where(Product.id.in_(product_uuids))
        )
        products = products_result.scalars().all()
        if not products:
            raise NotFoundException(message="未找到指定商品")

        product_data = []
        for product in products:
            features_result = await self.db.execute(
                select(ProductFeature)
                .where(ProductFeature.product_id == product.id)
                .order_by(ProductFeature.collected_at.desc())
                .limit(5)
            )
            features = features_result.scalars().all()

            feature_list = [
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

            product_data.append({
                "product_name": product.product_name,
                "platform": product.platform,
                "shop_name": product.shop_name,
                "category": product.category,
                "features": feature_list,
            })

        report = AIReport(
            user_id=user_id,
            title=title,
            report_type=report_type,
            content={"status": "generating"},
            status="generating",
        )
        self.db.add(report)
        await self.db.flush()

        report_prompt = self._build_report_prompt(report_type, product_data)

        ai_result = None
        providers_to_try = [provider_name] if provider_name else get_available_providers()
        if not providers_to_try:
            providers_to_try = ["deepseek", "openai"]

        for prov_name in providers_to_try:
            try:
                provider = get_provider(prov_name)
                ai_result = await provider.analyze_with_retry(report_prompt["prompt"], report_prompt["system"])
                break
            except Exception as e:
                logger.warning(f"Report AI provider {prov_name} failed: {e}, trying next...")
                continue

        if ai_result is None:
            report_content = self._rule_based_report(report_type, product_data)
            report.content = report_content
            report.status = "completed"
            await self.db.flush()

            if user:
                await manager.send_to_user(str(user_id), {
                    "type": "ai:report_completed",
                    "data": {"report_id": str(report.id), "title": title, "status": "completed"},
                    "ts": datetime.now(timezone.utc).isoformat(),
                })

            return {
                "id": str(report.id),
                "title": title,
                "report_type": report_type,
                "content": report_content,
                "status": "completed",
                "provider": "fallback",
                "model": "rule-based",
            }

        report.content = ai_result["result"]
        report.status = "completed"
        await self.db.flush()

        if user:
            await self.gate.record_usage(user.id, "gate:ai:report", {"report_type": report_type, "report_id": str(report.id)})
            await manager.send_to_user(str(user_id), {
                "type": "ai:report_completed",
                "data": {"report_id": str(report.id), "title": title, "status": "completed"},
                "ts": datetime.now(timezone.utc).isoformat(),
            })

        return {
            "id": str(report.id),
            "title": title,
            "report_type": report_type,
            "content": ai_result["result"],
            "status": "completed",
            "provider": provider_name or "openai",
            "model": ai_result["model"],
        }

    def _build_report_prompt(self, report_type: str, product_data: list[dict]) -> dict:
        system_map = {
            "product": "你是小红书选品分析报告撰写专家。你擅长从商品数据中提炼选品洞察，为电商运营者提供可执行的商业决策建议。请根据商品数据，生成结构化选品分析报告。报告必须包含明确的商业行动建议。",
            "category": "你是小红书品类分析专家。你擅长品类竞争格局分析、品类趋势判断和品类机会识别。请根据商品数据，生成品类分析报告，帮助运营者做出品类布局决策。",
            "trend": "你是小红书趋势分析专家。你深谙小红书平台流量分配规律、品类生命周期和趋势传播路径。请根据商品数据，生成趋势分析报告，帮助运营者把握市场节奏。",
            "risk": "你是小红书风险预警专家。你熟悉平台合规要求、经营风险和市场波动。请根据商品数据，生成风险评估报告，帮助运营者规避经营风险。",
        }

        template_map = {
            "product": "请为以下商品生成选品分析报告：\n{data}\n\n请以JSON格式返回：\n- title：报告标题\n- executive_summary：执行摘要（100字以内，突出核心结论）\n- product_analysis：商品竞争力分析（包含价格定位、销量表现、用户评价）\n- market_analysis：市场趋势分析（包含品类趋势、竞争格局、市场容量）\n- pricing_analysis：定价策略分析（包含价格竞争力、定价建议、促销策略）\n- competitive_position：竞争定位（包含差异化优势、竞争劣势、定位建议）\n- recommendations：选品建议列表（按优先级排序，每条包含action和reason）\n- next_steps：下一步行动计划（3-5个具体可执行步骤）\n- risk_assessment：风险评估（包含主要风险和应对措施）\n- conclusion：结论（50字以内，给出明确建议）",
            "category": "请为以下品类商品生成品类分析报告：\n{data}\n\n请以JSON格式返回：\n- title：报告标题\n- executive_summary：执行摘要\n- category_overview：品类概览（市场规模、增长趋势、竞争强度）\n- competition_analysis：竞争分析（头部玩家、市场集中度、进入壁垒）\n- opportunity_map：机会矩阵（高增长低竞争/高增长高竞争/低增长低竞争/低增长高竞争）\n- price_band_analysis：价格带分析（各价格段商品分布和表现）\n- trend_forecast：趋势预测（7天/30天/90天趋势判断）\n- entry_strategy：进入策略建议\n- risk_factors：风险因素\n- conclusion：结论",
            "trend": "请为以下商品生成趋势分析报告：\n{data}\n\n请以JSON格式返回：\n- title：报告标题\n- executive_summary：执行摘要\n- trend_overview：趋势总览（当前趋势方向、强度、持续时间）\n- trend_drivers：趋势驱动因素（内容驱动/季节驱动/事件驱动/自然增长）\n- trend_lifecycle：趋势生命周期判断（萌芽期/上升期/爆发期/成熟期/衰退期）\n- trend_score：趋势评分（0-100）\n- timing_analysis：时机分析（是否适合入场、最佳入场窗口）\n- trend_risks：趋势风险（趋势反转信号、替代品威胁）\n- action_plan：行动计划（立即行动/观察等待/暂缓入场）\n- monitoring_points：监控指标（需要持续关注的关键指标）\n- conclusion：结论",
            "risk": "请为以下商品生成风险评估报告：\n{data}\n\n请以JSON格式返回：\n- title：报告标题\n- executive_summary：执行摘要\n- overall_risk_level：整体风险等级（high/medium/low）\n- risk_categories：风险分类（合规风险/市场风险/运营风险/财务风险）\n- compliance_risks：合规风险详情（平台规则、广告法、产品质量）\n- market_risks：市场风险详情（竞争加剧、需求下降、价格战）\n- operational_risks：运营风险详情（供应链、库存、物流）\n- financial_risks：财务风险详情（成本上升、利润压缩、现金流）\n- mitigation_strategies：风险缓解策略（按优先级排序）\n- risk_monitoring：风险监控建议（关键指标和预警阈值）\n- conclusion：结论",
        }

        system = system_map.get(report_type, system_map["product"])
        template = template_map.get(report_type, template_map["product"])

        prompt = template.format(data=json.dumps(product_data, ensure_ascii=False, indent=2))

        return {"system": system, "prompt": prompt}

    def _rule_based_report(self, report_type: str, product_data: list[dict]) -> dict:
        if not product_data:
            return {"title": "分析报告", "executive_summary": "暂无足够数据生成报告", "conclusion": "数据不足"}

        products_count = len(product_data)
        all_prices = [p["features"][0]["price"] for p in product_data if p["features"] and p["features"][0].get("price")]
        all_sales = [p["features"][0]["sales_count"] for p in product_data if p["features"] and p["features"][0].get("sales_count")]
        all_ratings = [p["features"][0]["rating"] for p in product_data if p["features"] and p["features"][0].get("rating")]

        avg_price = sum(all_prices) / len(all_prices) if all_prices else None
        avg_sales = sum(all_sales) / len(all_sales) if all_sales else None
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else None

        base = {
            "title": f"{'商品' if report_type == 'product' else '品类' if report_type == 'category' else '趋势' if report_type == 'trend' else '风险'}分析报告",
            "executive_summary": f"本次分析涵盖{products_count}个商品，" + (f"均价{avg_price:.1f}元，" if avg_price else "") + (f"平均销量{avg_sales:.0f}，" if avg_sales else "") + "建议配置AI服务获取深度分析。",
        }

        if report_type == "product":
            base.update({
                "product_analysis": {
                    "price_position": f"均价{avg_price:.1f}元" if avg_price else "价格数据不足",
                    "sales_performance": f"平均销量{avg_sales:.0f}" if avg_sales else "销量数据不足",
                    "user_rating": f"平均评分{avg_rating:.1f}" if avg_rating else "评分数据不足",
                },
                "recommendations": [
                    {"action": "配置AI服务", "reason": "当前使用规则引擎，建议配置OpenAI/DeepSeek获取深度分析"},
                    {"action": "增加数据采集频率", "reason": "更多历史数据可提高分析准确性"},
                ],
                "next_steps": ["配置AI API密钥", "设置定时采集任务", "积累7天以上数据后重新分析"],
                "conclusion": "数据有限，建议配置AI服务后重新生成报告",
            })
        elif report_type == "category":
            base.update({
                "category_overview": {"product_count": products_count, "avg_price": avg_price, "avg_sales": avg_sales},
                "entry_strategy": "数据不足，建议积累更多品类数据后分析",
                "conclusion": "品类数据有限，建议扩展采集范围",
            })
        elif report_type == "trend":
            base.update({
                "trend_overview": "数据不足，无法判断趋势方向",
                "trend_score": 50,
                "action_plan": "观察等待，积累更多数据",
                "conclusion": "需要更多历史数据才能判断趋势",
            })
        elif report_type == "risk":
            base.update({
                "overall_risk_level": "medium",
                "risk_categories": ["数据不足风险"],
                "mitigation_strategies": [{"action": "增加数据采集", "priority": "high"}],
                "conclusion": "数据有限，风险等级暂定为中等",
            })

        return base
