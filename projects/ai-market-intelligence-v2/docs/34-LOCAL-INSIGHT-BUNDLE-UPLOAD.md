# 34 — 方案 A：本地聚合投喂 + 上传云（9 万 → AI 最优路径）

> **版本**：v1.0 · **日期**：2026-07-12  
> **原则**：9 万行 **never** 进 LLM；本地 PG 聚合 → 每类目 ~2–5KB `llm_feed.json` → 上传云展示

---

## 1. 三层压缩（成本最优）

```
L0  9.4 万 goods (delta≥1)          ← 本地 PG / sold_history，不上云
         ↓ SQL 聚合 + 类目 taxonomy
L1  ~20–80 类目 × sample_size        ← 每类目几百～几千行，仍在本地内存
         ↓ top 5% 增量切片 + 词频
L2  feed-v1.1 每类目 1 个 JSON       ← AI 只吃这个（~14–80 次 LLM × 5 Agent）
         ↓ 可选本地 LLM
L3  index.html 上传云 insight_shadow  ← 云零 PG、零 9 万 sync
```

| 阶段 | 数据量 | LLM tokens |
|------|--------|------------|
| 错误：9 万行 JSON 直喂 | ~GB 级 | 不可接受 |
| **正确：类目 feed** | ~50–400 KB/天 | ~14–80 类目 × 5 Agent |
| **最省：本地 LLM + 只上传 HTML** | ~几 MB/天 | 云 **0** token |

---

## 2. feed-v1.1 新增：`growth_direction_hints`

从类目内 **增速最高 5%**（至少 5 条）提炼 **产品方向关键词**，不含 title/goods_id：

```json
"growth_direction_hints": {
  "top_slice_size": 42,
  "top_slice_pct": 5.0,
  "avg_increment_in_slice": 128.5,
  "median_price_in_slice": 29.9,
  "product_direction_keywords": ["保湿", "防晒喷雾", "敏感肌"]
}
```

Agent Prompt 字段：`growth_direction_hints`（见 `feed_to_agent_metrics`）。

---

## 3. 本地命令

```powershell
cd E:\vuemonitor\xhs-cloud
$env:PYTHONPATH="E:\vuemonitor\xhs-cloud"
$env:XHS_DATABASE_URL="postgresql://..."   # 本地 PG（含 premium_goods_daily）

# 仅 feed（不调 LLM，审计用）
python cloud_deploy/scripts/export_local_insight_bundle.py --date 2026-07-12

# feed + 本地 5 Agent → index.html
python cloud_deploy/scripts/export_local_insight_bundle.py --date 2026-07-12 --llm
```

输出：`data/insight_export/insight_YYYYMMDD/{类目}/llm_feed.json`

数据源：`INSIGHT_PG_SOURCE=local_delta` → `premium_goods_daily.delta>=1`

---

## 4. 上传云（会员 AI Tab）

```bash
# Linux / Git Bash
bash cloud_deploy/scripts/upload_insight_bundle.sh 2026-07-12 root@你的ECS
```

```powershell
# Windows
.\scripts\push_insight_bundle.ps1 -Date 2026-07-12 -Host root@你的ECS
```

目标：`/opt/xhs-cloud/data/insight_shadow/insight_YYYYMMDD/`

---

## 5. 云主机配置（停精品库 sync）

`.env` 保持：

```env
XHS_PREMIUM_CLOUD_SYNC=0
XHS_INSIGHT_SHADOW_TIMER=0   # 可选，避免云 PG 261 条重复跑
```

精品库 sync API 返回 **410**；PG 不 init premium schema。

---

## 6. 与 doc 22 L0 的关系

| 项 | 云 PG 聚合 (旧) | 方案 A (推荐) |
|----|----------------|---------------|
| 观察池 | 云 goods_sold_daily ~261 | 本地 9 万 |
| 云 PG 精品库 | sync 贵 | **不同步** |
| LLM 输入 | 同上 feed | 同上 feed |
| 会员读 | insight_shadow | **同一目录**，上传即可 |
