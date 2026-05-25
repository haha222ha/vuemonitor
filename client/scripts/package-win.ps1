# Sprint 2: Windows Electron package (run on dev machine, not 2G server)
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ">>> XHS365 Windows package" -ForegroundColor Cyan

if (-not $SkipBuild) {
    npm run build
}

$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
npm run dist -- --win nsis --x64

$setup = Get-ChildItem -Path "$Root\release" -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($setup) {
    $dest = "$Root\..\deploy\downloads"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item $setup.FullName -Destination "$dest\XHS365-Setup-latest.exe" -Force
    Write-Host "OK: $($setup.FullName)" -ForegroundColor Green
    Write-Host "Copied to deploy/downloads/XHS365-Setup-latest.exe"
} else {
    Write-Host "FAIL: no exe in release/" -ForegroundColor Red
    exit 1
}
