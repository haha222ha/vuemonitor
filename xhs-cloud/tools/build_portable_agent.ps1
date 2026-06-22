#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Tools = $PSScriptRoot
$XhsRoot = (Resolve-Path (Join-Path $Tools "..")).Path
$OutRoot = Join-Path $XhsRoot "dist\XHS-Risk-Agent-Portable"
$AppDir = Join-Path $OutRoot "app"

Write-Host ""
Write-Host "  XHS Risk Agent portable build" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $OutRoot) { Remove-Item $OutRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

$copyItems = @(
    @{Src = Join-Path $Tools "local_risk_agent.py"; Dst = "tools\local_risk_agent.py"},
    @{Src = Join-Path $Tools "local_risk_agent_modes.py"; Dst = "tools\local_risk_agent_modes.py"},
    @{Src = Join-Path $Tools "portable_paths.py"; Dst = "tools\portable_paths.py"},
    @{Src = Join-Path $XhsRoot "cloud_deploy\crawler_runtime"; Dst = "cloud_deploy\crawler_runtime"},
    @{Src = Join-Path $XhsRoot "cloud_deploy\cloud_api\agent_service.py"; Dst = "cloud_deploy\cloud_api\agent_service.py"},
    @{Src = Join-Path $XhsRoot "cloud_deploy\cloud_api\config.py"; Dst = "cloud_deploy\cloud_api\config.py"},
    @{Src = Join-Path $XhsRoot "cloud_deploy\scripts\bootstrap_env.py"; Dst = "cloud_deploy\scripts\bootstrap_env.py"}
)
foreach ($item in $copyItems) {
    $dest = Join-Path $AppDir $item.Dst
    if (Test-Path $item.Src -PathType Container) {
        Copy-Item $item.Src $dest -Recurse -Force
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item $item.Src $dest -Force
    }
}
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "cloud_deploy\cloud_api") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "cloud_deploy\scripts") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $AppDir "cloud_deploy\__init__.py") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $AppDir "cloud_deploy\cloud_api\__init__.py") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $AppDir "cloud_deploy\scripts\__init__.py") | Out-Null

Write-Host "[1/4] copied app payload" -ForegroundColor Green

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "Python 3.10+ required" }

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    python -m pip install pyinstaller 2>&1 | Out-Null
}

Write-Host "[2/4] building agent exe..." -ForegroundColor Yellow
Push-Location $Tools
python -m PyInstaller --noconfirm --clean xhs_risk_agent.spec
if ($LASTEXITCODE -ne 0) { throw "agent build failed" }

$agentBuild = Join-Path $Tools "dist\XHS-Risk-Agent"
if (Test-Path $agentBuild) {
    Copy-Item "$agentBuild\*" $AppDir -Recurse -Force
    Write-Host "      agent exe copied" -ForegroundColor Green
}

Write-Host "[3/4] building setup exe..." -ForegroundColor Yellow
python -m PyInstaller --noconfirm --clean xhs_risk_agent_setup.spec
$setupExe = Join-Path $Tools "dist\XHS-Risk-Agent-Setup.exe"
if (-not (Test-Path $setupExe)) { throw "setup build failed" }
Copy-Item $setupExe $OutRoot -Force
Pop-Location

$readme = @'
# XHS Local Risk Agent Portable
# 1. Run XHS-Risk-Agent-Setup.exe on target Windows PC
# 2. API: https://monitor.xhs365.cn
# 3. Agent Key: same as server XHS_LOCAL_AGENT_KEY
# 4. Agent ID: unique per PC (e.g. home-bd-2)
# 5. Recommended: api_only, batch 80
'@
$readme | Set-Content -Path (Join-Path $OutRoot "README.txt") -Encoding UTF8

$zip = Join-Path $XhsRoot "dist\XHS-Risk-Agent-Portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$OutRoot\*" -DestinationPath $zip -Force

Write-Host "[4/4] done" -ForegroundColor Green
Write-Host "  out: $OutRoot"
Write-Host "  zip: $zip"
