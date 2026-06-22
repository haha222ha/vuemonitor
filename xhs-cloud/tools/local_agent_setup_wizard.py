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
import time
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


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _existing_config() -> dict[str, str]:
    for cand in (
        log_dir() / "local_agent.env",
        default_install_dir() / "local_agent.env",
    ):
        data = _parse_env_file(cand)
        if data:
            return data
    return {}


def _stop_running_agent(log_fn) -> None:
    _run_hidden(["schtasks", "/End", "/TN", TASK_NAME])
    for img in ("XHS-Risk-Agent.exe", "local_risk_agent.exe"):
        proc = _run_hidden(["taskkill", "/IM", img, "/F", "/T"])
        if proc.returncode == 0:
            log_fn(f"已停止运行中的 {img}")
    time.sleep(1)


def _install_ready(dest: Path) -> bool:
    return (dest / "cloud_deploy").is_dir() and (
        _agent_exe(dest).is_file() or (dest / "tools" / "local_risk_agent.py").is_file()
    )


def _copy_payload(dest: Path, log_fn, *, update_only: bool = False) -> None:
    if update_only and _install_ready(dest):
        log_fn(f"已安装版本存在，跳过复制程序文件: {dest}")
        return

    _stop_running_agent(log_fn)
    src = _payload_dir()
    dest.mkdir(parents=True, exist_ok=True)
    log_fn(f"复制程序文件: {src} -> {dest}")
    for item in src.iterdir():
        if item.name.lower() in ("xhs-risk-agent-setup.exe", "local_agent_setup_wizard.py"):
            continue
        dst = dest / item.name
        try:
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
        except OSError as exc:
            if _install_ready(dest):
                log_fn(f"跳过被占用的文件 {item.name}: {exc}")
                continue
            raise


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


def _write_wrapper_bat(install_dir: Path, cfg: Path) -> Path:
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
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(bat, encoding="utf-8")
    return wrapper


def _run_hidden(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )


def _register_task_schtasks(wrapper: Path, log_fn) -> str | None:
    tr = f'cmd /c "{wrapper}"'
    create = _run_hidden(
        [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            tr,
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
            "/F",
        ]
    )
    if create.returncode != 0:
        err = (create.stderr or create.stdout or "").strip()
        return err or f"schtasks create exit {create.returncode}"
    _run_hidden(["schtasks", "/Run", "/TN", TASK_NAME])
    log_fn(f"已注册计划任务(schtasks): {TASK_NAME}")
    return None


def _register_task_powershell(wrapper: Path, log_fn) -> str | None:
    w = str(wrapper).replace("'", "''")
    wd = str(log_dir()).replace("'", "''")
    ps = f"""
$ErrorActionPreference = 'Stop'
$Action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c ""{w}""' -WorkingDirectory '{wd}'
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue
"""
    proc = _run_hidden(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps]
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return err or f"powershell exit {proc.returncode}"
    log_fn(f"已注册计划任务(PowerShell): {TASK_NAME}")
    return None


def _register_startup_vbs(wrapper: Path, log_fn) -> None:
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    vbs = startup / "XHS-Risk-Agent.vbs"
    target = str(wrapper).replace('"', '""')
    vbs.write_text(
        f'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run """{target}""", 0, False\n',
        encoding="utf-8",
    )
    log_fn(f"已添加开机启动(启动文件夹): {vbs}")


def _start_agent_now(wrapper: Path, log_fn) -> None:
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
    subprocess.Popen(
        ["cmd.exe", "/c", str(wrapper)],
        cwd=str(log_dir()),
        creationflags=flags,
        close_fds=True,
    )
    log_fn("Agent 已在后台启动")


def _register_task(install_dir: Path, cfg: Path, log_fn) -> None:
    wrapper = _write_wrapper_bat(install_dir, cfg)
    log_fn(f"启动脚本: {wrapper}")

    err = _register_task_schtasks(wrapper, log_fn)
    if err:
        log_fn(f"schtasks 失败: {err}")
        err = _register_task_powershell(wrapper, log_fn)
    if err:
        log_fn(f"PowerShell 计划任务失败: {err}")
        log_fn("改用「启动文件夹」实现开机自启（无需管理员权限）")
        _register_startup_vbs(wrapper, log_fn)

    _start_agent_now(wrapper, log_fn)


class SetupApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XHS 本地 Risk Agent 安装向导")
        self.geometry("640x640")
        self.resizable(False, False)

        existing = _existing_config()

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="云端 API 地址").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.api_url = tk.StringVar(value=existing.get("XHS_CLOUD_API_URL", DEFAULT_API))
        ttk.Entry(frm, textvariable=self.api_url, width=52).grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Agent Key（与服务器一致）").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.agent_key = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_KEY", ""))
        ttk.Entry(frm, textvariable=self.agent_key, width=52, show="*").grid(row=1, column=1, pady=4)

        ttk.Label(frm, text="本机 ID（每台电脑不同）").grid(row=2, column=0, sticky=tk.W, pady=4)
        default_id = existing.get("XHS_LOCAL_AGENT_ID") or os.environ.get("COMPUTERNAME", "home-pc-2")
        self.agent_id = tk.StringVar(value=default_id)
        ttk.Entry(frm, textvariable=self.agent_id, width=52).grid(row=2, column=1, pady=4)

        ttk.Label(frm, text="采集模式").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.mode = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_MODE", "api_only"))
        ttk.Combobox(
            frm,
            textvariable=self.mode,
            values=("api_only", "api_then_browser"),
            state="readonly",
            width=49,
        ).grid(row=3, column=1, pady=4)

        ttk.Label(frm, text="每批条数").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.batch = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_BATCH", "80"))
        ttk.Entry(frm, textvariable=self.batch, width=52).grid(row=4, column=1, pady=4)

        ttk.Label(frm, text="并发数").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.concurrency = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_CONCURRENCY", "3"))
        ttk.Entry(frm, textvariable=self.concurrency, width=52).grid(row=5, column=1, pady=4)

        ttk.Label(frm, text="批间冷却(秒)").grid(row=6, column=0, sticky=tk.W, pady=4)
        self.cooldown_sec = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_COOLDOWN_SEC", "60"))
        ttk.Entry(frm, textvariable=self.cooldown_sec, width=52).grid(row=6, column=1, pady=4)

        ttk.Label(frm, text="无工单等待(秒)").grid(row=7, column=0, sticky=tk.W, pady=4)
        self.idle_sec = tk.StringVar(value=existing.get("XHS_LOCAL_AGENT_IDLE_SEC", "300"))
        ttk.Entry(frm, textvariable=self.idle_sec, width=52).grid(row=7, column=1, pady=4)

        ttk.Label(frm, text="安装目录").grid(row=8, column=0, sticky=tk.W, pady=4)
        self.install_dir = tk.StringVar(value=str(default_install_dir()))
        ttk.Entry(frm, textvariable=self.install_dir, width=52).grid(row=8, column=1, pady=4)

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=2, pady=10, sticky=tk.EW)
        ttk.Button(btns, text="测试连接", command=self.on_test).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="一键安装并启动", command=self.on_install).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="仅更新配置", command=self.on_update_config).pack(side=tk.LEFT, padx=4)

        self.log = scrolledtext.ScrolledText(frm, height=12, state=tk.DISABLED)
        self.log.grid(row=10, column=0, columnspan=2, sticky=tk.NSEW)
        frm.rowconfigure(10, weight=1)
        frm.columnconfigure(1, weight=1)

        self._log(f"打包模式: {'exe' if is_frozen() else '源码'}")
        self._log(f"默认安装到: {default_install_dir()}")
        if existing:
            self._log("已读取本机现有配置，可直接修改后点「仅更新配置」。")
        self._log("提示: 第二台电脑请填写不同的「本机 ID」，避免与云服务器抢同一批工单。")

    def _log(self, msg: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _values(self) -> dict[str, str]:
        def _int_field(raw: str, default: int, lo: int, hi: int, name: str) -> str:
            try:
                n = int(str(raw).strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} 请填写 {lo}-{hi} 的整数") from exc
            if n < lo or n > hi:
                raise ValueError(f"{name} 须在 {lo}-{hi} 之间")
            return str(n)

        return {
            "api_url": self.api_url.get().strip(),
            "agent_key": self.agent_key.get().strip(),
            "agent_id": self.agent_id.get().strip(),
            "mode": self.mode.get().strip() or "api_only",
            "batch": _int_field(self.batch.get(), 80, 10, 500, "每批条数"),
            "concurrency": _int_field(self.concurrency.get(), 3, 1, 10, "并发数"),
            "idle_sec": _int_field(self.idle_sec.get(), 300, 30, 3600, "无工单等待"),
            "cooldown_sec": _int_field(self.cooldown_sec.get(), 60, 0, 600, "批间冷却"),
            "cycle_cooldown_sec": "7200",
            "min_age_hours": "2",
        }

    def _finish_install(self, dest: Path, v: dict[str, str], *, update_only: bool) -> None:
        if not _install_ready(dest) and update_only:
            raise RuntimeError("尚未安装 Agent，请先点「一键安装并启动」")
        if not update_only:
            _copy_payload(dest, self._log, update_only=False)
        else:
            _copy_payload(dest, self._log, update_only=True)
        cfg = _write_config(dest, v)
        self._log(f"配置已写入: {cfg}")
        ok, msg = _test_api(v["api_url"], v["agent_key"], v["agent_id"])
        self._log(f"连接测试: {msg}")
        if not ok and not update_only:
            if not messagebox.askyesno("连接失败", f"{msg}\n仍要继续安装吗？"):
                return
        _stop_running_agent(self._log)
        _register_task(dest, cfg, self._log)
        self._log(
            f"完成 batch={v['batch']} 并发={v['concurrency']} "
            f"批间={v['cooldown_sec']}s"
        )
        self._log(f"日志: {log_dir() / 'agent.log'}")
        title = "更新成功" if update_only else "安装成功"
        messagebox.showinfo(
            title,
            f"{title}！\n"
            f"并发={v['concurrency']} 批间={v['cooldown_sec']}s\n"
            f"Agent 已重启。",
        )

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
        try:
            v = self._values()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return
        if len(v["agent_key"]) < 16:
            messagebox.showerror("错误", "请填写完整的 Agent Key")
            return
        dest = Path(self.install_dir.get().strip() or str(default_install_dir()))
        try:
            self._log("--- 开始安装 ---")
            self._finish_install(dest, v, update_only=False)
        except Exception as exc:
            self._log(f"安装失败: {exc}")
            messagebox.showerror("安装失败", str(exc))

    def on_update_config(self) -> None:
        try:
            v = self._values()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return
        if len(v["agent_key"]) < 16:
            messagebox.showerror("错误", "请填写完整的 Agent Key")
            return
        dest = Path(self.install_dir.get().strip() or str(default_install_dir()))
        try:
            self._log("--- 更新配置 ---")
            self._finish_install(dest, v, update_only=True)
        except Exception as exc:
            self._log(f"更新失败: {exc}")
            messagebox.showerror("更新失败", str(exc))


def main() -> None:
    if sys.platform != "win32":
        print("仅支持 Windows", file=sys.stderr)
        raise SystemExit(1)
    app = SetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
