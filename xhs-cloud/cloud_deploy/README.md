# 选品云端（XHS Monitor）独立部署

> **仓库**：https://github.com/haha222ha/vuemonitor（`xhs-cloud/` 目录，与现网 server/ 并列，零侵入）  
> **与 vuemonitor 完全隔离**：不改 `server/`、`gen_report.py`。  
> **共用 PG 实例** + schema `xhs_monitor` + 独立 systemd `:8080`。

---

## 1. 架构（2G 最小集）

```
本地 Windows（不变）
  gen_report → 全量MMDD/data.js
       │ scp / cloud_sync_client push
       ▼
/opt/xhs-cloud/data/incoming/
       │ timer 20:00 或手动 ingest
       ▼
PG xhs_monitor + report_archives/*.zip
       │
xhs-cloud-api :8080 → 会员下载 / 同步 API

/opt/vuemonitor  ← 现网，零改动，:8000
```

**默认不启用**：⑥ daemon、云侧 gen_report（省内存）。

---

## 2. 目录（/opt/xhs-cloud）

| 路径 | 用途 |
|------|------|
| `cloud_deploy/` | 本服务 Python 包 |
| `.env` | 环境变量 |
| `venv/` | Python 虚拟环境 |
| `data/incoming/` | scp 上传的 `全量MMDD/` |
| `data/report_archives/` | 会员 zip |

---

## 3. 首次安装（服务器）

```bash
# 1. 克隆 vuemonitor 仓库（与现网同一 repo，不同部署目录）
git clone https://github.com/haha222ha/vuemonitor.git /opt/vuemonitor
sudo mkdir -p /opt/xhs-cloud
sudo rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/
sudo chown -R $USER:$USER /opt/xhs-cloud

# 或单独克隆到 /opt/xhs-cloud（二选一）
# git clone https://github.com/haha222ha/vuemonitor.git /opt/xhs-cloud

# 2. 安装
cd /opt/xhs-cloud
sudo bash cloud_deploy/install.sh /opt/vuemonitor/xhs-cloud

# 3. 初始化 PG
sudo -u postgres psql -d vuemonitor -f /opt/xhs-cloud/cloud_deploy/database/init_xhs_monitor.sql
# 编辑 SQL 内密码，或与 .env 一致

# 4. 配置
nano /opt/xhs-cloud/.env

# 5. 启动
sudo systemctl start xhs-cloud-api
sudo systemctl enable xhs-ingest-report.timer
```

---

## 4. 日常 git 部署

**vuemonitor 现网（不变）：**
```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```

**选品云端：**
```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ --delete --exclude data --exclude venv --exclude .env
cd /opt/xhs-cloud && bash scripts/host-update.sh
```

---

## 5. 本地推报告（Windows）

```bash
# scp 报告目录到服务器
scp -r 全量0619 admin@ECS:/opt/xhs-cloud/data/incoming/

# 或 API 推 data.js（需配置 SYNC_KEY）
python cloud_sync_client.py push --data-js 全量0619/data.js
python cloud_sync_client.py backfill-sold   # 可选，需 XHS_DB_PATH
```

服务器手动入库：

```bash
sudo systemctl start xhs-ingest-report.service
```

---

## 6. API 速查

```bash
curl http://127.0.0.1:8080/api/v1/health

curl -X POST http://127.0.0.1:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"..."}'

curl http://127.0.0.1:8080/api/v1/member/reports \
  -H "Authorization: Bearer <token>"
```

同步（本地 cloud_sync_client）Header: `X-Sync-Key`

---

## 7. Nginx

```bash
sudo cp cloud_deploy/deploy/nginx-xhs-monitor.conf /etc/nginx/sites-available/xhs-monitor.conf
sudo ln -sf /etc/nginx/sites-available/xhs-monitor.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 8. 文件索引

| 文件 | 作用 |
|------|------|
| `database/init_xhs_monitor.sql` | PG schema 一次性初始化 |
| `scripts/host-update.sh` | git pull 后更新 |
| `scripts/run_daily_pipeline.py` | 报告入库（不跑 gen_report） |
| `scripts/sync_report_to_pg.py` | data.js → PG |
| `scripts/backfill_sold_history_pg.py` | sold_history 回补 |
| `cloud_api/main.py` | FastAPI |
| `systemd/xhs-cloud-api.service` | API 服务 |
| `systemd/xhs-ingest-report.timer` | 每日入库 |

---

## 9. 内存预算（2C2G）

| 组件 | 限制 |
|------|------|
| xhs-cloud-api | MemoryMax **256M** |
| vuemonitor | 已有 768M |
| PG | 共享实例，schema 数据量小 |

---

*独立系统 · 不修改 vuemonitor / gen_report*
