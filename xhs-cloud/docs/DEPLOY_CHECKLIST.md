# 服务器部署检查清单（完整版）

仓库：https://github.com/haha222ha/vuemonitor  
选品目录：`xhs-cloud/`  
部署路径：`/opt/xhs-cloud`

---

## 一、首次部署

- [ ] `git clone https://github.com/haha222ha/vuemonitor.git /opt/vuemonitor`
- [ ] `sudo bash /opt/vuemonitor/xhs-cloud/cloud_deploy/install.sh /opt/vuemonitor/xhs-cloud`
- [ ] 执行 PG 初始化：
  ```bash
  sudo -u postgres psql -d vuemonitor -f /opt/xhs-cloud/cloud_deploy/database/init_xhs_monitor.sql
  ```
- [ ] 配置 `/opt/xhs-cloud/.env`
- [ ] `sudo systemctl start xhs-cloud-api && sudo systemctl enable xhs-cloud-api`
- [ ] `sudo systemctl enable xhs-ingest-report.timer`
- [ ] 可选 enable：`xhs-daily-report.timer` / `xhs-weekly-report.timer` / `xhs-monthly-report.timer`
- [ ] `curl http://127.0.0.1:8080/api/v1/health`

---

## 二、本地数据整理（push 前）

```powershell
cd E:\vuemonitor\xhs-cloud
python tools/prepare_server_sync.py `
  --source "C:\Users\Administrator\Desktop\每日选品全量数据" `
  --main-db "D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db"
# 产出:
#   server_sync_pack/historical_reports/  — 6 份去重日报
#   server_sync_pack/monitor_pool/        — 日增量>0 商品 sold_history（~4.2MB gzip）
# 编辑 server_sync_pack/scp_upload.ps1 填 ECS IP 后上传
```

---

## 三、首次数据（服务器 import）

**A — 历史冷启动（推荐，用本地整理好的包）：**
```bash
# 本地先: python tools/prepare_server_sync.py && scp_upload.ps1
cd /opt/xhs-cloud
sudo -u admin env PYTHONPATH=/opt/xhs-cloud \
  ./venv/bin/python cloud_deploy/scripts/import_historical_reports.py \
  --root /opt/xhs-cloud/data/import_batch/historical_reports
sudo -u admin env PYTHONPATH=/opt/xhs-cloud \
  ./venv/bin/python cloud_deploy/scripts/import_monitor_pool_offline.py \
  --pack /opt/xhs-cloud/data/import_batch/monitor_pool
```

**B — 单日报 scp + ingest：**
```bash
scp -r 全量MMDD user@ECS:/opt/xhs-cloud/data/incoming/
sudo systemctl start xhs-ingest-report.service
```

**C — 本地 API 推：**
```bash
python tools/cloud_sync_client.py push --data-js 全量MMDD\data.js
python tools/cloud_sync_client.py backfill-sold   # 可选
```

**D — 云端 PG 生成（需 PG 已有 sold_daily / daily_items）：**
```bash
sudo systemctl start xhs-daily-report.service
# 或
python cloud_deploy/scripts/run_full_pipeline.py full
```

---

## 三、验收

- [ ] `GET /api/v1/sync/status` + `X-Sync-Key` → `monitor_pool_active` > 0
- [ ] 会员登录 → 下载 zip 含 `data.js` + `index_with_gr.html`
- [ ] `SELECT COUNT(*) FROM xhs_monitor.report_daily_items;` 有数据
- [ ] 周报/月报：`SELECT * FROM xhs_monitor.report_archives WHERE archive_type LIKE 'member_%';`
- [ ] vuemonitor `:8000` 仍正常

---

## 四、日常 pull

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
rsync -a /opt/vuemonitor/xhs-cloud/ /opt/xhs-cloud/ \
  --delete --exclude data --exclude venv --exclude .env
cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
```

---

## 五、禁止事项

- 不修改 vuemonitor `server/`、`gen_report.py`
- 不把 `.env` 提交 git
- 不给 `xhs_monitor_user` 写 `public` 表权限
