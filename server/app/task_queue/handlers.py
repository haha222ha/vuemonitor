import logging
from app.task_queue.queue import register_handler

logger = logging.getLogger(__name__)


async def handle_collect_task(payload: dict) -> dict:
    from app.core.database import async_session_factory
    from app.collect.engine import CollectEngine
    from app.models.collect import CollectTask
    from app.ws.manager import manager
    from datetime import datetime, timezone
    from sqlalchemy import select

    task_id = payload.get("task_id")
    if not task_id:
        return {"error": "missing task_id"}

    async with async_session_factory() as db:
        result = await db.execute(select(CollectTask).where(CollectTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return {"error": "task not found"}

        engine = CollectEngine(db)
        summary = await engine.execute_task(task.id)
        await db.commit()

        await manager.send_to_user(str(task.user_id), {
            "type": "collect:completed",
            "data": {"task_id": str(task.id), "summary": summary},
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    return {"status": "completed", "summary": summary}


async def handle_ai_analysis(payload: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.ai_service import AIService
    from sqlalchemy import select
    from app.models.product import Product

    product_id = payload.get("product_id")
    analysis_type = payload.get("analysis_type", "basic")

    async with async_session_factory() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            return {"error": "product not found"}

        ai = AIService(db)
        analysis = await ai.analyze_product(product, analysis_type)
        await db.commit()

    return {"status": "completed", "analysis_id": str(analysis.id) if analysis else None}


async def handle_report_generation(payload: dict) -> dict:
    from app.core.database import async_session_factory
    from app.services.ai_service import AIService

    user_id = payload.get("user_id")
    report_type = payload.get("report_type", "weekly")
    product_ids = payload.get("product_ids", [])

    async with async_session_factory() as db:
        ai = AIService(db)
        report = await ai.generate_report(user_id, report_type, product_ids)
        await db.commit()

    return {"status": "completed", "report_id": str(report.id) if report else None}


async def handle_feature_ranking(payload: dict) -> dict:
    from app.core.database import async_session_factory
    from app.feature.cloud_engine import CloudFeatureEngine

    category = payload.get("category")

    async with async_session_factory() as db:
        engine = CloudFeatureEngine(db)
        count = await engine.compute_all_rankings(category=category)
        await db.commit()

    return {"status": "completed", "rankings_computed": count}


def register_builtin_handlers():
    register_handler("collect", handle_collect_task)
    register_handler("ai_analysis", handle_ai_analysis)
    register_handler("report_generation", handle_report_generation)
    register_handler("feature_ranking", handle_feature_ranking)
    logger.info("Built-in task handlers registered")
