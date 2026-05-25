#!/bin/bash
# AIGC START
# intel.xhs365.cn 一键部署（在服务器 /opt/vuemonitor 下整段复制粘贴执行）
set -e
cd /opt/vuemonitor

echo "=== [1/5] 拉取最新代码 ==="
git fetch origin
git reset --hard origin/main

echo "=== [2/5] 写入店铺链接并构建情报前端 ==="
if [ -f config/intel_production.json ]; then
  SHOP_URL=$(python3 -c "import json; print(json.load(open('config/intel_production.json'))['xhs_shop_url'])")
  printf 'VITE_API_BASE_URL=/api/v1\nVITE_XHS_SHOP_URL=%s\n' "$SHOP_URL" > web-intel/.env.production
fi
cd web-intel
npm install --silent 2>/dev/null || npm install
npm run build
cd ..

echo "=== [3/5] 安装 Nginx 情报站配置 ==="
if [ -f nginx/intel.conf ]; then
  sudo cp nginx/intel.conf /etc/nginx/conf.d/intel.conf 2>/dev/null || sudo cp nginx/intel.conf /etc/nginx/sites-available/intel.conf
fi

echo "=== [4/5] 数据库迁移并重启后端 ==="
cd server
if [ -d .venv ]; then source .venv/bin/activate; elif [ -d venv ]; then source venv/bin/activate; fi
alembic upgrade head 2>/dev/null || true
cd ..
sudo systemctl restart vuemonitor

echo "=== [5/5] 重载 Nginx 并健康检查 ==="
sudo nginx -t
sudo nginx -s reload
sleep 3
curl -s http://127.0.0.1:8000/health | python3 -m json.tool || echo "health check failed"
curl -sI http://127.0.0.1/ | head -n 3

echo ""
echo "=== 部署完成 ==="
echo "前端: https://intel.xhs365.cn"
echo "若页面未更新: Ctrl+F5 强制刷新浏览器缓存"
