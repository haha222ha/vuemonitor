import logging

from sqlalchemy import select

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
    {"gate_key": "gate:monitor:add", "gate_name": "添加监控商品", "gate_type": "limit", "required_plan": "free", "description": "添加商品到监控列表（免费不限数量）"},
    {"gate_key": "gate:monitor:auto_refresh", "gate_name": "定时采集", "gate_type": "feature", "required_plan": "free", "description": "定时自动采集监控商品"},
    {"gate_key": "gate:collect:create", "gate_name": "创建采集任务", "gate_type": "feature", "required_plan": "free", "description": "创建商品采集任务"},
    {"gate_key": "gate:monitor:waterfall", "gate_name": "瀑布流视图", "gate_type": "feature", "required_plan": "free", "description": "瀑布流商品展示视图"},
    {"gate_key": "gate:monitor:category", "gate_name": "分类管理", "gate_type": "feature", "required_plan": "pro", "description": "商品分类管理功能"},
    {"gate_key": "gate:monitor:growth_24h", "gate_name": "24h增长数据", "gate_type": "feature", "required_plan": "pro", "description": "商品24小时增长数据展示"},
    {"gate_key": "gate:monitor:anomaly", "gate_name": "异常检测", "gate_type": "feature", "required_plan": "premium", "description": "自动异常检测和告警"},
    {"gate_key": "gate:monitor:compare", "gate_name": "商品对比", "gate_type": "feature", "required_plan": "pro", "description": "多商品对比趋势图"},
    {"gate_key": "gate:import:excel", "gate_name": "Excel批量导入", "gate_type": "limit", "required_plan": "pro", "description": "通过Excel批量导入商品"},
    {"gate_key": "gate:discovery:search", "gate_name": "商品发现搜索", "gate_type": "limit", "required_plan": "free", "description": "云端搜索添加（免费20次/天·按账号+IP），粘贴链接不限"},
    {"gate_key": "gate:discovery:burst", "gate_name": "爆品洞察", "gate_type": "limit", "required_plan": "premium", "description": "爆品榜单和飙升榜，Premium及以上可用"},
    {"gate_key": "gate:aipic:generate", "gate_name": "AI作图", "gate_type": "feature", "required_plan": "free", "description": "基础文生图/图生图"},
    {"gate_key": "gate:aipic:hd", "gate_name": "高清画质", "gate_type": "feature", "required_plan": "pro", "description": "HD画质生成"},
    {"gate_key": "gate:aipic:ultra", "gate_name": "超清画质", "gate_type": "feature", "required_plan": "premium", "description": "Ultra画质生成"},
    {"gate_key": "gate:aipic:style", "gate_name": "风格库", "gate_type": "feature", "required_plan": "pro", "description": "自定义风格"},
    {"gate_key": "gate:aipic:batch", "gate_name": "批量生成", "gate_type": "feature", "required_plan": "premium", "description": "批量生图"},
    {"gate_key": "gate:aipic:api", "gate_name": "API访问", "gate_type": "feature", "required_plan": "premium", "description": "API密钥调用"},
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
