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

        try:
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
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class DeepSeekProvider(AIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://www.packyapi.com/v1",
        )
        self.model = settings.DEEPSEEK_MODEL or "deepseek-v4-flash"

    async def analyze(self, prompt: str, system_prompt: str = "") -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
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
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise


def get_provider(provider_name: str | None = None) -> AIProvider:
    name = provider_name or settings.AI_DEFAULT_PROVIDER
    if name == "deepseek":
        return DeepSeekProvider()
    return OpenAIProvider()


ANALYSIS_PROMPTS = {
    "basic_analysis": {
        "system": "你是小红书电商选品数据分析专家。你熟悉小红书平台的商品生态、用户消费行为和选品趋势。请根据商品数据，给出专业的选品分析描述。",
        "template": "请分析以下小红书商品数据：\n{data}\n\n请以JSON格式返回分析结果，包含：\n- summary：商品概述（50字以内）\n- product_type：商品类型判断（实物/虚拟/服务）\n- strengths：商品优势列表（最多3条）\n- weaknesses：商品不足列表（最多3条）\n- market_demand：市场需求评估（high/medium/low）\n- suggestion：选品建议（100字以内）",
    },
    "trend_score": {
        "system": "你是小红书电商趋势分析专家。你了解小红书商品热度传播规律、品类流量分配和商品生命周期。请根据商品历史数据，评估商品趋势并打分。",
        "template": "请评估以下小红书商品的趋势：\n{data}\n\n请以JSON格式返回：\n- trend_score：趋势评分（0-100，综合销量/收藏/评论增速）\n- trend_direction：趋势方向（up/down/stable）\n- market_stage：市场阶段（emerging/growing/mature/declining）\n- key_factors：关键驱动因素列表\n- prediction：未来7天销量预测描述\n- recommended_actions：建议操作列表",
    },
    "prediction": {
        "system": "你是小红书爆款商品预测专家。你深谙小红书平台的推荐机制、用户消费画像和爆款商品特征。请根据商品多维数据，预测其爆款潜力。",
        "template": "请预测以下小红书商品的爆款潜力：\n{data}\n\n请以JSON格式返回：\n- explosion_score：爆款潜力评分（0-100）\n- potential_level：潜力等级（high/medium/low）\n- growth_indicators：增长指标（销量增速、收藏转化率、复购率）\n- audience_match：目标受众匹配度（0-100）\n- timing_score：上架时机评分（0-100）\n- risk_factors：风险因素列表\n- recommended_action：建议操作（stock_now/test_market/wait/avoid）\n- optimization_tips：优化建议列表",
    },
    "risk_warning": {
        "system": "你是小红书电商风险预警专家。你熟悉小红书商品合规要求、平台审核标准和常见经营风险。请根据商品数据，识别潜在风险。",
        "template": "请识别以下小红书商品的风险：\n{data}\n\n请以JSON格式返回：\n- risk_level：风险等级（high/medium/low）\n- risk_types：风险类型列表（合规风险/售后风险/竞争风险/库存风险/价格风险）\n- risk_details：风险详情描述\n- compliance_score：合规评分（0-100）\n- mitigation_suggestions：风险缓解建议列表\n- market_competition：市场竞争程度评估",
    },
    "report": {
        "system": "你是小红书选品分析报告撰写专家。你擅长从商品数据中提炼选品洞察，为电商运营者提供可执行的选品建议。请根据商品数据，生成结构化选品分析报告。",
        "template": "请为以下小红书商品生成选品分析报告：\n{data}\n\n请以JSON格式返回：\n- title：报告标题\n- executive_summary：执行摘要（100字以内）\n- product_analysis：商品竞争力分析\n- market_analysis：市场趋势分析\n- pricing_analysis：定价策略分析\n- competitive_position：同类商品竞争定位\n- recommendations：选品建议列表（按优先级排序）\n- next_steps：下一步行动计划\n- conclusion：结论",
    },
    "product_optimization": {
        "system": "你是小红书商品优化专家。你了解小红书商品标题优化、主图设计、定价策略和详情页对转化率的影响。请根据商品数据，给出优化建议。",
        "template": "请优化以下小红书商品：\n{data}\n\n请以JSON格式返回：\n- title_score：标题评分（0-100）\n- title_suggestions：标题优化建议列表\n- pricing_score：定价评分（0-100）\n- content_score：详情页评分（0-100）\n- seo_keywords：建议添加的关键词列表\n- tag_suggestions：建议标签列表\n- pricing_suggestion：定价建议\n- optimization_priority：优化优先级列表",
    },
}
