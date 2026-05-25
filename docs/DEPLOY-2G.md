# 2G2H 主机 Git 部署指南

适用于：**开发机 push → 生产机 pull**，主机约 **2GB RAM / 2 CPU**。

## 原则

| 操作 | 开发机 (Windows) | 2G 主机 |
|------|------------------|---------|
| `npm run build` | ✅ 执行 | ❌ 禁止（易 OOM） |
| `git push` | ✅ | — |
| `git pull` / `host-update.sh` | — | ✅ |
| `alembic upgrade` | 可选 | ✅ |
| `uvicorn --workers` | — | **1** |

## 一键流程

### 1. 开发机（每次发版）

```powershell
cd D:\vuemonitor
.\scripts\local-release.ps1 -Message "fix: 你的说明"
```

脚本会：构建 web-user / web-admin / web-intel → 跑关键测试 → commit → **push origin/main**。

### 2. 生产机（SSH 登录后，复制下面这一行）

```bash
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```

### 3. 首次安装 systemd（仅一次）

```bash
sudo cp /opt/vuemonitor/deploy/systemd/vuemonitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vuemonitor
```

## 可选：主机 cron 自动 pull（慎用）

```cron
# 每天 4:00 自动更新（需已配置 git 凭据）
0 4 * * * cd /opt/vuemonitor && git fetch origin main && [ $(git rev-parse HEAD) != $(git rev-parse origin/main) ] && bash scripts/host-update.sh >> /var/log/vuemonitor-update.log 2>&1
```

## 内存仍不足时

```bash
# 增加 1G swap（推荐）
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Docker 模式（2G）

若使用 `docker-compose.prod.yml`，已限制：server 512M、postgres 384M、redis 128M、`UVICORN_WORKERS=1`。

```bash
export UVICORN_WORKERS=1
docker compose -f docker-compose.prod.yml up -d --no-build
```

不要用 `deploy.sh` 的 `--no-cache` 全量构建，2G 会卡死。
