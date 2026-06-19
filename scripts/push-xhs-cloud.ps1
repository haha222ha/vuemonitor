# 提交并 push xhs-cloud 选品独立子系统
# 在 Git Bash 或已安装 git 的 PowerShell 中运行:
#   cd E:\vuemonitor
#   powershell -ExecutionPolicy Bypass -File scripts\push-xhs-cloud.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "未找到 git，请先安装 Git for Windows: https://git-scm.com/download/win"
    exit 1
}

& git status -sb
& git add xhs-cloud/ scripts/push-xhs-cloud.ps1 scripts/reopen-git-login.bat
& git status -sb

$msg = "add xhs-cloud: 选品监控独立子系统（PG xhs_monitor schema、文档、部署脚本）"

& git commit -m $msg
& git push -u origin main
Write-Host "Done. 服务器执行 pull 见 xhs-cloud/README.md"
