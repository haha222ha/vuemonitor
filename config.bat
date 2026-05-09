@echo off
chcp 65001 >nul 2>&1
title VueMonitor 配置工具

:MENU
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       VueMonitor 配置工具                 ║
echo  ╠══════════════════════════════════════════╣
echo  ║                                          ║
echo  ║  1. 修改服务器地址（API 地址）             ║
echo  ║  2. 配置 AI 密钥（OpenAI/DeepSeek）       ║
echo  ║  3. 修改数据库密码                        ║
echo  ║  4. 查看当前配置                          ║
echo  ║  5. 重置为默认配置                        ║
echo  ║  0. 退出                                 ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.
set /p "CHOICE=请选择 [0-5]: "

if "%CHOICE%"=="1" goto SET_SERVER
if "%CHOICE%"=="2" goto SET_AI
if "%CHOICE%"=="3" goto SET_DB
if "%CHOICE%"=="4" goto SHOW_CONFIG
if "%CHOICE%"=="5" goto RESET_CONFIG
if "%CHOICE%"=="0" exit /b 0
goto MENU

:SET_SERVER
echo.
echo  ┌──────────────────────────────────────────┐
echo  │  当前服务器地址配置                        │
echo  │                                          │
echo  │  客户端和管理后台通过这个地址连接后端API    │
echo  │                                          │
echo  │  本地开发:    http://localhost:8000        │
echo  │  远程服务器:  http://123.45.67.89:8000     │
echo  │  域名:        https://api.example.com      │
echo  └──────────────────────────────────────────┘
echo.
set /p "SERVER_URL=请输入新的服务器地址: "

if "%SERVER_URL%"=="" (
    echo  [!] 未输入，取消修改
    pause
    goto MENU
)

echo VITE_API_BASE_URL=%SERVER_URL%/api/v1> "%~dp0client\.env"
echo VITE_API_BASE_URL=%SERVER_URL%/api/v1> "%~dp0web-admin\.env"

echo.
echo  ✓ 已更新:
echo    client\.env    → VITE_API_BASE_URL=%SERVER_URL%/api/v1
echo    web-admin\.env → VITE_API_BASE_URL=%SERVER_URL%/api/v1
echo.
echo  [!] 如果服务端在远程服务器，还需要修改 server\.env 中的:
echo    CORS_ORIGINS — 添加客户端的访问地址
echo.
pause
goto MENU

:SET_AI
echo.
echo  ┌──────────────────────────────────────────┐
echo  │  AI 服务密钥配置                          │
echo  │                                          │
echo  │  至少配置一个即可使用 AI 分析功能           │
echo  │  留空跳过不修改                            │
echo  └──────────────────────────────────────────┘
echo.

set /p "OPENAI_KEY=OpenAI API Key (留空跳过): "
set /p "DEEPSEEK_KEY=DeepSeek API Key (留空跳过): "

if not exist "%~dp0server\.env" (
    echo  [!] server\.env 不存在，请先运行 setup.bat
    pause
    goto MENU
)

if not "%OPENAI_KEY%"=="" (
    powershell -Command "(Get-Content '%~dp0server\.env') -replace '^OPENAI_API_KEY=.*', 'OPENAI_API_KEY=%OPENAI_KEY%' | Set-Content '%~dp0server\.env'"
    echo  ✓ OPENAI_API_KEY 已更新
)
if not "%DEEPSEEK_KEY%"=="" (
    powershell -Command "(Get-Content '%~dp0server\.env') -replace '^DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=%DEEPSEEK_KEY%' | Set-Content '%~dp0server\.env'"
    echo  ✓ DEEPSEEK_API_KEY 已更新
)
echo.
pause
goto MENU

:SET_DB
echo.
echo  ┌──────────────────────────────────────────┐
echo  │  数据库密码修改                            │
echo  │                                          │
echo  │  会同时修改 .env 和 PostgreSQL             │
echo  └──────────────────────────────────────────┘
echo.
set /p "NEW_PASS=请输入新的数据库密码: "

if "%NEW_PASS%"=="" (
    echo  [!] 未输入，取消修改
    pause
    goto MENU
)

powershell -Command "(Get-Content '%~dp0server\.env') -replace '^DB_PASSWORD=.*', 'DB_PASSWORD=%NEW_PASS%' | Set-Content '%~dp0server\.env'"
echo  ✓ server\.env 中 DB_PASSWORD 已更新

set PGPASSWORD=saas_pass
psql -U saas_user -d vuemonitor -c "ALTER USER saas_user WITH PASSWORD '%NEW_PASS%';" 2>nul
if %errorlevel% equ 0 (
    echo  ✓ PostgreSQL 用户密码已更新
) else (
    echo  [!] PostgreSQL 密码修改失败，请手动执行:
    echo      psql -U saas_user -d vuemonitor -c "ALTER USER saas_user WITH PASSWORD '新密码';"
)
echo.
pause
goto MENU

:SHOW_CONFIG
echo.
echo  ════════════════════════════════════════════
echo  当前配置
echo  ════════════════════════════════════════════
echo.

if exist "%~dp0server\.env" (
    echo  [ server\.env ]
    for /f "tokens=1,* delims==" %%a in ('type "%~dp0server\.env" ^| findstr /v "^#" ^| findstr /v "^$"') do (
        echo    %%a=%%b
    )
    echo.
) else (
    echo  [!] server\.env 不存在
    echo.
)

if exist "%~dp0client\.env" (
    echo  [ client\.env ]
    type "%~dp0client\.env"
    echo.
) else (
    echo  [!] client\.env 不存在
    echo.
)

if exist "%~dp0web-admin\.env" (
    echo  [ web-admin\.env ]
    type "%~dp0web-admin\.env"
    echo.
) else (
    echo  [!] web-admin\.env 不存在
    echo.
)

pause
goto MENU

:RESET_CONFIG
echo.
echo  [!] 这将重置所有 .env 文件为默认值，确定吗？
set /p "CONFIRM=输入 YES 确认: "

if not "%CONFIRM%"=="YES" (
    echo  已取消
    pause
    goto MENU
)

copy "%~dp0server\.env.example" "%~dp0server\.env" >nul 2>&1
echo VITE_API_BASE_URL=http://localhost:8000/api/v1> "%~dp0client\.env"
echo VITE_API_BASE_URL=http://localhost:8000/api/v1> "%~dp0web-admin\.env"

echo  ✓ 所有配置已重置为默认值
echo.
pause
goto MENU
