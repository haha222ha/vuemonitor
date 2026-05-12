#!/bin/bash
set -e

# ============================================================
#  XHS365 服务器端一键部署脚本（GitHub Pull 模式）
#  在服务器上执行：bash deploy-server.sh
# ============================================================

# ====== 修改这里 ======
DOMAIN="your-domain.com"                # 你的域名
REPO_URL="https://github.com/你的用户名/vuemonitor.git"  # GitHub 仓库地址
DB_PASSWORD="修改为强密码"                # PostgreSQL 密码
REDIS_PASSWORD="修改为强密码"             # Redis 密码
JWT_SECRET=""                            # 留空自动生成
JWT_REFRESH_SECRET=""                    # 留空自动生成
ENCRYPTION_KEY=""                        # 留空自动生成
DEEPSEEK_API_KEY=""                      # DeepSeek API Key（可选）
# ======================

[ -z "$JWT_SECRET" ] && JWT_SECRET=$(openssl rand -hex 32)
[ -z "$JWT_REFRESH_SECRET" ] && JWT_REFRESH_SECRET=$(openssl rand -hex 32)
[ -z "$ENCRYPTION_KEY" ] && ENCRYPTION_KEY=$(openssl rand -hex 16)

DEPLOY_DIR="/opt/xhs365"
REPO_DIR="$DEPLOY_DIR/vuemonitor"

echo ""
echo "============================================"
echo "  XHS365 服务器端一键部署（GitHub Pull）"
echo "============================================"
echo "  域名:   $DOMAIN"
echo "  仓库:   $REPO_URL"
echo "  目录:   $DEPLOY_DIR"
echo "============================================"
echo ""

# ---------- [1] 安装依赖 ----------
echo "[1/9] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq git docker.io docker-compose-plugin nginx certbot python3-certbot-nginx nodejs npm > /dev/null 2>&1
systemctl enable docker
systemctl start docker
echo "  Docker + Nginx + Git 已安装"

# ---------- [2] 克隆仓库 ----------
echo "[2/9] 拉取代码..."
mkdir -p $DEPLOY_DIR
if [ -d "$REPO_DIR/.git" ]; then
    cd $REPO_DIR && git pull origin main
    echo "  代码已更新"
else
    git clone $REPO_URL $REPO_DIR
    echo "  代码已克隆"
fi

# ---------- [3] 创建目录 ----------
echo "[3/9] 创建部署目录..."
mkdir -p $DEPLOY_DIR/downloads/windows
mkdir -p $DEPLOY_DIR/downloads/macos
mkdir -p $DEPLOY_DIR/downloads/linux
mkdir -p $DEPLOY_DIR/backups

# ---------- [4] 构建 Web 前端 ----------
echo "[4/9] 构建 Web 前端..."
cd $REPO_DIR/web-user
npm install --quiet 2>/dev/null
npm run build 2>/dev/null
mkdir -p $DEPLOY_DIR/web-user/dist
cp -r dist/* $DEPLOY_DIR/web-user/dist/
echo "  Web 前端已构建"

# ---------- [5] 复制客户端安装包 ----------
echo "[5/9] 复制客户端安装包..."
if [ -d "$REPO_DIR/deploy/downloads" ]; then
    cp -rn $REPO_DIR/deploy/downloads/* $DEPLOY_DIR/downloads/ 2>/dev/null || true
    echo "  安装包已复制"
else
    echo "  [INFO] 暂无客户端安装包，后续构建后复制"
fi

# ---------- [6] 生成 .env ----------
echo "[6/9] 生成 .env 配置..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
cat > $DEPLOY_DIR/.env << ENVEOF
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
LOG_FORMAT=json

DB_HOST=postgres
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=saas_user
DB_PASSWORD=$DB_PASSWORD
DB_POOL_SIZE=20

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

JWT_SECRET=$JWT_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ENCRYPTION_KEY=$ENCRYPTION_KEY

CORS_ORIGINS=["https://$DOMAIN"]

DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY

DOWNLOADS_DIR=$DEPLOY_DIR/downloads
ENVEOF
    echo "  .env 已生成"
else
    echo "  .env 已存在，跳过（如需更新请手动编辑 $DEPLOY_DIR/.env）"
fi

# ---------- [7] 生成 docker-compose.yml ----------
echo "[7/9] 生成 Docker Compose 配置..."
cat > $DEPLOY_DIR/docker-compose.yml << COMPOSEEOF
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: vuemonitor
      POSTGRES_USER: saas_user
      POSTGRES_PASSWORD: $DB_PASSWORD
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U saas_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass $REDIS_PASSWORD
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "$REDIS_PASSWORD", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  server:
    build:
      context: $REPO_DIR/server
      dockerfile: Dockerfile
    restart: always
    ports:
      - "127.0.0.1:8000:8000"
    env_file:
      - $DEPLOY_DIR/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - $DEPLOY_DIR/downloads:/var/www/xhs365/downloads
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 2G

  db-backup:
    image: postgres:16-alpine
    restart: always
    environment:
      PGPASSWORD: $DB_PASSWORD
    volumes:
      - $DEPLOY_DIR/backups:/backups
    entrypoint: >
      sh -c "while true; do
        pg_dump -h postgres -U saas_user vuemonitor | gzip > /backups/backup_\$$(date +%Y%m%d_%H%M%S).sql.gz
        find /backups -name '*.sql.gz' -mtime +7 -delete
        sleep 86400
      done"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
  redisdata:
COMPOSEEOF

# ---------- [8] 启动服务 ----------
echo "[8/9] 启动 Docker 服务..."
cd $DEPLOY_DIR
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

echo "  等待数据库就绪..."
sleep 15
docker compose exec -T server alembic upgrade head 2>/dev/null || docker-compose exec -T server alembic upgrade head

# ---------- [9] 配置 Nginx + SSL ----------
echo "[9/9] 配置 Nginx..."
cp $REPO_DIR/deploy/nginx/xhs365.conf /etc/nginx/conf.d/xhs365.conf 2>/dev/null || true
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/conf.d/xhs365.conf 2>/dev/null || true
sed -i "s|/var/www/xhs365|$DEPLOY_DIR|g" /etc/nginx/conf.d/xhs365.conf 2>/dev/null || true

nginx -t 2>/dev/null && systemctl reload nginx || echo "[WARN] Nginx 配置需检查"

if [ "$DOMAIN" != "your-domain.com" ]; then
    echo "  正在申请 SSL 证书..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect 2>/dev/null || echo "[WARN] SSL 申请失败，请手动: certbot --nginx -d $DOMAIN"
fi

# ---------- 验证 ----------
echo ""
echo "============================================"
echo "  部署验证"
echo "============================================"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "FAIL")
echo "  服务端: $HEALTH"
VERSION=$(curl -s http://localhost:8000/api/v1/system/client/latest 2>/dev/null || echo "FAIL")
echo "  版本API: $VERSION"

echo ""
echo "============================================"
echo "  部署完成!"
echo "============================================"
echo ""
echo "  首页:     https://$DOMAIN"
echo "  下载页:   https://$DOMAIN/download"
echo "  API文档:  https://$DOMAIN/docs"
echo "  管理后台: https://$DOMAIN/dashboard"
echo ""
echo "  日常更新流程:"
echo "    1. 本地修改代码 → git push origin main"
echo "    2. 服务器执行: bash $DEPLOY_DIR/vuemonitor/deploy/update.sh"
echo ""