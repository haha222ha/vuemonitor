#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XHS 本地 risk 采集 — 可视化配置窗口。双击「启动本地采集配置.bat」打开。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "tools" / "local_agent.env"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "xhs-local-agent"
TASK_NAME = "XHS-Local-Risk-Agent"


def _log(widget: scrolledtext.ScrolledText, msg: str) -> None:
    widget.configure(state=tk.NORMAL)
    widget.insert(tk.END, msg + "\n")
    widget.see(tk.END)
    widget.configure(state=tk.DISABLED)


def _load_env() -> dict[str, str]:
    data = {
        "XHS_CLOUD_API_URL": "https://monitor.xhs365.cn",
        "XHS_LOCAL_AGENT_KEY": "",
        "XHS_LOCAL_AGENT_ID": os.environ.get("COMPUTERNAME", "home-pc"),
        "XHS_LOCAL_AGENT_BATCH": "80",
        "XHS_LOCAL_AGENT_CONCURRENCY": "5",
        "XHS_LOCAL_AGENT_IDLE_SEC": "300",
        "XHS_LOCAL_AGENT_COOLDOWN_SEC": "15",
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
        f"XHS_LOCAL_AGENT_IDLE_SEC={values['idle_sec']}",
        f"XHS_LOCAL_AGENT_COOLDOWN_SEC={values['cooldown_sec']}",
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


class AgentConfigApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XHS 本地 risk 采集配置")
        self.geometry("720x640")
        self.minsize(640, 520)
        self.configure(padx=12, pady=10)

        saved = _load_env()
        self.var_api = tk.StringVar(value=saved.get("XHS_CLOUD_API_URL", "https://monitor.xhs365.cn"))
        self.var_key = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_KEY", ""))
        self.var_agent_id = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_ID", "home-pc"))
        self.var_batch = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_BATCH", "80"))
        self.var_concurrency = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_CONCURRENCY", "5"))
        self.var_idle = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_IDLE_SEC", "300"))
        self.var_cooldown = tk.StringVar(value=saved.get("XHS_LOCAL_AGENT_COOLDOWN_SEC", "15"))
        self.var_show_key = tk.BooleanVar(value=False)

        self._build_ui()
        self._log("就绪。请填写服务器给的 Agent Key，点「测试连接」。")

    def _build_ui(self) -> None:
        frm = ttk.LabelFrame(self, text="连接设置（服务器 setup_agent_api.sh 会打印密钥）")
        frm.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frm, text="API 地址").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_api, width=52).grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=8, pady=6)

        ttk.Label(frm, text="Agent Key").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        self.entry_key = ttk.Entry(frm, textvariable=self.var_key, width=52, show="*")
        self.entry_key.grid(row=1, column=1, sticky=tk.EW, padx=8, pady=6)
        ttk.Checkbutton(frm, text="显示", variable=self.var_show_key, command=self._toggle_key).grid(
            row=1, column=2, padx=4, pady=6
        )
        frm.columnconfigure(1, weight=1)

        opt = ttk.LabelFrame(self, text="采集参数（一般不用改）")
        opt.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(opt, text="本机名称").grid(row=0, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(opt, textvariable=self.var_agent_id, width=20).grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)
        ttk.Label(opt, text="每批条数").grid(row=0, column=2, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(opt, textvariable=self.var_batch, width=8).grid(row=0, column=3, sticky=tk.W, padx=8, pady=4)
        ttk.Label(opt, text="并发数(1-10)").grid(row=1, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(opt, textvariable=self.var_concurrency, width=8).grid(row=1, column=1, sticky=tk.W, padx=8, pady=4)
        ttk.Label(opt, text="空闲等待(秒)").grid(row=1, column=2, sticky=tk.W, padx=8, pady=4)
        ttk.Entry(opt, textvariable=self.var_idle, width=8).grid(row=1, column=3, sticky=tk.W, padx=8, pady=4)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text="① 测试连接", command=self.on_test).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="② 安装浏览器", command=self.on_install_browser).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="③ 保存并开机自启", command=self.on_install).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="试跑一轮", command=self.on_run_once).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="打开日志", command=self.on_open_log).pack(side=tk.LEFT, padx=4)

        log_frm = ttk.LabelFrame(self, text="运行日志")
        log_frm.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(log_frm, height=16, state=tk.DISABLED, font=("Consolas", 10))
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tip = (
            "使用顺序：服务器 bash setup_agent_api.sh → 复制密钥到上面 → 测试连接 → "
            "安装浏览器 → 保存并开机自启。之后电脑开着就会自动采集并上传。"
        )
        ttk.Label(self, text=tip, wraplength=680, foreground="#555").pack(anchor=tk.W, pady=(6, 0))

    def _toggle_key(self) -> None:
        self.entry_key.configure(show="" if self.var_show_key.get() else "*")

    def _values(self) -> dict[str, str]:
        return {
            "api_url": self.var_api.get().strip(),
            "agent_key": self.var_key.get().strip(),
            "agent_id": self.var_agent_id.get().strip() or "home-pc",
            "batch": self.var_batch.get().strip() or "80",
            "concurrency": self.var_concurrency.get().strip() or "5",
            "idle_sec": self.var_idle.get().strip() or "300",
            "cooldown_sec": self.var_cooldown.get().strip() or "15",
        }

    def _log(self, msg: str) -> None:
        _log(self.log_box, msg)

    def _validate(self) -> dict[str, str] | None:
        v = self._values()
        if len(v["agent_key"]) < 16:
            messagebox.showwarning("提示", "请粘贴服务器给的 Agent Key（至少 16 位）")
            return None
        if not v["api_url"].startswith("http"):
            messagebox.showwarning("提示", "API 地址请以 http:// 或 https:// 开头")
            return None
        return v

    def _worker(self, title: str, fn) -> None:
        def run() -> None:
            self._log(f"--- {title} ---")
            try:
                fn()
            except Exception as exc:
                self._log(f"失败: {exc}")
                self.after(0, lambda: messagebox.showerror("失败", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    def on_test(self) -> None:
        v = self._validate()
        if not v:
            return

        def job() -> None:
            try:
                data = _api_test(v["api_url"], v["agent_key"])
                pending = data.get("pending_risk", "?")
                self._log(f"连接成功！待补采 risk 约 {pending} 条")
                self.after(0, lambda: messagebox.showinfo("成功", f"连接正常\n待补采 risk: {pending} 条"))
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                if e.code == 404:
                    raise RuntimeError(
                        "API 地址错误：请用 https://monitor.xhs365.cn\n"
                        "（不要用 xhs365.cn）"
                    ) from e
                if e.code == 401:
                    raise RuntimeError(
                        "Agent Key 无效：请到服务器执行\n"
                        "  grep XHS_LOCAL_AGENT_KEY /opt/xhs-cloud/.env\n"
                        "复制完整密钥粘贴到本窗口（不要有空格）"
                    ) from e
                raise RuntimeError(f"HTTP {e.code}: {body}") from e

        self._worker("测试连接", job)

    def on_install_browser(self) -> None:
        def job() -> None:
            self._log("安装 playwright（首次较慢）...")
            code, out = _run_cmd([sys.executable, "-m", "pip", "install", "-q", "playwright"])
            if code != 0:
                raise RuntimeError(out or "pip install 失败")
            self._log("下载 Chromium...")
            code, out = _run_cmd([sys.executable, "-m", "playwright", "install", "chromium"])
            if code != 0:
                raise RuntimeError(out or "playwright install 失败")
            self._log("浏览器安装完成")
            self.after(0, lambda: messagebox.showinfo("完成", "Chromium 已安装"))

        self._worker("安装浏览器", job)

    def on_install(self) -> None:
        v = self._validate()
        if not v:
            return
        if not messagebox.askyesno("确认", "将保存配置并安装开机自启（后台静默运行），继续？"):
            return

        def job() -> None:
            _save_env(v)
            self._log(f"配置已保存: {ENV_FILE}")
            ps1 = REPO_ROOT / "tools" / "install_local_risk_agent.ps1"
            code, out = _run_cmd(
                [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-EnvFile",
                    str(ENV_FILE),
                ]
            )
            if code != 0:
                raise RuntimeError(out or "计划任务安装失败")
            self._log(out)
            subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME], capture_output=True)
            self._log("已启动后台任务")
            self.after(
                0,
                lambda: messagebox.showinfo(
                    "完成",
                    "已安装开机自启，后台正在运行。\n\n日志位置:\n" + str(LOG_DIR / "agent.log"),
                ),
            )

        self._worker("保存并安装", job)

    def on_run_once(self) -> None:
        if not messagebox.askyesno(
            "提示",
            "后台任务已在自动采集时，不必再点试跑。\n仍要手动试跑一轮？",
        ):
            return
        v = self._validate()
        if not v:
            return
        _save_env(v)

        def job() -> None:
            env = {
                "XHS_CLOUD_API_URL": v["api_url"],
                "XHS_LOCAL_AGENT_KEY": v["agent_key"],
                "XHS_LOCAL_AGENT_FOREGROUND": "1",
            }
            code, out = _run_cmd([sys.executable, "tools/local_risk_agent.py", "run-once"], env=env)
            self._log(out or "(无输出)")
            if code != 0:
                raise RuntimeError("试跑失败，请看日志")
            self.after(0, lambda: messagebox.showinfo("完成", "试跑一轮结束"))

        self._worker("试跑一轮", job)

    def on_open_log(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / "agent.log"
        if not log_file.exists():
            log_file.write_text("", encoding="utf-8")
        os.startfile(str(LOG_DIR))


def main() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    app = AgentConfigApp()
    app.mainloop()


if __name__ == "__main__":
    main()
