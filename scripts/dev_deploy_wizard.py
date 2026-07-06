# -*- coding: utf-8 -*-
"""首次配置向导 — 电脑小白按步骤点即可，私钥路径粘贴后点保存。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

CONFIG_DIR = Path(os.environ.get("USERPROFILE", Path.home())) / ".xhs365"
CONFIG_FILE = CONFIG_DIR / "deploy_config.json"
ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = {
    "ssh_host": "47.239.181.111",
    "ssh_user": "admin",
    "ssh_port": "22",
    "ssh_alias": "xhs365-deploy",
    "identity_file": str(Path(os.environ.get("USERPROFILE", "")) / ".ssh" / "xhs365_pc_upload"),
    "vuemonitor_root": str(ROOT),
    "productanalyzer_root": r"E:\小红书监控系统所有文件相关\xhs_shelf_time",
}

SERVER_CMD = """cd /opt/vuemonitor
bash scripts/server-setup-github-deploy-key.sh
# ↑ 复制输出的公钥 → GitHub → Settings → Deploy keys → Add（只读）

git remote set-url origin git@github.com-vuemonitor:haha222ha/vuemonitor.git
cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh

rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/ /opt/xhs-cloud/cloud_deploy/ --delete
cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh"""


def _load() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            data.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return data


def _save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ssh_dir = Path(os.environ.get("USERPROFILE", Path.home())) / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    cfg = ssh_dir / "config"
    alias = data["ssh_alias"]
    block = (
        f"\nHost {alias}\n"
        f"    HostName {data['ssh_host']}\n"
        f"    User {data['ssh_user']}\n"
        f"    Port {data['ssh_port']}\n"
        f"    IdentityFile {data['identity_file']}\n"
        f"    IdentitiesOnly yes\n"
    )
    text = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
    lines, skip, out = text.splitlines(), False, []
    for line in lines:
        if line.strip() == f"Host {alias}":
            skip = True
            continue
        if skip:
            if line.startswith("Host ") and line.strip() != f"Host {alias}":
                skip = False
            else:
                continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    cfg.write_text("\n".join(out) + block, encoding="utf-8")


class Wizard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XHS365 部署向导（首次配置）")
        self.geometry("760x620")
        self.data = _load()
        self.step = 0
        self.body = ttk.Frame(self, padding=12)
        self.body.pack(fill=tk.BOTH, expand=True)
        self.nav = ttk.Frame(self, padding=8)
        self.nav.pack(fill=tk.X)
        ttk.Button(self.nav, text="上一步", command=self.prev).pack(side=tk.LEFT, padx=4)
        ttk.Button(self.nav, text="下一步", command=self.next).pack(side=tk.LEFT, padx=4)
        ttk.Button(self.nav, text="打开完整推送工具", command=self._open_gui).pack(side=tk.RIGHT)
        self._show()

    def _clear(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    def _show(self) -> None:
        self._clear()
        if self.step == 0:
            self._step_intro()
        elif self.step == 1:
            self._step_paste()
        elif self.step == 2:
            self._step_test()
        else:
            self._step_server()

    def _step_intro(self) -> None:
        ttk.Label(self.body, text="欢迎使用 XHS365 双链路部署向导", font=("", 14, "bold")).pack(anchor="w")
        ttk.Label(
            self.body,
            text="链路 A：你的电脑 → 云主机（推网站、安装包）\n链路 B：云主机 → 用户电脑（自动提示更新）\n\n"
            "密钥已在云主机生成。私钥下载到本机后，下一步粘贴私钥路径即可。\n"
            "私钥不要发给 AI 或任何人。",
            justify=tk.LEFT,
        ).pack(anchor="w", pady=8)

    def _step_paste(self) -> None:
        ttk.Label(self.body, text="第 2 步：粘贴私钥路径并保存", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(self.body, text="一般路径如下，可直接用默认值，或粘贴你下载私钥后的完整路径：").pack(anchor="w", pady=4)
        self.var_key = tk.StringVar(value=self.data.get("identity_file", DEFAULTS["identity_file"]))
        self.var_host = tk.StringVar(value=self.data.get("ssh_host", DEFAULTS["ssh_host"]))
        self.var_user = tk.StringVar(value=self.data.get("ssh_user", DEFAULTS["ssh_user"]))
        for label, var in [("云主机 IP", self.var_host), ("SSH 用户", self.var_user), ("私钥路径（粘贴）", self.var_key)]:
            row = ttk.Frame(self.body)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=label, width=16).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def save() -> None:
            self.data.update(
                {
                    "ssh_host": self.var_host.get().strip(),
                    "ssh_user": self.var_user.get().strip(),
                    "identity_file": self.var_key.get().strip(),
                    **{k: DEFAULTS[k] for k in DEFAULTS if k not in ("ssh_host", "ssh_user", "identity_file")},
                }
            )
            _save(self.data)
            messagebox.showinfo("已保存", f"配置已写入:\n{CONFIG_FILE}")

        ttk.Button(self.body, text="保存配置", command=save).pack(anchor="w", pady=8)

    def _step_test(self) -> None:
        ttk.Label(self.body, text="第 3 步：测试本机 → 云主机连接", font=("", 12, "bold")).pack(anchor="w")
        log = scrolledtext.ScrolledText(self.body, height=12, font=("Consolas", 10))
        log.pack(fill=tk.BOTH, expand=True, pady=8)

        def run_test() -> None:
            log.delete("1.0", tk.END)
            alias = self.data.get("ssh_alias", "xhs365-deploy")
            proc = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", alias, "echo 连接成功"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            log.insert(tk.END, proc.stdout + proc.stderr)
            if proc.returncode == 0:
                messagebox.showinfo("成功", "本机已能免密连接云主机！")
            else:
                messagebox.showerror("失败", "连接失败。请检查私钥路径，或联系助手。")

        ttk.Button(self.body, text="点我测试连接", command=run_test).pack(anchor="w")

    def _step_server(self) -> None:
        ttk.Label(self.body, text="第 4 步：复制下面命令到云主机 SSH 执行", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(self.body, text="（这部分需要你在服务器操作，AI 无法代替）").pack(anchor="w")
        box = scrolledtext.ScrolledText(self.body, height=16, font=("Consolas", 10))
        box.pack(fill=tk.BOTH, expand=True, pady=8)
        box.insert(tk.END, SERVER_CMD)
        ttk.Label(
            self.body,
            text="本机推送：运行 py -3.11 scripts\\dev_deploy_gui.py → 点 ② host-update 或 ④ 上传安装包",
        ).pack(anchor="w", pady=4)

    def prev(self) -> None:
        if self.step > 0:
            self.step -= 1
            self._show()

    def next(self) -> None:
        if self.step < 3:
            self.step += 1
            self._show()

    def _open_gui(self) -> None:
        gui = ROOT / "scripts" / "dev_deploy_gui.py"
        subprocess.Popen([sys.executable, str(gui)], cwd=str(ROOT))


def main() -> int:
    Wizard().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
