# 26 — T0 Shadow 7 天运维 Runbook

> **目标**：在不影响 Legacy 17:00 日报 zip 的前提下，开启 V2 情报 L0 预生成 Shadow 7 天验收。  
> **关联**：`22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md`、`25-GLOBAL-IMPLEMENTATION-GAPS.md`

---

## 1. 架构速览

| 组件 | 作用 |
|------|------|
| `xhs-insight-report.timer` | 每天 **02:30** 触发 |
| `run_insight_report_shadow.sh` | 调用 `cloud_insight_report.py --playbook full` |
| `data/insight_shadow/` | Shadow HTML 输出（**不**写入 Legacy `report_archives`） |
| Admin **情报 LLM** | https://admin.xhs365.cn/insight-llm — 配置 Key + 开关 |
| 用户访问 | 读库/HTML，**零 LLM** |

**LLM 调用时机**：仅 02:30 批处理；`enabled=true` + API Key 已保存 → 真 AI；否则 mock。

---

## 2. 前置条件

- [ ] PG 已配置 `XHS_DATABASE_URL`
- [ ] Legacy 日报 timer 正常（`xhs-daily-report.timer` 17:00）
- [ ] 近 7 天内有 `report_daily_items` 数据（否则 pipeline 报「PG 无数据」）
- [ ] `server/.env` 已配置 `XHS_CLOUD_API_URL` + `XHS_CLOUD_SYNC_KEY`（admin 代理选品云）

---

## 3. 云主机部署（一次性）

### 3.1 拉代码并部署

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main \
  && rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env \
  && cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

### 3.2 PG 迁移（V2 表 + system_settings）

```bash
cd /opt/xhs-cloud
source .env 2>/dev/null || true
psql "$XHS_DATABASE_URL" -f cloud_deploy/database/08_insight_v2_tables.sql
psql "$XHS_DATABASE_URL" -c "SET search_path TO xhs_monitor, public; \dt insight_*; \dt system_settings"
```

### 3.3 `.env` Shadow 开关（不改 Legacy）

```bash
# 追加到 /opt/xhs-cloud/.env
XHS_INSIGHT_SHADOW=1
XHS_INSIGHT_SHADOW_TIMER=1
# 可选：仍用 .env 强制 LLM（一般改用 admin 后台即可）
# INSIGHT_USE_LLM=1
```

### 3.4 启用 Shadow timer

```bash
bash /opt/xhs-cloud/cloud_deploy/scripts/ensure_insight_report_timer.sh
systemctl list-timers | grep insight
```

预期：`xhs-insight-report.timer` 下次触发约 **02:30**。

### 3.5 手动试跑（不必等到 02:30）

```bash
bash /opt/xhs-cloud/cloud_deploy/scripts/run_insight_report_shadow.sh $(date +%F)
# 或指定有数据的日期
bash /opt/xhs-cloud/cloud_deploy/scripts/run_insight_report_shadow.sh 2026-07-11
```

成功标志：

```bash
ls -la /opt/xhs-cloud/data/insight_shadow/insight_*/
cat /opt/xhs-cloud/data/insight_shadow/insight_*/pipeline_summary.json | head
journalctl -u xhs-insight-report.service -n 50 --no-pager
```

日志应含 `[insight-pipeline] LLM mode=on|mock ...` 与各类目 `OK 类目名`。

---

## 4. Admin 后台配置 LLM（推荐）

1. 登录 https://admin.xhs365.cn/login?redirect=/insight-llm  
2. 侧栏 **情报 LLM**  
3. 填写 PackyAPI Key（分组选 deepseek-officially）  
4. **启用真 LLM** → 保存  
5. **测试连接** → 应返回 `pong`  
6. 再执行 §3.5 手动试跑，确认 `meta.llm=true`

> Key 加密存入 PG `system_settings`（`insight_llm`），无需把 Key 写进 `.env`。  
> 加密密钥默认 `XHS_CLOUD_JWT_SECRET`；可另设 `XHS_SETTINGS_SECRET`。

---

## 5. Shadow 7 天验收清单

| 天 | 检查项 | 命令/位置 |
|----|--------|-----------|
| D0 | timer 已 enable | `systemctl is-enabled xhs-insight-report.timer` |
| D0 | 手动跑通 1 次 | §3.5 |
| D1–D7 | 02:30 自动成功 | `journalctl -u xhs-insight-report.service --since today` |
| 每日 | 输出目录增长 | `du -sh data/insight_shadow/` |
| 每日 | Legacy 不受影响 | `data/report_archives/` 仍 17:00 更新 |
| D3 | API library 可读 | 内测账号 `GET /api/v1/member/insight/library` |
| D7 | LLM 预算未爆 | admin 页日 Token 预算；日志无 mass mock fallback |

**通过标准**：

- 连续 7 天 timer 成功或手动补跑成功 ≥ 6 天  
- Shadow HTML ≥ 1 类目/日  
- Legacy zip 下载、会员页 Legacy Tab 无回归  
- `effective_enabled=true` 时报告 `meta.llm=true`

---

## 6. 回滚

| 操作 | 命令 |
|------|------|
| 停 Shadow timer | `sudo systemctl disable --now xhs-insight-report.timer` |
| 关 LLM（保留 mock 预生成） | admin 关闭「启用真 LLM」 |
| 完全停预生成 | `.env` 设 `XHS_INSIGHT_SHADOW_TIMER=0` + disable timer |
| 删 Shadow 数据 | `rm -rf /opt/xhs-cloud/data/insight_shadow/insight_*`（可选） |

**Legacy 无需回滚** — Shadow 与 `report_archives` 隔离。

---

## 7. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `PG 无 xxx 选品数据` | 该日无 daily pipeline | 换有数据日期或先跑 Legacy 日报 |
| `LLM mode=mock` | Key 未配或未启用 | admin 情报 LLM 页 |
| `LLM failed, fallback mock` | Key 无效/429 | 测试连接；查 Packy 余额 |
| timer 未触发 | 未 enable | `ensure_insight_report_timer.sh` |
| admin 503 | server 未配 Sync Key | `server/.env` |
| permission denied | data 目录属主 | `chown -R admin:admin data/insight_shadow` |

---

## 8. Shadow 结束后（T1 预备）

- [ ] 内测账号验证 Web AI Tab + insight library  
- [ ] 评估 Token 成本 × 类目数 × 7 天  
- [ ] 准备 `XHS_V2_LAUNCH=1`（仅新 SKU，见 doc 19/20）  
- [ ] **不要**在此阶段改 Legacy 支付页默认 SKU

---

## 9. 相关路径

```
/opt/xhs-cloud/
├── cloud_deploy/scripts/run_insight_report_shadow.sh
├── cloud_deploy/scripts/ensure_insight_report_timer.sh
├── cloud_deploy/systemd/xhs-insight-report.{service,timer}
├── cloud_deploy/reporting/insight_pipeline.py
├── cloud_deploy/cloud_api/insight_settings.py
└── data/insight_shadow/
```

Admin UI：`web-admin/src/views/InsightLlmConfigView.vue`  
API：`PUT /api/v1/admin/insight-llm-config`（xhs-cloud，经 server 代理）
