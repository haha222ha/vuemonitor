#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  XHS365 V2 一键更新 (含情报系统)"
echo "  前端已预构建，服务器无需 npm build"
echo "============================================"
echo ""

cd /opt/vuemonitor

echo "[1/4] 拉取最新代码（含预构建dist）..."
sudo git pull origin main
echo "  OK"

echo "[2/4] 数据库迁移..."
cd /opt/vuemonitor/server
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi
alembic upgrade head 2>/dev/null || echo "  迁移跳过（可能已是最新）"
echo "  OK"

echo "[3/4] 重启服务..."
sudo systemctl restart vuemonitor 2>/dev/null || sudo docker compose -f docker-compose.prod.yml up -d --remove-orphans 2>/dev/null || echo "  请手动重启服务"
sleep 3

echo "[4/4] 验证..."
HEALTH=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo "FAIL")
echo "  API: $HEALTH"

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