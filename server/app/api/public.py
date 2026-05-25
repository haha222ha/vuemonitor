from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/public", tags=["public"])

_REPO_ROOT = Path(__file__).resolve().parents[3]


@router.get("/support")
async def support_contact():
    """客服联系方式（QQ），供 Web/客户端展示，不依赖 SMTP。"""
    settings = get_settings()
    qq = (settings.SUPPORT_QQ or "").strip()
    chat_url = ""
    qr_url = (settings.SUPPORT_QQ_QR_URL or "").strip()
    if qq:
        chat_url = f"https://wpa.qq.com/msgrd?v=3&uin={qq}&site=qq&menu=yes"
        if not qr_url:
            qr_url = "/support-qq.png"
        elif qr_url.startswith("/"):
            site = (settings.SUPPORT_SITE_URL or "").rstrip("/")
            if site:
                qr_url = f"{site}{qr_url}"
    return {
        "code": 0,
        "data": {
            "qq": qq,
            "qq_chat_url": chat_url,
            "qq_qr_url": qr_url,
            "title": settings.SUPPORT_TITLE,
            "hint": settings.SUPPORT_HINT,
        },
    }


@router.get("/downloads")
async def client_downloads():
    """桌面客户端下载信息（安装包由 Nginx 静态目录提供）。"""
    settings = get_settings()
    site = (settings.SUPPORT_SITE_URL or "").rstrip("/")
    rel = settings.CLIENT_INSTALLER_PATH.replace("\\", "/")
    installer_path = _REPO_ROOT / rel
    available = installer_path.is_file()
    filename = installer_path.name if available else "XHS365-Setup-latest.exe"
    url = f"{site}/downloads/{filename}" if site else f"/downloads/{filename}"
    return {
        "code": 0,
        "data": {
            "version": settings.CLIENT_VERSION,
            "platform": "windows",
            "installer_url": url,
            "installer_available": available,
            "hint": "安装包未上传时请联系 QQ 客服获取" if not available else None,
        },
    }
