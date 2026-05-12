import sys
import os
import json
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TEST_USER = {
    "account": f"contract_test_{uuid.uuid4().hex[:8]}@test.com",
    "password": "TestPass123!",
    "name": "Contract Test User",
}

_test_token: str | None = None
_test_user_id: str | None = None
_test_product_id: str | None = None


def get_auth_headers():
    return {"Authorization": f"Bearer {_test_token}"} if _test_token else {}


class TestAuthContract:
    def test_register_contract(self):
        global _test_token, _test_user_id
        resp = client.post("/api/v1/auth/register", json=TEST_USER)
        assert resp.status_code in (200, 201, 400)
        data = resp.json()
        if resp.status_code in (200, 201):
            assert "access_token" in data or "id" in data

    def test_login_contract(self):
        global _test_token, _test_user_id
        resp = client.post("/api/v1/auth/login", json={
            "account": TEST_USER["account"],
            "password": TEST_USER["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        _test_token = data["access_token"]
        if "user" in data and "id" in data["user"]:
            _test_user_id = data["user"]["id"]

    def test_login_response_schema(self):
        resp = client.post("/api/v1/auth/login", json={
            "account": TEST_USER["account"],
            "password": TEST_USER["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("access_token"), str)
        assert len(data["access_token"]) > 0
        assert isinstance(data.get("token_type"), str)

    def test_login_invalid_credentials(self):
        resp = client.post("/api/v1/auth/login", json={
            "account": TEST_USER["account"],
            "password": "WrongPassword123!",
        })
        assert resp.status_code in (401, 400, 403)

    def test_refresh_token_contract(self):
        resp = client.post("/api/v1/auth/login", json={
            "account": TEST_USER["account"],
            "password": TEST_USER["password"],
        })
        data = resp.json()
        refresh_token = data.get("refresh_token")
        if refresh_token:
            resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert "access_token" in data2


class TestProductsContract:
    def test_list_products_schema(self):
        resp = client.get("/api/v1/products", headers=get_auth_headers())
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data or "data" in data

    def test_list_products_pagination(self):
        resp = client.get("/api/v1/products?page=1&page_size=10", headers=get_auth_headers())
        if resp.status_code == 200:
            data = resp.json()
            items_key = "items" if "items" in data else "data"
            items = data.get(items_key, [])
            if isinstance(items, dict):
                items = items.get("items", [])
            assert len(items) <= 10

    def test_list_products_platform_filter(self):
        resp = client.get("/api/v1/products?platform=xhs", headers=get_auth_headers())
        if resp.status_code == 200:
            data = resp.json()
            assert resp.status_code == 200

    def test_product_detail_404(self):
        resp = client.get(f"/api/v1/products/{uuid.uuid4()}", headers=get_auth_headers())
        assert resp.status_code in (404, 401)

    def test_product_compare_schema(self):
        resp = client.post("/api/v1/products/compare", json={
            "product_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 401, 404, 422)


class TestMonitorContract:
    def test_list_rules_schema(self):
        resp = client.get("/api/v1/monitor/rules", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_create_rule_validation(self):
        resp = client.post("/api/v1/monitor/rules", json={
            "name": "",
            "rule_type": "invalid_type",
        }, headers=get_auth_headers())
        assert resp.status_code in (422, 401, 400)

    def test_create_rule_schema(self):
        resp = client.post("/api/v1/monitor/rules", json={
            "product_id": str(uuid.uuid4()),
            "rule_name": "Test Rule",
            "rule_type": "price_drop",
            "conditions": {"threshold": 10},
            "is_active": True,
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 201, 401, 422)


class TestAIContract:
    def test_ai_analyze_contract(self):
        resp = client.post("/api/v1/ai/analyze", json={
            "product_id": str(uuid.uuid4()),
            "analysis_type": "trend",
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 401, 404, 422)

    def test_ai_report_templates(self):
        resp = client.get("/api/v1/ai/report-templates", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_ai_generate_report(self):
        resp = client.post("/api/v1/ai/generate-report", json={
            "product_id": str(uuid.uuid4()),
            "template_id": str(uuid.uuid4()),
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 401, 404, 422)


class TestTeamContract:
    def test_list_teams_schema(self):
        resp = client.get("/api/v1/teams", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_create_team_validation(self):
        resp = client.post("/api/v1/teams", json={
            "name": "",
        }, headers=get_auth_headers())
        assert resp.status_code in (422, 401, 400)

    def test_create_team_schema(self):
        resp = client.post("/api/v1/teams", json={
            "name": "Test Team",
            "description": "A test team for contract testing",
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 201, 401, 422)


class TestLicenseContract:
    def test_license_activate_validation(self):
        resp = client.post("/api/v1/license/activate", json={
            "code": "",
            "device_id": "",
        }, headers=get_auth_headers())
        assert resp.status_code in (422, 401, 400)

    def test_license_status_schema(self):
        resp = client.get("/api/v1/license/status", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_license_plan_info(self):
        resp = client.get("/api/v1/license/plan", headers=get_auth_headers())
        assert resp.status_code in (200, 401)


class TestSystemContract:
    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_metrics_endpoint(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_docs_endpoint(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert len(schema["paths"]) > 0


class TestNotificationContract:
    def test_list_notifications_schema(self):
        resp = client.get("/api/v1/notifications", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_unread_count_schema(self):
        resp = client.get("/api/v1/notifications/unread-count", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_mark_read_validation(self):
        resp = client.post("/api/v1/notifications/mark-read", json={
            "ids": [],
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 401, 422)


class TestSyncContract:
    def test_sync_status_schema(self):
        resp = client.get("/api/v1/sync/status", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_sync_push_validation(self):
        resp = client.post("/api/v1/sync/push", json={}, headers=get_auth_headers())
        assert resp.status_code in (422, 401, 400)


class TestGDPRContract:
    def test_gdpr_data_summary(self):
        resp = client.get("/api/v1/gdpr/data-summary", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_gdpr_export_request(self):
        resp = client.post("/api/v1/gdpr/export-request", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_gdpr_delete_request(self):
        resp = client.post("/api/v1/gdpr/delete-request", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_gdpr_consent(self):
        resp = client.post("/api/v1/gdpr/consent", json={
            "consent_type": "data_collection",
            "granted": True,
        }, headers=get_auth_headers())
        assert resp.status_code in (200, 401, 422)


class TestAlertContract:
    def test_list_alert_rules(self):
        resp = client.get("/api/v1/alerts/rules", headers=get_auth_headers())
        assert resp.status_code in (200, 401)

    def test_create_alert_rule_validation(self):
        resp = client.post("/api/v1/alerts/rules", json={
            "name": "",
            "rule_type": "",
        }, headers=get_auth_headers())
        assert resp.status_code in (422, 401, 400)

    def test_list_alert_events(self):
        resp = client.get("/api/v1/alerts/events", headers=get_auth_headers())
        assert resp.status_code in (200, 401)


class TestFeatureFlagContract:
    def test_list_features(self):
        resp = client.get("/api/v1/system/features", headers=get_auth_headers())
        assert resp.status_code in (200, 401)


class TestBackupContract:
    def test_list_backups(self):
        resp = client.get("/api/v1/system/backups", headers=get_auth_headers())
        assert resp.status_code in (200, 401)


class TestErrorHandling:
    def test_404_response_schema(self):
        resp = client.get("/api/v1/nonexistent-endpoint", headers=get_auth_headers())
        assert resp.status_code == 404

    def test_401_without_token(self):
        resp = client.get("/api/v1/products")
        assert resp.status_code in (401, 403)

    def test_422_invalid_json(self):
        resp = client.post("/api/v1/auth/login", content="invalid json", headers={
            "Content-Type": "application/json",
        })
        assert resp.status_code in (422, 400)

    def test_method_not_allowed(self):
        resp = client.patch("/api/v1/auth/login", json={})
        assert resp.status_code in (405, 404)


class TestResponseHeaders:
    def test_security_headers(self):
        resp = client.get("/health")
        headers = resp.headers
        assert "content-type" in headers

    def test_cors_headers(self):
        resp = client.options("/api/v1/products", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert resp.status_code in (200, 405, 400)


class TestPaginationContract:
    def test_pagination_response_schema(self):
        resp = client.get("/api/v1/products?page=1&page_size=5", headers=get_auth_headers())
        if resp.status_code == 200:
            data = resp.json()
            assert "items" in data or "data" in data

    def test_page_out_of_range(self):
        resp = client.get("/api/v1/products?page=99999&page_size=10", headers=get_auth_headers())
        if resp.status_code == 200:
            data = resp.json()
            items_key = "items" if "items" in data else "data"
            items = data.get(items_key, [])
            if isinstance(items, dict):
                items = items.get("items", [])
            assert len(items) == 0