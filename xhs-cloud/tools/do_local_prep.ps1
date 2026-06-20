# 本地一键：校验数据包 -> 打 tar 包 ->（可选）scp 上传
# 用法: powershell -ExecutionPolicy Bypass -File d:\vuemonitor\xhs-cloud\tools\do_local_prep.ps1
#       powershell -ExecutionPolicy Bypass -File d:\vuemonitor\xhs-cloud\tools\do_local_prep.ps1 -Upload
param(
    [switch]$Upload,
    [switch]$ForceExport,
    [string]$EcsHost = "xhs365.cn"
)

$ErrorActionPreference = "Stop"
$XhsRoot = Split-Path $PSScriptRoot -Parent
$Pack = Join-Path $XhsRoot "server_sync_pack"
$Hist = Join-Path $Pack "historical_reports"
$Pool = Join-Path $Pack "monitor_pool"
$Tar = Join-Path $Pack "xhs-import-batch.tar.gz"
function Find-MainDb {
    $candidates = @(
        "D:\0619xhs备份\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db",
        "D:\0618小红书备份\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db",
        "D:\jiekoufenxi\小红书多设备爬虫\crawl_data\xhs_burst_monitor.db"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    $found = python -c "import glob; p=glob.glob(r'D:\**\xhs_burst_monitor.db', recursive=True); print(p[0] if p else '')"
    if ($found) { return $found.Trim() }
    return $null
}

$MainDb = Find-MainDb

function Test-PackComplete {
    if (-not (Test-Path $Hist)) { return $false }
    $reportDirs = Get-ChildItem $Hist -Directory | Where-Object { Test-Path (Join-Path $_.FullName "data.js") }
    if ($reportDirs.Count -lt 1) { return $false }
    $parts = Get-ChildItem (Join-Path $Pool "sold_history") -Filter "part-*.jsonl.gz" -ErrorAction SilentlyContinue
    if ($parts.Count -lt 1) { return $false }
    if (-not (Test-Path (Join-Path $Pool "monitor_goods_ids.json"))) { return $false }
    return $true
}

Write-Host "=== local prep: server_sync_pack ===" -ForegroundColor Cyan

if (-not $MainDb) {
    if (-not (Test-PackComplete)) { throw "xhs_burst_monitor.db not found and pack incomplete" }
    Write-Host "db not found, pack complete -> skip export only" -ForegroundColor Yellow
}
if (-not (Test-Path $Hist)) { throw "missing historical_reports" }

$complete = Test-PackComplete
if ($ForceExport -or (-not $complete -and $MainDb)) {
    Write-Host "export monitor pool ..." -ForegroundColor Yellow
    Write-Host "db: $MainDb"
    Set-Location $XhsRoot
    python tools/export_monitor_pool_for_cloud.py --source $Hist --main-db $MainDb --out $Pool
} elseif (-not $complete) {
    throw "pack incomplete and no db found for export"
} else {
    Write-Host "pack OK, skip export (use -ForceExport to redo)" -ForegroundColor Green
}

Set-Location $XhsRoot
python tools/refresh_sync_manifest.py --pack $Pack

Copy-Item (Join-Path $XhsRoot "cloud_deploy\scripts\server_import.sh") (Join-Path $Pack "server_import.sh") -Force

if (Test-Path $Tar) { Remove-Item $Tar -Force }
Push-Location $Pack
try {
    tar -czf $Tar historical_reports monitor_pool manifest.json server_import.sh
} finally { Pop-Location }

$exp = Get-Content (Join-Path $Pool "export_manifest.json") -Raw | ConvertFrom-Json
$sizeMB = [math]::Round((Get-Item $Tar).Length / 1MB, 2)
Write-Host ""
Write-Host "DONE" -ForegroundColor Green
Write-Host "  goods: $($exp.monitor_goods_count)"
Write-Host "  tar:   $Tar ($sizeMB MB)"
Write-Host ""
Write-Host "SERVER (git pull then import):" -ForegroundColor Cyan
Write-Host "  cd /opt/vuemonitor && git pull"
Write-Host "  rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/ /opt/xhs-cloud/cloud_deploy/ --delete"
Write-Host "  bash /opt/xhs-cloud/cloud_deploy/scripts/server_import.sh"

if ($Upload) {
    Write-Host "uploading ..." -ForegroundColor Yellow
    scp $Tar "admin@${EcsHost}:/tmp/xhs-import-batch.tar.gz"
    ssh "admin@${EcsHost}" "mkdir -p /opt/xhs-cloud/data/import_batch; tar -xzf /tmp/xhs-import-batch.tar.gz -C /opt/xhs-cloud/data/import_batch"
    Write-Host "upload done, run server_import.sh on server" -ForegroundColor Green
}
