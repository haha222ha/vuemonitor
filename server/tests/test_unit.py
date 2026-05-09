import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.core.exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
)
from shared.constants.feature_gates import PLAN_HIERARCHY, is_plan_sufficient, PLAN_LIMITS
from shared.constants.error_codes import ERROR_CODES
from app.collect.rate_controller import AdaptiveRateController


class TestSecurity:
    def test_hash_and_verify_password(self):
        password = "TestPass123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPass123", hashed) is False

    def test_create_and_decode_access_token(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
        payload = decode_access_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert payload["plan"] == "pro"
        assert payload["role"] == "user"

    def test_create_and_decode_refresh_token(self):
        user_id = str(uuid.uuid4())
        token = create_refresh_token(subject=user_id)
        payload = decode_refresh_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        user_id = str(uuid.uuid4())
        access_token = create_access_token(subject=user_id)
        with pytest.raises(Exception):
            decode_refresh_token(access_token)

    def test_refresh_token_rejected_as_access(self):
        user_id = str(uuid.uuid4())
        refresh_token = create_refresh_token(subject=user_id)
        with pytest.raises(Exception):
            decode_access_token(refresh_token)

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_access_token("invalid.token.here")

    def test_token_has_expiry(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id)
        payload = decode_access_token(token)
        assert "exp" in payload


class TestExceptions:
    def test_not_found_exception(self):
        exc = NotFoundException(message="测试不存在")
        assert exc.code == ERROR_CODES["NOT_FOUND"]
        assert exc.message == "测试不存在"

    def test_unauthorized_exception(self):
        exc = UnauthorizedException()
        assert exc.code == ERROR_CODES["USER_CREDENTIALS_INVALID"]

    def test_forbidden_exception(self):
        exc = ForbiddenException()
        assert exc.code == ERROR_CODES["GATE_FEATURE_UNAUTHORIZED"]

    def test_bad_request_exception(self):
        exc = BadRequestException(message="参数错误")
        assert exc.code == ERROR_CODES["BAD_REQUEST"]
        assert exc.message == "参数错误"

    def test_app_exception_detail(self):
        exc = AppException(code=99999, message="test", detail={"key": "value"})
        assert exc.detail == {"key": "value"}


class TestFeatureGates:
    def test_plan_hierarchy(self):
        assert PLAN_HIERARCHY["free"] < PLAN_HIERARCHY["pro"]
        assert PLAN_HIERARCHY["pro"] < PLAN_HIERARCHY["premium"]
        assert PLAN_HIERARCHY["premium"] < PLAN_HIERARCHY["enterprise"]

    def test_is_plan_sufficient(self):
        assert is_plan_sufficient("free", "free") is True
        assert is_plan_sufficient("pro", "free") is True
        assert is_plan_sufficient("free", "pro") is False
        assert is_plan_sufficient("enterprise", "premium") is True
        assert is_plan_sufficient("premium", "enterprise") is False

    def test_plan_limits(self):
        assert PLAN_LIMITS["free"]["maxProducts"] == 3
        assert PLAN_LIMITS["pro"]["maxProducts"] == 50
        assert PLAN_LIMITS["premium"]["maxProducts"] == -1
        assert PLAN_LIMITS["enterprise"]["maxProducts"] == -1


class TestErrorCodes:
    def test_error_codes_exist(self):
        assert "NOT_FOUND" in ERROR_CODES
        assert "BAD_REQUEST" in ERROR_CODES
        assert "USER_CREDENTIALS_INVALID" in ERROR_CODES
        assert "GATE_FEATURE_UNAUTHORIZED" in ERROR_CODES

    def test_error_codes_unique(self):
        values = list(ERROR_CODES.values())
        assert len(values) == len(set(values))


class TestRateController:
    @pytest.mark.asyncio
    async def test_first_request_no_wait(self):
        controller = AdaptiveRateController(base_interval=1.0)
        import time
        start = time.time()
        await controller.acquire()
        elapsed = time.time() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_on_success_reduces_interval(self):
        controller = AdaptiveRateController(base_interval=2.0)
        for _ in range(10):
            controller.on_success()
        assert controller.current_interval < 2.0

    @pytest.mark.asyncio
    async def test_on_risk_doubles_interval(self):
        controller = AdaptiveRateController(base_interval=1.0)
        controller.on_risk_detected()
        assert controller.current_interval == 2.0

    @pytest.mark.asyncio
    async def test_on_error_increases_interval(self):
        controller = AdaptiveRateController(base_interval=1.0)
        controller.on_error()
        assert controller.current_interval == 1.5

    @pytest.mark.asyncio
    async def test_interval_capped_at_max(self):
        controller = AdaptiveRateController(base_interval=5.0, max_interval=10.0)
        controller.on_risk_detected()
        assert controller.current_interval == 10.0

    @pytest.mark.asyncio
    async def test_interval_floored_at_min(self):
        controller = AdaptiveRateController(base_interval=0.5, min_interval=0.2)
        for _ in range(100):
            controller.on_success()
        assert controller.current_interval >= 0.2

    @pytest.mark.asyncio
    async def test_reset(self):
        controller = AdaptiveRateController(base_interval=5.0)
        controller.on_risk_detected()
        controller.reset()
        assert controller.current_interval == 1.0
        assert controller.consecutive_success == 0


class TestRiskDetector:
    def test_detect_rate_limit_429(self):
        from app.collect.engine import RiskDetector
        result = RiskDetector.detect("", 429)
        assert result is not None
        assert result["risk_type"] == "rate_limit"
        assert result["risk_level"] == "medium"

    def test_detect_ip_blocked_403(self):
        from app.collect.engine import RiskDetector
        result = RiskDetector.detect("", 403)
        assert result is not None
        assert result["risk_type"] == "ip_blocked"
        assert result["risk_level"] == "critical"

    def test_detect_captcha_keyword(self):
        from app.collect.engine import RiskDetector
        result = RiskDetector.detect("请输入验证码继续操作", 200)
        assert result is not None
        assert result["risk_type"] == "captcha"

    def test_detect_login_required_keyword(self):
        from app.collect.engine import RiskDetector
        result = RiskDetector.detect("请登录后查看", 200)
        assert result is not None
        assert result["risk_type"] == "login_required"

    def test_detect_no_risk(self):
        from app.collect.engine import RiskDetector
        result = RiskDetector.detect("正常商品数据", 200)
        assert result is None


class TestPasswordValidation:
    def test_valid_password(self):
        from app.schemas.auth import RegisterRequest
        req = RegisterRequest(email="test@example.com", nickname="test", password="ValidPass123")
        assert req.password == "ValidPass123"

    def test_password_no_uppercase(self):
        from app.schemas.auth import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", nickname="test", password="lowercase123")

    def test_password_no_lowercase(self):
        from app.schemas.auth import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", nickname="test", password="UPPERCASE123")

    def test_password_no_digit(self):
        from app.schemas.auth import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", nickname="test", password="NoDigitsHere")

    def test_password_too_short(self):
        from app.schemas.auth import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", nickname="test", password="Ab1")
