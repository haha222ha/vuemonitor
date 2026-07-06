# -*- coding: utf-8 -*-
"""上传 ProductAnalyzer 安装包到 xhs365 生产机并刷新静态目录。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "deploy" / "downloads"
INSTALLER = DL / "XHS365-Setup-latest.exe"
VERSION_JSON = DL / "productanalyzer-version.json"
MEMBER_HTML = ROOT / "xhs-cloud" / "cloud_deploy" / "assets" / "member_portal.html"

DEFAULT_HOST = "xhs365"
REMOTE_VUE = "/opt/vuemonitor"
REMOTE_CLOUD = "/opt/xhs-cloud"
STAGING = "/tmp/pa-upload"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)


def scp_upload(local: Path, host: str, remote_path: str) -> None:
    run(["scp", str(local), f"{host}:{remote_path}"])


def main() -> int:
    parser = argparse.ArgumentParser(description="上传 ProductAnalyzer 安装包到生产服务器")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"SSH Host，默认 {DEFAULT_HOST}")
    parser.add_argument("--skip-exe", action="store_true", help="仅同步 json/html，不上传 exe")
    parser.add_argument("--use-sudo", action="store_true", default=True,
                        help="admin 用户时通过 /tmp 暂存再 sudo 复制（默认开启）")
    args = parser.parse_args()
    host = args.host

    if not args.skip_exe and not INSTALLER.is_file():
        print(f"缺少安装包: {INSTALLER}", file=sys.stderr)
        return 1

    run(["ssh", host, f"mkdir -p {STAGING}"])

    if not args.skip_exe:
        scp_upload(INSTALLER, host, f"{STAGING}/XHS365-Setup-latest.exe")

    if VERSION_JSON.is_file():
        scp_upload(VERSION_JSON, host, f"{STAGING}/productanalyzer-version.json")

    if MEMBER_HTML.is_file():
        scp_upload(MEMBER_HTML, host, f"{STAGING}/member_portal.html")

    remote = f"""
set -e
sudo mkdir -p {REMOTE_VUE}/deploy/downloads {REMOTE_VUE}/web-user/dist/downloads {REMOTE_CLOUD}/cloud_deploy/assets
if [ -f {STAGING}/XHS365-Setup-latest.exe ]; then
  sudo cp -f {STAGING}/XHS365-Setup-latest.exe {REMOTE_VUE}/deploy/downloads/XHS365-Setup-latest.exe
  sudo cp -f {STAGING}/XHS365-Setup-latest.exe {REMOTE_VUE}/web-user/dist/downloads/XHS365-Setup-latest.exe
fi
if [ -f {STAGING}/productanalyzer-version.json ]; then
  sudo cp -f {STAGING}/productanalyzer-version.json {REMOTE_VUE}/deploy/downloads/
  sudo cp -f {STAGING}/productanalyzer-version.json {REMOTE_VUE}/web-user/dist/downloads/
fi
if [ -f {STAGING}/member_portal.html ]; then
  sudo cp -f {STAGING}/member_portal.html {REMOTE_CLOUD}/cloud_deploy/assets/member_portal.html
fi
sudo systemctl restart vuemonitor 2>/dev/null || true
sudo systemctl restart xhs-cloud-api 2>/dev/null || sudo systemctl restart xhs-monitor 2>/dev/null || true
curl -s http://127.0.0.1:8000/api/v1/public/downloads | head -c 240 || true
echo
ls -lh {REMOTE_VUE}/deploy/downloads/XHS365-Setup-latest.exe 2>/dev/null || true
rm -rf {STAGING}
"""
    run(["ssh", host, remote])
    print("\n完成。请验证:")
    print("  https://www.xhs365.cn/download")
    print("  https://monitor.xhs365.cn/member")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
