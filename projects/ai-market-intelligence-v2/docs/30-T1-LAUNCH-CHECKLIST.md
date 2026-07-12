# 30 — T1 开流量今日冲刺清单

> **一条命令开 T1**：`bash /opt/vuemonitor/xhs-cloud/cloud_deploy/scripts/v2-t1-launch.sh`

---

## 今日必做（按顺序）

### 1. 选品云 T1 开流量（~5 分钟）

```bash
export XHS_MEMBER_TOKEN='你的token'
export XHS_SMOKE_EXPECT=legacy_dual
bash /opt/vuemonitor/xhs-cloud/cloud_deploy/scripts/v2-t1-launch.sh
```

写入 `XHS_V2_LAUNCH=1` → 全链路部署 → smoke → 检查支付页仅 `insight_*`。

### 2. 浏览器验收

- https://monitor.xhs365.cn/member → Ctrl+Shift+R
- 老月卡：双 Tab + 雷达 + **为你推荐** + 健康度
- Admin 发 **AI 情报体验码** → 新账号注册 → 仅 AI Tab（`insight_only`）

### 3. 体验码账号 smoke

```bash
export XHS_MEMBER_TOKEN='体验码账号token'
export XHS_SMOKE_EXPECT=insight_only
bash /opt/xhs-cloud/cloud_deploy/scripts/insight_shadow_smoke.sh
```

### 4. SaaS Admin（若未跑）

```bash
cd /opt/vuemonitor && git pull && bash scripts/host-update.sh
```

---

## T0（7 天并行，不用阻塞 T1）

```bash
bash /opt/xhs-cloud/cloud_deploy/scripts/launch_daily_ops.sh
```

---

## T2 已代码就绪

| 功能 | API |
|------|-----|
| 为你推荐 | `GET /member/insight/recommendations` |
| 健康度 | `GET /member/insight/health-score` |
| 工作流回填 | `GET/POST /member/insight/workflow` |

---

## GA 仍须独立排期

- PC ProductAnalyzer 合并（`xhs_shelf_time` 仓库）
- 最后 Legacy 到期 → `CONFIRM=1 bash .../disable_legacy_report_timer.sh`

---

## 体验码 Day1–3

见 **`31-EXPERIENCE-CODE-SOP.md`**
