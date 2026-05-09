#!/bin/bash

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       XHS365 服务启动                 ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# 检查 Redis
redis-cli ping > /dev/null 2>&1 || {
    echo -e "  ${CYAN}启动 Redis...${NC}"
    sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null
}

# 检查 .env
[ ! -f "$SCRIPT_DIR/server/.env" ] && {
    cp "$SCRIPT_DIR/server/.env.example" "$SCRIPT_DIR/server/.env"
    echo -e "  ${CYAN}已创建 server/.env，请编辑配置${NC}"
}

# 启动服务端
echo -e "  ${CYAN}启动 API 服务 (端口 8000)...${NC}"
cd "$SCRIPT_DIR/server"
nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/vuemonitor-api.log 2>&1 &
echo $! > /tmp/vuemonitor-api.pid
sleep 2

# 启动客户端
echo -e "  ${CYAN}启动客户端 (端口 5173)...${NC}"
cd "$SCRIPT_DIR/client"
nohup npm run dev > /tmp/vuemonitor-client.log 2>&1 &
echo $! > /tmp/vuemonitor-client.pid
sleep 2

# 启动管理后台
echo -e "  ${CYAN}启动管理后台 (端口 5174)...${NC}"
cd "$SCRIPT_DIR/web-admin"
nohup npm run dev > /tmp/vuemonitor-admin.log 2>&1 &
echo $! > /tmp/vuemonitor-admin.pid

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          ${GREEN}✓ 全部启动完成${NC}                   ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  API 文档:   http://localhost:8000/docs  ║"
echo "  ║  客户端:     http://localhost:5173       ║"
echo "  ║  管理后台:   http://localhost:5174       ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  停止: bash start.sh --stop             ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
