# PyInstaller spec — XHS Risk Agent 后台采集
# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
XHS = ROOT.parent

a = Analysis(
    [str(ROOT / 'local_risk_agent.py')],
    pathex=[str(ROOT), str(XHS)],
    binaries=[],
    datas=[
        (str(XHS / 'cloud_deploy' / 'crawler_runtime'), 'cloud_deploy/crawler_runtime'),
        (str(XHS / 'cloud_deploy' / 'cloud_api' / 'agent_service.py'), 'cloud_deploy/cloud_api'),
        (str(XHS / 'cloud_deploy' / 'cloud_api' / 'config.py'), 'cloud_deploy/cloud_api'),
        (str(XHS / 'cloud_deploy' / 'scripts' / 'bootstrap_env.py'), 'cloud_deploy/scripts'),
        (str(ROOT / 'local_risk_agent_modes.py'), 'tools'),
        (str(ROOT / 'portable_paths.py'), 'tools'),
    ],
    hiddenimports=[
        'local_risk_agent_modes',
        'portable_paths',
        'cloud_deploy.cloud_api.agent_service',
        'cloud_deploy.cloud_api.config',
        'cloud_deploy.scripts.bootstrap_env',
        'xhs_full_sold_fetch',
        'xhs_paths',
        'shop_collectors',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright', 'matplotlib', 'numpy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XHS-Risk-Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='XHS-Risk-Agent',
)
