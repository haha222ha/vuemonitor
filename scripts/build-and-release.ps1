$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.ScriptName
$CLIENT_DIR = Join-Path $PROJECT_ROOT "client"
$RELEASE_DIR = Join-Path $CLIENT_DIR "release"
$DEPLOY_DIR = Join-Path $PROJECT_ROOT "deploy"
$DOWNLOADS_DIR = Join-Path $DEPLOY_DIR "downloads"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  XHS365 客户端构建与发布脚本" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $CLIENT_DIR)) {
    Write-Host "[ERROR] 客户端目录不存在: $CLIENT_DIR" -ForegroundColor Red
    exit 1
}

Push-Location $CLIENT_DIR

Write-Host "[1/5] 安装依赖..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] npm install 失败" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "[2/5] 构建客户端代码..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] 构建失败" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "[3/5] 打包安装程序..." -ForegroundColor Yellow
Write-Host "  目标平台: Windows (NSIS + Portable)" -ForegroundColor Gray

npm run dist -- --win
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Windows 打包失败，可能当前环境不支持" -ForegroundColor Yellow
}

Pop-Location

Write-Host ""
Write-Host "[4/5] 整理发布文件..." -ForegroundColor Yellow

if (-not (Test-Path $DOWNLOADS_DIR)) {
    New-Item -ItemType Directory -Path $DOWNLOADS_DIR -Force | Out-Null
    Write-Host "  创建下载目录: $DOWNLOADS_DIR" -ForegroundColor Gray
}

$version = "0.1.0"
$packageJson = Get-Content (Join-Path $CLIENT_DIR "package.json") -Raw | ConvertFrom-Json
if ($packageJson.version) {
    $version = $packageJson.version
}

Write-Host "  版本号: $version" -ForegroundColor Gray

if (Test-Path $RELEASE_DIR) {
    $files = Get-ChildItem -Path $RELEASE_DIR -Recurse -File | Where-Object {
        $_.Extension -in ".exe", ".dmg", ".zip", ".AppImage", ".deb", ".rpm", ".yml", ".json"
    }

    foreach ($file in $files) {
        $destName = $file.Name
        $destPath = Join-Path $DOWNLOADS_DIR $destName

        if ($file.Extension -in ".exe", ".dmg", ".AppImage", ".deb", ".rpm") {
            $platformDir = switch ($file.Extension) {
                ".exe" { "windows" }
                ".dmg" { "macos" }
                ".AppImage" { "linux" }
                ".deb" { "linux" }
                ".rpm" { "linux" }
                default { "other" }
            }

            $platformPath = Join-Path $DOWNLOADS_DIR $platformDir
            if (-not (Test-Path $platformPath)) {
                New-Item -ItemType Directory -Path $platformPath -Force | Out-Null
            }
            $destPath = Join-Path $platformPath $destName
        }

        Copy-Item $file.FullName -Destination $destPath -Force
        $sizeMB = [math]::Round($file.Length / 1MB, 2)
        Write-Host "  复制: $($file.Name) ($sizeMB MB)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "[5/5] 生成版本清单..." -ForegroundColor Yellow

$manifest = @{
    version = $version
    releaseDate = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    platforms = @{}
}

$windowsDir = Join-Path $DOWNLOADS_DIR "windows"
if (Test-Path $windowsDir) {
    $exeFiles = Get-ChildItem $windowsDir -Filter "*.exe"
    if ($exeFiles.Count -gt 0) {
        $manifest.platforms.windows = @{}
        foreach ($f in $exeFiles) {
            $installerType = if ($f.Name -match "Setup") { "installer" } else { "portable" }
            $manifest.platforms.windows[$installerType] = @{
                filename = $f.Name
                size = $f.Length
                url = "/downloads/windows/$($f.Name)"
                sha256 = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
            }
        }
    }
}

$macosDir = Join-Path $DOWNLOADS_DIR "macos"
if (Test-Path $macosDir) {
    $dmgFiles = Get-ChildItem $macosDir -Filter "*.dmg"
    if ($dmgFiles.Count -gt 0) {
        $manifest.platforms.macos = @{}
        foreach ($f in $dmgFiles) {
            $manifest.platforms.macos["dmg"] = @{
                filename = $f.Name
                size = $f.Length
                url = "/downloads/macos/$($f.Name)"
                sha256 = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
            }
        }
    }
}

$linuxDir = Join-Path $DOWNLOADS_DIR "linux"
if (Test-Path $linuxDir) {
    $appImageFiles = Get-ChildItem $linuxDir -Filter "*.AppImage"
    if ($appImageFiles.Count -gt 0) {
        $manifest.platforms.linux = @{}
        foreach ($f in $appImageFiles) {
            $ext = $f.Extension.TrimStart(".")
            $manifest.platforms.linux[$ext] = @{
                filename = $f.Name
                size = $f.Length
                url = "/downloads/linux/$($f.Name)"
                sha256 = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
            }
        }
    }
}

$manifestPath = Join-Path $DOWNLOADS_DIR "latest.json"
$manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8
Write-Host "  版本清单: $manifestPath" -ForegroundColor Gray

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  构建完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "发布文件位于: $DOWNLOADS_DIR" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 将 deploy/ 目录上传到服务器" -ForegroundColor White
Write-Host "  2. 配置 Nginx 指向 downloads/ 目录" -ForegroundColor White
Write-Host "  3. 客户端通过 https://your-domain.com/downloads/latest.json 检查更新" -ForegroundColor White