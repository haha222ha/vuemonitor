@echo off
chcp 65001 >nul
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File tools\build_portable_agent.ps1
pause
