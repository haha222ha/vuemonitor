import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aipic import AipicStyleLibrary

logger = logging.getLogger(__name__)

PRESET_STYLES = [
    ("国风水墨", "traditional chinese ink painting, watercolor, elegant, minimalist, zen", "blurry, low quality", "艺术"),
    ("赛博朋克", "cyberpunk, neon lights, futuristic city, rain, dark atmosphere", "bright, sunny, natural", "艺术"),
    ("水彩插画", "watercolor illustration, soft colors, artistic, dreamy", "harsh, dark, realistic", "艺术"),
    ("3D渲染", "3D render, octane render, cinema 4D, highly detailed, studio lighting", "flat, 2d, sketch", "技术"),
    ("日系动漫", "anime style, japanese animation, vibrant colors, detailed eyes", "realistic, photographic", "艺术"),
    ("油画风格", "oil painting, classical art, rich colors, textured brushstrokes", "digital, smooth, flat", "艺术"),
    ("极简设计", "minimalist design, clean lines, white space, modern, simple", "cluttered, complex, ornate", "设计"),
    ("电商产品", "product photography, white background, studio lighting, commercial", "artistic, abstract, dark", "商业"),
    ("人像摄影", "professional portrait photography, bokeh, natural lighting, high detail", "cartoon, anime, painting", "摄影"),
    ("像素艺术", "pixel art, 8-bit, retro game style, low resolution aesthetic", "realistic, high resolution", "游戏"),
]


async def init_preset_styles(db: AsyncSession) -> None:
    for name, prompt, neg, cat in PRESET_STYLES:
        result = await db.execute(
            select(AipicStyleLibrary).where(AipicStyleLibrary.style_name == name)
        )
        if result.scalar_one_or_none():
            continue
        style = AipicStyleLibrary(
            style_name=name,
            style_prompt=prompt,
            style_negative_prompt=neg,
            category=cat,
            is_preset=True,
        )
        db.add(style)
    await db.flush()


async def get_style_list(db: AsyncSession, category: str = "") -> list[dict]:
    query = select(AipicStyleLibrary)
    if category:
        query = query.where(AipicStyleLibrary.category == category)
    query = query.order_by(AipicStyleLibrary.category, AipicStyleLibrary.created_at)
    result = await db.execute(query)
    styles = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "style_name": s.style_name,
            "style_prompt": s.style_prompt,
            "style_negative_prompt": s.style_negative_prompt,
            "preview_image": s.preview_image,
            "category": s.category,
            "is_preset": s.is_preset,
        }
        for s in styles
    ]


async def get_style_by_name(db: AsyncSession, style_name: str) -> dict | None:
    result = await db.execute(
        select(AipicStyleLibrary).where(AipicStyleLibrary.style_name == style_name)
    )
    style = result.scalar_one_or_none()
    if not style:
        return None
    return {
        "style_name": style.style_name,
        "style_prompt": style.style_prompt,
        "style_negative_prompt": style.style_negative_prompt,
        "category": style.category,
    }


async def add_style(
    db: AsyncSession,
    style_name: str,
    style_prompt: str,
    negative_prompt: str = "",
    category: str = "通用",
) -> tuple[bool, str]:
    result = await db.execute(
        select(AipicStyleLibrary).where(AipicStyleLibrary.style_name == style_name)
    )
    if result.scalar_one_or_none():
        return False, "风格名称已存在"

    style = AipicStyleLibrary(
        style_name=style_name,
        style_prompt=style_prompt,
        style_negative_prompt=negative_prompt,
        category=category,
        is_preset=False,
    )
    db.add(style)
    await db.flush()
    return True, "风格添加成功"


async def delete_style(db: AsyncSession, style_name: str) -> tuple[bool, str]:
    result = await db.execute(
        select(AipicStyleLibrary).where(
            AipicStyleLibrary.style_name == style_name,
            not AipicStyleLibrary.is_preset,
        )
    )
    style = result.scalar_one_or_none()
    if not style:
        return False, "风格不存在或为预设风格不可删除"

    await db.delete(style)
    await db.flush()
    return True, "风格删除成功"
