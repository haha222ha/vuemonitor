#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "  ${CYAN}XHS365 日常更新${NC}"
echo ""

echo -e "  ${CYAN}[1/4]${NC} 拉取最新代码..."
git fetch origin main
git reset --hard origin/main
echo -e "       ${GREEN}✓${NC} 代码已更新"

echo -e "  ${CYAN}[2/4]${NC} 重建 Web 前端..."
cd "$SCRIPT_DIR/web-user"
npm install --quiet 2>/dev/null
npm run build 2>/dev/null
echo -e "       ${GREEN}✓${NC} 前端已重建"

echo -e "  ${CYAN}[3/4]${NC} 数据库迁移..."
cd "$SCRIPT_DIR/server"
source .venv/bin/activate
PYTHONPATH="$SCRIPT_DIR/server" alembic upgrade head
echo -e "       ${GREEN}✓${NC} 迁移完成"

echo -e "  ${CYAN}[4/4]${NC} 重启服务..."
sudo systemctl restart vuemonitor
sleep 2
if systemctl is-active --quiet vuemonitor; then
    echo -e "       ${GREEN}✓${NC} 服务已重启"
else
    echo -e "       ${RED}✗${NC} 服务启动失败，请检查: journalctl -u vuemonitor -n 20"
fi

echo ""
echo -e "  ${GREEN}更新完成！${NC}"
echo ""
