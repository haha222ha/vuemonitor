# 提交并 push risk 补扫 + claim 机制到 GitHub
# 用法: powershell -ExecutionPolicy Bypass -File tools\git_push_risk_rescan.ps1
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root

$git = $null
foreach ($p in @(
    "git",
    "D:\PortableGit\cmd\git.exe",
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Users\Administrator\mingit\cmd\git.exe"
)) {
    if (Get-Command $p -ErrorAction SilentlyContinue) { $git = $p; break }
    if (Test-Path $p) { $git = $p; break }
}
if (-not $git) {
    Write-Host "未安装 Git。" -ForegroundColor Red
    exit 1
}

$files = @(
    "xhs-cloud/cloud_deploy/cloud_api/scan_claim.py",
    "xhs-cloud/cloud_deploy/cloud_api/agent_service.py",
    "xhs-cloud/cloud_deploy/cloud_api/database_pg.py",
    "xhs-cloud/cloud_deploy/cloud_api/main.py",
    "xhs-cloud/cloud_deploy/cloud_api/sync_service.py",
    "xhs-cloud/cloud_deploy/config/daemon.json",
    "xhs-cloud/cloud_deploy/daemon/cloud_daemon.py",
    "xhs-cloud/cloud_deploy/scripts/daemon_status.py",
    "xhs-cloud/tools/local_risk_agent.py",
    "xhs-cloud/tools/local_agent.env.example",
    "xhs-cloud/tools/setup_local_agent.ps1",
    "xhs-cloud/tools/git_push_risk_rescan.ps1"
)

& $git add @files
$st = & $git diff --cached --name-only
if (-not $st) {
    Write-Host "没有新改动需要提交。" -ForegroundColor Green
    exit 0
}

& $git commit -m @"
feat(xhs-cloud): risk 补扫 + 认领机制，家庭 Agent 与 daemon 不重复扫

- daemon 全池扫完后每 2h 补扫 risk（claim TTL 25min）
- Agent API 拉工单时原子认领 scan_claim_by
- daemon.json 默认启用 risk_rescan
- 本地 Agent 支持 min_age_hours 与 2h 整轮冷却
"@

Write-Host "正在 push 到 origin main ..." -ForegroundColor Cyan
& $git push origin main
Write-Host "Push 完成。服务器: cd /opt/vuemonitor && git pull && rsync ... && restart" -ForegroundColor Green
