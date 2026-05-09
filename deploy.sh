#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       XHS365 一键部署工具 v0.1          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ===== 检查 root =====
if [ "$EUID" -ne 0 ]; then
    echo -e "  ${RED}[!] 请使用 sudo 运行此脚本${NC}"
    echo "      sudo bash deploy.sh"
    exit 1
fi

# ===== 1. 安装系统依赖 =====
echo -e "  ${CYAN}[1/6]${NC} 安装系统依赖..."

if command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3.11 python3.11-venv python3-pip \
        postgresql-16 redis-server nginx curl git build-essential \
        python3-dev libpq-dev > /dev/null 2>&1
elif command -v yum &> /dev/null; then
    yum install -y python3.11 python3-pip postgresql16-server redis nginx \
        curl git gcc python3-devel postgresql-devel > /dev/null 2>&1
fi

echo -e "       ${GREEN}✓${NC} 系统依赖安装完成"

# ===== 2. 安装 Node.js =====
echo -e "  ${CYAN}[2/6]${NC} 检查 Node.js..."

if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 18 ]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y nodejs > /dev/null 2>&1
fi
echo -e "       Node.js $(node -v) ${GREEN}✓${NC}"

# ===== 3. 配置 PostgreSQL =====
echo -e "  ${CYAN}[3/6]${NC} 配置 PostgreSQL..."

systemctl enable postgresql > /dev/null 2>&1
systemctl start postgresql > /dev/null 2>&1

su - postgres -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='saas_user'\"" 2>/dev/null | grep -q "1 row" || {
    su - postgres -c "psql -c \"CREATE USER saas_user WITH PASSWORD 'saas_pass';\"" > /dev/null 2>&1
    su - postgres -c "psql -c \"CREATE DATABASE vuemonitor OWNER saas_user;\"" > /dev/null 2>&1
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE vuemonitor TO saas_user;\"" > /dev/null 2>&1
    echo -e "       数据库创建完成"
}

TABLE_COUNT=$(su - postgres -c "psql -d vuemonitor -tAc \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users';\"" 2>/dev/null)
if [ "$TABLE_COUNT" = "0" ]; then
    su - postgres -c "psql -d vuemonitor -f $SCRIPT_DIR/database/schema.sql" > /dev/null 2>&1
    su - postgres -c "psql -d vuemonitor -f $SCRIPT_DIR/database/seed.sql" > /dev/null 2>&1
    echo -e "       Schema 初始化完成"
else
    echo -e "       Schema 已存在，跳过"
fi

# ===== 4. 配置 Redis =====
echo -e "  ${CYAN}[4/6]${NC} 配置 Redis..."
systemctl enable redis-server > /dev/null 2>&1 || systemctl enable redis > /dev/null 2>&1
systemctl start redis-server > /dev/null 2>&1 || systemctl start redis > /dev/null 2>&1
echo -e "       Redis ${GREEN}✓${NC}"

# ===== 5. 生成安全密钥 =====
echo -e "  ${CYAN}[5/6]${NC} 生成安全密钥..."

if [ ! -f "$SCRIPT_DIR/server/.env" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    JWT_REFRESH=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    ENC_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")

    cat > "$SCRIPT_DIR/server/.env" << EOF
APP_NAME=XHS365
APP_VERSION=0.1.0
DEBUG=false
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=saas_user
DB_PASSWORD=saas_pass
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET=${JWT_SECRET}
JWT_REFRESH_SECRET=${JWT_REFRESH}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${ENC_KEY}
AI_DEFAULT_PROVIDER=openai
AI_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
CORS_ORIGINS=["http://localhost","http://localhost:5173","http://localhost:5174"]
EOF
    echo -e "       .env 已生成（含安全密钥）"
else
    echo -e "       .env 已存在，跳过"
fi

# ===== 6. 安装项目依赖 =====
echo -e "  ${CYAN}[6/6]${NC} 安装项目依赖..."

# 服务端
cd "$SCRIPT_DIR/server"
pip3 install poetry -q 2>/dev/null || pip install poetry -q 2>/dev/null
poetry install --no-interaction --no-dev 2>/dev/null || {
    pip3 install fastapi uvicorn[standard] sqlalchemy alembic asyncpg psycopg2-binary \
        pydantic pydantic-settings python-jose[cryptography] python-multipart \
        aiohttp redis apscheduler jinja2 openai langchain-core structlog httpx \
        bcrypt pycryptodome 2>/dev/null
}

# 客户端
cd "$SCRIPT_DIR/client"
npm install --legacy-peer-deps 2>/dev/null

# 管理后台
cd "$SCRIPT_DIR/web-admin"
npm install --legacy-peer-deps 2>/dev/null

# 构建管理后台
cd "$SCRIPT_DIR/web-admin"
npm run build 2>/dev/null

echo -e "       依赖安装完成 ${GREEN}✓${NC}"

# ===== 配置 systemd 服务 =====
echo ""
echo -e "  ${CYAN}配置系统服务...${NC}"

cat > /etc/systemd/system/vuemonitor.service << EOF
[Unit]
Description=XHS365 API Server
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR/server
ExecStart=$(which poetry 2>/dev/null || echo /usr/local/bin/poetry) run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload > /dev/null 2>&1
systemctl enable vuemonitor > /dev/null 2>&1
systemctl restart vuemonitor > /dev/null 2>&1

# ===== 配置 Nginx =====
cat > /etc/nginx/sites-available/vuemonitor << 'NGINX'
server {
    listen 80;
    server_name _;

    # 管理后台
    location / {
        root /opt/vuemonitor/web-admin/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/vuemonitor /etc/nginx/sites-enabled/ 2>/dev/null
rm -f /etc/nginx/sites-enabled/default 2>/dev/null
nginx -t 2>/dev/null && systemctl restart nginx 2>/dev/null

# ===== 完成 =====
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          🎉 部署完成！                    ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  管理后台:   http://${SERVER_IP}          ║"
echo "  ║  API 文档:   http://${SERVER_IP}/docs    ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  服务管理:                                ║"
echo "  ║    systemctl status vuemonitor           ║"
echo "  ║    systemctl restart vuemonitor          ║"
echo "  ║    journalctl -u vuemonitor -f           ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  如需配置 AI，请编辑:                     ║"
echo "  ║  ${SCRIPT_DIR}/server/.env               ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
