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

    async def get_insight_llm_config(self) -> dict:
        return await self._request("GET", "/api/v1/admin/insight-llm-config")

    async def save_insight_llm_config(self, payload: dict) -> dict:
        return await self._request("PUT", "/api/v1/admin/insight-llm-config", json=payload)

    async def test_insight_llm_config(self) -> dict:
        return await self._request("POST", "/api/v1/admin/insight-llm-config/test", timeout=120.0)

    async def get_member_contact(self) -> dict:
        return await self._request("GET", "/api/v1/admin/member-contact")

    async def save_member_contact(self, payload: dict) -> dict:
        return await self._request("PUT", "/api/v1/admin/member-contact", json=payload)

    async def upload_member_contact_qr(self, *, filename: str, content: bytes, content_type: str) -> dict:
        """上传微信二维码图片到选品云（multipart/form-data）。"""
        if not self.is_configured:
            raise XhsCloudNotConfigured("未配置 XHS_CLOUD_API_URL 或 XHS_CLOUD_SYNC_KEY")
        url = f"{self.base_url}/api/v1/admin/member-contact/upload"
        files = {"file": (filename, content, content_type or "image/png")}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=self._headers(), files=files)
        except httpx.RequestError as e:
            logger.warning("xhs-cloud upload failed: POST %s", url, exc_info=e)
            raise HTTPException(status_code=502, detail=f"选品云服务不可达: {e}") from e
        if resp.status_code == 401:
            raise HTTPException(status_code=502, detail="选品云 Sync Key 不匹配，请检查 server/.env")
        if resp.status_code >= 400:
            detail = resp.text[:200] if resp.text else resp.reason_phrase
            raise HTTPException(status_code=502, detail=f"选品云上传失败 ({resp.status_code}): {detail}")
        return resp.json()

    # ========== A/B 测试指标 ==========

    async def get_ab_test_metrics(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        ranking_key: str | None = None,
        mode: str | None = None,
        limit: int = 1000,
    ) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if ranking_key:
            params["ranking_key"] = ranking_key
        if mode:
            params["mode"] = mode
        return await self._request("GET", "/api/v1/admin/ab-test/metrics", params=params)

    async def get_ab_test_aggregate(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return await self._request("GET", "/api/v1/admin/ab-test/aggregate", params=params)

    async def list_ab_test_dates(self) -> dict:
        return await self._request("GET", "/api/v1/admin/ab-test/dates")

    async def save_ab_test_score(self, payload: dict) -> dict:
        return await self._request("PUT", "/api/v1/admin/ab-test/score", json=payload)

    async def get_ab_test_report(self, *, report_date: str, mode: str) -> dict:
        return await self._request(
            "GET",
            "/api/v1/admin/ab-test/report",
            params={"report_date": report_date, "mode": mode},
        )


def get_xhs_cloud_client() -> XhsCloudClient:
    return XhsCloudClient()
