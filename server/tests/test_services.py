import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


class TestLicenseService:
    def test_generate_license_code_format(self):
        from app.services.license_service import LicenseService
        db = AsyncMock()
        service = LicenseService(db)
        code = service.generate_code("pro", 365)
        assert code.startswith("VM-")
        parts = code.split("-")
        assert len(parts) == 6

    def test_generate_license_code_uniqueness(self):
        from app.services.license_service import LicenseService
        db = AsyncMock()
        service = LicenseService(db)
        codes = {service.generate_code("pro", 365) for _ in range(20)}
        assert len(codes) == 20

    def test_validate_code_format_valid(self):
        from app.services.license_service import LicenseService
        db = AsyncMock()
        service = LicenseService(db)
        code = service.generate_code("pro", 365)
        assert service.validate_code_format(code) is True

    def test_validate_code_format_invalid(self):
        from app.services.license_service import LicenseService
        db = AsyncMock()
        service = LicenseService(db)
        assert service.validate_code_format("INVALID") is False

    def test_plan_quotas_from_constants(self):
        from shared.constants.feature_gates import PLAN_LIMITS
        quotas = PLAN_LIMITS.get("pro", {})
        assert "maxProducts" in quotas
        assert "aiCallsPerDay" in quotas

    def test_plan_quotas_unknown_defaults_free(self):
        from shared.constants.feature_gates import PLAN_LIMITS
        quotas = PLAN_LIMITS.get("unknown_plan", PLAN_LIMITS["free"])
        assert quotas["maxProducts"] == 10


class TestBackupService:
    def test_backup_service_initialization(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_list_backups(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        backups = await service.list_backups()
        assert isinstance(backups, list)

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self):
        from app.services.backup_service import BackupService
        service = BackupService()
        result = await service.cleanup_old_backups(retention_days=30)
        assert result >= 0


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

    def test_alert_history(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        history = service.get_alert_history()
        assert isinstance(history, list)

    def test_alert_stats(self):
        from app.services.alert_service import AlertService
        service = AlertService()
        stats = service.get_alert_stats()
        assert isinstance(stats, dict)


class TestRateLimiter:
    def test_rate_limiter_initialization(self):
        from app.middleware.rate_limit import RedisRateLimitMiddleware
        assert RedisRateLimitMiddleware is not None


class TestQuotaMiddleware:
    def test_quota_middleware_initialization(self):
        from app.middleware.quota import QuotaEnforcementMiddleware
        assert QuotaEnforcementMiddleware is not None


class TestPrometheusMiddleware:
    def test_prometheus_middleware_initialization(self):
        from app.middleware.prometheus import PrometheusMiddleware
        assert PrometheusMiddleware is not None

    def test_counter_operations(self):
        from app.middleware.prometheus import counter_inc
        counter_inc("test_counter", value=1, label="test")

    def test_gauge_operations(self):
        from app.middleware.prometheus import gauge_set
        gauge_set("test_gauge", 42.5, label="test")

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
        assert len(trace_id) > 0
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_generate_span_id(self):
        from app.middleware.tracing import generate_span_id
        span_id = generate_span_id()
        assert len(span_id) > 0
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
        from app.middleware.logging import StructuredLoggingMiddleware
        assert StructuredLoggingMiddleware is not None


class TestGracefulShutdown:
    def test_graceful_shutdown_initialization(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        assert shutdown is not None

    def test_register_task(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        shutdown.register_task("task_1", {"type": "test"})
        assert shutdown.is_shutting_down is False

    def test_unregister_task(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        shutdown.register_task("task_1", {"type": "test"})
        shutdown.unregister_task("task_1")

    def test_register_shutdown_callback(self):
        from app.core.graceful_shutdown import GracefulShutdown
        shutdown = GracefulShutdown()
        called = []
        shutdown.register_shutdown_callback(lambda: called.append(True))
        assert len(called) == 0


class TestLicenseModel:
    def test_license_code_creation(self):
        from app.models.license import LicenseCode
        code = LicenseCode(
            code="VM-PRO123-AB-CD-EF-1234AB-CDP",
            plan="pro",
            max_activations=1,
            duration_days=365,
            status="unused",
        )
        assert code.plan == "pro"
        assert code.status == "unused"

    def test_license_activation_creation(self):
        from app.models.license import LicenseActivation
        activation = LicenseActivation(
            license_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            device_fingerprint="device-123",
        )
        assert activation.device_fingerprint == "device-123"


class TestWebSocketManager:
    def test_websocket_manager_initialization(self):
        from app.ws.manager import ConnectionManager
        manager = ConnectionManager()
        assert manager is not None

    def test_connection_stats(self):
        from app.ws.manager import ConnectionManager
        manager = ConnectionManager()
        stats = manager.get_connection_stats()
        assert isinstance(stats, dict)


class TestSecurityHeaders:
    def test_security_headers_middleware(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware is not None


class TestCORS:
    def test_cors_configuration(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "CORS_ORIGINS")


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
        assert "USER_CREDENTIALS_INVALID" in ERROR_CODES
        assert "NOT_FOUND" in ERROR_CODES
        assert "INTERNAL_ERROR" in ERROR_CODES
