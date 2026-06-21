#!/usr/bin/env bash
# 服务器一键：开启本地 Agent 上传接口
# 用法: bash /opt/vuemonitor/xhs-cloud/scripts/setup_agent_api.sh
set -euo pipefail

ENV_FILE="${XHS_ENV_FILE:-/opt/xhs-cloud/.env}"
DEPLOY_SRC="${DEPLOY_SRC:-/opt/vuemonitor/xhs-cloud/cloud_deploy}"
DEPLOY_DST="${DEPLOY_DST:-/opt/xhs-cloud/cloud_deploy}"

echo "=== 1/4 同步代码 ==="
if [[ -d /opt/vuemonitor/.git ]]; then
  (cd /opt/vuemonitor && git pull) || true
fi
rsync -a "$DEPLOY_SRC/" "$DEPLOY_DST/" --delete

echo "=== 2/4 写入 Agent Key ==="
touch "$ENV_FILE"
if grep -q '^XHS_LOCAL_AGENT_KEY=' "$ENV_FILE" 2>/dev/null; then
  KEY=$(grep '^XHS_LOCAL_AGENT_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2-)
  echo "已有密钥，保持不变"
else
  KEY=$(openssl rand -hex 24 2>/dev/null || head -c 48 /dev/urandom | xxd -p -c 48)
  echo "XHS_LOCAL_AGENT_KEY=$KEY" >> "$ENV_FILE"
  echo "已生成新密钥"
fi

echo "=== 3/4 启动 cloud-api ==="
sudo systemctl enable xhs-cloud-api 2>/dev/null || true
sudo systemctl restart xhs-cloud-api
sleep 2

echo "=== 4/4 健康检查 ==="
curl -sf "http://127.0.0.1:${XHS_CLOUD_PORT:-8080}/api/v1/health" | head -c 80
echo ""

echo ""
echo "============================================"
echo "  服务器好了！把下面这行复制到你家里电脑："
echo ""
echo "  XHS_LOCAL_AGENT_KEY=$KEY"
echo ""
echo "  然后在本机运行 setup_local_agent.ps1"
echo "============================================"
