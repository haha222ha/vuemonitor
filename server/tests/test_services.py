import sys
import os
import uuid
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


class TestLicenseService:
    def test_generate_license_code_format(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        code = service.generate_code("pro", 365, 100)
        assert len(code) == 29
        assert code[8] == "-"
        assert code[17] == "-"
        assert code[26] == "-"

    def test_generate_license_code_uniqueness(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        codes = {service.generate_code("pro", 365, 100) for _ in range(20)}
        assert len(codes) == 20

    def test_validate_license_code_valid(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        code = service.generate_code("pro", 365, 100)
        result = service.validate_code(code)
        assert result["valid"] is True
        assert result["plan"] == "pro"

    def test_validate_license_code_invalid(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        result = service.validate_code("INVALID-CODE-FORMAT")
        assert result["valid"] is False

    def test_validate_license_code_tampered(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        code = service.generate_code("pro", 365, 100)
        tampered = code[:-1] + ("A" if code[-1] != "A" else "B")
        result = service.validate_code(tampered)
        assert result["valid"] is False

    def test_get_plan_quotas(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        quotas = service.get_plan_quotas("pro")
        assert "maxProducts" in quotas
        assert "maxConcurrent" in quotas
        assert "aiCallsPerDay" in quotas

    def test_get_plan_quotas_unknown(self):
        from app.services.license_service import LicenseService
        service = LicenseService()
        quotas = service.get_plan_quotas("unknown_plan")
        assert quotas["maxProducts"] == 10


class TestTaskQueue:
    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        from app.task_queue.queue import TaskQueue
        queue = TaskQueue()
        task_id = await queue.enqueue("test_task", {"key": "value"}, priority=1)
        assert task_id is not None
        assert len(task_id) > 0

    @pytest.mark.asyncio
    async def test_enqueue_task_with_priority(self):
        from app.task_queue.queue import TaskQueue
        queue = TaskQueue()
        low_id = await queue.enqueue("test", {"p": "low"}, priority=10)
        high_id = await queue.enqueue("test", {"p": "high"}, priority=1)
        assert low_id != high_id

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        from app.task_queue.queue import TaskQueue
        queue = TaskQueue()
        task_id = await queue.enqueue("test_task", {"key": "value"})
        status = await queue.get_status(task_id)
        assert status is not None
        assert status["type"] == "test_task"

    @pytest.mark.asyncio
    async def test_get_queue_stats(self):
        from app.task_queue.queue import TaskQueue
        queue = TaskQueue()
        await queue.enqueue("task_a", {})
        await queue.enqueue("task_b", {})
        stats = await queue.get_stats()
        assert stats["pending"] >= 2


class TestBackupService:
    def test_backup_service_initialization(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        assert service is not None

    def test_get_backup_list_empty(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        backups = service.get_backups()
        assert isinstance(backups, list)

    def test_cleanup_old_backups(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        result = service.cleanup_old_backups(keep=5)
        assert result >= 0


class TestFeatureFlag:
    def test_feature_flag_initialization(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        assert service is not None

    def test_is_enabled_default(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        enabled = service.is_enabled("non_existent_feature")
        assert enabled is False

    def test_set_and_get_feature(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        service.set_feature("test_feature", True, "Test feature")
        assert service.is_enabled("test_feature") is True

    def test_set_feature_with_rollout(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        service.set_feature("rollout_feature", True, "Rollout test", rollout_percent=50)
        feature = service.get_feature("rollout_feature")
        assert feature["rollout_percent"] == 50

    def test_disable_feature(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        service.set_feature("temp_feature", True, "Temp")
        service.set_feature("temp_feature", False, "Temp")
        assert service.is_enabled("temp_feature") is False

    def test_get_all_features(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        service.set_feature("f1", True, "Feature 1")
        service.set_feature("f2", False, "Feature 2")
        features = service.get_all_features()
        assert "f1" in features
        assert "f2" in features

    def test_check_plan_access(self):
        from app.services.feature_flag import FeatureFlagService
        service = FeatureFlagService()
        service.set_feature("premium_feature", True, "Premium", required_plan="premium")
        assert service.is_enabled("premium_feature", user_plan="premium") is True
        assert service.is_enabled("premium_feature", user_plan="free") is False


class TestSLAMonitor:
    def test_sla_monitor_initialization(self):
        from app.services.sla_monitor import SLAMonitor
        monitor = SLAMonitor()
        slos = monitor.get_slos()
        assert "availability" in slos
        assert "latency_p95" in slos
        assert "latency_p99" in slos
        assert "error_budget_burn" in slos

    def test_sla_default_targets(self):
        from app.services.sla_monitor import SLAMonitor
        monitor = SLAMonitor()
        slos = monitor.get_slos()
        assert slos["availability"]["target"] == 0.999
        assert slos["latency_p95"]["target"] == 0.5
        assert slos["latency_p99"]["target"] == 2.0

    def test_update_slo_config(self):
        from app.services.sla_monitor import SLAMonitor
        monitor = SLAMonitor()
        result = monitor.update_slo("availability", {"target": 0.995})
        assert result["target"] == 0.995

    def test_delete_custom_slo(self):
        from app.services.sla_monitor import SLAMonitor
        monitor = SLAMonitor()
        monitor.update_slo("custom_slo", {"target": 0.9})
        assert monitor.delete_slo("custom_slo") is True

    def test_delete_builtin_slo_fails(self):
        from app.services.sla_monitor import SLAMonitor
        monitor = SLAMonitor()
        assert monitor.delete_slo("availability") is False


class TestErrorCapture:
    def test_error_capture_initialization(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        assert capture is not None

    def test_capture_exception(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        capture.configure(environment="test")
        try:
            raise ValueError("Test error")
        except ValueError as e:
            capture.capture_exception(e, {"context": "test"})

        events = capture.get_events()
        assert len(events) > 0
        assert events[0]["type"] == "ValueError"
        assert events[0]["message"] == "Test error"

    def test_capture_message(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        capture.configure(environment="test")
        capture.capture_message("Test warning", level="warning")
        events = capture.get_events()
        assert len(events) > 0

    def test_get_events_with_level_filter(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        capture.configure(environment="test")
        capture.capture_message("Info msg", level="info")
        capture.capture_message("Error msg", level="error")
        errors = capture.get_events(level="error")
        assert all(e["level"] == "error" for e in errors)

    def test_clear_events(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        capture.configure(environment="test")
        capture.capture_message("Test", level="info")
        capture.clear_events()
        assert len(capture.get_events()) == 0

    def test_disabled_capture(self):
        from app.services.error_capture import ErrorCapture
        capture = ErrorCapture()
        try:
            raise RuntimeError("Should not be captured")
        except RuntimeError as e:
            capture.capture_exception(e)
        assert len(capture.get_events()) == 0


class TestAlertService:
    def test_alert_service_initialization(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_send_alert_webhook(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        with patch.object(service, "_send_webhook", new_callable=AsyncMock) as mock_send:
            await service.send_alert(
                title="Test Alert",
                message="Test message",
                severity="warning",
                channel="webhook",
            )
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_log_only(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        result = await service.send_alert(
            title="Test",
            message="Test",
            severity="info",
            channel="log",
        )
        assert result is True

    def test_alert_severity_levels(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        assert service.is_severity_enabled("critical") is True
        assert service.is_severity_enabled("warning") is True
        assert service.is_severity_enabled("info") is True


class TestRateLimiter:
    def test_rate_limiter_initialization(self):
        from app.middleware.rate_limit import RedisRateLimitMiddleware
        assert RedisRateLimitMiddleware is not None

    def test_get_plan_limits(self):
        from app.middleware.rate_limit import get_plan_limit
        free_limit = get_plan_limit("free")
        pro_limit = get_plan_limit("pro")
        assert free_limit > 0
        assert pro_limit > free_limit


class TestQuotaMiddleware:
    def test_quota_middleware_initialization(self):
        from app.middleware.quota import QuotaEnforcementMiddleware
        assert QuotaEnforcementMiddleware is not None


class TestPrometheusMiddleware:
    def test_prometheus_middleware_initialization(self):
        from app.middleware.prometheus import PrometheusMiddleware
        assert PrometheusMiddleware is not None

    def test_counter_operations(self):
        from app.middleware.prometheus import counter_inc, counter_get
        counter_inc("test_counter", label="test")
        value = counter_get("test_counter", label="test")
        assert value >= 1

    def test_gauge_operations(self):
        from app.middleware.prometheus import gauge_set, gauge_get
        gauge_set("test_gauge", 42.5)
        value = gauge_get("test_gauge")
        assert value == 42.5

    def test_histogram_operations(self):
        from app.middleware.prometheus import histogram_observe
        histogram_observe("test_histogram", 0.5, label="test")

    def test_generate_output(self):
        from app.middleware.prometheus import generate_prometheus_output
        output = generate_prometheus_output()
        assert isinstance(output, str)
        assert len(output) > 0


class TestTracingMiddleware:
    def test_tracing_middleware_initialization(self):
        from app.middleware.tracing import TracingMiddleware
        assert TracingMiddleware is not None

    def test_generate_trace_id(self):
        from app.middleware.tracing import generate_trace_id
        trace_id = generate_trace_id()
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_generate_span_id(self):
        from app.middleware.tracing import generate_span_id
        span_id = generate_span_id()
        assert len(span_id) == 16
        assert all(c in "0123456789abcdef" for c in span_id)

    def test_trace_storage(self):
        from app.middleware.tracing import get_trace, get_all_traces, clear_traces
        clear_traces()
        traces = get_all_traces()
        assert len(traces) == 0


class TestSecurityAudit:
    def test_security_audit_middleware_initialization(self):
        from app.middleware.security_audit import SecurityAuditMiddleware
        assert SecurityAuditMiddleware is not None


class TestStructuredLogging:
    def test_structured_logging_middleware_initialization(self):
        from app.middleware.structured_logging import StructuredLoggingMiddleware
        assert StructuredLoggingMiddleware is not None


class TestGracefulShutdown:
    def test_graceful_shutdown_initialization(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        assert shutdown is not None

    def test_create_checkpoint(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        checkpoint_id = shutdown.create_checkpoint("test_type", {"key": "value"})
        assert checkpoint_id is not None

    def test_get_checkpoint(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        cid = shutdown.create_checkpoint("test_type", {"data": 123})
        checkpoint = shutdown.get_checkpoint(cid)
        assert checkpoint is not None
        assert checkpoint["type"] == "test_type"

    def test_remove_checkpoint(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        cid = shutdown.create_checkpoint("test", {})
        shutdown.remove_checkpoint(cid)
        assert shutdown.get_checkpoint(cid) is None

    def test_get_all_checkpoints(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        shutdown.create_checkpoint("type_a", {})
        shutdown.create_checkpoint("type_b", {})
        checkpoints = shutdown.get_all_checkpoints()
        assert len(checkpoints) >= 2


class TestDatabasePool:
    def test_get_pool_stats(self):
        from app.core.database import get_pool_stats
        import asyncio
        stats = asyncio.get_event_loop().run_until_complete(get_pool_stats())
        assert "pool_size" in stats
        assert "checked_out" in stats
        assert "overflow" in stats


class TestEncryption:
    def test_encrypt_decrypt(self):
        from app.core.encryption import encrypt, decrypt
        original = "sensitive_data_123"
        encrypted = encrypt(original)
        assert encrypted != original
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        from app.core.encryption import encrypt, decrypt
        encrypted = encrypt("")
        assert decrypt(encrypted) == ""

    def test_encrypt_special_characters(self):
        from app.core.encryption import encrypt, decrypt
        original = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt(original)
        assert decrypt(encrypted) == original

    def test_encrypt_unicode(self):
        from app.core.encryption import encrypt, decrypt
        original = "你好世界🌍"
        encrypted = encrypt(original)
        assert decrypt(encrypted) == original


class TestGDPR:
    def test_gdpr_data_summary(self):
        from app.services.gdpr_service import GDPRService
        service = GDPRService()
        summary = service.get_data_summary("test_user_id")
        assert "products" in summary
        assert "features" in summary
        assert "analyses" in summary

    def test_gdpr_export_request(self):
        from app.services.gdpr_service import GDPRService
        service = GDPRService()
        request_id = service.create_export_request("test_user_id")
        assert request_id is not None

    def test_gdpr_deletion_request(self):
        from app.services.gdpr_service import GDPRService
        service = GDPRService()
        request_id = service.create_deletion_request("test_user_id")
        assert request_id is not None

    def test_gdpr_consent_management(self):
        from app.services.gdpr_service import GDPRService
        service = GDPRService()
        service.set_consent("test_user_id", "data_collection", True)
        assert service.get_consent("test_user_id", "data_collection") is True
        service.set_consent("test_user_id", "data_collection", False)
        assert service.get_consent("test_user_id", "data_collection") is False


class TestOperationAudit:
    def test_audit_log_creation(self):
        from app.services.audit_service import AuditService
        service = AuditService()
        log_id = service.record(
            user_id="test_user",
            action="test_action",
            resource="test_resource",
            resource_id="123",
            details={"key": "value"},
        )
        assert log_id is not None

    def test_audit_log_query(self):
        from app.services.audit_service import AuditService
        service = AuditService()
        service.record("user_a", "action_a", "res_a", "1", {})
        service.record("user_b", "action_b", "res_b", "2", {})
        logs = service.query(user_id="user_a")
        assert len(logs) >= 1
        assert all(log["user_id"] == "user_a" for log in logs)

    def test_audit_log_pagination(self):
        from app.services.audit_service import AuditService
        service = AuditService()
        for i in range(10):
            service.record("test_user", f"action_{i}", "resource", str(i), {})
        logs = service.query(limit=5, offset=0)
        assert len(logs) <= 5


class TestAIReportTemplate:
    def test_template_creation(self):
        from app.models.ai_report_template import AIReportTemplate
        template = AIReportTemplate(
            id=str(uuid.uuid4()),
            name="Test Template",
            description="A test template",
            template_type="product_analysis",
            content={"sections": ["summary", "trends", "recommendations"]},
            is_default=False,
        )
        assert template.name == "Test Template"
        assert template.template_type == "product_analysis"

    def test_template_default(self):
        from app.models.ai_report_template import AIReportTemplate
        template = AIReportTemplate(
            id=str(uuid.uuid4()),
            name="Default",
            description="Default template",
            template_type="product_analysis",
            content={},
            is_default=True,
        )
        assert template.is_default is True


class TestAlertRuleEngine:
    def test_alert_rule_creation(self):
        from app.models.alert_rule import AlertRule
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name="Test Rule",
            rule_type="threshold",
            conditions={"metric": "price", "operator": "lt", "value": 100},
            severity="warning",
            is_active=True,
        )
        assert rule.name == "Test Rule"
        assert rule.rule_type == "threshold"
        assert rule.severity == "warning"

    def test_alert_event_creation(self):
        from app.models.alert_rule import AlertEvent
        event = AlertEvent(
            id=str(uuid.uuid4()),
            rule_id=str(uuid.uuid4()),
            product_id=str(uuid.uuid4()),
            severity="critical",
            message="Price dropped below threshold",
            data={"current_price": 50, "threshold": 100},
        )
        assert event.severity == "critical"
        assert event.message == "Price dropped below threshold"


class TestTeamModels:
    def test_team_creation(self):
        from app.models.team import Team
        team = Team(
            id=str(uuid.uuid4()),
            name="Test Team",
            owner_id=str(uuid.uuid4()),
            description="A test team",
        )
        assert team.name == "Test Team"

    def test_team_member_creation(self):
        from app.models.team import TeamMember
        member = TeamMember(
            id=str(uuid.uuid4()),
            team_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            role="member",
        )
        assert member.role == "member"

    def test_team_invitation_creation(self):
        from app.models.team import TeamInvitation
        invitation = TeamInvitation(
            id=str(uuid.uuid4()),
            team_id=str(uuid.uuid4()),
            inviter_id=str(uuid.uuid4()),
            invitee_email="test@example.com",
            token=str(uuid.uuid4()),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert invitation.invitee_email == "test@example.com"
        assert invitation.status == "pending"


class TestLicenseModel:
    def test_license_code_creation(self):
        from app.models.license import LicenseCode
        code = LicenseCode(
            id=str(uuid.uuid4()),
            code="TEST-CODE-1234",
            plan="pro",
            max_devices=1,
            duration_days=365,
            max_products=100,
            is_used=False,
            created_by="admin",
        )
        assert code.plan == "pro"
        assert code.is_used is False

    def test_license_activation_creation(self):
        from app.models.license import LicenseActivation
        activation = LicenseActivation(
            id=str(uuid.uuid4()),
            code_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            device_id="device-123",
            activated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
        assert activation.device_id == "device-123"
        assert activation.is_active is True


class TestCacheModule:
    def test_cache_key_generation(self):
        from app.core.cache import cache_key
        key = cache_key("products", "list", page=1, size=20)
        assert "products" in key
        assert "list" in key

    @pytest.mark.asyncio
    async def test_cache_get_set(self):
        from app.core.cache import cache_get, cache_set, cache_delete
        await cache_set("test_key", "test_value", ttl=60)
        value = await cache_get("test_key")
        assert value == "test_value"
        await cache_delete("test_key")
        value = await cache_get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_batch_operations(self):
        from app.core.cache import cache_set_batch, cache_get_batch, cache_delete_batch
        data = {"k1": "v1", "k2": "v2", "k3": "v3"}
        await cache_set_batch(data, ttl=60)
        results = await cache_get_batch(["k1", "k2", "k3"])
        assert results["k1"] == "v1"
        assert results["k2"] == "v2"
        await cache_delete_batch(["k1", "k2", "k3"])

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        from app.core.cache import cache_set, cache_get, invalidate_user_cache
        await cache_set("user:123:products", "data", ttl=60)
        await invalidate_user_cache("123")
        value = await cache_get("user:123:products")
        assert value is None


class TestWebSocketManager:
    def test_websocket_manager_initialization(self):
        from app.api.ws import ConnectionManager
        manager = ConnectionManager()
        assert manager is not None

    def test_connection_tracking(self):
        from app.api.ws import ConnectionManager
        manager = ConnectionManager()
        assert manager.get_active_connections() == 0


class TestSecurityHeaders:
    def test_security_headers_middleware(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware is not None


class TestCORS:
    def test_cors_configuration(self):
        from app.core.config import settings
        assert hasattr(settings, "CORS_ORIGINS") or hasattr(settings, "BACKEND_CORS_ORIGINS")


class TestConstants:
    def test_plan_hierarchy(self):
        from shared.constants.feature_gates import PLAN_HIERARCHY
        assert "free" in PLAN_HIERARCHY
        assert "pro" in PLAN_HIERARCHY
        assert "premium" in PLAN_HIERARCHY
        assert "enterprise" in PLAN_HIERARCHY

    def test_plan_sufficiency(self):
        from shared.constants.feature_gates import is_plan_sufficient
        assert is_plan_sufficient("premium", "pro") is True
        assert is_plan_sufficient("free", "pro") is False
        assert is_plan_sufficient("pro", "pro") is True

    def test_error_codes(self):
        from shared.constants.error_codes import ERROR_CODES
        assert "AUTH_INVALID_CREDENTIALS" in ERROR_CODES
        assert "NOT_FOUND" in ERROR_CODES
        assert "RATE_LIMIT_EXCEEDED" in ERROR_CODES