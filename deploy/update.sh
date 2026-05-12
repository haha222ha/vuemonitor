#!/bin/bash
set -e

# ============================================================
#  XHS365 日常更新脚本（GitHub Pull 后执行）
#  服务器执行：bash update.sh
#
#  完整更新流程：
#    1. 本地: git add . && git commit -m "xxx" && git push origin main
#    2. 服务器: bash /opt/xhs365/vuemonitor/deploy/update.sh
# ============================================================

DEPLOY_DIR="/opt/xhs365"
REPO_DIR="$DEPLOY_DIR/vuemonitor"

echo ""
echo "============================================"
echo "  XHS365 更新部署"
echo "============================================"
echo ""

# ---------- [1] 拉取最新代码 ----------
echo "[1/5] 拉取最新代码..."
cd $REPO_DIR
git pull origin main
echo "  代码已更新"

# ---------- [2] 重建 Web 前端 ----------
echo "[2/5] 重建 Web 前端..."
cd $REPO_DIR/web-user
npm install --quiet 2>/dev/null
npm run build 2>/dev/null
cp -r dist/* $DEPLOY_DIR/web-user/dist/
echo "  Web 前端已更新"

# ---------- [3] 复制客户端安装包 ----------
echo "[3/5] 复制客户端安装包..."
if [ -d "$REPO_DIR/deploy/downloads" ]; then
    cp -rn $REPO_DIR/deploy/downloads/* $DEPLOY_DIR/downloads/ 2>/dev/null || true
    echo "  安装包已更新"
fi

# ---------- [4] 重建并重启 Docker ----------
echo "[4/5] 重建并重启服务端..."
cd $DEPLOY_DIR
docker compose up -d --build server 2>/dev/null || docker-compose up -d --build server

# ---------- [5] 数据库迁移 ----------
echo "[5/5] 数据库迁移..."
sleep 5
docker compose exec -T server alembic upgrade head 2>/dev/null || docker-compose exec -T server alembic upgrade head

# ---------- 验证 ----------
echo ""
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "FAIL")
echo "  服务端状态: $HEALTH"

echo ""
echo "============================================"
echo "  更新完成!"
echo "============================================"