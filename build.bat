@echo off
chcp 65001 >nul 2>&1
title VueMonitor 一键构建

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       VueMonitor 一键构建打包             ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ===== 配置服务器地址 =====
set "SERVER_URL=%~1"

if "%SERVER_URL%"=="" (
    echo  ┌──────────────────────────────────────────┐
    echo  │  请输入你的服务器地址（API 所在地址）       │
    echo  │                                          │
    echo  │  本地开发输入:  http://localhost:8000      │
    echo  │  远程服务器输入: http://你的IP:8000        │
    echo  │  域名输入:      https://api.example.com   │
    echo  └──────────────────────────────────────────┘
    echo.
    set /p "SERVER_URL=服务器地址: "
)

if "%SERVER_URL%"=="" (
    echo  [!] 未输入服务器地址，使用默认值 http://localhost:8000
    set "SERVER_URL=http://localhost:8000"
)

echo.
echo  服务器地址: %SERVER_URL%
echo.

:: ===== 写入客户端配置 =====
echo  [0/3] 写入服务器地址配置...
echo VITE_API_BASE_URL=%SERVER_URL%/api/v1> "%~dp0client\.env"
echo       ✓ client\.env → VITE_API_BASE_URL=%SERVER_URL%/api/v1

:: ===== 写入管理后台配置 =====
echo VITE_API_BASE_URL=%SERVER_URL%/api/v1> "%~dp0web-admin\.env"
echo       ✓ web-admin\.env → VITE_API_BASE_URL=%SERVER_URL%/api/v1

:: ===== 1. 构建管理后台 =====
echo  [1/3] 构建 Web 管理后台...
cd /d "%~dp0web-admin"
call npm run build
if %errorlevel% neq 0 (
    echo       ❌ 管理后台构建失败
    pause
    exit /b 1
)
echo       ✓ 管理后台构建完成 → web-admin\dist\

:: ===== 2. 构建客户端前端 =====
echo  [2/3] 构建 Electron 客户端前端...
cd /d "%~dp0client"
call npm run build
if %errorlevel% neq 0 (
    echo       ❌ 客户端前端构建失败
    pause
    exit /b 1
)
echo       ✓ 客户端前端构建完成 → client\dist\

:: ===== 3. 打包 Electron 安装程序 =====
echo  [3/3] 打包 Electron 安装程序...
cd /d "%~dp0client"
call npx electron-builder --win
if %errorlevel% neq 0 (
    echo       ❌ Electron 打包失败
    pause
    exit /b 1
)
echo       ✓ 安装程序打包完成 → client\release\

:: ===== 完成 =====
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          🎉 构建完成！                    ║
echo  ╠══════════════════════════════════════════╣
echo  ║  服务器地址:  %SERVER_URL%               ║
echo  ║  管理后台:    web-admin\dist\            ║
echo  ║  安装程序:    client\release\            ║
echo  ╠══════════════════════════════════════════╣
echo  ║  安装程序会自动连接到上面的服务器地址       ║
echo  ╚══════════════════════════════════════════╝
echo.

explorer "%~dp0client\release"
pause
