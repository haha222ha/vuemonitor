#Requires -Version 5.1
<#
一键安装本地 risk 静默采集（家里电脑运行）

用法:
  1. 服务器 SSH 执行: bash scripts/setup_agent_api.sh
  2. 复制输出的 XHS_LOCAL_AGENT_KEY
  3. 本机 PowerShell:
     cd D:\vuemonitor\xhs-cloud
     powershell -ExecutionPolicy Bypass -File tools\setup_local_agent.ps1
#>
param(
    [string]$ApiUrl = "https://monitor.xhs365.cn",
    [string]$AgentKey = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

Write-Host ""
Write-Host "  XHS 本地 risk 采集 — 一键安装" -ForegroundColor Cyan
Write-Host "  ==============================" -ForegroundColor Cyan
Write-Host ""

if (-not $AgentKey) {
    $AgentKey = Read-Host "粘贴服务器给的 XHS_LOCAL_AGENT_KEY"
}
$AgentKey = $AgentKey.Trim()
if ($AgentKey.Length -lt 16) {
    throw "密钥太短，请从服务器 setup_agent_api.sh 输出里完整复制"
}

$customUrl = Read-Host "API 地址 [直接回车用 $ApiUrl]"
if ($customUrl.Trim()) { $ApiUrl = $customUrl.Trim() }

Write-Host ""
Write-Host "[1/5] 安装 Python 依赖..." -ForegroundColor Yellow
python -m pip install -q playwright 2>$null
if ($LASTEXITCODE -ne 0) { throw "pip install 失败，请先安装 Python 3.10+" }

Write-Host "[2/5] 安装 Chromium（首次较慢）..." -ForegroundColor Yellow
python -m playwright install chromium

Write-Host "[3/5] 写配置文件..." -ForegroundColor Yellow
$EnvFile = Join-Path $RepoRoot "tools\local_agent.env"
@(
    "XHS_CLOUD_API_URL=$ApiUrl"
    "XHS_LOCAL_AGENT_KEY=$AgentKey"
    "XHS_LOCAL_AGENT_ID=$env:COMPUTERNAME"
    "XHS_LOCAL_AGENT_BATCH=800"
    "XHS_LOCAL_AGENT_CONCURRENCY=3"
    "XHS_LOCAL_AGENT_IDLE_SEC=300"
    "XHS_LOCAL_AGENT_COOLDOWN_SEC=15"
    "XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC=7200"
    "XHS_LOCAL_AGENT_MIN_AGE_HOURS=2"
    "XHS_LOCAL_AGENT_MODE=api_then_browser"
) | Set-Content -Path $EnvFile -Encoding UTF8

Write-Host "[4/5] 测试连接..." -ForegroundColor Yellow
$env:XHS_CLOUD_API_URL = $ApiUrl
$env:XHS_LOCAL_AGENT_KEY = $AgentKey
$env:XHS_LOCAL_AGENT_FOREGROUND = "1"
python tools\local_risk_agent.py status
if ($LASTEXITCODE -ne 0) { throw "连接失败，检查 API 地址和密钥" }

Write-Host "[5/5] 安装开机自启（后台静默）..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "tools\install_local_risk_agent.ps1") -EnvFile $EnvFile
schtasks /Run /TN "XHS-Local-Risk-Agent" 2>$null

Write-Host ""
Write-Host "  全部完成！" -ForegroundColor Green
Write-Host "  - 已后台运行，开机自动启动"
Write-Host "  - 日志: $env:LOCALAPPDATA\xhs-local-agent\agent.log"
Write-Host ""
Write-Host "  查看日志: Get-Content `"$env:LOCALAPPDATA\xhs-local-agent\agent.log`" -Tail 15" -ForegroundColor Gray
Write-Host ""
