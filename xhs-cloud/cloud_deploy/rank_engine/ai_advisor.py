# -*- coding: utf-8 -*-
"""云侧 AI 顾问批量生成 — 读脱敏 context，产出 advice.json 结构。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from cloud_deploy.rank_engine.compliance import sanitize_context, validate_advisory_output


class AiAdvisor:
    def run_batch(self, *, target_date: str, context: dict[str, Any]) -> dict[str, Any]:
        ctx = sanitize_context(context or {})
        report_date = str(target_date or ctx.get("target_date") or "")[:10]
        if not report_date:
            raise ValueError("缺少 target_date")

        try:
            from cloud_deploy.scripts.insight_llm_runtime import apply_admin_insight_llm
            from cloud_deploy.reporting.insight_llm_client import chat_json_with_usage, llm_configured

            apply_admin_insight_llm(log_prefix="advisor")
            if llm_configured():
                advice = self._llm_generate(report_date, ctx)
                validate_advisory_output(advice)
                return advice
        except Exception:
            pass

        advice = self._template_generate(report_date, ctx)
        validate_advisory_output(advice)
        return advice

    def _template_generate(self, report_date: str, ctx: dict[str, Any]) -> dict[str, Any]:
        summary = str(ctx.get("market_summary") or ctx.get("summary") or "市场数据已接收，系统正在生成完整 AI 解读。")
        directions = []
        for block in ctx.get("direction_advices") or ctx.get("directions") or ctx.get("direction_blocks") or []:
            if not isinstance(block, dict):
                continue
            key = str(block.get("key") or block.get("direction") or "")
            if not key:
                continue
            text = str(block.get("content") or block.get("summary") or "")
            directions.append({
                "key": key,
                "title": block.get("title") or key,
                "summary": text[:200],
                "content": text or block.get("summary") or "",
            })
        return {
            "report_date": report_date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "daily_overview": {
                "title": "今日市场观察",
                "summary": summary[:240],
                "content": summary,
            },
            "direction_advices": directions[:8],
            "disclaimer": "仅供参考，不构成投资建议。",
        }

    def _llm_generate(self, report_date: str, ctx: dict[str, Any]) -> dict[str, Any]:
        from cloud_deploy.reporting.insight_llm_client import chat_json_with_usage

        system = (
            "你是小红书选品 AI 顾问。根据脱敏市场 context 生成 JSON："
            "daily_overview{title,summary,content}，direction_advices[{key,title,summary,content}]。"
            "禁止输出 goods_id、店铺名、商品链接、完整商品标题列表。"
        )
        user = json.dumps({"report_date": report_date, "context": ctx}, ensure_ascii=False)[:120_000]
        parsed, _usage = chat_json_with_usage(system, user, temperature=0.35, agent="ceo")
        overview = parsed.get("daily_overview") or parsed.get("overview") or {}
        directions = parsed.get("direction_advices") or parsed.get("directions") or []
        return {
            "report_date": report_date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "daily_overview": {
                "title": overview.get("title") or "今日市场观察",
                "summary": (overview.get("summary") or overview.get("content") or "")[:240],
                "content": overview.get("content") or overview.get("summary") or "",
            },
            "direction_advices": directions[:12],
            "disclaimer": "仅供参考，不构成投资建议。",
        }
