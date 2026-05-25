# AIGC START
# 读取 config/intel_production.json 写入 web-intel/.env.production 并构建 dist
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $RepoRoot "config\intel_production.json"
$IntelDir = Join-Path $RepoRoot "web-intel"
$EnvProd = Join-Path $IntelDir ".env.production"

if (-not (Test-Path $ConfigPath)) {
    Write-Error "缺少配置文件: $ConfigPath"
}

$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$shopUrl = $config.xhs_shop_url
if (-not $shopUrl -or $shopUrl -match "REPLACE") {
    Write-Warning "请在 config/intel_production.json 中设置真实的小红书店铺链接 xhs_shop_url"
}

$envContent = @"
# 由 scripts/build-web-intel.ps1 自动生成，请勿手改（改 config/intel_production.json）
VITE_API_BASE_URL=/api/v1
VITE_XHS_SHOP_URL=$shopUrl
"@

Set-Content -Path $EnvProd -Value $envContent -Encoding UTF8 -NoNewline
Write-Host "[build-web-intel] VITE_XHS_SHOP_URL=$shopUrl" -ForegroundColor Cyan

Push-Location $IntelDir
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[build-web-intel] dist 构建完成" -ForegroundColor Green
} finally {
    Pop-Location
}
# AIGC END
