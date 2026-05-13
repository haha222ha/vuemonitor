import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.feature_gate import FeatureGate

logger = logging.getLogger(__name__)

FEATURE_GATES_SEED = [
    {"gate_key": "gate:ai:basic_analysis", "gate_name": "AI基础分析", "gate_type": "limit", "required_plan": "free", "description": "基础商品分析，所有套餐可用"},
    {"gate_key": "gate:ai:trend_score", "gate_name": "AI趋势评分", "gate_type": "limit", "required_plan": "pro", "description": "商品趋势评分和竞品分析"},
    {"gate_key": "gate:ai:prediction", "gate_name": "AI爆品预测", "gate_type": "limit", "required_plan": "premium", "description": "爆品预测和选品建议"},
    {"gate_key": "gate:ai:risk_warning", "gate_name": "AI风险预警", "gate_type": "limit", "required_plan": "premium", "description": "商品风险预警"},
    {"gate_key": "gate:ai:competitor_analysis", "gate_name": "AI竞品分析", "gate_type": "limit", "required_plan": "pro", "description": "竞品对比分析"},
    {"gate_key": "gate:ai:product_selection", "gate_name": "AI选品建议", "gate_type": "limit", "required_plan": "premium", "description": "选品方向建议"},
    {"gate_key": "gate:ai:product_optimization", "gate_name": "AI商品优化", "gate_type": "limit", "required_plan": "pro", "description": "商品标题和详情优化"},
    {"gate_key": "gate:ai:batch_analysis", "gate_name": "AI批量分析", "gate_type": "limit", "required_plan": "premium", "description": "批量商品分析"},
    {"gate_key": "gate:ai:report", "gate_name": "AI分析报告", "gate_type": "limit", "required_plan": "pro", "description": "生成AI分析报告"},
    {"gate_key": "gate:ai:note_optimization", "gate_name": "AI笔记优化", "gate_type": "limit", "required_plan": "pro", "description": "小红书笔记内容优化"},
    {"gate_key": "gate:monitor:add", "gate_name": "添加监控商品", "gate_type": "limit", "required_plan": "free", "description": "添加商品到监控列表"},
]


async def seed_feature_gates() -> None:
    async with async_session_factory() as session:
        try:
            for gate_data in FEATURE_GATES_SEED:
                result = await session.execute(
                    select(FeatureGate).where(FeatureGate.gate_key == gate_data["gate_key"])
                )
                existing = result.scalar_one_or_none()
                if not existing:
                    gate = FeatureGate(**gate_data, is_active=True)
                    session.add(gate)
                    logger.info(f"Seeded feature gate: {gate_data['gate_key']}")

            await session.commit()
        except Exception as e:
            logger.warning(f"Feature gate seeding skipped (DB not ready): {e}")
            await session.rollback()
