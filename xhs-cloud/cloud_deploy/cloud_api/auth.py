# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud_deploy.cloud_api.config import get_settings
from cloud_deploy.cloud_api import database as db

security = HTTPBearer(auto_error=False)


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
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return payload
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


def current_member(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if not cred:
        raise HTTPException(status_code=401, detail="需要登录")
    payload = decode_token(cred.credentials)
    uid = int(payload["sub"])
    user = db.get_active_member(uid)
    if not user:
        raise HTTPException(status_code=402, detail="会员已过期或停用")
    return user


def login_member(username: str, password: str) -> dict:
    user = db.authenticate(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误，或会员已过期")
    profile = db.get_member_profile(user["id"]) or user
    token = create_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "membership": profile,
    }
