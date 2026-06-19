# 本地推云工具

在 **gen_report 完成后**运行，**不修改** `gen_report.py`。

## 环境变量

| 变量 | 说明 |
|------|------|
| `XHS_CLOUD_PKG_ROOT` | 指向 `xhs-cloud` 根目录，如 `E:\vuemonitor\xhs-cloud` |
| `XHS_CLOUD_API_URL` | 服务器 API，如 `http://ECS:8080` |
| `XHS_CLOUD_SYNC_KEY` | 与服务器 `/opt/xhs-cloud/.env` 一致 |
| `XHS_DB_PATH` | 可选，本地 SQLite 主库，用于 sold_history 回补 |

## 命令

```bash
python tools/cloud_sync_client.py push --data-js 全量0619\data.js
python tools/cloud_sync_client.py backfill-sold
python tools/cloud_sync_client.py after-report --data-js 全量0619\data.js
```
