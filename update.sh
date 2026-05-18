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

echo -e "  ${CYAN}[1/7]${NC} 拉取最新代码..."
git fetch origin main
git reset --hard origin/main
echo -e "       ${GREEN}✓${NC} 代码已更新"

echo -e "  ${CYAN}[2/7]${NC} 重建 web-user..."
cd "$SCRIPT_DIR/web-user"
npm install --quiet 2>/dev/null
npm run build
if [ ! -f "dist/index.html" ]; then
    echo -e "       ${RED}✗${NC} web-user build failed - dist/index.html not found"
    exit 1
fi
echo -e "       ${GREEN}✓${NC} web-user 已重建"

echo -e "  ${CYAN}[3/7]${NC} 重建 web-admin..."
cd "$SCRIPT_DIR/web-admin"
npm install --quiet 2>/dev/null
npm run build
if [ ! -f "dist/index.html" ]; then
    echo -e "       ${RED}✗${NC} web-admin build failed - dist/index.html not found"
    exit 1
fi
echo -e "       ${GREEN}✓${NC} web-admin 已重建"

echo -e "  ${CYAN}[4/7]${NC} 数据库迁移..."
cd "$SCRIPT_DIR/server"
source .venv/bin/activate
PYTHONPATH="$SCRIPT_DIR/server" alembic upgrade head
echo -e "       ${GREEN}✓${NC} 迁移完成"

echo -e "  ${CYAN}[5/7]${NC} 确保下载目录..."
mkdir -p "$SCRIPT_DIR/deploy/downloads"
if [ ! -f "$SCRIPT_DIR/deploy/downloads/XHS365-Setup-0.1.0.exe" ]; then
    echo -e "       ${RED}⚠${NC} 安装包不存在: deploy/downloads/XHS365-Setup-0.1.0.exe"
    echo -e "       ${CYAN}→${NC} 请从本地上传: scp client/release/XHS365-Setup-0.1.0.exe server:/opt/vuemonitor/deploy/downloads/"
else
    echo -e "       ${GREEN}✓${NC} 安装包就绪"
fi

echo -e "  ${CYAN}[6/7]${NC} 重启服务..."
sudo systemctl restart vuemonitor
sudo systemctl reload nginx
echo -e "       ${GREEN}✓${NC} 服务已重启"

echo -e "  ${CYAN}[7/7]${NC} 健康检查..."
sleep 3
if curl -sf http://127.0.0.1:8000/api/v1/health > /dev/null; then
    echo -e "       ${GREEN}✓${NC} API Server: OK"
else
    echo -e "       ${RED}✗${NC} API Server: FAILED - check: journalctl -u vuemonitor -n 20"
    exit 1
fi

if curl -sf http://127.0.0.1:80 > /dev/null; then
    echo -e "       ${GREEN}✓${NC} Nginx: OK"
else
    echo -e "       ${RED}✗${NC} Nginx: FAILED"
    exit 1
fi

echo ""
echo -e "  ${GREEN}更新完成！${NC}"
echo ""
