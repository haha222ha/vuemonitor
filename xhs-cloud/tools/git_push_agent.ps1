# 提交并 push 本地 Agent 相关代码到 GitHub
# 用法: powershell -ExecutionPolicy Bypass -File tools\git_push_agent.ps1
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$git = $null
foreach ($p in @(
    "git",
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe"
)) {
    if (Get-Command $p -ErrorAction SilentlyContinue) { $git = $p; break }
    if (Test-Path $p) { $git = $p; break }
}
if (-not $git) {
    Write-Host "未安装 Git。请先安装: https://git-scm.com/download/win" -ForegroundColor Red
    Write-Host "安装后重新运行本脚本，或把 D:\vuemonitor 拷到有 Git 的电脑 push。" -ForegroundColor Yellow
    exit 1
}

& $git status -sb
& $git add `
    xhs-cloud/cloud_deploy/cloud_api/agent_service.py `
    xhs-cloud/cloud_deploy/cloud_api/auth.py `
    xhs-cloud/cloud_deploy/cloud_api/config.py `
    xhs-cloud/cloud_deploy/cloud_api/main.py `
    xhs-cloud/cloud_deploy/.env.example `
    xhs-cloud/cloud_deploy/scripts/local_risk_playwright_scan.py `
    xhs-cloud/scripts/setup_agent_api.sh `
    xhs-cloud/tools/local_risk_agent.py `
    xhs-cloud/tools/install_local_risk_agent.ps1 `
    xhs-cloud/tools/setup_local_agent.ps1 `
    xhs-cloud/tools/local_agent.env.example `
    xhs-cloud/tools/git_push_agent.ps1

$st = & $git status --porcelain
if (-not $st) {
    Write-Host "没有新改动需要提交。" -ForegroundColor Green
    exit 0
}

& $git commit -m @"
feat: 本地 risk Agent HTTP 回传（无需开 PG 5432）

- 云端 /api/v1/agent/* 鉴权接口
- local_risk_agent 静默采集 + 开机自启
- setup 一键脚本
"@

Write-Host "正在 push 到 origin main ..." -ForegroundColor Cyan
& $git push origin main
Write-Host "Push 完成。请到服务器执行: cd /opt/vuemonitor && git pull" -ForegroundColor Green
