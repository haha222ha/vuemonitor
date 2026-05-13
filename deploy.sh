#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "  ========================================"
echo "  |     XHS365 一键部署工具 v1.0        |"
echo "  ========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-docker}"

usage() {
    echo "Usage: $0 [docker|native]"
    echo "  docker  - Docker Compose 部署 (默认)"
    echo "  native  - 原生部署 (systemd)"
    exit 1
}

if [ "$MODE" != "docker" ] && [ "$MODE" != "native" ]; then
    usage
fi

echo -e "  部署模式: ${CYAN}${MODE}${NC}"
echo ""

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "  ${RED}[!] Docker 未安装，正在安装...${NC}"
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker && systemctl start docker
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo -e "  ${RED}[!] Docker Compose 未安装${NC}"
        exit 1
    fi
    echo -e "  Docker $(docker --version | awk '{print $3}') ${GREEN}OK${NC}"
}

generate_env() {
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo -e "  .env 已存在，跳过生成"
        echo -e "  如需重新生成，请先删除 .env 文件"
        return
    fi

    echo -e "  ${CYAN}[*]${NC} 生成生产环境变量..."
    python3 "$SCRIPT_DIR/scripts/generate_secrets.py" > "$SCRIPT_DIR/.env"

    echo ""
    echo -e "  ${YELLOW}[!] 请编辑 .env 文件，填写以下必填项:${NC}"
    echo -e "      - OPENAI_API_KEY / DEEPSEEK_API_KEY"
    echo -e "      - SMTP_HOST / SMTP_USER / SMTP_PASSWORD"
    echo ""
    read -p "  是否现在编辑 .env? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-vi} "$SCRIPT_DIR/.env"
    fi
}

check_env_security() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo -e "  ${RED}[!] .env 文件不存在${NC}"
        return 1
    fi
    python3 "$SCRIPT_DIR/scripts/generate_secrets.py" --check "$SCRIPT_DIR/.env"
}

deploy_docker() {
    echo -e "  ${CYAN}[1/4]${NC} 检查 Docker 环境..."
    check_docker

    echo -e "  ${CYAN}[2/4]${NC} 生成环境变量..."
    generate_env

    echo -e "  ${CYAN}[3/4]${NC} 安全检查..."
    check_env_security

    echo -e "  ${CYAN}[4/4]${NC} 启动服务..."
    cd "$SCRIPT_DIR"

    COMPOSE_CMD="docker-compose"
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    fi

    $COMPOSE_CMD -f docker-compose.prod.yml build --no-cache
    $COMPOSE_CMD -f docker-compose.prod.yml up -d

    echo -e "  等待服务启动..."
    sleep 15

    echo ""
    echo -e "  ${CYAN}健康检查...${NC}"
    for i in $(seq 1 6); do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "  API Server: ${GREEN}OK${NC}"
            break
        fi
        if [ $i -eq 6 ]; then
            echo -e "  API Server: ${RED}FAILED${NC}"
            echo -e "  查看日志: $COMPOSE_CMD -f docker-compose.prod.yml logs server"
        fi
        sleep 5
    done

    echo ""
    echo "  ========================================"
    echo "  |          部署完成!                    |"
    echo "  ========================================"
    echo ""
    echo "  API:       http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  用户前端:  http://localhost:5174"
    echo "  管理后台:  http://localhost:3000"
    echo "  Grafana:   http://localhost:3000 (admin/admin)"
    echo ""
    echo "  管理命令:"
    echo "    $COMPOSE_CMD -f docker-compose.prod.yml ps"
    echo "    $COMPOSE_CMD -f docker-compose.prod.yml logs -f server"
    echo "    $COMPOSE_CMD -f docker-compose.prod.yml down"
    echo ""
}

deploy_native() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "  ${RED}[!] 原生部署请使用 sudo 运行${NC}"
        exit 1
    fi

    echo -e "  ${CYAN}[1/6]${NC} 安装系统依赖..."
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq python3.11 python3.11-venv python3-pip \
            postgresql-16 redis-server nginx curl git build-essential \
            python3-dev libpq-dev > /dev/null 2>&1
    fi
    echo -e "       ${GREEN}OK${NC}"

    echo -e "  ${CYAN}[2/6]${NC} 检查 Node.js..."
    if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 18 ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y nodejs > /dev/null 2>&1
    fi
    echo -e "       Node.js $(node -v) ${GREEN}OK${NC}"

    echo -e "  ${CYAN}[3/6]${NC} 配置 PostgreSQL..."
    systemctl enable postgresql > /dev/null 2>&1
    systemctl start postgresql > /dev/null 2>&1

    su - postgres -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='saas_user'\"" 2>/dev/null | grep -q "1 row" || {
        DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
        su - postgres -c "psql -c \"CREATE USER saas_user WITH PASSWORD '${DB_PASS}';\"" > /dev/null 2>&1
        su - postgres -c "psql -c \"CREATE DATABASE vuemonitor OWNER saas_user;\"" > /dev/null 2>&1
        su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE vuemonitor TO saas_user;\"" > /dev/null 2>&1
        echo -e "       数据库创建完成 (密码已自动生成)"
    }

    TABLE_COUNT=$(su - postgres -c "psql -d vuemonitor -tAc \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users';\"" 2>/dev/null)
    if [ "$TABLE_COUNT" = "0" ]; then
        su - postgres -c "psql -d vuemonitor -f $SCRIPT_DIR/database/schema.sql" > /dev/null 2>&1
        su - postgres -c "psql -d vuemonitor -f $SCRIPT_DIR/database/seed.sql" > /dev/null 2>&1
        echo -e "       Schema 初始化完成"
    else
        echo -e "       Schema 已存在，跳过"
    fi

    echo -e "  ${CYAN}[4/6]${NC} 配置 Redis..."
    systemctl enable redis-server > /dev/null 2>&1 || systemctl enable redis > /dev/null 2>&1
    systemctl start redis-server > /dev/null 2>&1 || systemctl start redis > /dev/null 2>&1
    echo -e "       Redis ${GREEN}OK${NC}"

    echo -e "  ${CYAN}[5/6]${NC} 生成安全密钥..."
    generate_env

    echo -e "  ${CYAN}[6/6]${NC} 安装项目依赖..."
    cd "$SCRIPT_DIR/server"
    pip3 install -r requirements.txt -q 2>/dev/null

    cd "$SCRIPT_DIR/web-user"
    npm install --legacy-peer-deps 2>/dev/null && npm run build 2>/dev/null

    cd "$SCRIPT_DIR/web-admin"
    npm install --legacy-peer-deps 2>/dev/null && npm run build 2>/dev/null
    echo -e "       ${GREEN}OK${NC}"

    echo -e "  ${CYAN}配置 systemd 服务...${NC}"
    cat > /etc/systemd/system/vuemonitor.service << EOF
[Unit]
Description=XHS365 API Server
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR/server
ExecStart=$(which uvicorn 2>/dev/null || echo /usr/local/bin/uvicorn) app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload > /dev/null 2>&1
    systemctl enable vuemonitor > /dev/null 2>&1
    systemctl restart vuemonitor > /dev/null 2>&1

    echo ""
    echo "  ========================================"
    echo "  |          部署完成!                    |"
    echo "  ========================================"
    echo ""
    echo "  systemctl status vuemonitor"
    echo "  journalctl -u vuemonitor -f"
    echo ""
}

if [ "$MODE" = "docker" ]; then
    deploy_docker
else
    deploy_native
fi
