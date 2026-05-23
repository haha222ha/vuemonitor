import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aipic import AipicGenerateQueue, AipicUserWork

logger = logging.getLogger(__name__)


async def submit_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    prompt: str,
    negative_prompt: str = "",
    model_name: str = "gpt-image-2",
    ratio_key: str = "square",
    style_name: str = "",
    task_type: str = "text2img",
    quality_tier: str = "standard",
    credits_cost: int = 1,
    input_image_path: str = "",
) -> AipicGenerateQueue:
    task_id = f"task_{uuid.uuid4().hex[:16]}"

    max_order_result = await db.execute(
        select(func.coalesce(func.max(AipicGenerateQueue.queue_order), 0))
    )
    max_order = max_order_result.scalar() or 0

    task = AipicGenerateQueue(
        user_id=user_id,
        task_id=task_id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        model_name=model_name,
        ratio_key=ratio_key,
        style_name=style_name,
        task_type=task_type,
        quality_tier=quality_tier,
        credits_cost=credits_cost,
        input_image_path=input_image_path,
        task_status="待执行",
        queue_order=max_order + 1,
    )
    db.add(task)
    await db.flush()
    return task


async def get_next_task(db: AsyncSession) -> AipicGenerateQueue | None:
    result = await db.execute(
        select(AipicGenerateQueue)
        .where(AipicGenerateQueue.task_status == "待执行")
        .order_by(AipicGenerateQueue.queue_order.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.task_status = "执行中"
    task.execute_time = datetime.now(UTC)
    await db.flush()
    return task


async def complete_task(
    db: AsyncSession,
    task_id: str,
    output_image_path: str,
    seed: int = -1,
) -> None:
    result = await db.execute(
        select(AipicGenerateQueue)
        .where(AipicGenerateQueue.task_id == task_id)
        .with_for_update()
    )
    task = result.scalar_one_or_none()
    if not task:
        return

    task.task_status = "已完成"
    task.finish_time = datetime.now(UTC)
    task.output_image_path = output_image_path
    task.seed = seed

    work = AipicUserWork(
        user_id=task.user_id,
        task_id=task.task_id,
        prompt=task.prompt,
        negative_prompt=task.negative_prompt,
        model_name=task.model_name,
        ratio_key=task.ratio_key,
        style_name=task.style_name,
        task_type=task.task_type,
        quality_tier=task.quality_tier,
        credits_cost=task.credits_cost,
        input_image_path=task.input_image_path,
        output_image_path=output_image_path,
    )
    db.add(work)
    await db.flush()


async def fail_task(
    db: AsyncSession,
    task_id: str,
    fail_reason: str,
) -> None:
    result = await db.execute(
        select(AipicGenerateQueue)
        .where(AipicGenerateQueue.task_id == task_id)
        .with_for_update()
    )
    task = result.scalar_one_or_none()
    if not task:
        return

    task.task_status = "失败"
    task.finish_time = datetime.now(UTC)
    task.fail_reason = fail_reason
    await db.flush()


async def cancel_task(db: AsyncSession, task_id: str, user_id: uuid.UUID) -> tuple[bool, str]:
    result = await db.execute(
        select(AipicGenerateQueue)
        .where(
            AipicGenerateQueue.task_id == task_id,
            AipicGenerateQueue.user_id == user_id,
        )
        .with_for_update()
    )
    task = result.scalar_one_or_none()
    if not task:
        return False, "任务不存在"
    if task.task_status != "待执行":
        return False, "只能取消待执行的任务"

    task.task_status = "已取消"
    task.finish_time = datetime.now(UTC)
    await db.flush()
    return True, "取消成功"


async def get_user_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = select(AipicGenerateQueue).where(AipicGenerateQueue.user_id == user_id)
    count_query = select(func.count()).where(AipicGenerateQueue.user_id == user_id)

    if status:
        query = query.where(AipicGenerateQueue.task_status == status)
        count_query = count_query.where(AipicGenerateQueue.task_status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AipicGenerateQueue.created_at.desc()).offset(offset).limit(page_size)
    )
    tasks = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "task_id": t.task_id,
                "prompt": t.prompt[:100],
                "model_name": t.model_name,
                "ratio_key": t.ratio_key,
                "task_type": t.task_type,
                "quality_tier": t.quality_tier,
                "task_status": t.task_status,
                "credits_cost": t.credits_cost,
                "submit_time": t.created_at.isoformat() if t.created_at else None,
                "finish_time": t.finish_time.isoformat() if t.finish_time else None,
                "output_image_path": t.output_image_path,
                "fail_reason": t.fail_reason,
            }
            for t in tasks
        ],
        "page": page,
        "page_size": page_size,
    }


async def get_queue_stats(db: AsyncSession) -> dict:
    pending = await db.execute(
        select(func.count()).where(AipicGenerateQueue.task_status == "待执行")
    )
    running = await db.execute(
        select(func.count()).where(AipicGenerateQueue.task_status == "执行中")
    )
    completed = await db.execute(
        select(func.count()).where(AipicGenerateQueue.task_status == "已完成")
    )
    failed = await db.execute(
        select(func.count()).where(AipicGenerateQueue.task_status == "失败")
    )
    return {
        "pending": pending.scalar() or 0,
        "running": running.scalar() or 0,
        "completed": completed.scalar() or 0,
        "failed": failed.scalar() or 0,
    }
