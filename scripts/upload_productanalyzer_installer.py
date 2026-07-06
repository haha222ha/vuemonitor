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

DEFAULT_HOST = "root@47.239.181.111"
REMOTE_VUE = "/opt/vuemonitor"
REMOTE_CLOUD = "/opt/xhs-cloud"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="上传 ProductAnalyzer 安装包到生产服务器")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"SSH 目标，默认 {DEFAULT_HOST}")
    parser.add_argument("--skip-exe", action="store_true", help="仅同步 json/html，不上传 exe（已上传过）")
    args = parser.parse_args()

    if not args.skip_exe and not INSTALLER.is_file():
        print(f"缺少安装包: {INSTALLER}", file=sys.stderr)
        print("请先将 ProductAnalyzer_Setup_*.exe 复制为 deploy/downloads/XHS365-Setup-latest.exe")
        return 1

    host = args.host
    if not args.skip_exe:
        run(["scp", str(INSTALLER), f"{host}:{REMOTE_VUE}/deploy/downloads/XHS365-Setup-latest.exe"])
        run(["scp", str(INSTALLER), f"{host}:{REMOTE_VUE}/web-user/dist/downloads/XHS365-Setup-latest.exe"])

    if VERSION_JSON.is_file():
        for dest in (
            f"{REMOTE_VUE}/deploy/downloads/productanalyzer-version.json",
            f"{REMOTE_VUE}/web-user/dist/downloads/productanalyzer-version.json",
        ):
            run(["scp", str(VERSION_JSON), f"{host}:{dest}"])

    if MEMBER_HTML.is_file():
        run(["scp", str(MEMBER_HTML), f"{host}:{REMOTE_CLOUD}/cloud_deploy/assets/member_portal.html"])

    remote = f"""
set -e
cd {REMOTE_VUE}
grep -q 'CLIENT_VERSION.*2026.07.06' server/app/config.py 2>/dev/null || sed -i 's/CLIENT_VERSION: str = \\"[^\\"]*\\"/CLIENT_VERSION: str = \\"2026.07.06\\"/' server/app/config.py || true
systemctl restart vuemonitor 2>/dev/null || true
systemctl restart xhs-cloud-api 2>/dev/null || systemctl restart xhs-monitor 2>/dev/null || true
curl -s http://127.0.0.1:8000/api/v1/public/downloads | head -c 200 || true
echo
ls -lh {REMOTE_VUE}/deploy/downloads/XHS365-Setup-latest.exe 2>/dev/null || true
"""
    run(["ssh", host, remote])
    print("\n完成。请验证:")
    print("  https://www.xhs365.cn/download")
    print("  https://monitor.xhs365.cn/member")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
