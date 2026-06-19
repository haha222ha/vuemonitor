# 本地整理待同步到服务器的数据（不进入 git）
# 用法:
#   .\tools\prepare_server_sync.ps1
#   .\tools\prepare_server_sync.ps1 -SourceRoot "C:\Users\Administrator\Desktop\每日选品全量数据"

param(
    [string]$SourceRoot = "C:\Users\Administrator\Desktop\每日选品全量数据",
    [string]$OutRoot = ""
)

$ErrorActionPreference = "Stop"
$XhsRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (Test-Path "$PSScriptRoot\..\cloud_deploy") {
    $XhsRoot = Split-Path $PSScriptRoot -Parent
}
if (-not $OutRoot) {
    $OutRoot = Join-Path $XhsRoot "server_sync_pack"
}

$HistDir = Join-Path $OutRoot "historical_reports"
New-Item -ItemType Directory -Force -Path $HistDir | Out-Null

Write-Host "源目录: $SourceRoot"
Write-Host "输出:   $OutRoot"

if (-not (Test-Path $SourceRoot)) {
    Write-Error "源目录不存在: $SourceRoot"
}

$manifest = @{
    prepared_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    source_root = $SourceRoot
    output_root = $OutRoot
    reports     = @()
}

# 优先 全量MMDD 命名；去重同日期保留 data.js 更大者
$dirs = Get-ChildItem $SourceRoot -Directory | Where-Object {
    Test-Path (Join-Path $_.FullName "data.js")
}

$byDate = @{}
foreach ($d in $dirs) {
    $js = Join-Path $d.FullName "data.js"
    $size = (Get-Item $js).Length
    # 从 data.js 读 date（轻量读前 500 字节）
    $head = [System.IO.File]::ReadAllText($js, [System.Text.Encoding]::UTF8).Substring(0, [Math]::Min(500, $size))
    $date = if ($head -match '"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"') { $Matches[1] } else { $d.Name }

    if ($byDate.ContainsKey($date)) {
        if ($size -gt $byDate[$date].Size) { $byDate[$date] = @{ Dir = $d; Size = $size; Date = $date } }
    } else {
        $byDate[$date] = @{ Dir = $d; Size = $size; Date = $date }
    }
}

$sorted = $byDate.Values | Sort-Object Date
$totalMB = 0

foreach ($item in $sorted) {
    $src = $item.Dir.FullName
    $destName = $item.Dir.Name
    # 统一复制到 historical_reports/全量MMDD 或保留原名
    if ($destName -notmatch "^全量") {
        $mmdd = $item.Date.Replace("-", "").Substring(4)
        $destName = "全量$mmdd"
    }
    $dest = Join-Path $HistDir $destName

    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item -Path $src -Destination $dest -Recurse -Force

    $hasHtml = Test-Path (Join-Path $dest "index_with_gr.html")
    if (-not $hasHtml) {
        $tpl = Join-Path $XhsRoot "cloud_deploy\assets\index_with_gr.html"
        if (Test-Path $tpl) { Copy-Item $tpl (Join-Path $dest "index_with_gr.html") }
    }

    $mb = [math]::Round($item.Size / 1MB, 2)
    $totalMB += $mb
    $manifest.reports += @{
        report_date = $item.Date
        dir_name    = $destName
        source_dir  = $item.Dir.Name
        data_js_mb  = $mb
        has_html    = $hasHtml -or (Test-Path (Join-Path $dest "index_with_gr.html"))
        server_path = "/opt/xhs-cloud/data/import_batch/$destName"
    }
    Write-Host "  [OK] $($item.Date) -> $destName ($mb MB)"
}

$manifest.total_reports = $manifest.reports.Count
$manifest.total_data_js_mb = [math]::Round($totalMB, 2)

$manifestPath = Join-Path $OutRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content $manifestPath -Encoding UTF8

$readme = @"
# 服务器同步数据包（本地生成，勿提交 git）

生成时间: $($manifest.prepared_at)
报告数量: $($manifest.total_reports)
data.js 合计: $($manifest.total_data_js_mb) MB

## 目录

``````
server_sync_pack/
  historical_reports/   ← scp 到服务器
    全量0616/
    全量0617/
    ...
  manifest.json
  scp_upload.ps1        ← 上传脚本（填 ECS IP）
``````

## 服务器导入（pull + 部署完成后）

``````bash
# 1. 上传到服务器
scp -r historical_reports/* user@ECS:/opt/xhs-cloud/data/import_batch/

# 2. 批量入库
cd /opt/xhs-cloud
sudo -u admin env PYTHONPATH=/opt/xhs-cloud ./venv/bin/python \\
  cloud_deploy/scripts/import_historical_reports.py \\
  --root /opt/xhs-cloud/data/import_batch
``````

## 可选：sold_history 回补

若挂载本地 SQLite 只读路径到服务器 XHS_DB_PATH，ingest 时会自动回补。
否则部署后用 API 推送 sold-history。
"@

Set-Content (Join-Path $OutRoot "README.md") $readme -Encoding UTF8

$scpScript = @"
# 填写 ECS 信息后运行
`$ECS = "your-server-ip"
`$USER = "admin"
`$SRC = "$HistDir"
`$DEST = "/opt/xhs-cloud/data/import_batch/"

ssh `${USER}@`${ECS} "mkdir -p `$DEST"
scp -r "`$SRC\*" "`${USER}@`${ECS}:`$DEST"
Write-Host "上传完成。SSH 登录后执行 import_historical_reports.py"
"@
Set-Content (Join-Path $OutRoot "scp_upload.ps1") $scpScript -Encoding UTF8

Write-Host ""
Write-Host "完成: $($manifest.total_reports) 份报告, 合计 $totalMB MB"
Write-Host "清单: $manifestPath"
Write-Host "下一步: 编辑 server_sync_pack/scp_upload.ps1 后上传，或 push 代码后在服务器 import"
