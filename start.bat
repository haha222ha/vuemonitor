@echo off
chcp 65001 >nul 2>&1
title XHS365 启动

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       XHS365 服务启动                    ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查 Redis
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo  启动 Redis...
    start "Redis" redis-server
    timeout /t 2 >nul
)

:: 检查 .env
if not exist "%~dp0server\.env" (
    echo  [!] 未找到 server\.env，正在从模板创建...
    copy "%~dp0server\.env.example" "%~dp0server\.env" >nul
    echo      请编辑 server\.env 配置你的密钥和 API Key
)

:: 启动服务端
echo  启动 API 服务 (端口 8000)...
cd /d "%~dp0server"
start "XHS365-API" cmd /k "poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>nul || python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

:: 启动客户端
echo  启动客户端 (端口 5173)...
cd /d "%~dp0client"
start "XHS365-Client" cmd /k "npm run dev"
timeout /t 2 >nul

:: 启动管理后台
echo  启动管理后台 (端口 5174)...
cd /d "%~dp0web-admin"
start "XHS365-Admin" cmd /k "npm run dev"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          ✓ 全部启动完成                   ║
echo  ╠══════════════════════════════════════════╣
echo  ║  API 文档:   http://localhost:8000/docs  ║
echo  ║  客户端:     http://localhost:5173       ║
echo  ║  管理后台:   http://localhost:5174       ║
echo  ╚══════════════════════════════════════════╝
echo.
