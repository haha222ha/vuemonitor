# AIGC START
# 注册 Windows 计划任务：按 config/intel_production.json 的 sync_schedule 每日执行 scheduled_sync.ps1
# 需以管理员身份运行一次: powershell -ExecutionPolicy Bypass -File register_windows_tasks.ps1
param(
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$SyncDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $SyncDir)
$ConfigPath = Join-Path $RepoRoot "config\intel_production.json"
$Runner = Join-Path $SyncDir "scheduled_sync.ps1"
$TaskPrefix = "VuemonitorIntelSync"

if (-not (Test-Path $Runner)) {
    Write-Error "找不到 $Runner"
}

$schedules = @("08:00", "20:00")
if (Test-Path $ConfigPath) {
    $cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.sync_schedule) {
        $schedules = @($cfg.sync_schedule)
    }
}

if ($Unregister) {
    Get-ScheduledTask -TaskName "$TaskPrefix*" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Write-Host "已移除 $TaskPrefix* 计划任务"
    exit 0
}

$idx = 0
foreach ($time in $schedules) {
    $idx++
    $taskName = "${TaskPrefix}_${idx}"
    $parts = $time -split ":"
    $hour = [int]$parts[0]
    $minute = if ($parts.Length -gt 1) { [int]$parts[1] } else { 0 }

    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
    $trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date -Hour $hour -Minute $minute -Second 0)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host "已注册: $taskName  每日 $time"
}

Write-Host ""
Write-Host "完成。手动测试: powershell -File `"$Runner`""
Write-Host "移除任务: powershell -File `"$PSCommandPath`" -Unregister"
# AIGC END
