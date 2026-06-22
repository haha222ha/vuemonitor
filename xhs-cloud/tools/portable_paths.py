# -*- coding: utf-8 -*-
"""便携版 / PyInstaller 打包路径解析。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """exe 或源码包根目录（含 cloud_deploy）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_install_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "XHS-Risk-Agent"


def installed_root() -> Path:
    env = os.environ.get("XHS_RISK_AGENT_HOME", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    inst = default_install_dir()
    if inst.is_dir() and (inst / "cloud_deploy").is_dir():
        return inst
    return bundle_root()


def log_dir() -> Path:
    d = os.environ.get("XHS_LOCAL_AGENT_LOG_DIR", "").strip()
    if d:
        p = Path(d)
    else:
        p = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "xhs-local-agent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_file() -> Path:
    env = os.environ.get("XHS_LOCAL_AGENT_ENV", "").strip()
    if env:
        return Path(env)
    for cand in (
        log_dir() / "local_agent.env",
        installed_root() / "local_agent.env",
        bundle_root() / "tools" / "local_agent.env",
    ):
        if cand.is_file():
            return cand
    return log_dir() / "local_agent.env"


def apply_runtime_paths() -> Path:
    """注入 PYTHONPATH / XHS_CLOUD_ROOT / XHS_CRAWLER_ROOT。"""
    root = installed_root()
    os.environ.setdefault("XHS_RISK_AGENT_HOME", str(root))
    os.environ.setdefault("XHS_CLOUD_ROOT", str(root))
    os.environ.setdefault(
        "XHS_CRAWLER_ROOT",
        str(root / "cloud_deploy" / "crawler_runtime"),
    )
    os.environ.setdefault("XHS_LOCAL_AGENT_LOG_DIR", str(log_dir()))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    crawler = os.environ["XHS_CRAWLER_ROOT"]
    if crawler not in sys.path and os.path.isdir(crawler):
        sys.path.insert(0, crawler)
    return root
