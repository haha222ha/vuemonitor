import base64
import logging
import os
import uuid

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

QUALITY_TIERS = {
    "standard": {"api_quality": "standard", "model": "gpt-image-2", "credits_cost": 1},
    "hd": {"api_quality": "high", "model": "gpt-image-2", "credits_cost": 2},
    "ultra": {"api_quality": "high", "model": "gpt-image-2", "credits_cost": 4},
}

PRESET_RATIOS = {
    "square": {"label": "1:1", "sizes": {"standard": "1024x1024", "hd": "1024x1024", "ultra": "2048x2048"}},
    "portrait": {"label": "2:3", "sizes": {"standard": "1024x1536", "hd": "1024x1536", "ultra": "1366x2048"}},
    "landscape": {"label": "3:2", "sizes": {"standard": "1536x1024", "hd": "1536x1024", "ultra": "2048x1366"}},
    "wide": {"label": "16:9", "sizes": {"standard": "1536x1024", "hd": "1536x1024", "ultra": "2048x1152"}},
}

OPENAI_SUPPORTED_SIZES = {
    "1024x1024", "1536x1024", "1024x1536",
    "2048x2048", "2160x3840", "3840x2160",
    "1366x2048", "2048x1366", "2048x1152",
}


def _resolve_size(ratio_key: str, quality_tier: str) -> str:
    ratio = PRESET_RATIOS.get(ratio_key, PRESET_RATIOS["square"])
    size = ratio["sizes"].get(quality_tier, ratio["sizes"]["standard"])
    if size in OPENAI_SUPPORTED_SIZES:
        return size
    parts = size.split("x")
    w, h = int(parts[0]), int(parts[1])
    if w == h:
        return "1024x1024" if w <= 1024 else "2048x2048"
    elif w < h:
        return "1024x1536" if h <= 1536 else "2160x3840"
    else:
        return "1536x1024" if w <= 1536 else "3840x2160"


def _resolve_quality(quality_tier: str) -> str:
    tier = QUALITY_TIERS.get(quality_tier, QUALITY_TIERS["standard"])
    return tier["api_quality"]


def get_credits_cost(quality_tier: str) -> int:
    tier = QUALITY_TIERS.get(quality_tier, QUALITY_TIERS["standard"])
    return tier["credits_cost"]


async def generate_image_async(
    prompt: str,
    negative_prompt: str = "",
    model_name: str = "gpt-image-2",
    ratio_key: str = "square",
    style_prompt: str = "",
    input_image_path: str = "",
    task_type: str = "text2img",
    quality_tier: str = "standard",
) -> dict:
    settings = get_settings()

    full_prompt = f"{style_prompt}, {prompt}" if style_prompt else prompt

    size_str = _resolve_size(ratio_key, quality_tier)
    quality = _resolve_quality(quality_tier)
    tier_info = QUALITY_TIERS.get(quality_tier, QUALITY_TIERS["standard"])
    use_model = tier_info.get("model", settings.AIPIC_OPENAI_MODEL)

    if not settings.AIPIC_OPENAI_API_KEY:
        return {"success": False, "error": "AIPIC_OPENAI_API_KEY 未配置"}

    outputs_dir = settings.AIPIC_OUTPUTS_DIR or os.path.join(os.getcwd(), "aipic_outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    try:
        if task_type == "img2img" and input_image_path and os.path.exists(input_image_path):
            result = await _generate_img2img(
                full_prompt, input_image_path, size_str, quality, use_model, settings
            )
        else:
            result = await _generate_text2img(
                full_prompt, size_str, quality, use_model, settings
            )
        return result
    except Exception as e:
        logger.error(f"生成图片失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _generate_text2img(
    prompt: str, size: str, quality: str, model: str, settings
) -> dict:
    url = f"{settings.AIPIC_OPENAI_BASE_URL}/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
        "response_format": "b64_json",
        "output_format": "png",
    }
    headers = {
        "Authorization": f"Bearer {settings.AIPIC_OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.AIPIC_OPENAI_TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    image_data = base64.b64decode(data["data"][0]["b64_json"])
    output_filename = f"{uuid.uuid4().hex}.png"
    outputs_dir = settings.AIPIC_OUTPUTS_DIR or os.path.join(os.getcwd(), "aipic_outputs")
    output_path = os.path.join(outputs_dir, output_filename)

    with open(output_path, "wb") as f:
        f.write(image_data)

    return {"success": True, "output_path": output_path}


async def _generate_img2img(
    prompt: str, input_image_path: str, size: str, quality: str, model: str, settings
) -> dict:
    url = f"{settings.AIPIC_OPENAI_BASE_URL}/images/edits"

    with open(input_image_path, "rb") as f:
        image_bytes = f.read()

    filename = os.path.basename(input_image_path)

    async with httpx.AsyncClient(timeout=settings.AIPIC_OPENAI_TIMEOUT) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.AIPIC_OPENAI_API_KEY}"},
            data={
                "model": model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": "1",
                "response_format": "b64_json",
                "output_format": "png",
            },
            files={"image": (filename, image_bytes, "image/png")},
        )
        response.raise_for_status()
        data = response.json()

    image_data = base64.b64decode(data["data"][0]["b64_json"])
    output_filename = f"{uuid.uuid4().hex}.png"
    outputs_dir = settings.AIPIC_OUTPUTS_DIR or os.path.join(os.getcwd(), "aipic_outputs")
    output_path = os.path.join(outputs_dir, output_filename)

    with open(output_path, "wb") as f:
        f.write(image_data)

    return {"success": True, "output_path": output_path}
