@echo off
chcp 65001 >nul 2>&1
title VueMonitor 一键部署

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       VueMonitor 一键部署工具 v0.1       ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ===== 检查管理员权限 =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] 需要管理员权限，正在请求提权...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ===== 检查并安装 Chocolatey =====
where choco >nul 2>&1
if %errorlevel% neq 0 (
    echo  [1/7] 安装 Chocolatey 包管理器...
    powershell -NoProfile -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    refreshenv >nul 2>&1
) else (
    echo  [1/7] Chocolatey .............. 已安装
)

:: ===== 安装基础依赖 =====
echo  [2/7] 检查并安装基础依赖...

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 Git...
    choco install git -y >nul 2>&1
) else (
    echo       Git .................... 已安装
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 Python 3.11...
    choco install python311 -y >nul 2>&1
) else (
    echo       Python ................. 已安装
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 Node.js 20...
    choco install nodejs-lts -y >nul 2>&1
) else (
    echo       Node.js ................ 已安装
)

where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 PostgreSQL 16...
    choco install postgresql16 --params '/Password:saas_pass' -y >nul 2>&1
) else (
    echo       PostgreSQL ............. 已安装
)

where redis-cli >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 Redis...
    choco install redis-64 -y >nul 2>&1
) else (
    echo       Redis .................. 已安装
)

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo       安装 Docker Desktop...
    choco install docker-desktop -y >nul 2>&1
) else (
    echo       Docker ................. 已安装
)

:: ===== 刷新环境变量 =====
call refreshenv >nul 2>&1
set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts;C:\Program Files\PostgreSQL\16\bin;C:\Program Files\Redis"

:: ===== 安装 Poetry =====
where poetry >nul 2>&1
if %errorlevel% neq 0 (
    echo  [3/7] 安装 Poetry...
    pip install poetry -q
) else (
    echo  [3/7] Poetry ................. 已安装
)

:: ===== 配置数据库 =====
echo  [4/7] 配置 PostgreSQL 数据库...

set PGPASSWORD=saas_pass
psql -U postgres -c "SELECT 1 FROM pg_roles WHERE rolname='saas_user'" 2>nul | findstr "1" >nul
if %errorlevel% neq 0 (
    psql -U postgres -c "CREATE USER saas_user WITH PASSWORD 'saas_pass';" 2>nul
    psql -U postgres -c "CREATE DATABASE vuemonitor OWNER saas_user;" 2>nul
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE vuemonitor TO saas_user;" 2>nul
    echo       数据库和用户创建完成
) else (
    echo       数据库已存在，跳过
)

:: 初始化 Schema
psql -U saas_user -d vuemonitor -h localhost -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='users';" 2>nul | findstr "0" >nul
if %errorlevel% equ 0 (
    psql -U saas_user -d vuemonitor -h localhost -f "%~dp0database\schema.sql" 2>nul
    psql -U saas_user -d vuemonitor -h localhost -f "%~dp0database\seed.sql" 2>nul
    echo       数据库 Schema 初始化完成
) else (
    echo       Schema 已存在，跳过
)

:: ===== 生成安全密钥 =====
echo  [5/7] 生成安全密钥并配置环境...

if not exist "%~dp0server\.env" (
    for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set JWT_SECRET=%%i
    for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set JWT_REFRESH=%%i
    for /f %%i in ('python -c "import secrets; print(secrets.token_hex(16))"') do set ENC_KEY=%%i

    (
        echo APP_NAME=VueMonitor
        echo APP_VERSION=0.1.0
        echo DEBUG=true
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo DB_NAME=vuemonitor
        echo DB_USER=saas_user
        echo DB_PASSWORD=saas_pass
        echo REDIS_HOST=localhost
        echo REDIS_PORT=6379
        echo JWT_SECRET=%JWT_SECRET%
        echo JWT_REFRESH_SECRET=%JWT_REFRESH%
        echo JWT_ALGORITHM=HS256
        echo JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
        echo ENCRYPTION_KEY=%ENC_KEY%
        echo AI_DEFAULT_PROVIDER=openai
        echo AI_DEFAULT_MODEL=gpt-4o-mini
        echo OPENAI_API_KEY=
        echo DEEPSEEK_API_KEY=
        echo CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]
    ) > "%~dp0server\.env"
    echo       .env 已生成（含自动生成的安全密钥）
) else (
    echo       .env 已存在，跳过
)

if not exist "%~dp0client\.env" (
    echo VITE_API_BASE_URL=http://localhost:8000/api/v1 > "%~dp0client\.env"
)
if not exist "%~dp0web-admin\.env" (
    echo VITE_API_BASE_URL=http://localhost:8000/api/v1 > "%~dp0web-admin\.env"
)

:: ===== 安装项目依赖 =====
echo  [6/7] 安装项目依赖...

echo       服务端依赖...
cd /d "%~dp0server"
poetry install --no-interaction 2>nul
if %errorlevel% neq 0 (
    pip install fastapi uvicorn[standard] sqlalchemy alembic asyncpg psycopg2-binary pydantic pydantic-settings python-jose[cryptography] python-multipart aiohttp redis apscheduler jinja2 openai langchain-core structlog httpx bcrypt pycryptodome pytest pytest-asyncio 2>nul
)

echo       客户端依赖...
cd /d "%~dp0client"
call npm install --legacy-peer-deps 2>nul

echo       管理后台依赖...
cd /d "%~dp0web-admin"
call npm install --legacy-peer-deps 2>nul

:: ===== 启动服务 =====
echo  [7/7] 启动所有服务...
echo.

:: 启动 Redis（如果未运行）
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    start "Redis" redis-server
    timeout /t 2 >nul
)

:: 启动服务端
cd /d "%~dp0server"
start "VueMonitor-Server" cmd /k "poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>nul || python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

:: 启动客户端
cd /d "%~dp0client"
start "VueMonitor-Client" cmd /k "npm run dev"
timeout /t 2 >nul

:: 启动管理后台
cd /d "%~dp0web-admin"
start "VueMonitor-Admin" cmd /k "npm run dev"

:: ===== 完成 =====
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          🎉 部署完成！                    ║
echo  ╠══════════════════════════════════════════╣
echo  ║  API 文档:   http://localhost:8000/docs  ║
echo  ║  客户端:     http://localhost:5173       ║
echo  ║  管理后台:   http://localhost:5174       ║
echo  ╠══════════════════════════════════════════╣
echo  ║  如需配置 AI 分析，请编辑:               ║
echo  ║  server\.env 中的 OPENAI_API_KEY         ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
