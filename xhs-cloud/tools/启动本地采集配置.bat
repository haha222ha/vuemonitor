@echo off
chcp 65001 >nul
cd /d "%~dp0.."
start "" pythonw "%~dp0local_agent_gui.py" 2>nul || (
    echo 未找到 Python，尝试用 python 启动...
    python "%~dp0local_agent_gui.py"
)