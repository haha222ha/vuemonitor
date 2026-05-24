#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  XHS365 V2 一键更新 (含情报系统)"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /opt/vuemonitor

echo "[1/6] 拉取最新代码..."
git pull origin main
echo "  OK"

echo "[2/6] 构建前端 (web-user)..."
cd /opt/vuemonitor/web-user
npm install --silent 2>/dev/null
npm run build 2>/dev/null
echo "  OK"

echo "[3/6] 构建前端 (web-admin)..."
cd /opt/vuemonitor/web-admin
npm install --silent 2>/dev/null
npm run build 2>/dev/null
echo "  OK"

echo "[4/6] 构建前端 (web-intel)..."
cd /opt/vuemonitor/web-intel
npm install --silent 2>/dev/null
npm run build 2>/dev/null
echo "  OK"

echo "[5/6] 数据库迁移..."
cd /opt/vuemonitor/server
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi
alembic upgrade head 2>/dev/null || echo "  迁移跳过（可能已是最新）"
echo "  OK"

echo "[6/6] 重启服务..."
sudo systemctl restart vuemonitor 2>/dev/null || docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>/dev/null || echo "  请手动重启服务"
sleep 3

echo ""
echo "============================================"
echo "  更新完成!"
echo "============================================"
echo ""
echo "  验证各站点:"
echo "    curl -s -o /dev/null -w '%{http_code}' https://www.xhs365.cn"
echo "    curl -s -o /dev/null -w '%{http_code}' https://admin.xhs365.cn"
echo "    curl -s -o /dev/null -w '%{http_code}' https://api.xhs365.cn/health"
echo ""

if [ -f /etc/nginx/sites-enabled/intel.xhs365.cn ]; then
  echo "  情报系统:"
  echo "    curl -s -o /dev/null -w '%{http_code}' https://intel.xhs365.cn"
  echo ""
fi

echo "============================================"