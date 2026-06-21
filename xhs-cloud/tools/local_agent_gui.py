#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XHS 本地 risk 采集 — 可视化配置窗口。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "tools" / "local_agent.env"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "xhs-local-agent"
AGENT_LOG = LOG_DIR / "agent.log"
COMPARE_JSON = LOG_DIR / "mode_compare.json"
LAST_RUN_JSON = LOG_DIR / "last_run.json"
TASK_NAME = "XHS-Local-Risk-Agent"


def _append_log(widget: scrolledtext.ScrolledText, msg: str) -> None:
    widget.configure(state=tk.NORMAL)
    widget.insert(tk.END, msg + "\n")
    widget.see(tk.END)
    widget.configure(state=tk.DISABLED)


def _set_log_text(widget: scrolledtext.ScrolledText, text: str) -> None:
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, text)
    widget.see(tk.END)
    widget.configure(state=tk.DISABLED)


def _load_env() -> dict[str, str]:
    data = {
        "XHS_CLOUD_API_URL": "https://monitor.xhs365.cn",
        "XHS_LOCAL_AGENT_KEY": "",
        "XHS_LOCAL_AGENT_ID": os.environ.get("COMPUTERNAME", "home-pc"),
        "XHS_LOCAL_AGENT_BATCH": "800",
        "XHS_LOCAL_AGENT_CONCURRENCY": "3",
        "XHS_LOCAL_AGENT_MODE": "api_only",
        "XHS_LOCAL_AGENT_IDLE_SEC": "300",
        "XHS_LOCAL_AGENT_COOLDOWN_SEC": "15",
        "XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC": "3600",
    }
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def _save_env(values: dict[str, str]) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_tail(path: Path, max_lines: int = 200) -> str:
    if not path.is_file():
        return f"（暂无文件: {path}）"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            return "（文件为空）"
        return "\n".join(lines[-max_lines:])
    except OSError as exc:
        return f"读取失败: {exc}"


def _format_compare_report(rows: list) -> str:
    if not rows:
        return "（暂无对比数据，请先点「模式对比」）"
    lines = [
        "采集模式对比报告",
        "=" * 72,
        f"{'模式':<22} {'成功':>6} {'成功率':>8} {'耗时s':>8} {'均耗ms':>8}  引擎分布",
        "-" * 72,
    ]
    best_ok = max(int(r.get("ok") or 0) for r in rows)
    for r in rows:
        mode = str(r.get("mode") or "")
        label = str(r.get("label") or mode)[:20]
        ok = int(r.get("ok") or 0)
        total = int(r.get("total") or 0)
        rate = r.get("ok_rate", 0)
        wall = r.get("wall_s", 0)
        avg_ms = r.get("avg_ok_ms", 0)
        engines = r.get("engines_ok") or {}
        eng_txt = ", ".join(f"{k}:{v}" for k, v in engines.items()) or "-"
        mark = " ★" if ok == best_ok and total else ""
        lines.append(
            f"{label:<22} {ok:>3}/{total:<3} {rate:>7}% {wall:>8} {avg_ms:>8}  {eng_txt}{mark}"
        )
    lines.append("-" * 72)
    lines.append("★ = 成功条数最高（同批测试）")
    lines.append(f"\n原始 JSON: {COMPARE_JSON}")
    return "\n".join(lines)


def _format_last_run() -> str:
    if not LAST_RUN_JSON.is_file():
        return ""
    try:
        data = json.loads(LAST_RUN_JSON.read_text(encoding="utf-8"))
        return (
            f"\n最近一轮正式采集 last_run.json:\n"
            f"  模式: {data.get('mode', '?')}\n"
            f"  扫描: {data.get('scanned', '?')}  成功: {data.get('ok', '?')}\n"
            f"  耗时: {data.get('wall_s', '?')}s\n"
        )
    except (OSError, json.JSONDecodeError):
        return ""


def _api_test(api_url: str, agent_key: str) -> dict:
    url = f"{api_url.rstrip('/')}/api/v1/agent/risk-worklist?limit=1&include_pending=1"
    req = urllib.request.Request(
        url,
        headers={"X-Agent-Key": agent_key, "User-Agent": "xhs-local-agent-gui/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _run_cmd(cmd: list[str], env: dict | None = None) -> tuple[int, str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    merged["PYTHONPATH"] = str(REPO_ROOT)
    merged["XHS_CRAWLER_ROOT"] = str(REPO_ROOT / "cloud_deploy" / "crawler_runtime")
    merged["XHS_ENABLE_PLAYWRIGHT"] = "1"
    p = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=merged,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def _stop_agent_workers(compare_proc: subprocess.Popen | None = None) -> list[str]:
    """停止计划任务、对比子进程、local_risk_agent 相关 Python 进程。"""
    notes: list[str] = []

    if compare_proc is not None and compare_proc.poll() is None:
        try:
            compare_proc.terminate()
            compare_proc.wait(timeout=5)
            notes.append("已停止对比测试进程")
        except Exception:
            try:
                compare_proc.kill()
                notes.append("已强制结束对比测试")
            except Exception as exc:
                notes.append(f"结束对比进程失败: {exc}")

    subprocess.run(["schtasks", "/End", "/TN", TASK_NAME], capture_output=True)
    notes.append("已停止计划任务（不再自动重启本轮）")

    killed = 0
    try:
        ps = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine -match 'local_risk_agent' } | "
            "ForEach-Object { $_.ProcessId }"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for pid in out.strip().split():
            if not pid.isdigit():
                continue
            r = subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
            if r.returncode == 0:
                killed += 1
    except Exception as exc:
        notes.append(f"清理进程时异常: {exc}")
    else:
        notes.append(f"已结束采集进程 {killed} 个")

    try:
        with open(AGENT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [GUI] 用户手动停止采集\n")
    except OSError:
        pass

    return notes


class AgentConfigApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XHS 本地 risk 采集配置")
        self.geometry("820x720")
        self.minsize(700, 560)
        self.configure(padx=10, pady=8)

        saved = _load_env()
        self.var_api = tk.StringVar(value=saved.get("XHS_CLOUD_API_URL", "https://monitor.xhs365.cn"))
        self.var_key = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_KEY", ""))
        self.var_agent_id = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_ID", "home-pc"))
        self.var_batch = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_BATCH", "800"))
        self.var_concurrency = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_CONCURRENCY", "3"))
        self.var_mode = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_MODE", "api_only"))
        self.var_idle = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_IDLE_SEC", "300"))
        self.var_cooldown = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_COOLDOWN_SEC", "15"))
        self.var_cycle_cooldown = tk.StringVar(
            value=saved.get("XHS_LOCAL_AGENT_CYCLE_COOLDOWN_SEC", "3600")
        )
        self.var_show_key = tk.BooleanVar(value=False)
        self.var_auto_refresh = tk.BooleanVar(value=True)
        self._agent_log_pos = 0
        self._compare_proc: subprocess.Popen | None = None

        self._build_ui()
        self._log_op("就绪。配置好后点「测试连接」；后台日志在「运行日志」页自动刷新。")
        self._refresh_agent_log()
        self._refresh_compare_view()
        self._schedule_poll()

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        tab_cfg = ttk.Frame(self.notebook, padding=6)
        tab_run = ttk.Frame(self.notebook, padding=6)
        tab_cmp = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab_cfg, text="配置")
        self.notebook.add(tab_run, text="运行日志")
        self.notebook.add(tab_cmp, text="模式对比报告")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_config_tab(tab_cfg)
        self._build_runtime_log_tab(tab_run)
        self._build_compare_tab(tab_cmp)

    def _build_config_tab(self, parent: ttk.Frame) -> None:
        frm = ttk.LabelFrame(parent, text="连接设置")
        frm.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(frm, text="API 地址").grid(row=0, column=0, sticky=tk.W, padx=6, pady=4)
        ttk.Entry(frm, textvariable=self.var_api, width=50).grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=6)
        ttk.Label(frm, text="Agent Key").grid(row=1, column=0, sticky=tk.W, padx=6, pady=4)
        self.entry_key = ttk.Entry(frm, textvariable=self.var_key, width=50, show="*")
        self.entry_key.grid(row=1, column=1, sticky=tk.EW, padx=6)
        ttk.Checkbutton(frm, text="显示", variable=self.var_show_key, command=self._toggle_key).grid(row=1, column=2)
        frm.columnconfigure(1, weight=1)

        opt = ttk.LabelFrame(parent, text="采集参数")
        opt.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(opt, text="每批").grid(row=0, column=0, padx=4)
        ttk.Entry(opt, textvariable=self.var_batch, width=6).grid(row=0, column=1, padx=4)
        ttk.Label(opt, text="并发").grid(row=0, column=2, padx=4)
        ttk.Entry(opt, textvariable=self.var_concurrency, width=6).grid(row=0, column=3, padx=4)
        ttk.Label(opt, text="模式").grid(row=0, column=4, padx=4)
        ttk.Combobox(
            opt,
            textvariable=self.var_mode,
            width=18,
            state="readonly",
            values=["api_only", "multi_browser", "single_browser", "api_then_browser"],
        ).grid(row=0, column=5, padx=4)
        ttk.Label(opt, text="E仅API(推荐) A多浏览器 C单浏览器 D API+浏览器", foreground="#666").grid(row=1, column=0, columnspan=6, sticky=tk.W, padx=4)
        ttk.Label(opt, text="批间冷却s").grid(row=2, column=0, padx=4, pady=2)
        ttk.Entry(opt, textvariable=self.var_cooldown, width=6).grid(row=2, column=1, padx=4, pady=2)
        ttk.Label(opt, text="整轮冷却s").grid(row=2, column=2, padx=4, pady=2)
        ttk.Entry(opt, textvariable=self.var_cycle_cooldown, width=6).grid(row=2, column=3, padx=4, pady=2)
        ttk.Label(opt, text="无工单s").grid(row=2, column=4, padx=4, pady=2)
        ttk.Entry(opt, textvariable=self.var_idle, width=6).grid(row=2, column=5, padx=4, pady=2)
        ttk.Label(opt, text="整轮=扫完当日 risk 池后休眠(默认3600=1h)", foreground="#666").grid(
            row=3, column=0, columnspan=6, sticky=tk.W, padx=4
        )

        btns = ttk.Frame(parent)
        btns.pack(fill=tk.X, pady=(0, 6))
        for text, cmd in [
            ("①测试连接", self.on_test),
            ("②安装浏览器", self.on_install_browser),
            ("③保存并自启", self.on_install),
            ("模式对比", self.on_compare),
        ]:
            ttk.Button(btns, text=text, command=cmd).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns,
            text="■ 停止采集",
            command=self.on_stop,
            fg="#b00020",
            activeforeground="#b00020",
            relief=tk.GROOVE,
            padx=8,
        ).pack(side=tk.LEFT, padx=8)

        op_frm = ttk.LabelFrame(parent, text="本窗口操作日志")
        op_frm.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(op_frm, height=12, state=tk.DISABLED, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _build_runtime_log_tab(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(bar, text=f"文件: {AGENT_LOG}").pack(side=tk.LEFT)
        ttk.Checkbutton(bar, text="每3秒自动刷新", variable=self.var_auto_refresh).pack(side=tk.LEFT, padx=12)
        ttk.Button(bar, text="立即刷新", command=self._refresh_agent_log).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="打开日志目录", command=self.on_open_log).pack(side=tk.LEFT, padx=4)
        tk.Button(
            bar,
            text="■ 停止采集",
            command=self.on_stop,
            fg="#b00020",
            activeforeground="#b00020",
            relief=tk.GROOVE,
            padx=6,
        ).pack(side=tk.LEFT, padx=4)
        self.lbl_run_status = ttk.Label(bar, text="", foreground="#0066cc")
        self.lbl_run_status.pack(side=tk.RIGHT, padx=4)

        self.agent_log_box = scrolledtext.ScrolledText(
            parent, height=28, state=tk.DISABLED, font=("Consolas", 9), wrap=tk.WORD
        )
        self.agent_log_box.pack(fill=tk.BOTH, expand=True)

    def _build_compare_tab(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(bar, text=f"文件: {COMPARE_JSON}").pack(side=tk.LEFT)
        ttk.Button(bar, text="刷新报告", command=self._refresh_compare_view).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="运行模式对比", command=self.on_compare).pack(side=tk.LEFT, padx=4)

        self.compare_box = scrolledtext.ScrolledText(
            parent, height=28, state=tk.DISABLED, font=("Consolas", 9), wrap=tk.WORD
        )
        self.compare_box.pack(fill=tk.BOTH, expand=True)

    def _toggle_key(self) -> None:
        self.entry_key.configure(show="" if self.var_show_key.get() else "*")

    def _values(self) -> dict[str, str]:
        return {
            "api_url": self.var_api.get().strip(),
            "agent_key": self.var_key.get().strip(),
            "agent_id": self.var_agent_id.get().strip() or "home-pc",
            "batch": self.var_batch.get().strip() or "800",
            "concurrency": self.var_concurrency.get().strip() or "3",
            "mode": self.var_mode.get().strip() or "api_only",
            "idle_sec": self.var_idle.get().strip() or "300",
            "cooldown_sec": self.var_cooldown.get().strip() or "15",
            "cycle_cooldown_sec": self.var_cycle_cooldown.get().strip() or "3600",
        }

    def _log_op(self, msg: str) -> None:
        _append_log(self.log_box, msg)

    def _on_tab_changed(self, _event=None) -> None:
        idx = self.notebook.index(self.notebook.select())
        if idx == 1:
            self._refresh_agent_log(incremental=False)
        elif idx == 2:
            self._refresh_compare_view()

    def _schedule_poll(self) -> None:
        if self.var_auto_refresh.get():
            self._refresh_agent_log(incremental=True)
        self.after(3000, self._schedule_poll)

    def _refresh_agent_log(self, incremental: bool = False) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if not AGENT_LOG.is_file():
            if not incremental:
                _set_log_text(self.agent_log_box, "（后台尚未产生日志，保存并自启后会写入）")
            return
        try:
            size = AGENT_LOG.stat().st_size
            if incremental and size < self._agent_log_pos:
                self._agent_log_pos = 0
            if incremental and size > self._agent_log_pos:
                with open(AGENT_LOG, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self._agent_log_pos)
                    chunk = f.read()
                    self._agent_log_pos = f.tell()
                if chunk:
                    self.agent_log_box.configure(state=tk.NORMAL)
                    self.agent_log_box.insert(tk.END, chunk)
                    self.agent_log_box.see(tk.END)
                    self.agent_log_box.configure(state=tk.DISABLED)
            elif not incremental:
                text = _read_tail(AGENT_LOG, 300)
                extra = _format_last_run()
                _set_log_text(self.agent_log_box, text + extra)
                self._agent_log_pos = size
                n = len(text.splitlines()) if text else 0
                self.lbl_run_status.configure(text=f"共 {n} 行 | 更新 {time.strftime('%H:%M:%S')}")
        except OSError as exc:
            if not incremental:
                _set_log_text(self.agent_log_box, f"读取失败: {exc}")

    def _refresh_compare_view(self) -> None:
        if not COMPARE_JSON.is_file():
            _set_log_text(self.compare_box, _format_compare_report([]))
            return
        try:
            rows = json.loads(COMPARE_JSON.read_text(encoding="utf-8"))
            text = _format_compare_report(rows if isinstance(rows, list) else [])
            text += "\n\n--- JSON 原文 ---\n"
            text += json.dumps(rows, ensure_ascii=False, indent=2)
            _set_log_text(self.compare_box, text)
        except (OSError, json.JSONDecodeError) as exc:
            _set_log_text(self.compare_box, f"读取 mode_compare.json 失败: {exc}")

    def _validate(self) -> dict[str, str] | None:
        v = self._values()
        if len(v["agent_key"]) < 16:
            messagebox.showwarning("提示", "请粘贴服务器给的 Agent Key")
            return None
        if not v["api_url"].startswith("http"):
            messagebox.showwarning("提示", "API 地址请以 http:// 或 https:// 开头")
            return None
        return v

    def _worker(self, title: str, fn, on_ok=None) -> None:
        def run() -> None:
            self._log_op(f"--- {title} ---")
            try:
                fn()
                if on_ok:
                    self.after(0, on_ok)
            except Exception as exc:
                self._log_op(f"失败: {exc}")
                self.after(0, lambda: messagebox.showerror("失败", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    def on_test(self) -> None:
        v = self._validate()
        if not v:
            return

        def job() -> None:
            data = _api_test(v["api_url"], v["agent_key"])
            pending = data.get("pending_risk", "?")
            self._log_op(f"连接成功！待补采 risk 约 {pending} 条")
            self.after(0, lambda: messagebox.showinfo("成功", f"待补采 risk: {pending} 条"))

        self._worker("测试连接", job)

    def on_install_browser(self) -> None:
        def job() -> None:
            self._log_op("安装 playwright...")
            code, out = _run_cmd([sys.executable, "-m", "pip", "install", "-q", "playwright"])
            if code != 0:
                raise RuntimeError(out or "pip install 失败")
            code, out = _run_cmd([sys.executable, "-m", "playwright", "install", "chromium"])
            if code != 0:
                raise RuntimeError(out or "playwright install 失败")
            self._log_op("浏览器安装完成")

        self._worker("安装浏览器", job)

    def on_install(self) -> None:
        v = self._validate()
        if not v:
            return
        if not messagebox.askyesno("确认", "保存配置并安装开机自启？"):
            return

        def job() -> None:
            _save_env(v)
            ps1 = REPO_ROOT / "tools" / "install_local_risk_agent.ps1"
            code, out = _run_cmd(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-EnvFile", str(ENV_FILE)]
            )
            if code != 0:
                raise RuntimeError(out or "计划任务安装失败")
            self._log_op(out or "计划任务已安装")
            subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME], capture_output=True)
            self._log_op("已启动后台任务")

        def on_ok() -> None:
            self._refresh_agent_log()
            self.notebook.select(1)
            messagebox.showinfo("完成", "已启动后台采集\n请切到「运行日志」页查看")

        self._worker("保存并安装", job, on_ok=on_ok)

    def on_compare(self) -> None:
        v = self._validate()
        if not v:
            return
        _save_env(v)

        def job() -> None:
            env = {
                **os.environ,
                "XHS_CLOUD_API_URL": v["api_url"],
                "XHS_LOCAL_AGENT_KEY": v["agent_key"],
                "XHS_LOCAL_AGENT_FOREGROUND": "1",
                "XHS_LOCAL_AGENT_LOG_DIR": str(LOG_DIR),
                "XHS_LOCAL_AGENT_COMPARE_N": "9",
                "PYTHONPATH": str(REPO_ROOT),
            }
            self._log_op("对比开始（D→C→A，每模式 9 条，请切到「运行日志」查看）")
            self.after(0, lambda: self.notebook.select(1))
            proc = subprocess.Popen(
                [sys.executable, "tools/local_risk_agent.py", "compare"],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._compare_proc = proc
            assert proc.stdout is not None
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.after(0, lambda s=line: self._log_op(s))
                    self.after(0, lambda: self._refresh_agent_log(incremental=False))
                code = proc.wait()
            finally:
                self._compare_proc = None
            self.after(0, lambda: self._refresh_agent_log(incremental=False))
            self.after(0, lambda: self._refresh_compare_view())
            if code != 0:
                raise RuntimeError(f"对比退出码 {code}")

        def on_ok() -> None:
            self._refresh_compare_view()
            self.notebook.select(2)
            messagebox.showinfo("完成", "对比报告已更新，见「模式对比报告」页")

        self._worker("模式对比", job, on_ok=on_ok)

    def on_stop(self) -> None:
        if not messagebox.askyesno(
            "停止采集",
            "将停止：\n"
            "· 后台采集任务\n"
            "· 正在跑的对比测试\n"
            "· 相关 Python/浏览器进程\n\n"
            "（计划任务仍保留，下次可点「保存并自启」再开）\n"
            "确定停止？",
        ):
            return

        def job() -> None:
            notes = _stop_agent_workers(self._compare_proc)
            for n in notes:
                self._log_op(n)
            self.after(0, lambda: self._refresh_agent_log(incremental=False))

        def on_ok() -> None:
            messagebox.showinfo("已停止", "采集已停止。\n要再开：改好配置后点「③保存并自启」")

        self._worker("停止采集", job, on_ok=on_ok)

    def on_open_log(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(LOG_DIR))


def main() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    app = AgentConfigApp()
    app.mainloop()


if __name__ == "__main__":
    main()
