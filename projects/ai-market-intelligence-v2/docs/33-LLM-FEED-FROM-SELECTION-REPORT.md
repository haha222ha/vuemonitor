# 33 — 选品报告 → LLM 投喂包（feed-v1）

> **版本**：v1.0 · **日期**：2026-07-12  
> **回答**：AI 情报建议从哪来？如何像选品日报一样「脚本化、可审计」地生成？

---

## 1. 结论（一句话）

**AI 情报与 Legacy 选品报告读同一份 PG 选品池**；区别是 Legacy 输出 `data.js`（商品行），V2 先聚合成 **类目级 `llm_feed.json`**，再喂给 5 Agent 生成叙事报告。

```
PG 选品池（fetch_items_auto，与 cloud_gen_report 相同）
        │
        ├─► cloud_gen_report.py ──► data.js + HTML（Legacy 会员）
        │
        └─► cloud_insight_report.py
                 │
                 ├─ aggregate_items_to_insights（类目 + k-匿名）
                 ├─ build_llm_feed() ──► llm_feed.json + llm_feed.md
                 ├─ feed_to_agent_metrics() ──► 5 Agent Prompt
                 └─ render_insight_html() ──► 会员 AI Tab
```

---

## 2. 为什么需要 feed 层？

| 问题 | feed-v1 如何解决 |
|------|------------------|
| 「AI 是不是瞎编？」 | 每个类目落盘 `llm_feed.json`，可对照 PG 样本数与指数 |
| 「和选品报告什么关系？」 | `provenance` 写明同源脚本、`raw_selection_rows` |
| 「喂什么格式最好？」 | **JSON 主、MD 辅**；Agent 只吃 JSON，运维看 MD |
| 「合规？」 | 禁止 goods_id / 店铺 / 标题列表；仅 keyword_themes 词频 |

---

## 3. feed-v1 结构

路径（Shadow）：

```
data/insight_shadow/insight_YYYYMMDD/{类目}/
  llm_feed.json      ← AI 输入快照（审计）
  llm_feed.md        ← 人类可读摘要
  insight.json       ← metrics + report + llm_feed 全量 meta
  index.html         ← 会员可见页
```

### 3.1 JSON 顶层字段

| 块 | 含义 |
|----|------|
| `schema_version` | `feed-v1` |
| `provenance` | 数据源、选品行数、k-匿名、生成时间 |
| `selection_summary` | 虚拟/实体占比、新品占比、中位价、行为 mix |
| `indices` | 蓝海/竞争/增速/价格带/price_distribution |
| `trends` | trend_label + trend_7d |
| `context` | keyword_themes、similar_categories、season_note |
| `compliance` | disclaimer + forbidden_outputs |

### 3.2 与 Agent Prompt 的映射

`feed_to_agent_metrics()` 扁平化为 Agent 可用的 JSON，在原有 indices 基础上增加：

- `selection_summary`（类目内结构）
- `keyword_themes`（脱敏主题词，非标题）

Prompt 版本：`agent-v1-feed`（L1 缓存键随 feed 内容变化自动失效重算）。

---

## 4. 脚本命令

### 4.1 完整管道（预生成 + LLM）

```bash
bash /opt/xhs-cloud/cloud_deploy/scripts/run_insight_report_shadow.sh
# 或
cd /opt/xhs-cloud
./venv/bin/python cloud_deploy/scripts/cloud_insight_report.py --date 2026-07-12 --playbook full
```

### 4.2 仅导出 feed（不调 LLM，审计用）

```bash
cd /opt/xhs-cloud
PYTHONPATH=/opt/xhs-cloud ./venv/bin/python cloud_deploy/scripts/export_insight_llm_feeds.py --date 2026-07-12
# 输出: data/llm_feeds/feed_YYYYMMDD/{类目}/llm_feed.json
```

### 4.3 Legacy 选品日报（对照）

```bash
cd /opt/xhs-cloud
./venv/bin/python cloud_deploy/scripts/cloud_gen_report.py --date 2026-07-12 --source auto
```

**同一天、同一 `--source auto`，两者读同一 PG 快照。**

---

## 5. 代码位置

| 文件 | 职责 |
|------|------|
| `reporting/pg_reader.py` | 选品池读取（与日报共用） |
| `reporting/insight_metric_engine.py` | 类目聚合 → InsightMetrics |
| `reporting/insight_llm_feed.py` | **feed-v1 构建 / MD / Agent 扁平化** |
| `reporting/insight_pipeline.py` | 串联 feed → Agent → HTML |
| `scripts/export_insight_llm_feeds.py` | 仅导出 feed |
| `prompts/agents.yaml` | 5 Agent，注明 feed 字段 |

---

## 6. 验收清单

- [ ] 跑完 Shadow 后，任意类目目录存在 `llm_feed.json` + `llm_feed.md`
- [ ] `provenance.raw_selection_rows` > 0 且与当日 PG 有数据一致
- [ ] `selection_summary.sample_size` ≥ k-匿名阈值
- [ ] JSON 内无 goods_id / store_name / 完整 title
- [ ] 改 feed 字段后 L1 cache miss，重跑 LLM（`PROMPT_VERSION=agent-v1-feed`）

---

## 7. 后续（可选）

| ID | 内容 |
|----|------|
| feed-v2 | 子类目拆分、周环比、价格带 Top3 结构（仍无单品） |
| 会员 UI | AI Tab 折叠展示「投喂摘要」链到 llm_feed.md |
| 对齐 Legacy | manifest 记录对应 `全量MMDD/data.js` 的 report_date |
