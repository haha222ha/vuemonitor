@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=%~dp0..
start "" pythonw "%~dp0local_agent_gui.py" 2>nul || (
    echo Python not found. Trying python.exe...
    start "" python "%~dp0local_agent_gui.py"
)
