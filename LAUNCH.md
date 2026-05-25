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

完成后在主机跑完整 Sprint（含 AI）：

```bash
cd /opt/vuemonitor/server && source .venv/bin/activate
RUN_AI=1 ADMIN_EMAIL=admin@xhs365.cn ADMIN_PASSWORD='你的密码' \
  bash /opt/vuemonitor/scripts/run_sprints.sh
```

详见 [docs/SPRINT1-2.md](docs/SPRINT1-2.md)。

Windows 打包：`client\scripts\package-win.ps1`
