# XHS365 上线验收清单

## 自动化（推荐）

| 步骤 | 命令 | 环境 |
|------|------|------|
| 本地发版 | `.\scripts\local-release.ps1 -Message "..."` | Windows 开发机 |
| 主机更新 | 见 `HOST_UPDATE.md` 一行命令 | 2G 生产机 |
| API 冒烟 | `python scripts/api_smoke.py --base-url http://127.0.0.1:8000` | 主机 |
| 黄金路径 E2E | `python scripts/e2e_api_flow.py --base-url http://127.0.0.1:8000` | 主机 |
| 外网验收 | `bash scripts/verify_production.sh` | 主机 |
| 创建 Admin | `cd server && source .venv/bin/activate && python ../scripts/seed_admin.py` | 主机一次 |

`host-update.sh` 已集成：健康检查 → api_smoke → e2e（--skip-ai）→ verify_production。

## 手工浏览器（Sprint 1）

- [ ] www 注册 / 登录
- [ ] 添加监控商品
- [ ] 触发 AI 基础分析（需 DEEPSEEK_API_KEY）
- [ ] 创建监控规则并查看通知
- [ ] admin 后台登录（seed_admin 后）

## GitHub 自动部署（可选）

仓库 Settings → Secrets：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`

push `main` 后 workflow `Host Auto Update` 会 SSH 执行 `host-update.sh`。
