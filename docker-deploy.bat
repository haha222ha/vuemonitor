@echo off
chcp 65001 >nul 2>&1
title VueMonitor Docker 一键部署

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     VueMonitor Docker 一键部署            ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查 Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] 未检测到 Docker，正在安装 Docker Desktop...
    powershell -Command "Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe' -OutFile '%TEMP%\docker-installer.exe'; Start-Process '%TEMP%\docker-installer.exe' -Wait"
    echo      安装完成，请重启电脑后重新运行此脚本
    pause
    exit /b 1
)

:: 生成安全密钥
if not exist "%~dp0.env" (
    echo  生成安全密钥...
    for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set JWT_SECRET=%%i
    for /f %%i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set JWT_REFRESH=%%i
    for /f %%i in ('python -c "import secrets; print(secrets.token_hex(16))"') do set ENC_KEY=%%i

    (
        echo DB_NAME=vuemonitor
        echo DB_USER=saas_user
        echo DB_PASSWORD=saas_pass
        echo JWT_SECRET=%JWT_SECRET%
        echo JWT_REFRESH_SECRET=%JWT_REFRESH%
        echo ENCRYPTION_KEY=%ENC_KEY%
        echo OPENAI_API_KEY=
        echo DEEPSEEK_API_KEY=
    ) > "%~dp0.env"
    echo      .env 已生成
) else (
    echo      .env 已存在，跳过
)

:: 构建并启动
echo  构建并启动 Docker 容器...
docker compose up -d --build

if %errorlevel% neq 0 (
    echo  ❌ 启动失败，请检查 Docker 是否正常运行
    pause
    exit /b 1
)

echo.
echo  等待服务就绪...
timeout /t 10 >nul

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          🎉 部署完成！                    ║
echo  ╠══════════════════════════════════════════╣
echo  ║  管理后台:   http://localhost            ║
echo  ║  API 文档:   http://localhost/docs       ║
echo  ║  PostgreSQL: localhost:5432              ║
echo  ║  Redis:      localhost:6379              ║
echo  ╠══════════════════════════════════════════╣
echo  ║  停止:  docker compose down              ║
echo  ║  日志:  docker compose logs -f           ║
echo  ║  重启:  docker compose restart           ║
echo  ╚══════════════════════════════════════════╝
echo.

:: 自动打开浏览器
start http://localhost
pause
