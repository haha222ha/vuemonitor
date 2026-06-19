# 已弃用 systemd 单元（2G 最小部署请勿 enable）

| 文件 | 原因 |
|------|------|
| `xhs-daemon.service` | 云侧 ⑥ 扫描，P1+；2G 不默认启用 |
| `xhs-daily-report.service` | 旧版含 gen_report 调用，已由 `xhs-ingest-report` 替代 |
| `xhs-daily-report.timer` | 同上 |
| `xhs-weekly-report.*` | 周报 P1 占位 |

**当前应启用：**

- `xhs-cloud-api.service`
- `xhs-ingest-report.timer`
