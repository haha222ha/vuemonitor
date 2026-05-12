$ErrorActionPreference = "Stop"

# ============================================================
#  XHS365 一键更新脚本（GitHub Push/Pull 模式）
#  使用方法：修改下方变量后，直接复制粘贴到 PowerShell 执行
#
#  完整流程：
#    1. 本地: git add . && git commit -m "xxx" && git push origin main
#    2. 本地: 执行此脚本（SSH到服务器拉取代码+重建+重启）
# ============================================================

# ====== 修改这里 ======
$SERVER_HOST = "root@你的服务器IP"        # 服务器地址，如 root@192.168.1.100
# ======================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  XHS365 一键更新（GitHub Pull 模式）" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  服务器: $SERVER_HOST" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---------- [1] 确认本地已推送 ----------
Write-Host "[1/3] 检查本地代码状态..." -ForegroundColor Yellow
$unpushed = git log origin/main..HEAD --oneline 2>$null
if ($unpushed) {
    Write-Host "  发现未推送的提交，正在推送..." -ForegroundColor Yellow
    git push origin main
    Write-Host "  代码已推送到 GitHub" -ForegroundColor Green
} else {
    Write-Host "  本地代码已是最新，无需推送" -ForegroundColor Green
}

# ---------- [2] SSH 到服务器拉取并重建 ----------
Write-Host "[2/3] 服务器拉取代码并重建..." -ForegroundColor Yellow
ssh $SERVER_HOST @"
cd /opt/vuemonitor
echo '  拉取最新代码...'
git pull origin main

echo '  重建Web前端...'
cd web-user
npm install --quiet 2>/dev/null
npm run build 2>/dev/null

echo '  数据库迁移...'
cd /opt/vuemonitor/server
source .venv/bin/activate
alembic upgrade head 2>/dev/null

echo '  重启服务端...'
sudo systemctl restart vuemonitor
"@

# ---------- [3] 验证 ----------
Write-Host "[3/3] 验证服务状态..." -ForegroundColor Yellow
ssh $SERVER_HOST @"
sleep 3
HEALTH=\$(curl -s http://localhost:8000/health 2>/dev/null || echo 'FAIL')
echo "  服务端状态: \$HEALTH"
sudo systemctl is-active vuemonitor
"@

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  更新完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green