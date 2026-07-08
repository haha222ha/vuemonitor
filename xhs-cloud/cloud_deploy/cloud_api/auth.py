# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud_deploy.cloud_api.config import get_settings
from cloud_deploy.cloud_api import database as db

security = HTTPBearer(auto_error=False)
MEMBER_COOKIE = "xhs_member_session"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def create_token(user: dict, ttl_hours: int | None = None) -> str:
    s = get_settings()
    if ttl_hours is None:
        ttl_hours = s.xhs_cloud_jwt_ttl_days * 24
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "exp": int(time.time()) + ttl_hours * 3600,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(
        s.xhs_cloud_jwt_secret.encode(),
        f"{h}.{p}".encode(),
        hashlib.sha256,
    ).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def decode_token(token: str) -> dict[str, Any]:
    return _decode_token_payload(token, allow_expired=False)


def decode_token_graceful(token: str, grace_seconds: int = 7 * 86400) -> dict[str, Any]:
    """允许 JWT 过期后在 grace 窗口内刷新。"""
    return _decode_token_payload(token, allow_expired=True, grace_seconds=grace_seconds)


def _decode_token_payload(
    token: str,
    *,
    allow_expired: bool = False,
    grace_seconds: int = 0,
) -> dict[str, Any]:
    s = get_settings()
    try:
        h, p, sig = token.split(".")
        expect = hmac.new(
            s.xhs_cloud_jwt_secret.encode(),
            f"{h}.{p}".encode(),
            hashlib.sha256,
        ).digest()
        got = base64.urlsafe_b64decode(sig + "==")
        if not hmac.compare_digest(expect, got):
            raise ValueError("bad sig")
        pad = "=" * (-len(p) % 4)
        payload = json.loads(base64.urlsafe_b64decode(p + pad))
        exp = int(payload.get("exp", 0) or 0)
        now = int(time.time())
        if exp and exp < now:
            if not allow_expired or exp + grace_seconds < now:
                raise ValueError("expired")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"无效令牌: {e}") from e


def verify_sync_key(x_sync_key: str | None = Header(default=None, alias="X-Sync-Key")) -> None:
    s = get_settings()
    if not x_sync_key or not hmac.compare_digest(x_sync_key, s.xhs_cloud_sync_key):
        raise HTTPException(status_code=401, detail="Sync Key 无效")


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host or ""
    return ""


def verify_agent_access(
    request: Request,
    x_agent_key: str | None = Header(default=None, alias="X-Agent-Key"),
) -> None:
    """本地采集 Agent 专用鉴权（与会员 Sync Key 分离，可配 IP 白名单）。"""
    s = get_settings()
    expected = (s.xhs_local_agent_key or s.xhs_cloud_sync_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="未配置 XHS_LOCAL_AGENT_KEY")
    if not x_agent_key or not hmac.compare_digest(x_agent_key, expected):
        raise HTTPException(status_code=401, detail="Agent Key 无效")
    allowlist = (s.xhs_agent_ip_allowlist or "").strip()
    if not allowlist:
        return
    ip = _client_ip(request)
    allowed = {x.strip() for x in allowlist.split(",") if x.strip()}
    if ip not in allowed:
        raise HTTPException(status_code=403, detail="IP 未授权")


def resolve_member_token(
    cred: HTTPAuthorizationCredentials | None,
    request: Request | None = None,
    access_token: str = "",
) -> str:
    if cred and cred.credentials:
        return cred.credentials.strip()
    token = (access_token or "").strip()
    if token:
        return token
    if request is not None:
        cookie = (request.cookies.get(MEMBER_COOKIE) or "").strip()
        if cookie:
            return cookie
    return ""


def member_auth_response(payload: dict) -> JSONResponse:
    """登录/续期响应：写入 HttpOnly Cookie，浏览器刷新后仍可鉴权。"""
    s = get_settings()
    resp = JSONResponse(content=payload)
    token = (payload.get("access_token") or "").strip()
    if not token:
        return resp
    resp.set_cookie(
        key=MEMBER_COOKIE,
        value=token,
        max_age=max(int(s.xhs_cloud_jwt_ttl_days or 30), 1) * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return resp


def clear_member_cookie_response(payload: dict | None = None) -> JSONResponse:
    resp = JSONResponse(content=payload or {"message": "已退出"})
    resp.delete_cookie(MEMBER_COOKIE, path="/", samesite="lax")
    return resp


def current_member(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    user = current_user(request, cred)
    member = db.get_active_member(user["id"])
    if not member:
        raise HTTPException(status_code=402, detail="会员已过期或停用")
    return member


def current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    token = resolve_member_token(cred, request)
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    return user_from_token(token)


def user_from_token(token: str) -> dict:
    payload = decode_token(token)
    uid = int(payload["sub"])
    username = str(payload.get("username") or "")
    if not username:
        profile = db.get_member_profile(uid)
        if profile:
            username = profile.get("username") or ""
    if not username:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"id": uid, "username": username}


def member_from_token(token: str) -> dict:
    user = user_from_token(token)
    member = db.get_active_member(user["id"])
    if not member:
        raise HTTPException(status_code=402, detail="会员已过期或停用")
    return member


def login_member(username: str, password: str) -> dict:
    user = db.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    profile = db.get_member_profile(user["id"]) or user
    token = create_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "membership": profile,
        "login_method": "password",
    }


def login_member_by_code(auth_code: str) -> dict:
    try:
        profile = db.login_with_auth_code(auth_code)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    token = create_token({"id": profile["id"], "username": profile["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "membership": profile,
        "login_method": "auth_code",
    }


def refresh_member_token(token: str) -> dict:
    payload = decode_token_graceful(token)
    uid = int(payload["sub"])
    profile = db.get_member_profile(uid)
    if not profile:
        raise HTTPException(status_code=401, detail="用户不存在")
    new_token = create_token({"id": uid, "username": profile["username"]})
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "membership": profile,
    }


def change_member_password(
    user_id: int,
    new_password: str,
    current_password: str | None = None,
) -> None:
    try:
        db.change_password(user_id, new_password, current_password=current_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
