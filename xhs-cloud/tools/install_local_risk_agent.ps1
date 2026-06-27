#Requires -Version 5.1
<#
.SYNOPSIS
  安装/卸载本地 risk Agent 计划任务（默认不启用自动采集）

.PARAMETER EnvFile
  本地 agent 配置

.PARAMETER EnableScheduledTask
  注册开机自启并立即运行（需 local_agent.env 中 XHS_LOCAL_AGENT_ENABLED=1）

.PARAMETER Uninstall
  禁用并结束计划任务，不删除日志目录

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\install_local_risk_agent.ps1 -Uninstall
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\install_local_risk_agent.ps1 -EnvFile tools\local_agent.env -EnableScheduledTask
#>
param(
    [string]$EnvFile = "",
    [string]$PythonExe = "",
    [string]$RepoRoot = "",
    [switch]$EnableScheduledTask,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$TaskName = "XHS-Local-Risk-Agent"
$LogDir = Join-Path $env:LOCALAPPDATA "xhs-local-agent"

function Stop-AgentWorkers {
    schtasks /End /TN $TaskName 2>$null | Out-Null
    try {
        $procs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
        foreach ($p in $procs) {
            $cmd = $p.CommandLine
            if ($cmd -and $cmd -match 'local_risk_agent\.py') {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Host "Stop-AgentWorkers warn: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if ($Uninstall) {
    Stop-AgentWorkers
    schtasks /Change /TN $TaskName /DISABLE 2>$null
    $stub = @'
@echo off
echo [XHS-Local-Risk-Agent] disabled, skip start.
exit /b 0
'@
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Set-Content -Path (Join-Path $LogDir "run_agent.bat") -Value $stub -Encoding ASCII
    Write-Host "Disabled $TaskName (task disabled, workers stopped)." -ForegroundColor Green
    Write-Host "Log dir: $LogDir"
    exit 0
}

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

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not $EnvFile) {
    $EnvFile = Join-Path $RepoRoot "tools\local_agent.env.example"
}

$envLines = @()
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) { $envLines += "set $line" }
    }
}

$Wrapper = Join-Path $LogDir "run_agent.bat"
$batLines = @(
    '@echo off'
    "cd /d `"$RepoRoot`""
)
foreach ($el in $envLines) { $batLines += $el }
$batLines += @(
    "set XHS_LOCAL_AGENT_ENV=$EnvFile"
    "set XHS_LOCAL_AGENT_LOG_DIR=$LogDir"
    "set XHS_CRAWLER_ROOT=$RepoRoot\cloud_deploy\crawler_runtime"
    "set XHS_ENABLE_PLAYWRIGHT=1"
    "set PYTHONPATH=$RepoRoot"
    'if "%XHS_LOCAL_AGENT_ENABLED%"=="0" ('
    '  echo [XHS-Local-Risk-Agent] XHS_LOCAL_AGENT_ENABLED=0, skip start.'
    '  exit /b 0'
    ')'
    'if not defined XHS_LOCAL_AGENT_ENABLED set XHS_LOCAL_AGENT_ENABLED=0'
    'if "%XHS_LOCAL_AGENT_ENABLED%"=="0" ('
    '  echo [XHS-Local-Risk-Agent] auto collect not enabled, skip start.'
    '  exit /b 0'
    ')'
    "`"$Pythonw`" `"$AgentScript`" run"
)
$bat = $batLines -join "`r`n"
Set-Content -Path $Wrapper -Value $bat -Encoding ASCII

if (-not $EnableScheduledTask) {
    Stop-AgentWorkers
    schtasks /Change /TN $TaskName /DISABLE 2>$null
    Write-Host "Wrapper written (auto collect OFF by default)." -ForegroundColor Green
    Write-Host "  Env: $EnvFile"
    Write-Host "  Wrapper: $Wrapper"
    Write-Host ""
    Write-Host "To enable on logon: set XHS_LOCAL_AGENT_ENABLED=1 in local_agent.env then:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File tools\install_local_risk_agent.ps1 -EnvFile `"$EnvFile`" -EnableScheduledTask"
    exit 0
}

$enabled = $false
if (Test-Path $EnvFile) {
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*XHS_LOCAL_AGENT_ENABLED\s*=\s*(.+)\s*$') {
            $v = $matches[1].Trim().ToLower()
            if ($v -in @('1', 'true', 'yes', 'on', 'enabled')) { $enabled = $true }
            break
        }
    }
}
if (-not $enabled) {
    throw "XHS_LOCAL_AGENT_ENABLED is not 1; refusing scheduled task. Edit $EnvFile and retry."
}

$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Action2 = New-ScheduledTaskAction -Execute $Wrapper -WorkingDirectory $LogDir
Register-ScheduledTask -TaskName $TaskName -Action $Action2 -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
schtasks /Change /TN $TaskName /ENABLE | Out-Null

Write-Host "Installed and enabled scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Env: $EnvFile"
Write-Host "  Log: $LogDir\agent.log"
Write-Host ""
Write-Host "Start now: schtasks /Run /TN $TaskName"
Write-Host "Disable: powershell -ExecutionPolicy Bypass -File tools\install_local_risk_agent.ps1 -Uninstall"
