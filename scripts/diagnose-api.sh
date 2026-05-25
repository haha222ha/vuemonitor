#!/bin/bash
# API 服务一键诊断（2G 主机）
set -euo pipefail

echo "========== vuemonitor 诊断 =========="
echo ""

echo "--- systemctl status ---"
sudo systemctl status vuemonitor --no-pager -l 2>/dev/null || echo "vuemonitor 服务未安装"

echo ""
echo "--- 最近日志 (40 行) ---"
sudo journalctl -u vuemonitor -n 40 --no-pager 2>/dev/null || true

echo ""
echo "--- 8000 端口 ---"
ss -lntp 2>/dev/null | grep ':8000' || netstat -lntp 2>/dev/null | grep ':8000' || echo "8000 未监听"

echo ""
echo "--- .env 关键项（不显示密码值）---"
ENV_FILE="/opt/vuemonitor/server/.env"
if [ -f "$ENV_FILE" ]; then
  for key in JWT_SECRET JWT_REFRESH_SECRET ENCRYPTION_KEY DB_PASSWORD DB_HOST REDIS_HOST REDIS_PASSWORD DEBUG; do
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
      val=$(grep "^${key}=" "$ENV_FILE" | cut -d= -f2- | head -c 8)
      if [ -z "$val" ] || [ "$val" = "change-me" ]; then
        echo "  $key = (空或默认值) ⚠"
      else
        echo "  $key = 已设置 ✓"
      fi
    else
      echo "  $key = 缺失 ✗"
    fi
  done
else
  echo "  未找到 $ENV_FILE ✗"
fi

echo ""
echo "--- 依赖服务 ---"
systemctl is-active postgresql 2>/dev/null && echo "postgresql: active" || echo "postgresql: inactive"
systemctl is-active redis-server 2>/dev/null && echo "redis-server: active" || systemctl is-active redis 2>/dev/null && echo "redis: active" || echo "redis: inactive"

echo ""
echo "--- curl /health ---"
curl -sv --max-time 5 http://127.0.0.1:8000/health 2>&1 | tail -25 || true

echo ""
echo "========== 结束 =========="
