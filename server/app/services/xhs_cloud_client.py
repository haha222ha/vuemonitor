# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


class XhsCloudNotConfigured(Exception):
    pass


class XhsCloudClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = (settings.XHS_CLOUD_API_URL or "").rstrip("/")
        self.sync_key = settings.XHS_CLOUD_SYNC_KEY or ""
        self.member_portal_url = (settings.XHS_CLOUD_MEMBER_PORTAL_URL or "").rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.sync_key and self.sync_key != "change-me")

    def _headers(self) -> dict[str, str]:
        return {"X-Sync-Key": self.sync_key}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        timeout: float = 15.0,
    ) -> Any:
        if not self.is_configured:
            raise XhsCloudNotConfigured("未配置 XHS_CLOUD_API_URL 或 XHS_CLOUD_SYNC_KEY")
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )
        except httpx.RequestError as e:
            logger.warning("xhs-cloud request failed: %s %s", method, url, exc_info=e)
            raise HTTPException(status_code=502, detail=f"选品云服务不可达: {e}") from e

        if resp.status_code == 401:
            raise HTTPException(status_code=502, detail="选品云 Sync Key 不匹配，请检查 server/.env")
        if resp.status_code >= 400:
            detail = resp.text[:200] if resp.text else resp.reason_phrase
            raise HTTPException(status_code=502, detail=f"选品云 API 错误 ({resp.status_code}): {detail}")
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    async def health(self) -> dict:
        if not self.base_url:
            raise XhsCloudNotConfigured("未配置 XHS_CLOUD_API_URL")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/v1/health")
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "error", "code": resp.status_code}
        except httpx.RequestError as e:
            return {"status": "offline", "error": str(e)}

    async def stats(self) -> dict:
        return await self._request("GET", "/api/v1/admin/stats")

    async def list_codes(self, *, limit: int = 100, status: str | None = None) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/api/v1/admin/auth-codes", params=params)

    async def generate_codes(self, payload: dict) -> dict:
        return await self._request("POST", "/api/v1/admin/auth-codes", json=payload)

    async def revoke_code(self, code: str) -> dict:
        from urllib.parse import quote

        safe = quote(code.strip(), safe="")
        return await self._request("POST", f"/api/v1/admin/auth-codes/{safe}/revoke")

    async def list_member_feedback(self, *, limit: int = 100, status: str | None = None) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/api/v1/admin/member-feedback", params=params)

    async def update_member_feedback(self, item_id: int, payload: dict) -> dict:
        return await self._request("PATCH", f"/api/v1/admin/member-feedback/{item_id}", json=payload)

    async def list_member_keyword_requests(self, *, limit: int = 100, status: str | None = None) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/api/v1/admin/member-keyword-requests", params=params)

    async def update_member_keyword_request(self, item_id: int, payload: dict) -> dict:
        return await self._request("PATCH", f"/api/v1/admin/member-keyword-requests/{item_id}", json=payload)


def get_xhs_cloud_client() -> XhsCloudClient:
    return XhsCloudClient()
