# 方案 A：Windows 开发机上传本地 insight_export → 云 insight_shadow
# 用法:
#   .\scripts\push_insight_bundle.ps1 -Date 2026-07-12 -Host root@你的ECS
param(
    [Parameter(Mandatory = $true)][string]$Date,
    [string]$Host = $env:XHS_INSIGHT_HOST,
    [string]$Root = "E:\vuemonitor\xhs-cloud"
)

if (-not $Host) { throw "请设置 -Host 或环境变量 XHS_INSIGHT_HOST" }

$day = $Date.Replace("-", "")
$src = Join-Path $Root "data\insight_export\insight_$day"
$dest = "/opt/xhs-cloud/data/insight_shadow/insight_$day/"

if (-not (Test-Path $src)) {
    throw "缺少本地目录 $src — 先运行 export_local_insight_bundle.py"
}

Write-Host "[upload-insight] $src -> ${Host}:$dest"
scp -r "$src\*" "${Host}:${dest}"
Write-Host "[upload-insight] OK — 会员页 Ctrl+F5 强刷"
