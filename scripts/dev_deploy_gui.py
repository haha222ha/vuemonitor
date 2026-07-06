# -*- coding: utf-8 -*-
"""选品报告 / vuemonitor 开发机 → 云主机 可视化推送工具。

私钥仅保存在本机配置文件，不会提交到 git，也不要发给 AI。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = Path(os.environ.get("USERPROFILE", Path.home())) / ".xhs365"
CONFIG_FILE = CONFIG_DIR / "deploy_config.json"
UPLOAD_SCRIPT = ROOT / "scripts" / "upload_productanalyzer_installer.py"
HOST_UPDATE_CMD = (
    "cd /opt/vuemonitor && sudo rm -rf client/node_modules 2>/dev/null; "
    "git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh"
)
XHS_CLOUD_UPDATE_CMD = (
    "rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/ /opt/xhs-cloud/cloud_deploy/ --delete && "
    "cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh"
)

DEFAULTS = {
    "ssh_host": "47.239.181.111",
    "ssh_user": "admin",
    "ssh_port": "22",
    "ssh_alias": "xhs365-deploy",
    "identity_file": str(Path(os.environ.get("USERPROFILE", "")) / ".ssh" / "xhs365_pc_upload"),
    "vuemonitor_root": str(ROOT),
    "productanalyzer_root": r"E:\小红书监控系统所有文件相关\xhs_shelf_time",
}


def _load_config() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            data.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return data


def _save_config(values: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_log(widget: scrolledtext.ScrolledText, msg: str) -> None:
    widget.configure(state=tk.NORMAL)
    widget.insert(tk.END, msg + "\n")
    widget.see(tk.END)
    widget.configure(state=tk.DISABLED)


def _run_capture(cmd: list[str], env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def _write_ssh_config(alias: str, host: str, user: str, port: str, identity_file: str) -> None:
    ssh_dir = Path(os.environ.get("USERPROFILE", Path.home())) / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    config_path = ssh_dir / "config"
    block = (
        f"\nHost {alias}\n"
        f"    HostName {host}\n"
        f"    User {user}\n"
        f"    Port {port}\n"
        f"    IdentityFile {identity_file}\n"
        f"    IdentitiesOnly yes\n"
    )
    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    lines = existing.splitlines()
    out_lines: list[str] = []
    skip = False
    for line in lines:
        if line.strip() == f"Host {alias}":
            skip = True
            continue
        if skip:
            if line.startswith("Host ") and line.strip() != f"Host {alias}":
                skip = False
            else:
                continue
        out_lines.append(line)
    while out_lines and not out_lines[-1].strip():
        out_lines.pop()
    new_text = "\n".join(out_lines) + block
    config_path.write_text(new_text if new_text.endswith("\n") else new_text + "\n", encoding="utf-8")


class DeployGui:
    def __init__(self) -> None:
        self.cfg = _load_config()
        self.root = tk.Tk()
        self.root.title("XHS365 开发机 → 云主机 推送")
        self.root.geometry("820x640")
        self.root.minsize(720, 520)

        self.vars = {
            "ssh_host": tk.StringVar(value=self.cfg.get("ssh_host", DEFAULTS["ssh_host"])),
            "ssh_user": tk.StringVar(value=self.cfg.get("ssh_user", DEFAULTS["ssh_user"])),
            "ssh_port": tk.StringVar(value=str(self.cfg.get("ssh_port", DEFAULTS["ssh_port"]))),
            "ssh_alias": tk.StringVar(value=self.cfg.get("ssh_alias", DEFAULTS["ssh_alias"])),
            "identity_file": tk.StringVar(value=self.cfg.get("identity_file", DEFAULTS["identity_file"])),
            "vuemonitor_root": tk.StringVar(value=self.cfg.get("vuemonitor_root", DEFAULTS["vuemonitor_root"])),
            "productanalyzer_root": tk.StringVar(
                value=self.cfg.get("productanalyzer_root", DEFAULTS["productanalyzer_root"])
            ),
        }

        self._build()
        self.log = self.log_widget

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        conn = ttk.LabelFrame(frm, text="SSH 连接（私钥仅存本机，勿发给 AI）", padding=8)
        conn.pack(fill=tk.X, **pad)

        grid = ttk.Frame(conn)
        grid.pack(fill=tk.X)
        labels = [
            ("云主机 IP", "ssh_host"),
            ("SSH 用户", "ssh_user"),
            ("端口", "ssh_port"),
            ("SSH 别名", "ssh_alias"),
        ]
        for i, (label, key) in enumerate(labels):
            ttk.Label(grid, text=label).grid(row=i // 2, column=(i % 2) * 2, sticky="e", **pad)
            ttk.Entry(grid, textvariable=self.vars[key], width=28).grid(
                row=i // 2, column=(i % 2) * 2 + 1, sticky="we", **pad
            )

        key_row = ttk.Frame(conn)
        key_row.pack(fill=tk.X, pady=4)
        ttk.Label(key_row, text="私钥路径").pack(side=tk.LEFT)
        ttk.Entry(key_row, textvariable=self.vars["identity_file"]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(key_row, text="浏览…", command=self._browse_key).pack(side=tk.LEFT)
        ttk.Button(key_row, text="保存配置", command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(key_row, text="测试连接", command=self._test_ssh).pack(side=tk.LEFT)

        paths = ttk.LabelFrame(frm, text="本地路径", padding=8)
        paths.pack(fill=tk.X, **pad)
        for label, key in [
            ("vuemonitor 根目录", "vuemonitor_root"),
            ("ProductAnalyzer 根目录", "productanalyzer_root"),
        ]:
            row = ttk.Frame(paths)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.vars[key]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        actions = ttk.LabelFrame(frm, text="推送操作", padding=8)
        actions.pack(fill=tk.X, **pad)
        btns = ttk.Frame(actions)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="① 仅 Git Push（代码到 GitHub）", command=self._git_push).pack(
            side=tk.LEFT, padx=4, pady=2
        )
        ttk.Button(btns, text="② 服务器 host-update（拉代码+重启）", command=self._host_update).pack(
            side=tk.LEFT, padx=4, pady=2
        )
        ttk.Button(btns, text="③ xhs-cloud 同步+重启", command=self._xhs_cloud_update).pack(
            side=tk.LEFT, padx=4, pady=2
        )
        btns2 = ttk.Frame(actions)
        btns2.pack(fill=tk.X, pady=4)
        ttk.Button(btns2, text="④ 上传 PC 安装包（exe+版本json）", command=self._upload_installer).pack(
            side=tk.LEFT, padx=4, pady=2
        )
        ttk.Button(
            btns2,
            text="⑤ 完整发版（git push + host-update + 上传安装包）",
            command=self._full_release,
        ).pack(side=tk.LEFT, padx=4, pady=2)

        ttk.Label(
            frm,
            text="链路说明：①② 更新网站/API；④ 更新用户 PC 端安装包；用户电脑启动后会读 productanalyzer-version.json 提示更新。",
            wraplength=780,
        ).pack(anchor="w", **pad)

        self.log_widget = scrolledtext.ScrolledText(frm, height=18, state=tk.DISABLED, font=("Consolas", 10))
        self.log_widget.pack(fill=tk.BOTH, expand=True, **pad)

    def _collect(self) -> dict:
        return {k: v.get().strip() for k, v in self.vars.items()}

    def _save(self) -> None:
        data = self._collect()
        _save_config(data)
        try:
            _write_ssh_config(
                data["ssh_alias"], data["ssh_host"], data["ssh_user"], data["ssh_port"], data["identity_file"]
            )
        except Exception as e:
            messagebox.showwarning("SSH config", f"写入 ~/.ssh/config 失败: {e}")
        messagebox.showinfo("已保存", f"配置已写入:\n{CONFIG_FILE}")

    def _browse_key(self) -> None:
        path = filedialog.askopenfilename(title="选择 SSH 私钥文件")
        if path:
            self.vars["identity_file"].set(path)

    def _alias(self) -> str:
        return self._collect()["ssh_alias"] or "xhs365-deploy"

    def _ensure_ready(self) -> bool:
        data = self._collect()
        key = Path(data["identity_file"])
        if not key.is_file():
            messagebox.showerror("缺少私钥", f"私钥不存在:\n{key}\n\n请先在云主机生成密钥并下载到本机。")
            return False
        _save_config(data)
        try:
            _write_ssh_config(
                data["ssh_alias"], data["ssh_host"], data["ssh_user"], data["ssh_port"], data["identity_file"]
            )
        except Exception as e:
            messagebox.showerror("SSH config", str(e))
            return False
        return True

    def _run_async(self, title: str, fn) -> None:
        def worker() -> None:
            _append_log(self.log, f"\n===== {title} =====")
            try:
                fn()
            except Exception as e:
                _append_log(self.log, f"错误: {e}")
                self.root.after(0, lambda: messagebox.showerror(title, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _test_ssh(self) -> None:
        if not self._ensure_ready():
            return

        def job() -> None:
            code, out = _run_capture(["ssh", "-o", "BatchMode=yes", self._alias(), "echo OK"])
            _append_log(self.log, out.strip() or "(无输出)")
            if code == 0:
                self.root.after(0, lambda: messagebox.showinfo("测试成功", "SSH 免密连接正常"))
            else:
                self.root.after(0, lambda: messagebox.showerror("测试失败", out[-500:]))

        self._run_async("测试 SSH", job)

    def _git_push(self) -> None:
        def job() -> None:
            code, out = _run_capture(["git", "push", "origin", "main"])
            _append_log(self.log, out)
            if code != 0:
                raise RuntimeError("git push 失败")

        self._run_async("Git Push", job)

    def _ssh_cmd(self, remote: str, title: str) -> None:
        if not self._ensure_ready():
            return

        def job() -> None:
            code, out = _run_capture(["ssh", self._alias(), remote])
            _append_log(self.log, out)
            if code != 0:
                raise RuntimeError(f"{title} 失败 (exit {code})")
            self.root.after(0, lambda: messagebox.showinfo(title, "完成"))

        self._run_async(title, job)

    def _host_update(self) -> None:
        self._ssh_cmd(HOST_UPDATE_CMD, "host-update")

    def _xhs_cloud_update(self) -> None:
        self._ssh_cmd(XHS_CLOUD_UPDATE_CMD, "xhs-cloud 更新")

    def _upload_installer(self) -> None:
        if not self._ensure_ready():
            return
        exe = Path(self._collect()["vuemonitor_root"]) / "deploy" / "downloads" / "XHS365-Setup-latest.exe"
        if not exe.is_file():
            messagebox.showerror("缺少安装包", f"请先构建并复制安装包到:\n{exe}")
            return

        def job() -> None:
            py = sys.executable
            code, out = _run_capture([py, str(UPLOAD_SCRIPT), "--host", self._alias()])
            _append_log(self.log, out)
            if code != 0:
                raise RuntimeError("上传安装包失败")
            self.root.after(0, lambda: messagebox.showinfo("上传完成", "安装包与版本 json 已同步到服务器"))

        self._run_async("上传安装包", job)

    def _full_release(self) -> None:
        def job() -> None:
            for step, cmd in [
                ("git push", ["git", "push", "origin", "main"]),
                ("host-update", ["ssh", self._alias(), HOST_UPDATE_CMD]),
            ]:
                if step == "host-update" and not self._ensure_ready():
                    raise RuntimeError("SSH 未就绪")
                code, out = _run_capture(cmd)
                _append_log(self.log, f"[{step}]\n{out}")
                if code != 0:
                    raise RuntimeError(f"{step} 失败")
            exe = Path(self._collect()["vuemonitor_root"]) / "deploy" / "downloads" / "XHS365-Setup-latest.exe"
            if exe.is_file():
                py = sys.executable
                code, out = _run_capture([py, str(UPLOAD_SCRIPT), "--host", self._alias()])
                _append_log(self.log, f"[upload installer]\n{out}")
                if code != 0:
                    raise RuntimeError("上传安装包失败")
            else:
                _append_log(self.log, f"跳过安装包上传（不存在）: {exe}")
            self.root.after(0, lambda: messagebox.showinfo("完整发版", "已完成"))

        if not messagebox.askyesno("确认", "将依次执行: git push → host-update → 上传安装包（若存在）。继续？"):
            return
        self._run_async("完整发版", job)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = DeployGui()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
