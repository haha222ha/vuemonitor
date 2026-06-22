#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XHS 本地 Risk Agent — 一键安装向导（可 PyInstaller 打包为 Setup.exe）。

用法:
  python tools/local_agent_setup_wizard.py
  或双击 XHS-Risk-Agent-Setup.exe
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from portable_paths import bundle_root, default_install_dir, is_frozen, log_dir

TASK_NAME = "XHS-Local-Risk-Agent"
DEFAULT_API = "https://monitor.xhs365.cn"


def _payload_dir() -> Path:
    root = bundle_root()
    for cand in (root.parent / "app", root / "app", root):
        if (cand / "cloud_deploy").is_dir():
            return cand
    return root


def _agent_exe(install_dir: Path) -> Path:
    for name in ("XHS-Risk-Agent.exe", "xhs-risk-agent.exe", "local_risk_agent.exe"):
        p = install_dir / name
        if p.is_file():
            return p
    return install_dir / "XHS-Risk-Agent.exe"


def _copy_payload(dest: Path, log_fn) -> None:
    src = _payload_dir()
    dest.mkdir(parents=True, exist_ok=True)
    log_fn(f"复制程序文件: {src} -> {dest}")
    for item in src.iterdir():
        if item.name.lower() in ("xhs-risk-agent-setup.exe", "local_agent_setup_wizard.py"):
            continue
        dst = dest / item.name
        if item.is_dir():
            if dst.exists():
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)


def _write_config(dest: Path, values: dict[str, str]) -> Path:
    cfg = dest / "local_agent.env"
    lines = [
        f"XHS_CLOUD_API_URL={values['api_url']}",
        f"XHS_LOCAL_AGENT_KEY={values['agent_key']}",
        f"XHS_LOCAL_AGENT_ID={values['agent_id']}",
        f"XHS_LOCAL_AGENT_BATCH={values['batch']}",
        f"XHS_LOCAL_AGENT_CONCURRENCY={values['concurrency']}",
        f"XHS_LOCAL_AGENT_MODE={values['mode']}",
        f"XHS_LOCAL_AGENT_IDLE_SEC={values['idle_sec']}",
        f"XHS_LOCAL_AGENT_COOLDOWN_SEC={values['cooldown_sec']}",
        f"XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC={values['cycle_cooldown_sec']}",
        f"XHS_LOCAL_AGENT_MIN_AGE_HOURS={values['min_age_hours']}",
    ]
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_cfg = log_dir() / "local_agent.env"
    log_cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cfg


def _test_api(api_url: str, agent_key: str, agent_id: str) -> tuple[bool, str]:
    url = (
        f"{api_url.rstrip('/')}/api/v1/agent/risk-worklist"
        f"?limit=1&agent_id={agent_id}&min_age_hours=2"
    )
    req = urllib.request.Request(
        url,
        headers={"X-Agent-Key": agent_key, "User-Agent": "xhs-risk-agent-setup/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        pending = data.get("pending_risk")
        items = len(data.get("items") or [])
        return True, f"连接成功 pending={pending} 本批样例={items}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def _register_task(install_dir: Path, cfg: Path, log_fn) -> None:
    agent = _agent_exe(install_dir)
    wrapper = log_dir() / "run_agent.bat"
    if agent.is_file():
        cmd = f'"{agent}" run'
        work = install_dir
    else:
        py = shutil.which("pythonw") or shutil.which("python")
        if not py:
            raise RuntimeError("未找到 Agent 可执行文件，也未找到 Python")
        script = install_dir / "tools" / "local_risk_agent.py"
        if not script.is_file():
            script = bundle_root() / "tools" / "local_risk_agent.py"
        cmd = f'"{py}" "{script}" run'
        work = install_dir

    bat = f"""@echo off
set XHS_RISK_AGENT_HOME={install_dir}
set XHS_CLOUD_ROOT={install_dir}
set XHS_CRAWLER_ROOT={install_dir}\\cloud_deploy\\crawler_runtime
set XHS_LOCAL_AGENT_ENV={cfg}
set XHS_LOCAL_AGENT_LOG_DIR={log_dir()}
set XHS_ENABLE_PLAYWRIGHT=0
cd /d "{work}"
{cmd}
"""
    wrapper.write_text(bat, encoding="ascii")
    log_fn(f"计划任务包装: {wrapper}")

    ps = f"""
$Action = New-ScheduledTaskAction -Execute '{wrapper}' -WorkingDirectory '{log_dir()}'
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
Start-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )
    log_fn(f"已注册并启动计划任务: {TASK_NAME}")


class SetupApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XHS 本地 Risk Agent 安装向导")
        self.geometry("620x520")
        self.resizable(False, False)

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="云端 API 地址").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.api_url = tk.StringVar(value=DEFAULT_API)
        ttk.Entry(frm, textvariable=self.api_url, width=52).grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Agent Key（与服务器一致）").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.agent_key = tk.StringVar()
        ttk.Entry(frm, textvariable=self.agent_key, width=52, show="*").grid(row=1, column=1, pady=4)

        ttk.Label(frm, text="本机 ID（每台电脑不同）").grid(row=2, column=0, sticky=tk.W, pady=4)
        default_id = os.environ.get("COMPUTERNAME", "home-pc-2")
        self.agent_id = tk.StringVar(value=default_id)
        ttk.Entry(frm, textvariable=self.agent_id, width=52).grid(row=2, column=1, pady=4)

        ttk.Label(frm, text="采集模式").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.mode = tk.StringVar(value="api_only")
        ttk.Combobox(
            frm,
            textvariable=self.mode,
            values=("api_only", "api_then_browser"),
            state="readonly",
            width=49,
        ).grid(row=3, column=1, pady=4)

        ttk.Label(frm, text="每批条数").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.batch = tk.StringVar(value="80")
        ttk.Entry(frm, textvariable=self.batch, width=52).grid(row=4, column=1, pady=4)

        ttk.Label(frm, text="安装目录").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.install_dir = tk.StringVar(value=str(default_install_dir()))
        ttk.Entry(frm, textvariable=self.install_dir, width=52).grid(row=5, column=1, pady=4)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, pady=10, sticky=tk.EW)
        ttk.Button(btns, text="测试连接", command=self.on_test).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="一键安装并启动", command=self.on_install).pack(side=tk.LEFT, padx=4)

        self.log = scrolledtext.ScrolledText(frm, height=14, state=tk.DISABLED)
        self.log.grid(row=7, column=0, columnspan=2, sticky=tk.NSEW)
        frm.rowconfigure(7, weight=1)
        frm.columnconfigure(1, weight=1)

        self._log(f"打包模式: {'exe' if is_frozen() else '源码'}")
        self._log(f"默认安装到: {default_install_dir()}")
        self._log("提示: 第二台电脑请填写不同的「本机 ID」，避免与云服务器抢同一批工单。")

    def _log(self, msg: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _values(self) -> dict[str, str]:
        return {
            "api_url": self.api_url.get().strip(),
            "agent_key": self.agent_key.get().strip(),
            "agent_id": self.agent_id.get().strip(),
            "mode": self.mode.get().strip() or "api_only",
            "batch": self.batch.get().strip() or "80",
            "concurrency": "3",
            "idle_sec": "300",
            "cooldown_sec": "15",
            "cycle_cooldown_sec": "7200",
            "min_age_hours": "2",
        }

    def on_test(self) -> None:
        v = self._values()
        if len(v["agent_key"]) < 16:
            messagebox.showerror("错误", "请填写完整的 Agent Key")
            return
        ok, msg = _test_api(v["api_url"], v["agent_key"], v["agent_id"])
        self._log(msg)
        if ok:
            messagebox.showinfo("测试", msg)
        else:
            messagebox.showerror("测试失败", msg)

    def on_install(self) -> None:
        v = self._values()
        if len(v["agent_key"]) < 16:
            messagebox.showerror("错误", "请填写完整的 Agent Key")
            return
        dest = Path(self.install_dir.get().strip() or str(default_install_dir()))
        try:
            self._log("--- 开始安装 ---")
            _copy_payload(dest, self._log)
            cfg = _write_config(dest, v)
            self._log(f"配置已写入: {cfg}")
            ok, msg = _test_api(v["api_url"], v["agent_key"], v["agent_id"])
            self._log(f"连接测试: {msg}")
            if not ok:
                if not messagebox.askyesno("连接失败", f"{msg}\n仍要继续安装吗？"):
                    return
            _register_task(dest, cfg, self._log)
            self._log("安装完成！Agent 已在后台运行，开机自动启动。")
            self._log(f"日志: {log_dir() / 'agent.log'}")
            messagebox.showinfo("完成", "安装成功！\nAgent 已启动，开机自动运行。")
        except Exception as exc:
            self._log(f"安装失败: {exc}")
            messagebox.showerror("安装失败", str(exc))


def main() -> None:
    if sys.platform != "win32":
        print("仅支持 Windows", file=sys.stderr)
        raise SystemExit(1)
    app = SetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
