# -*- coding: utf-8 -*-
"""云侧 AI 顾问批量生成 — LLM 主路径 + 模板兜底。

主路径：每个榜单独立 LLM 调用 + daily_overview + 跨榜综述。
兜底  ：LLM 未配置 / 整体失败 → 走 pre_analysis 或模板。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from cloud_deploy.rank_engine.compliance import sanitize_context, validate_advisory_output

# 默认每个榜单送给 LLM 的最大条目数（控制 token 与成本）
_TOP_ITEMS_PER_RANKING = 30
# 跨榜综述最多取的榜单数
_MAX_RANKINGS_FOR_CROSS = 12


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

        # 主路径：LLM 真实生成（llm_enhance=True 或 LLM 已配置时自动启用）
        from cloud_deploy.reporting.insight_llm_client import llm_configured

        use_llm = llm_enhance or llm_configured()
        if use_llm and llm_configured():
            try:
                advice = self._llm_generate(report_date, ctx)
                validate_advisory_output(advice)
                return advice
            except Exception as e:
                print(f"[advisor] LLM 主路径失败，回退模板: {e}", file=sys.stderr, flush=True)

        # 兼容旧路径：本地预生成 advice（随 context 上传）
        pre = ctx.get("pre_analysis") or ctx.get("advice")
        if isinstance(pre, dict) and (pre.get("daily_overview") or pre.get("direction_advices")):
            advice = self._normalize_pregen(report_date, pre)
            if llm_enhance:
                advice = self._maybe_llm_enhance(report_date, advice, ctx)
            validate_advisory_output(advice)
            return advice

        # 最终兜底：规则模板
        advice = self._template_generate(report_date, ctx)
        if llm_enhance:
            advice = self._maybe_llm_enhance(report_date, advice, ctx)
        validate_advisory_output(advice)
        return advice

    # ---------- LLM 主路径 ----------

    def _llm_generate(self, report_date: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """LLM 主路径：daily_overview + 每榜独立调用 + 跨榜综述。"""
        from cloud_deploy.reporting.insight_llm_client import chat_json_with_usage

        started_at = datetime.now(timezone.utc).isoformat()

        # 1) daily_overview（1 次 LLM 调用）
        overview = self._llm_daily_overview(report_date, ctx, chat_json_with_usage)

        # 2) 每个榜单独立调用（≈30 次）
        rankings = ctx.get("rankings") or {}
        directions: list[dict[str, Any]] = []
        for key, ranking in rankings.items():
            try:
                item = self._llm_ranking(report_date, ranking, chat_json_with_usage)
                if item:
                    directions.append(item)
            except Exception as e:
                print(f"[advisor] ranking '{key}' LLM 失败，模板兜底: {e}", file=sys.stderr, flush=True)
                fallback = self._template_ranking(report_date, ranking)
                if fallback:
                    directions.append(fallback)

        # 3) 跨榜综述（1 次 LLM 调用）
        cross = None
        try:
            cross = self._llm_cross_summary(report_date, ctx, directions, chat_json_with_usage)
        except Exception as e:
            print(f"[advisor] 跨榜综述 LLM 失败，跳过: {e}", file=sys.stderr, flush=True)

        finished_at = datetime.now(timezone.utc).isoformat()
        return {
            "report_date": report_date,
            "generated_at": finished_at,
            "meta": {
                "target_date": report_date,
                "mode": "llm",
                "generator": "cloud_llm",
                "started_at": started_at,
                "finished_at": finished_at,
                "schema_version": "1.0",
                "ranking_count": len(rankings),
                "directions_count": len(directions),
            },
            "daily_overview": overview,
            "direction_advices": directions,
            "cross_summary": cross,
            "disclaimer": "以上内容由 AI 基于脱敏榜单数据生成，仅供参考，不构成投资或经营建议。",
        }

    def _llm_daily_overview(self, report_date: str, ctx: dict[str, Any], chat_fn) -> dict[str, Any]:
        brief = ctx.get("daily_brief") or {}
        rankings = ctx.get("rankings") or {}
        top_cats = brief.get("top_categories") or []
        cats_text = "\n".join(
            f"  - {c.get('category','未知')}: 占比 {c.get('share_pct', c.get('count','?'))}"
            for c in top_cats[:10]
        ) or "  （暂无）"

        ranking_titles = "\n".join(
            f"  - {r.get('title','?')}（{r.get('item_count',0)}条）"
            for r in list(rankings.values())[:_MAX_RANKINGS_FOR_CROSS]
        ) or "  （暂无）"

        system = (
            "你是小红书选品顾问首席分析师。基于脱敏榜单 brief（不含商品 ID/店铺名/真实标题），"
            "输出一段生动的当日市场观察。\n"
            "合规：禁止 goods_id、店铺名、商品链接、完整商品标题；可提及类目、价格带、关注度等级。\n"
            "输出 JSON: {\"title\": str, \"summary\": str(<=240字), \"content\": str(800-1500字markdown)}"
        )
        user = (
            f"报告日期：{report_date}\n"
            f"活跃方向数：{brief.get('active_direction_count', len(rankings))}\n"
            f"总样本数：{(ctx.get('meta') or {}).get('pool_size', '未知')}\n"
            f"TOP 类目分布：\n{cats_text}\n\n"
            f"今日榜单清单：\n{ranking_titles}\n\n"
            "请输出今日市场观察：概述市场温度、识别强势类目与价格带、点出值得关注的方向。"
        )
        parsed, _u = chat_fn(system, user, temperature=0.5, agent="ceo")
        return {
            "title": str(parsed.get("title") or "今日市场观察"),
            "summary": str(parsed.get("summary") or "")[:240],
            "content": str(parsed.get("content") or parsed.get("summary") or ""),
        }

    def _llm_ranking(self, report_date: str, ranking: dict[str, Any], chat_fn) -> dict[str, Any] | None:
        title = ranking.get("title") or ranking.get("key") or "维度解读"
        description = ranking.get("description") or ""
        items = ranking.get("items") or []
        if not items:
            return None

        items_text = self._format_items_for_llm(items[:_TOP_ITEMS_PER_RANKING])
        system = (
            "你是小红书选品顾问分析师。基于一个脱敏榜单的条目（reference_no + 抽象标签），"
            "输出该方向的结构化解读。\n"
            "合规：禁止 goods_id、店铺名、商品链接、完整商品标题；只能引用 reference_no 编号。\n"
            "输出 JSON: {\"key\": str, \"title\": str, \"summary\": str(<=200字), "
            "\"content\": str(600-1200字markdown), \"key_points\": [str]}"
        )
        user = (
            f"报告日期：{report_date}\n"
            f"榜单：{title}\n描述：{description}\n"
            f"条目数：{ranking.get('item_count', len(items))}\n"
            f"TOP {min(len(items), _TOP_ITEMS_PER_RANKING)} 条脱敏数据：\n{items_text}\n\n"
            "请输出该方向的深度解读：识别共性特征、解释排序逻辑、给出可执行选品建议。"
        )
        parsed, _u = chat_fn(system, user, temperature=0.5)
        return {
            "key": str(ranking.get("key") or parsed.get("key") or ""),
            "title": str(parsed.get("title") or title),
            "summary": str(parsed.get("summary") or "")[:200],
            "content": str(parsed.get("content") or ""),
            "key_points": list(parsed.get("key_points") or [])[:8],
        }

    def _llm_cross_summary(
        self,
        report_date: str,
        ctx: dict[str, Any],
        directions: list[dict[str, Any]],
        chat_fn,
    ) -> dict[str, Any] | None:
        """跨榜综述：发现多榜交集与隐含信号。"""
        if len(directions) < 3:
            return None
        snippets = "\n\n".join(
            f"【{d.get('title','?')}】\n{(d.get('summary') or d.get('content') or '')[:200]}"
            for d in directions[:_MAX_RANKINGS_FOR_CROSS]
        )
        system = (
            "你是小红书选品顾问首席分析师。基于已生成的多个方向解读，"
            "输出跨榜综述：发现交集信号、识别矛盾点、给出综合选品方向。\n"
            "合规：禁止 goods_id、店铺名、商品链接、完整商品标题。\n"
            "输出 JSON: {\"title\": str, \"content\": str(500-1000字markdown), "
            "\"action_items\": [str]}"
        )
        user = (
            f"报告日期：{report_date}\n"
            f"已生成 {len(directions)} 个方向解读：\n{snippets}\n\n"
            "请输出跨榜综述：哪些方向出现共识？哪些信号冲突？中小商家应优先关注哪 2-3 个方向？"
        )
        parsed, _u = chat_fn(system, user, temperature=0.5, agent="ceo")
        return {
            "title": str(parsed.get("title") or "跨榜综述"),
            "content": str(parsed.get("content") or ""),
            "action_items": list(parsed.get("action_items") or [])[:6],
        }

    def _format_items_for_llm(self, items: list[dict[str, Any]]) -> str:
        lines = []
        for it in items:
            lines.append(
                f"  #{it.get('reference_no','?')} | 类目:{it.get('category_tag','未知')} | "
                f"价格带:{it.get('price_range_label','未知')} | "
                f"日增量:{it.get('daily_sales_increment',0)} | "
                f"增速:{it.get('growth_rate_pct',0)}% | "
                f"关注度:{it.get('attention_level_label','未知')} | "
                f"竞争:{it.get('competition_level_label','未知')} | "
                f"趋势信号:{it.get('trend_signal_label','未知')}"
            )
        return "\n".join(lines) if lines else "  （无数据）"

    def _template_ranking(self, report_date: str, ranking: dict[str, Any]) -> dict[str, Any] | None:
        """单榜 LLM 失败时的模板兜底。"""
        items = ranking.get("items") or []
        if not items:
            return None
        title = ranking.get("title") or ranking.get("key") or "维度解读"
        top3 = items[:3]
        lines = [f"- #{it.get('reference_no','?')} {it.get('category_tag','')} 价位{it.get('price_range_label','')} 增量{it.get('daily_sales_increment',0)}"
                 for it in top3]
        return {
            "key": str(ranking.get("key") or ""),
            "title": title,
            "summary": f"Top3 占该榜 {len(items)} 条，呈现 {top3[0].get('trend_signal_label','变化')} 特征。",
            "content": f"本方向共 {len(items)} 条脱敏条目。TOP3：\n" + "\n".join(lines) +
                       "\n\n（本方向 LLM 调用失败，已用模板兜底，建议稍后重试生成。）",
            "key_points": [],
        }

    # ---------- 旧路径保留（向后兼容） ----------

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
        """旧路径可选 LLM 补充（保留以兼容老调用方）。"""
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
