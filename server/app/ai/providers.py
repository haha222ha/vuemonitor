import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIProvider(ABC):
    @abstractmethod
    async def analyze(self, prompt: str, system_prompt: str = "") -> dict:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.AI_DEFAULT_MODEL

    async def analyze(self, prompt: str, system_prompt: str = "") -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"raw_content": content}

        return {"result": parsed, "usage": usage, "model": self.model}


class DeepSeekProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )
        self.model = "deepseek-chat"

    async def analyze(self, prompt: str, system_prompt: str = "") -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"raw_content": content}

        return {"result": parsed, "usage": usage, "model": self.model}


def get_provider(provider_name: str | None = None) -> AIProvider:
    name = provider_name or settings.AI_DEFAULT_PROVIDER
    if name == "deepseek":
        return DeepSeekProvider()
    return OpenAIProvider()


ANALYSIS_PROMPTS = {
    "basic_analysis": {
        "system": "你是一个电商数据分析专家。请根据商品数据，给出简洁的分析描述。",
        "template": "请分析以下商品数据：\n{data}\n\n请以JSON格式返回分析结果，包含：summary（概述）、strengths（优势）、weaknesses（不足）、suggestion（建议）",
    },
    "trend_score": {
        "system": "你是一个电商趋势分析专家。请根据商品历史数据，评估商品趋势并打分。",
        "template": "请评估以下商品的趋势：\n{data}\n\n请以JSON格式返回：trend_score（0-100趋势分）、trend_direction（up/down/stable）、key_factors（关键因素列表）、prediction（短期预测）",
    },
    "prediction": {
        "system": "你是一个电商爆品预测专家。请根据商品多维数据，预测其爆品潜力。",
        "template": "请预测以下商品的爆品潜力：\n{data}\n\n请以JSON格式返回：explosion_score（0-100爆品分）、potential_level（high/medium/low）、growth_indicators（增长指标）、risk_factors（风险因素）、recommended_action（建议操作）",
    },
    "risk_warning": {
        "system": "你是一个电商风险预警专家。请根据商品数据，识别潜在风险。",
        "template": "请识别以下商品的风险：\n{data}\n\n请以JSON格式返回：risk_level（high/medium/low）、risk_types（风险类型列表）、risk_details（风险详情）、mitigation_suggestions（缓解建议）",
    },
    "report": {
        "system": "你是一个电商分析报告撰写专家。请根据商品数据，生成结构化分析报告。",
        "template": "请为以下商品生成分析报告：\n{data}\n\n请以JSON格式返回：title（报告标题）、executive_summary（执行摘要）、market_analysis（市场分析）、competitive_analysis（竞争分析）、recommendations（建议列表）、conclusion（结论）",
    },
}
