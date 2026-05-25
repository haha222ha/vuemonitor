# XHS365 快速上线

## 开发机（每次发版）

```powershell
cd D:\vuemonitor
.\scripts\local-release.ps1 -Message "feat: 说明"
```

## 生产机（每次 pull，复制一行）

```bash
cd /opt/vuemonitor && sudo rm -rf client/node_modules 2>/dev/null; git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
```

## 首次：创建管理员

```bash
cd /opt/vuemonitor/server && source .venv/bin/activate && python ../scripts/seed_admin.py --email admin@xhs365.cn --password '你的强密码'
```

## 配置 SMTP（`server/.env`）

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=noreply@xhs365.cn
```

## 配置 AI（`server/.env`）

```env
DEEPSEEK_API_KEY=sk-...
```

完成后去掉 E2E 的 `--skip-ai`（host-update 内默认 skip-ai，有 Key 可手动跑完整 E2E）。
