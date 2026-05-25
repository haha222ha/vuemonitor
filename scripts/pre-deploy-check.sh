#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

step() { echo -e "\n${YELLOW}>>> $1${NC}"; }
ok() { echo -e "  ${GREEN}[OK]${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; ((WARN++)); }

echo "============================================"
echo "  XHS365 生产部署前检查"
echo "============================================"

step "1. 环境文件检查"
if [ -f ".env" ]; then
    ok ".env 文件存在"
    python scripts/generate_secrets.py --check .env
else
    fail ".env 文件不存在，请运行: python scripts/generate_secrets.py > .env"
fi

step "2. Docker Secrets 检查"
SECRETS_DIR="./secrets"
REQUIRED_SECRETS="db_password redis_password jwt_secret jwt_refresh_secret encryption_key backup_encryption_key"
if [ -d "$SECRETS_DIR" ]; then
    for s in $REQUIRED_SECRETS; do
        if [ -f "$SECRETS_DIR/${s}.txt" ] && [ -s "$SECRETS_DIR/${s}.txt" ]; then
            ok "secrets/${s}.txt"
        else
            fail "secrets/${s}.txt 缺失或为空"
        fi
    done
else
    fail "secrets/ 目录不存在，请运行: python scripts/generate_secrets.py --docker-secrets"
fi

step "3. SSL 证书检查"
for cert in /etc/nginx/ssl/xhs365.cn.pem /etc/nginx/ssl/xhs365.cn.key; do
    if [ -f "$cert" ]; then
        ok "$cert 存在"
    else
        warn "$cert 不存在（首次部署需上传）"
    fi
done

step "4. 数据库连接检查"
if command -v psql &>/dev/null; then
    if PGPASSWORD="${DB_PASSWORD:-}" psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-saas_user}" -d "${DB_NAME:-vuemonitor}" -c "SELECT 1" &>/dev/null; then
        ok "数据库连接正常"
    else
        fail "数据库连接失败"
    fi
else
    warn "psql 未安装，跳过数据库连接检查"
fi

step "5. Redis 连接检查"
if command -v redis-cli &>/dev/null; then
    if redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" -a "${REDIS_PASSWORD:-}" ping &>/dev/null; then
        ok "Redis 连接正常"
    else
        fail "Redis 连接失败"
    fi
else
    warn "redis-cli 未安装，跳过 Redis 连接检查"
fi

step "6. Docker 环境检查"
if command -v docker &>/dev/null; then
    ok "Docker 已安装: $(docker --version)"
    if docker info &>/dev/null; then
        ok "Docker daemon 运行中"
    else
        fail "Docker daemon 未运行"
    fi
else
    fail "Docker 未安装"
fi

if command -v docker-compose &>/dev/null || docker compose version &>/dev/null; then
    ok "Docker Compose 已安装"
else
    fail "Docker Compose 未安装"
fi

step "7. 端口占用检查"
for port in 8000 5432 6379 80 443; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        warn "端口 $port 已被占用"
    else
        ok "端口 $port 可用"
    fi
done

step "8. 磁盘空间检查"
AVAIL_GB=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$AVAIL_GB" -gt 10 ]; then
    ok "磁盘剩余 ${AVAIL_GB}GB"
else
    fail "磁盘剩余仅 ${AVAIL_GB}GB，建议至少 10GB"
fi

step "9. 前端构建产物检查"
for dir in web-user/dist web-admin/dist; do
    if [ -d "$dir" ] && [ "$(ls -A $dir 2>/dev/null)" ]; then
        SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
        ok "$dir 存在 ($SIZE)"
    else
        warn "$dir 不存在，需运行: cd $(dirname $dir) && npm run build"
    fi
done

step "10. Alembic 迁移状态检查"
if [ -f "server/alembic.ini" ]; then
    cd server
    if python -m alembic current 2>/dev/null; then
        ok "Alembic 迁移状态可查询"
    else
        warn "无法获取 Alembic 迁移状态（可能需要数据库连接）"
    fi
    cd ..
else
    warn "alembic.ini 未找到"
fi

echo ""
echo "============================================"
echo -e "  检查结果: ${GREEN}${PASS} 通过${NC} | ${RED}${FAIL} 失败${NC} | ${YELLOW}${WARN} 警告${NC}"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    echo -e "  ${RED}存在失败项，请修复后再部署！${NC}"
    exit 1
else
    echo -e "  ${GREEN}所有必要检查通过，可以部署！${NC}"
    exit 0
fi
