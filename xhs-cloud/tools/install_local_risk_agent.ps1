#Requires -Version 5.1
<#
.SYNOPSIS
  安装本地 risk 静默采集 Agent（Windows 开机自启，pythonw 后台运行）

.PARAMETER EnvFile
  本地 agent 配置（含 XHS_CLOUD_API_URL、XHS_LOCAL_AGENT_KEY 等）

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\install_local_risk_agent.ps1 `
    -EnvFile D:\vuemonitor\xhs-cloud\tools\local_agent.env
#>
param(
    [string]$EnvFile = "",
    [string]$PythonExe = "",
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$AgentScript = Join-Path $RepoRoot "tools\local_risk_agent.py"
if (-not (Test-Path $AgentScript)) {
    throw "找不到 $AgentScript"
}

if (-not $PythonExe) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) { throw "未找到 python，请先安装 Python 3.10+" }
}

$Pythonw = Join-Path (Split-Path $PythonExe -Parent) "pythonw.exe"
if (-not (Test-Path $Pythonw)) { $Pythonw = $PythonExe }

$LogDir = Join-Path $env:LOCALAPPDATA "xhs-local-agent"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not $EnvFile) {
    $EnvFile = Join-Path $RepoRoot "tools\local_agent.env.example"
}

$TaskName = "XHS-Local-Risk-Agent"
$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$AgentScript`" run" -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null

# 写入启动包装 bat（注入环境变量）
$Wrapper = Join-Path $LogDir "run_agent.bat"
$envLines = @()
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) { $envLines += "set $line" }
    }
}
$bat = @"
@echo off
cd /d "$RepoRoot"
$($envLines -join "`r`n")
set XHS_LOCAL_AGENT_ENV=$EnvFile
set XHS_LOCAL_AGENT_LOG_DIR=$LogDir
set XHS_CRAWLER_ROOT=$RepoRoot\cloud_deploy\crawler_runtime
set XHS_ENABLE_PLAYWRIGHT=1
set PYTHONPATH=$RepoRoot
"$Pythonw" "$AgentScript" run
"@
Set-Content -Path $Wrapper -Value $bat -Encoding ASCII

$Action2 = New-ScheduledTaskAction -Execute $Wrapper -WorkingDirectory $LogDir
Register-ScheduledTask -TaskName $TaskName -Action $Action2 -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null

Write-Host "已安装计划任务: $TaskName" -ForegroundColor Green
Write-Host "  配置: $EnvFile"
Write-Host "  日志: $LogDir\agent.log"
Write-Host ""
Write-Host "下一步:"
Write-Host "  1. 复制 tools\local_agent.env.example 为 local_agent.env 并填写 API URL / Agent Key"
Write-Host "  2. playwright install chromium"
Write-Host "  3. 测试: set XHS_LOCAL_AGENT_FOREGROUND=1 && python tools\local_risk_agent.py status"
Write-Host "  4. 启动任务: schtasks /Run /TN $TaskName"
