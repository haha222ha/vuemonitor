# 选品云端（xhs-cloud）需求规格书 v1.0

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 仓库位置 | https://github.com/haha222ha/vuemonitor → `xhs-cloud/` |
| 状态 | **完整版可部署** · 含 §11 安装上线说明 |
| 关联现网 | vuemonitor `server/`（:8000）**零代码修改** |

---

## 1. 项目目标

建设**独立于 vuemonitor** 的选品监控与会员交付子系统：

1. 以本地 `gen_report` 产出的 **`data.js`（选品日报）** 为商品来源（**不迁移 13GB SQLite 全库**）
2. 将报告中 **日增量 > 0**（`v1d > 0` 或 `actual_v1d > 0`）的商品及其 **日级销量历史（sold_history）** 写入 **PostgreSQL `xhs_monitor` schema**
3. 提供 **会员 zip 下载**（`index_with_gr.html` + `data.js`，与现网 gen_report 同结构）
4. 与 vuemonitor **共用 PG 实例**、**独立 schema**、**独立进程**（`:8080`）

---

## 2. 系统边界（强制）

| 禁止 | 允许 |
|------|------|
| 修改 `server/`、`web-user/`、vuemonitor Alembic | 在 `xhs-cloud/` 内新增代码 |
| 修改 `gen_report.py`、爬虫、跟踪库 | **只读**消费 `data.js`、只读 SQLite `sold_history` 回补 |
| 修改 `public` schema 表结构 | 新建 `xhs_monitor` schema |
| 会员提供 PG 全库 API | zip 离线包 + 鉴权下载 |

---

## 3. 数据库设计（已挑出）

### 3.1 与 vuemonitor 的关系

```
PostgreSQL :5432
└── 数据库 vuemonitor
    ├── public.*              ← vuemonitor 现网（不动）
    └── xhs_monitor.*       ← 本子系统（独立用户 xhs_monitor_user）
```

初始化：`cloud_deploy/database/init_xhs_monitor.sql`

### 3.2 核心表（P0）

| 表 | 用途 |
|----|------|
| `monitor_goods` | 监控池：报告入选且 v1d>0 或 actual>0 |
| `goods_sold_daily` | 监控池商品的日级销量全量历史 |
| `report_daily_items` | 每日报告行（28 列，与 gen_report.COLUMNS 一致） |
| `report_daily_meta` | 每日报告 meta |
| `goods_metrics_daily` | 每日指标快照 |
| `report_archives` | 会员 zip 索引 |
| `goods_sync_state` | sold_history 回补进度 |
| `users` / `memberships` | 选品会员（独立于 public.users） |

### 3.3 入池规则（已确认）

```text
报告 items 全量 → report_daily_items
若 v1d > 0 OR actual_v1d > 0 → upsert monitor_goods
新入池 → goods_sync_state.sold_daily_backfill_done = false → 触发 sold_history 回补
```

### 3.4 不上云

- 全库 `goods`（~1180 万行）
- 本地 SQLite 文件整体（~13GB）
- 未入报告的商品
- `sold_snapshots` 全量日内快照（云侧 Phase 2 仅 90 天，可选）

---

## 4. 数据流

### 4.1 当前 P0（过渡 · 已实现）

```text
本地 Windows
  gen_report.py（不动）→ 全量MMDD/data.js
       │
       ├─ tools/cloud_sync_client.py push  ──HTTP──▶ 云 API /sync/daily-report
       ├─ tools/cloud_sync_client.py backfill-sold（可选，读本地 sold_history）
       └─ scp 全量MMDD/ ──▶ /opt/xhs-cloud/data/incoming/

云端 /opt/xhs-cloud
  run_daily_pipeline.py（入库，不跑 gen_report）
       → zip + report_archives + PG 同步
  xhs-cloud-api :8080
       → 会员登录 / 报告列表 / zip 下载
```

### 4.2 云端生成（P1 · 已实现）

```text
PG xhs_monitor（report_daily_items / goods_sold_daily）
  → cloud_gen_report.py / run_full_pipeline.py full
  → 全量MMDD/data.js + zip + report_archives

周期报告:
  → run_full_pipeline.py weekly|monthly
  → 周报MMDD / 月报YYYYMM + member_weekly_zip / member_monthly_zip

历史冷启动:
  → import_historical_reports.py 批量导入本地 全量*
```

**已实现（P2/P3/P4）：** `goods_sold_snapshots` 90 天滚动 + 回补/增量同步 + `cloud_daemon` PG 扫描 + `monitor_rules` 规则引擎。

---

## 5. 功能需求

### FR-01 报告同步（P0 ✅）

| ID | 需求 |
|----|------|
| FR-01-01 | 解析 `data.js`，幂等写入 `report_daily_meta` + `report_daily_items` |
| FR-01-02 | `v1d>0 OR actual>0` 入 `monitor_goods`，更新 `peak_v1d` |
| FR-01-03 | 写入 `goods_metrics_daily` |
| FR-01-04 | API `POST /api/v1/sync/daily-report`，Header `X-Sync-Key` |

### FR-02 日照回补（P0 ✅）

| ID | 需求 |
|----|------|
| FR-02-01 | 新入池商品从本地 `sold_history` 全量回补 → `goods_sold_daily` |
| FR-02-02 | API `POST /api/v1/sync/sold-history` 批量推送 |
| FR-02-03 | `goods_sync_state` 记录回补完成度 |

### FR-03 会员 zip（P0 ✅）

| ID | 需求 | 周期 | 状态 |
|----|------|------|------|
| FR-03-01 | 入库时打 zip（html + data.js） | **日报** | ✅ `member_daily_zip` |
| FR-03-02 | `report_archives` 登记 | **日报** | ✅ |
| FR-03-03 | 报告列表 API | 日/周/月 | ✅ |
| FR-03-04 | zip 下载 API | 日/周/月 | ✅ 日报 |
| FR-03-05 | 过期会员 402 | — | ✅ |

**日报链路（已实现，名称是 `xhs-ingest-report`，不是 weekly）：**

```text
本地 gen_report → data.js
  → scp / cloud_sync_client / incoming 目录
  → run_daily_pipeline.py（每日 20:00 timer 或手动）
  → PG report_daily_* + monitor_goods + zip → 会员下载
```

**周报 / 月报（P1 ✅）：** `cloud_period_report.py` + `xhs-weekly-report.timer` / `xhs-monthly-report.timer`，登记 `member_weekly_zip` / `member_monthly_zip`。

### FR-04 部署（P0 ✅）

| ID | 需求 |
|----|------|
| FR-04-01 | 独立 `/opt/xhs-cloud`，git 与 vuemonitor 同仓库 |
| FR-04-02 | `install.sh` + `host-update.sh` |
| FR-04-03 | systemd `xhs-cloud-api` MemoryMax 256M |
| FR-04-04 | nginx 独立反代（可选） |

---

## 6. 非功能需求

| 类别 | 指标 |
|------|------|
| 内存 | API ≤256M；与 vuemonitor 2C2G 共存 |
| 隔离 | 不触碰 `public` schema |
| 安全 | SYNC_KEY + JWT；`.env` 不入库 |
| 幂等 | 同 `report_date` 重复同步不重复行 |

---

## 7. 部署清单

详见 [DEPLOY_CHECKLIST.md](./DEPLOY_CHECKLIST.md)，**完整安装步骤见 §11（文档末尾）**。

---

## 8. 代码索引

| 模块 | 路径 |
|------|------|
| 同步核心 | `cloud_deploy/cloud_api/sync_service.py` |
| FastAPI | `cloud_deploy/cloud_api/main.py` |
| 入库流水线 | `cloud_deploy/scripts/run_daily_pipeline.py` |
| 统一流水线 | `cloud_deploy/scripts/run_full_pipeline.py` |
| 云端日报 | `cloud_deploy/scripts/cloud_gen_report.py` |
| 周报/月报 | `cloud_deploy/scripts/cloud_period_report.py` |
| 历史冷启动 | `cloud_deploy/scripts/import_historical_reports.py` |
| 报告生成库 | `cloud_deploy/reporting/` |
| HTML 模板 | `cloud_deploy/assets/index_with_gr.html` |
| 本地推云 | `tools/cloud_sync_client.py` |
| 本地联调 | `docker-compose.dev.yml` |
| E2E 测试 | `cloud_deploy/tests/e2e_test.py` |
| 本地数据整理 | `tools/prepare_server_sync.py` → `server_sync_pack/`（含 `monitor_pool/` sold_history 导出） |
| PG DDL | `cloud_deploy/database/init_xhs_monitor.sql` |

---

## 9. 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **P0** | **日报** data.js 入库 + PG + 日报 zip + 会员 API + 部署 | ✅ |
| P1 | **周报 / 月报** zip 聚合生成 | ✅ |
| P1 | `cloud_gen_report.py` 读 PG 在云端出报告 | ✅ |
| P1 | 历史报告冷启动批量入库 | ✅ `import_historical_reports.py` |
| P1 | 本地 docker-compose PG 联调 | ✅ |
| P2 | sold_snapshots 90 天 + 清理 Job | ✅ |
| P2 | 增量 sold_history 同步 | ✅ |
| P3 | cloud_daemon 云扫描写 PG | ✅（可选，2G 默认不 enable） |
| P4 | 规则引擎 + monitor_alerts | ✅ 轻量版 |
| P5 | sold_snapshots 全历史 / 规则告警通道 | ⏳ |

---

## 10. 已确认决策

| # | 决策 |
|---|------|
| 1 | 监控池：`v1d > 0 OR actual_v1d > 0` |
| 2 | 不上云 13GB SQLite，仅日照子集 |
| 3 | 不改 gen_report / vuemonitor |
| 4 | 会员交付：html+data.js zip，无 PDF |
| 5 | 过期会员 402 封禁 |
| 6 | PG：同实例 `vuemonitor` 库 + `xhs_monitor` schema |

---

## 11. 安装与上线说明（最终版）

> 目标：**纯线上纯自动**。代码 git 一次 push，数据本地整理一次 upload，服务器一次 pull + import。

### 11.1 本地（Windows）— 代码 push

```powershell
cd E:\vuemonitor
git add xhs-cloud/
git commit -m "feat(xhs-cloud): 选品云服务完整版"
git push origin main
```

**本地 E2E 自测（push 前）：**

```powershell
cd E:\vuemonitor\xhs-cloud
.\cloud_deploy\tests\run_e2e.ps1
# 期望: PASS>=22  FAIL=0
```

### 11.2 本地 — 历史数据整理（首次上云）

```powershell
cd E:\vuemonitor\xhs-cloud
python tools/prepare_server_sync.py `
  --source "C:\Users\Administrator\Desktop\每日选品全量数据" `
  --main-db "D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db"
# 可选：同时导出近 90 天 sold_snapshots
# python tools/prepare_server_sync.py --snapshots
```

| 产出 | 说明 | 进 git |
|------|------|--------|
| `server_sync_pack/historical_reports/全量*` | gen_report 历史日报 data.js | 否 |
| `server_sync_pack/monitor_pool/sold_history/` | **日增量>0 商品**的 sold_history（从 SQLite 导出子集） | 否 |
| `server_sync_pack/monitor_pool/monitor_goods_ids.json` | 监控池 goods_id 清单 | 否 |
| `server_sync_pack/manifest.json` | 汇总清单 | 否 |
| `server_sync_pack/scp_upload.ps1` | 上传脚本 | 否 |

**不上传：** 13GB SQLite 全库、`.env` 密码。仅导出监控池（`v1d>0 OR actual_v1d>0`）对应商品的日级销量历史。

### 11.3 服务器 — 首次安装

```bash
git clone https://github.com/haha222ha/vuemonitor.git /opt/vuemonitor
sudo bash /opt/vuemonitor/xhs-cloud/cloud_deploy/install.sh /opt/vuemonitor/xhs-cloud
sudo -u postgres psql -d vuemonitor -f /opt/xhs-cloud/cloud_deploy/database/init_xhs_monitor.sql
cp /opt/xhs-cloud/cloud_deploy/.env.example /opt/xhs-cloud/.env && nano /opt/xhs-cloud/.env
```

### 11.4 上传历史数据 + import

```powershell
# 本地
cd E:\vuemonitor\xhs-cloud\server_sync_pack
# 编辑 scp_upload.ps1 填 ECS IP 后:
.\scp_upload.ps1
```

```bash
# 服务器（按顺序）
cd /opt/xhs-cloud

# 1. 历史日报 → report_daily_items + monitor_goods
sudo -u admin env PYTHONPATH=/opt/xhs-cloud ./venv/bin/python \
  cloud_deploy/scripts/import_historical_reports.py \
  --root /opt/xhs-cloud/data/import_batch/historical_reports

# 2. 监控池 sold_history → goods_sold_daily
sudo -u admin env PYTHONPATH=/opt/xhs-cloud ./venv/bin/python \
  cloud_deploy/scripts/import_monitor_pool_offline.py \
  --pack /opt/xhs-cloud/data/import_batch/monitor_pool
```

### 11.5 启用纯线上全自动

```bash
sudo systemctl enable xhs-cloud-api xhs-daemon \
  xhs-daily-report.timer xhs-weekly-report.timer \
  xhs-monthly-report.timer xhs-prune-snapshots.timer
sudo systemctl start xhs-cloud-api xhs-daemon
```

### 11.6 E2E 验收

```bash
export E2E_DATABASE_URL="$XHS_DATABASE_URL"
bash /opt/xhs-cloud/cloud_deploy/tests/run_e2e.sh
```

### 11.7 日常代码更新

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env
cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

---

*文档结束*
