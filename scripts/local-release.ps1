param(
    [string]$Message = "",
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Write-Step($msg) { Write-Host ""; Write-Host ">>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  OK: $msg" -ForegroundColor Green }
function Write-Err($msg) { Write-Host "  FAIL: $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  XHS365 local release (push then host-update.sh on server)" -ForegroundColor Cyan

if (-not $SkipBuild) {
    foreach ($proj in @("web-user", "web-admin", "web-intel")) {
        Write-Step "Build $proj"
        Push-Location (Join-Path $Root $proj)
        if (-not (Test-Path "node_modules")) { npm ci }
        npm run build
        if (-not (Test-Path "dist\index.html")) { Write-Err "$proj dist/index.html missing" }
        Pop-Location
        Write-Ok "$proj built"
    }
}

if (-not $SkipTests) {
    Write-Step "Server email tests"
    Push-Location (Join-Path $Root "server")
    python -m pytest tests/test_services.py::TestEmailService -q --tb=no
    if ($LASTEXITCODE -ne 0) { Write-Err "pytest failed" }
    Pop-Location
    Write-Ok "pytest passed"

    Write-Step "Client normalizer tests"
    Push-Location (Join-Path $Root "client")
    npx vitest run src/main/collect/normalizer.test.ts
    if ($LASTEXITCODE -ne 0) { Write-Err "vitest failed" }
    Pop-Location
    Write-Ok "vitest passed"
}

Write-Step "Git commit"
git add -A
git reset HEAD -- .env 2>$null
git reset HEAD -- .env.* 2>$null
git reset HEAD -- secrets/ 2>$null

$status = git status --porcelain
if (-not $status) {
    Write-Host "  No changes to commit" -ForegroundColor Yellow
} else {
    if (-not $Message) {
        $Message = "chore: release $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    }
    git commit -m $Message
    Write-Ok "committed"
}

if (-not $SkipPush) {
    Write-Step "Git push origin main"
    git push origin main
    if ($LASTEXITCODE -ne 0) { Write-Err "git push failed" }
    Write-Ok "pushed"
}

Write-Host ""
Write-Host "  On 2G host run:" -ForegroundColor Green
Write-Host "    cd /opt/vuemonitor"
Write-Host "    bash scripts/host-update.sh"
Write-Host ""
