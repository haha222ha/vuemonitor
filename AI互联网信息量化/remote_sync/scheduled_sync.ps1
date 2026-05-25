# AIGC START
# 定时同步入口：数据库全量同步 +（可选）上传最新选题 HTML 报告
# 供 Windows 任务计划程序调用，或手动双击运行
$ErrorActionPreference = "Stop"
$SyncDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $SyncDir)
$LogDir = Join-Path $SyncDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunnerLog = Join-Path $LogDir "scheduled_runner_$Stamp.log"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $RunnerLog -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Log "=== scheduled_sync start ==="
Set-Location $SyncDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Log "ERROR: 未找到 python，请安装 Python 并加入 PATH"
    exit 1
}

Write-Log "Python: $($python.Source)"
& $python.Source "full_sync.py" --scheduled 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "scheduled_sync_$Stamp.log")
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Log "=== scheduled_sync OK ==="
} else {
    Write-Log "=== scheduled_sync FAILED exit=$code ==="
}
exit $code
# AIGC END
