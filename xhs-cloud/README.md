# xhs-cloud — 选品监控独立子系统

| 项 | 说明 |
|----|------|
| **GitHub** | https://github.com/haha222ha/vuemonitor |
| **本目录** | `xhs-cloud/`（与 `server/` 并列，**零侵入**） |
| **服务器** | `/opt/xhs-cloud` · API `:8080` |
| **数据库** | PG 库 `vuemonitor` · schema **`xhs_monitor`** |
| **现网** | `/opt/vuemonitor` · `:8000` **不改** |

## 文档

- [需求规格书 v1.0](./docs/需求规格书_xhs-cloud_v1.md)
- [架构定稿](./docs/架构定稿.md)
- [部署检查清单](./docs/DEPLOY_CHECKLIST.md)
- [部署手册](./cloud_deploy/README.md)

## 本地推云（gen_report 后）

```bash
cd E:\vuemonitor\xhs-cloud
set XHS_CLOUD_PKG_ROOT=E:\vuemonitor\xhs-cloud
set XHS_CLOUD_API_URL=http://你的服务器:8080
set XHS_CLOUD_SYNC_KEY=与服务器一致
python tools\cloud_sync_client.py after-report --data-js D:\path\全量0619\data.js
```

## 服务器首次

```bash
git clone https://github.com/haha222ha/vuemonitor.git /opt/vuemonitor
sudo bash /opt/vuemonitor/xhs-cloud/cloud_deploy/install.sh /opt/vuemonitor/xhs-cloud
```

详见 [docs/DEPLOY_CHECKLIST.md](./docs/DEPLOY_CHECKLIST.md)。

## P0 交付范围

- data.js → PG（监控池 + 日照 + 报告 28 列）
- 会员 zip 下载 API
- git pull 部署脚本
- **不含**：云 gen_report、云 ⑥ 扫描（P1）
