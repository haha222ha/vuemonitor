from urllib.parse import quote

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/public", tags=["public"])


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
