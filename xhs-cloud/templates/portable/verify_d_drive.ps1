# D 盘移动硬盘结构验证 — 插入任意电脑后运行:
#   powershell -ExecutionPolicy Bypass -File D:\vuemonitor\xhs-cloud\templates\portable\verify_d_drive.ps1

$ErrorActionPreference = "Continue"

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    return $true
}

$pathsConfig = "D:\xhs-data\config\portable_paths.env"
if (-not (Import-DotEnv $pathsConfig)) {
    Write-Host "警告: 未找到 $pathsConfig" -ForegroundColor Yellow
    Write-Host "请先复制 templates\portable\portable_paths.env.example 并填写 XHS_CRAWLER_ROOT" -ForegroundColor Yellow
}

$crawlerRoot = $env:XHS_CRAWLER_ROOT
if ([string]::IsNullOrWhiteSpace($crawlerRoot)) {
    Write-Host "警告: XHS_CRAWLER_ROOT 未设置，跳过爬虫目录检查" -ForegroundColor Yellow
}

$paths = @(
    "D:\vuemonitor\xhs-cloud\docs\需求规格书_精品库双向同步_v1.md",
    "D:\关键词搜索\最终版_实体产品搜索词库.txt",
    "D:\关键词搜索\最终版_虚拟产品搜索词库.txt",
    "D:\选品报告",
    $pathsConfig
)

if (-not [string]::IsNullOrWhiteSpace($crawlerRoot)) {
    $paths += @(
        (Join-Path $crawlerRoot "xhs_premium_schema.py"),
        (Join-Path $crawlerRoot "crawl_data")
    )
}

Write-Host "=== D 盘便携工作区验证 ===" -ForegroundColor Cyan
if (-not [string]::IsNullOrWhiteSpace($crawlerRoot)) {
    Write-Host "XHS_CRAWLER_ROOT = $crawlerRoot" -ForegroundColor Cyan
}

$ok = 0
$fail = 0
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "OK   $p" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "缺失 $p" -ForegroundColor Red
        $fail++
    }
}

Write-Host ""
Write-Host "通过 $ok / $($paths.Count)" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
if ($fail -eq 0) {
    Write-Host "可打开 Cursor 文件夹: D:\vuemonitor" -ForegroundColor Green
}
