# -*- coding: utf-8 -*-
"""云侧 AI 顾问批量生成 — 读脱敏 context，产出 advice.json 结构。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from cloud_deploy.rank_engine.compliance import sanitize_context, validate_advisory_output


class AiAdvisor:
    def run_batch(
        self,
        *,
        target_date: str,
        context: dict[str, Any],
        llm_enhance: bool = False,
    ) -> dict[str, Any]:
        ctx = sanitize_context(context or {})
        report_date = str(
            target_date
            or (ctx.get("meta") or {}).get("target_date")
            or ctx.get("target_date")
            or ""
        )[:10]
        if not report_date:
            raise ValueError("缺少 target_date")

        # 主路径：本机已预生成的 advice（随 context 上传）
        pre = ctx.get("pre_analysis") or ctx.get("advice")
        if isinstance(pre, dict) and (pre.get("daily_overview") or pre.get("direction_advices")):
            advice = self._normalize_pregen(report_date, pre)
            if llm_enhance:
                advice = self._maybe_llm_enhance(report_date, advice, ctx)
            validate_advisory_output(advice)
            return advice

        # 兜底：规则模板（仍非 LLM 主路径）
        advice = self._template_generate(report_date, ctx)
        if llm_enhance:
            advice = self._maybe_llm_enhance(report_date, advice, ctx)
        validate_advisory_output(advice)
        return advice

    def _normalize_pregen(self, report_date: str, pre: dict[str, Any]) -> dict[str, Any]:
        meta = pre.get("meta") or {}
        overview = pre.get("daily_overview") or {}
        directions = pre.get("direction_advices") or []
        return {
            "report_date": report_date,
            "generated_at": meta.get("finished_at") or datetime.now(timezone.utc).isoformat(),
            "meta": {
                "target_date": report_date,
                "mode": meta.get("mode") or "pregen",
                "generator": meta.get("generator") or "local_pregen",
                "finished_at": meta.get("finished_at"),
                "schema_version": meta.get("schema_version") or "1.0",
            },
            "daily_overview": {
                "title": overview.get("title") or "今日市场观察",
                "summary": (overview.get("summary") or overview.get("content") or "")[:240],
                "content": overview.get("content") or overview.get("summary") or "",
            },
            "direction_advices": directions,
            "disclaimer": pre.get("disclaimer") or "仅供参考，不构成投资建议。",
            "dynamic": pre.get("dynamic"),
        }

    def _maybe_llm_enhance(self, report_date: str, advice: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        """可选 LLM 补充：在预生成 advice 上追加 dynamic 块，失败则原样返回。"""
        try:
            from cloud_deploy.reporting.insight_llm_client import llm_configured

            if not llm_configured():
                return advice
            snippet = self._llm_supplement_snippet(report_date, advice, ctx)
            if snippet:
                advice = dict(advice)
                advice["dynamic"] = {
                    "query": "今日市场补充观察",
                    "content": snippet,
                    "source": "llm_supplement",
                }
        except Exception:
            pass
        return advice

    def _llm_supplement_snippet(self, report_date: str, advice: dict[str, Any], ctx: dict[str, Any]) -> str:
        from cloud_deploy.reporting.insight_llm_client import chat_json_with_usage

        system = (
            "你是小红书选品顾问。根据已有预生成报告与脱敏 context，"
            "输出一段 200 字以内的补充观察（纯文本）。"
            "禁止 goods_id、店铺名、商品链接、完整标题。"
        )
        user = json.dumps(
            {"report_date": report_date, "overview": advice.get("daily_overview"), "brief": ctx.get("daily_brief")},
            ensure_ascii=False,
        )[:8000]
        parsed, _ = chat_json_with_usage(system, user, temperature=0.3, agent="ceo")
        if isinstance(parsed, dict):
            return str(parsed.get("content") or parsed.get("snippet") or "")
        return ""

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
