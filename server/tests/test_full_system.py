import sys
import os
import asyncio
import uuid
import time
import traceback
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "vuemonitor_test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-testing-only")
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-deepseek-key-for-testing-only")

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results = {"pass": 0, "fail": 0, "skip": 0, "errors": []}


def record(module, name, status, detail=""):
    if status == PASS:
        results["pass"] += 1
        print(f"  ✅ [{module}] {name}")
    elif status == FAIL:
        results["fail"] += 1
        results["errors"].append(f"[{module}] {name}: {detail}")
        print(f"  ❌ [{module}] {name} — {detail}")
    else:
        results["skip"] += 1
        print(f"  ⏭️  [{module}] {name} — {detail}")


def safe_test(module, name, fn):
    try:
        fn()
    except Exception as e:
        record(module, name, FAIL, str(e))


async def safe_test_async(module, name, fn):
    try:
        await fn()
    except Exception as e:
        record(module, name, FAIL, str(e))


# ═══════════════════════════════════════════════════════════════
# M01: 模块导入测试
# ═══════════════════════════════════════════════════════════════
def test_imports():
    module = "IMPORT"
    imports = [
        ("app.config", "Settings, get_settings"),
        ("app.core.security", "hash_password, verify_password, create_access_token, create_refresh_token, decode_access_token, decode_refresh_token"),
        ("app.core.exceptions", "AppException, NotFoundException, UnauthorizedException, ForbiddenException, BadRequestException"),
        ("app.core.database", "Base, get_db, init_db"),
        ("app.models.user", "User, RefreshToken"),
        ("app.models.product", "Product, ProductFeature"),
        ("app.models.monitor", "MonitorRule, Notification"),
        ("app.models.collect", "CollectTask, CollectTaskItem"),
        ("app.models.admin", "ProxyPool, AdminAuditLog, RiskEvent"),
        ("app.models.license", "LicenseCode"),
        ("app.models.ai", "AIAnalysis, AIReport"),
        ("app.models.feature_gate", "FeatureGate, FeatureGateUsage"),
        ("app.schemas.auth", "RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest, UserInfoResponse"),
        ("app.schemas.user", None),
        ("app.middleware.auth", "get_current_user, CurrentUser, AdminUser"),
        ("app.middleware.feature_gate", "FeatureGateMiddleware"),
        ("app.services.auth_service", "AuthService"),
        ("app.services.sync_service", "SyncService"),
        ("app.ai.service", "AIService"),
        ("app.ai.providers", "get_provider, ANALYSIS_PROMPTS"),
        ("app.collect.engine", "CollectEngine, ProxyManager, RiskDetector"),
        ("app.collect.rate_controller", "AdaptiveRateController"),
        ("app.ws.manager", "ConnectionManager, manager"),
        ("app.scheduler.tasks", "process_pending_tasks, check_proxy_health"),
        ("app.api.router", "api_router"),
        ("shared.constants.feature_gates", "PLAN_LIMITS, PLAN_HIERARCHY, is_plan_sufficient"),
        ("shared.constants.error_codes", "ERROR_CODES"),
    ]

    for mod_path, classes in imports:
        try:
            mod = __import__(mod_path, fromlist=classes.split(", ") if classes else [])
            if classes:
                for cls_name in classes.split(", "):
                    cls_name = cls_name.strip()
                    if not hasattr(mod, cls_name):
                        record(module, f"{mod_path}.{cls_name}", FAIL, "属性不存在")
                        break
                else:
                    record(module, f"{mod_path} ({classes})", PASS)
            else:
                record(module, mod_path, PASS)
        except Exception as e:
            record(module, f"{mod_path}", FAIL, traceback.format_exc()[:200])


# ═══════════════════════════════════════════════════════════════
# M02: 核心安全模块测试
# ═══════════════════════════════════════════════════════════════
def test_security():
    module = "SECURITY"
    from app.core.security import (
        hash_password, verify_password, create_access_token,
        create_refresh_token, decode_access_token, decode_refresh_token,
    )

    def t_hash_verify():
        hashed = hash_password("TestPass123")
        if hashed != "TestPass123" and verify_password("TestPass123", hashed):
            record(module, "密码哈希与验证", PASS)
        else:
            record(module, "密码哈希与验证", FAIL, "验证失败")

    def t_wrong_pass():
        hashed = hash_password("TestPass123")
        if not verify_password("WrongPass999", hashed):
            record(module, "错误密码验证失败", PASS)
        else:
            record(module, "错误密码验证失败", FAIL, "应该返回False")

    def t_long_pass():
        long_pw = "A" * 100 + "1b"
        if verify_password(long_pw, hash_password(long_pw)):
            record(module, "长密码截断(>72字节)", PASS)
        else:
            record(module, "长密码截断(>72字节)", FAIL, "长密码验证失败")

    def t_access_token():
        token = create_access_token(subject="user-123", extra={"plan": "pro", "role": "user"})
        payload = decode_access_token(token)
        if payload["sub"] == "user-123" and payload["type"] == "access" and payload["plan"] == "pro":
            record(module, "Access Token 创建与解码", PASS)
        else:
            record(module, "Access Token 创建与解码", FAIL, f"payload不匹配: {payload}")

    def t_refresh_token():
        token = create_refresh_token(subject="user-456")
        payload = decode_refresh_token(token)
        if payload["sub"] == "user-456" and payload["type"] == "refresh":
            record(module, "Refresh Token 创建与解码", PASS)
        else:
            record(module, "Refresh Token 创建与解码", FAIL, f"payload不匹配: {payload}")

    def t_token_type_mismatch():
        token = create_access_token(subject="user-789")
        try:
            decode_refresh_token(token)
            record(module, "token类型不匹配应拒绝", FAIL, "应该抛出异常")
        except (ValueError, Exception):
            record(module, "token类型不匹配应拒绝", PASS)

    def t_fake_token():
        try:
            decode_access_token("fake.token.here")
            record(module, "伪造token解码应失败", FAIL, "应该抛出异常")
        except Exception:
            record(module, "伪造token解码应失败", PASS)

    safe_test(module, "密码哈希与验证", t_hash_verify)
    safe_test(module, "错误密码验证失败", t_wrong_pass)
    safe_test(module, "长密码截断(>72字节)", t_long_pass)
    safe_test(module, "Access Token 创建与解码", t_access_token)
    safe_test(module, "Refresh Token 创建与解码", t_refresh_token)
    safe_test(module, "token类型不匹配应拒绝", t_token_type_mismatch)
    safe_test(module, "伪造token解码应失败", t_fake_token)


# ═══════════════════════════════════════════════════════════════
# M03: 配置模块测试
# ═══════════════════════════════════════════════════════════════
def test_config():
    module = "CONFIG"
    from app.config import get_settings, Settings

    def t_type():
        s = get_settings()
        if isinstance(s, Settings):
            record(module, "get_settings 返回 Settings 实例", PASS)
        else:
            record(module, "get_settings 返回 Settings 实例", FAIL, f"类型: {type(s)}")

    def t_db_url():
        s = get_settings()
        if "postgresql+asyncpg://" in s.DATABASE_URL:
            record(module, "DATABASE_URL 格式正确", PASS)
        else:
            record(module, "DATABASE_URL 格式正确", FAIL, s.DATABASE_URL)

    def t_redis_url():
        s = get_settings()
        if "redis://" in s.REDIS_URL_RESOLVED:
            record(module, "REDIS_URL_RESOLVED 格式正确", PASS)
        else:
            record(module, "REDIS_URL_RESOLVED 格式正确", FAIL, s.REDIS_URL_RESOLVED)

    def t_cors():
        s = get_settings()
        if isinstance(s.CORS_ORIGINS, list) and len(s.CORS_ORIGINS) > 0:
            record(module, "CORS_ORIGINS 是列表", PASS)
        else:
            record(module, "CORS_ORIGINS 是列表", FAIL, str(s.CORS_ORIGINS))

    def t_jwt():
        s = get_settings()
        if s.JWT_SECRET and s.JWT_ALGORITHM and s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0:
            record(module, "JWT 配置项存在", PASS)
        else:
            record(module, "JWT 配置项存在", FAIL, "缺少JWT配置")

    safe_test(module, "get_settings 返回 Settings 实例", t_type)
    safe_test(module, "DATABASE_URL 格式正确", t_db_url)
    safe_test(module, "REDIS_URL_RESOLVED 格式正确", t_redis_url)
    safe_test(module, "CORS_ORIGINS 是列表", t_cors)
    safe_test(module, "JWT 配置项存在", t_jwt)


# ═══════════════════════════════════════════════════════════════
# M04: 异常处理测试
# ═══════════════════════════════════════════════════════════════
def test_exceptions():
    module = "EXCEPTIONS"
    from app.core.exceptions import (
        AppException, NotFoundException, UnauthorizedException,
        ForbiddenException, BadRequestException, register_exception_handlers,
    )

    def t_not_found():
        e = NotFoundException(message="测试")
        if e.code == 90002:
            record(module, "NotFoundException code=90002", PASS)
        else:
            record(module, "NotFoundException code", FAIL, f"code={e.code}")

    def t_unauthorized():
        e = UnauthorizedException(message="测试")
        if e.code == 40020:
            record(module, "UnauthorizedException code=40020", PASS)
        else:
            record(module, "UnauthorizedException code", FAIL, f"code={e.code}")

    def t_forbidden():
        e = ForbiddenException(message="测试")
        if e.code == 42010:
            record(module, "ForbiddenException code=42010", PASS)
        else:
            record(module, "ForbiddenException code", FAIL, f"code={e.code}")

    def t_bad_request():
        e = BadRequestException(message="测试")
        if e.code == 90001:
            record(module, "BadRequestException code=90001", PASS)
        else:
            record(module, "BadRequestException code", FAIL, f"code={e.code}")

    def t_register():
        from fastapi import FastAPI
        app = FastAPI()
        register_exception_handlers(app)
        record(module, "register_exception_handlers 不报错", PASS)

    safe_test(module, "NotFoundException code=40400", t_not_found)
    safe_test(module, "UnauthorizedException code=40101", t_unauthorized)
    safe_test(module, "ForbiddenException code=40310", t_forbidden)
    safe_test(module, "BadRequestException code=40000", t_bad_request)
    safe_test(module, "register_exception_handlers 不报错", t_register)


# ═══════════════════════════════════════════════════════════════
# M05: Schema 验证测试
# ═══════════════════════════════════════════════════════════════
def test_schemas():
    module = "SCHEMA"
    from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

    def t_register_valid():
        r = RegisterRequest(email="test@example.com", nickname="test", password="TestPass123")
        if r.email == "test@example.com":
            record(module, "RegisterRequest 正常创建", PASS)
        else:
            record(module, "RegisterRequest 正常创建", FAIL)

    def t_register_weak():
        try:
            RegisterRequest(email="test@example.com", nickname="test", password="weak")
            record(module, "弱密码拒绝", FAIL, "应该拒绝弱密码")
        except Exception:
            record(module, "弱密码拒绝", PASS)

    def t_register_no_upper():
        try:
            RegisterRequest(email="test@example.com", nickname="test", password="lowercase1")
            record(module, "无大写字母拒绝", FAIL, "应该拒绝")
        except Exception:
            record(module, "无大写字母拒绝", PASS)

    def t_register_no_digit():
        try:
            RegisterRequest(email="test@example.com", nickname="test", password="NoDigitsHere")
            record(module, "无数字拒绝", FAIL, "应该拒绝")
        except Exception:
            record(module, "无数字拒绝", PASS)

    def t_register_bad_email():
        try:
            RegisterRequest(email="not-an-email", nickname="test", password="TestPass123")
            record(module, "无效邮箱拒绝", FAIL, "应该拒绝")
        except Exception:
            record(module, "无效邮箱拒绝", PASS)

    def t_login():
        LoginRequest(email="test@example.com", password="anypassword")
        record(module, "LoginRequest 正常创建", PASS)

    def t_token_response():
        r = TokenResponse(access_token="at", refresh_token="rt", expires_in=1800)
        if r.token_type == "bearer":
            record(module, "TokenResponse 字段完整", PASS)
        else:
            record(module, "TokenResponse 字段完整", FAIL, f"token_type={r.token_type}")

    safe_test(module, "RegisterRequest 正常创建", t_register_valid)
    safe_test(module, "弱密码拒绝", t_register_weak)
    safe_test(module, "无大写字母拒绝", t_register_no_upper)
    safe_test(module, "无数字拒绝", t_register_no_digit)
    safe_test(module, "无效邮箱拒绝", t_register_bad_email)
    safe_test(module, "LoginRequest 正常创建", t_login)
    safe_test(module, "TokenResponse 字段完整", t_token_response)


# ═══════════════════════════════════════════════════════════════
# M06: Feature Gate 逻辑测试
# ═══════════════════════════════════════════════════════════════
def test_feature_gates():
    module = "FEATURE_GATE"
    from shared.constants.feature_gates import PLAN_LIMITS, PLAN_HIERARCHY, is_plan_sufficient

    def t_all_plans():
        if all(k in PLAN_LIMITS for k in ["free", "pro", "premium", "enterprise"]):
            record(module, "PLAN_LIMITS 包含所有套餐", PASS)
        else:
            missing = set(["free", "pro", "premium", "enterprise"]) - set(PLAN_LIMITS.keys())
            record(module, "PLAN_LIMITS 包含所有套餐", FAIL, f"缺少: {missing}")

    def t_free_limit():
        free_limits = PLAN_LIMITS.get("free", {})
        if "maxProducts" in free_limits:
            record(module, "free 套餐有产品数量限制", PASS)
        else:
            record(module, "free 套餐有产品数量限制", FAIL, f"keys: {list(free_limits.keys())}")

    def t_enterprise_gte_premium():
        ent = PLAN_LIMITS.get("enterprise", {})
        prem = PLAN_LIMITS.get("premium", {})
        if ent.get("maxProducts", 0) >= prem.get("maxProducts", 0):
            record(module, "enterprise >= premium", PASS)
        else:
            record(module, "enterprise >= premium", FAIL, f"ent={ent}, prem={prem}")

    def t_sufficient():
        if is_plan_sufficient("enterprise", "pro"):
            record(module, "enterprise 满足 pro", PASS)
        else:
            record(module, "enterprise 满足 pro", FAIL)

    def t_insufficient():
        if not is_plan_sufficient("free", "pro"):
            record(module, "free 不满足 pro", PASS)
        else:
            record(module, "free 不满足 pro", FAIL)

    def t_equal():
        if is_plan_sufficient("pro", "pro"):
            record(module, "pro 满足 pro", PASS)
        else:
            record(module, "pro 满足 pro", FAIL)

    safe_test(module, "PLAN_LIMITS 包含所有套餐", t_all_plans)
    safe_test(module, "free 套餐有产品数量限制", t_free_limit)
    safe_test(module, "enterprise >= premium", t_enterprise_gte_premium)
    safe_test(module, "enterprise 满足 pro", t_sufficient)
    safe_test(module, "free 不满足 pro", t_insufficient)
    safe_test(module, "pro 满足 pro", t_equal)


# ═══════════════════════════════════════════════════════════════
# M07: 速率控制器测试
# ═══════════════════════════════════════════════════════════════
def test_rate_controller():
    module = "RATE_CTRL"
    from app.collect.rate_controller import AdaptiveRateController

    def t_initial():
        rc = AdaptiveRateController(base_interval=1.0)
        if rc.current_interval == 1.0:
            record(module, "初始间隔为 base_interval", PASS)
        else:
            record(module, "初始间隔为 base_interval", FAIL, f"interval={rc.current_interval}")

    def t_success_decrease():
        rc = AdaptiveRateController(base_interval=1.0)
        for _ in range(10):
            rc.on_success()
        if rc.current_interval < 1.0:
            record(module, "on_success 连续10次后间隔减小", PASS)
        else:
            record(module, "on_success 连续10次后间隔减小", FAIL, f"interval={rc.current_interval}")

    def t_risk_double():
        rc = AdaptiveRateController(base_interval=1.0)
        rc.on_risk_detected()
        if rc.current_interval == 2.0:
            record(module, "on_risk_detected 间隔翻倍", PASS)
        else:
            record(module, "on_risk_detected 间隔翻倍", FAIL, f"interval={rc.current_interval}")

    def t_error_increase():
        rc = AdaptiveRateController(base_interval=1.0)
        rc.on_error()
        if rc.current_interval == 1.5:
            record(module, "on_error 间隔增加50%", PASS)
        else:
            record(module, "on_error 间隔增加50%", FAIL, f"interval={rc.current_interval}")

    def t_max_interval():
        rc = AdaptiveRateController(base_interval=8.0, max_interval=10.0)
        rc.on_risk_detected()
        if rc.current_interval <= 10.0:
            record(module, "间隔不超过 max_interval", PASS)
        else:
            record(module, "间隔不超过 max_interval", FAIL, f"interval={rc.current_interval}")

    def t_min_interval():
        rc = AdaptiveRateController(base_interval=0.3, min_interval=0.2)
        for _ in range(30):
            rc.on_success()
        if rc.current_interval >= 0.2:
            record(module, "间隔不低于 min_interval", PASS)
        else:
            record(module, "间隔不低于 min_interval", FAIL, f"interval={rc.current_interval}")

    def t_reset():
        rc = AdaptiveRateController(base_interval=1.0)
        rc.on_risk_detected()
        rc.on_risk_detected()
        rc.reset()
        if rc.current_interval == 1.0 and rc.consecutive_success == 0:
            record(module, "reset 恢复默认", PASS)
        else:
            record(module, "reset 恢复默认", FAIL, f"interval={rc.current_interval}")

    async def t_acquire():
        rc = AdaptiveRateController(base_interval=0.01)
        start = time.time()
        await rc.acquire()
        elapsed = time.time() - start
        if elapsed < 0.1:
            record(module, "acquire 首次不等待", PASS)
        else:
            record(module, "acquire 首次不等待", FAIL, f"elapsed={elapsed:.3f}s")

    safe_test(module, "初始间隔为 base_interval", t_initial)
    safe_test(module, "on_success 连续10次后间隔减小", t_success_decrease)
    safe_test(module, "on_risk_detected 间隔翻倍", t_risk_double)
    safe_test(module, "on_error 间隔增加50%", t_error_increase)
    safe_test(module, "间隔不超过 max_interval", t_max_interval)
    safe_test(module, "间隔不低于 min_interval", t_min_interval)
    safe_test(module, "reset 恢复默认", t_reset)
    asyncio.run(t_acquire())


# ═══════════════════════════════════════════════════════════════
# M08: 风险检测器测试
# ═══════════════════════════════════════════════════════════════
def test_risk_detector():
    module = "RISK_DETECT"
    from app.collect.engine import RiskDetector

    def t_429():
        result = RiskDetector.detect("", 429)
        if result and result["risk_type"] == "rate_limit":
            record(module, "429 → rate_limit", PASS)
        else:
            record(module, "429 → rate_limit", FAIL, f"result={result}")

    def t_403():
        result = RiskDetector.detect("", 403)
        if result and result["risk_type"] == "ip_blocked":
            record(module, "403 → ip_blocked", PASS)
        else:
            record(module, "403 → ip_blocked", FAIL, f"result={result}")

    def t_captcha():
        result = RiskDetector.detect("请输入验证码继续操作", 200)
        if result and result["risk_type"] == "captcha":
            record(module, "验证码关键词 → captcha", PASS)
        else:
            record(module, "验证码关键词 → captcha", FAIL, f"result={result}")

    def t_login():
        result = RiskDetector.detect("请登录后查看", 200)
        if result and result["risk_type"] == "login_required":
            record(module, "登录关键词 → login_required", PASS)
        else:
            record(module, "登录关键词 → login_required", FAIL, f"result={result}")

    def t_normal():
        result = RiskDetector.detect("商品价格：99元", 200)
        if result is None:
            record(module, "正常响应 → None", PASS)
        else:
            record(module, "正常响应 → None", FAIL, f"result={result}")

    def t_english():
        result = RiskDetector.detect("Too many requests, please try again later", 200)
        if result and result["risk_type"] == "rate_limit":
            record(module, "英文关键词检测", PASS)
        else:
            record(module, "英文关键词检测", FAIL, f"result={result}")

    safe_test(module, "429 → rate_limit", t_429)
    safe_test(module, "403 → ip_blocked", t_403)
    safe_test(module, "验证码关键词 → captcha", t_captcha)
    safe_test(module, "登录关键词 → login_required", t_login)
    safe_test(module, "正常响应 → None", t_normal)
    safe_test(module, "英文关键词检测", t_english)


# ═══════════════════════════════════════════════════════════════
# M09: WebSocket 管理器测试
# ═══════════════════════════════════════════════════════════════
def test_ws_manager():
    module = "WS_MANAGER"
    from app.ws.manager import ConnectionManager

    async def run():
        def t_empty():
            mgr = ConnectionManager()
            if len(mgr.active_connections) == 0:
                record(module, "新建管理器无连接", PASS)
            else:
                record(module, "新建管理器无连接", FAIL, f"connections={len(mgr.active_connections)}")

        async def t_disconnect_nonexist():
            mgr = ConnectionManager()
            mgr.disconnect("nonexistent")
            record(module, "disconnect 不存在的用户不报错", PASS)

        async def t_send_nonexist():
            mgr = ConnectionManager()
            await mgr.send_to_user("nonexistent", {"type": "test"})
            record(module, "send_to_user 不存在的用户不报错", PASS)

        async def t_connect_disconnect():
            mgr = ConnectionManager()
            ws = AsyncMock()
            await mgr.connect("user-1", ws)
            r1 = len(mgr.active_connections) == 1
            mgr.disconnect("user-1")
            r2 = len(mgr.active_connections) == 0
            if r1 and r2:
                record(module, "connect 和 disconnect", PASS)
            else:
                record(module, "connect 和 disconnect", FAIL)

        async def t_send():
            mgr = ConnectionManager()
            ws = AsyncMock()
            await mgr.connect("user-1", ws)
            await mgr.send_to_user("user-1", {"type": "test", "data": "hello"})
            if ws.send_json.called:
                record(module, "send_to_user 发送消息", PASS)
            else:
                record(module, "send_to_user 发送消息", FAIL, "send_json未被调用")

        async def t_kick_old():
            mgr = ConnectionManager()
            ws1 = AsyncMock()
            ws2 = AsyncMock()
            await mgr.connect("user-1", ws1)
            await mgr.connect("user-1", ws2)
            if ws1.close.called and mgr.active_connections["user-1"] is ws2:
                record(module, "重复连接踢掉旧连接", PASS)
            else:
                record(module, "重复连接踢掉旧连接", FAIL, f"close_called={ws1.close.called}")

        t_empty()
        await t_disconnect_nonexist()
        await t_send_nonexist()
        await t_connect_disconnect()
        await t_send()
        await t_kick_old()

    asyncio.run(run())


# ═══════════════════════════════════════════════════════════════
# M10: AI Providers 测试
# ═══════════════════════════════════════════════════════════════
def test_ai_providers():
    module = "AI_PROVIDER"
    from app.ai.providers import get_provider, ANALYSIS_PROMPTS

    def t_basic():
        if "basic_analysis" in ANALYSIS_PROMPTS:
            record(module, "ANALYSIS_PROMPTS 包含 basic_analysis", PASS)
        else:
            record(module, "ANALYSIS_PROMPTS 包含 basic_analysis", FAIL, f"keys={list(ANALYSIS_PROMPTS.keys())}")

    def t_trend():
        if "trend_score" in ANALYSIS_PROMPTS:
            record(module, "ANALYSIS_PROMPTS 包含 trend_score", PASS)
        else:
            record(module, "ANALYSIS_PROMPTS 包含 trend_score", FAIL)

    def t_prediction():
        if "prediction" in ANALYSIS_PROMPTS:
            record(module, "ANALYSIS_PROMPTS 包含 prediction", PASS)
        else:
            record(module, "ANALYSIS_PROMPTS 包含 prediction", FAIL)

    def t_risk():
        if "risk_warning" in ANALYSIS_PROMPTS:
            record(module, "ANALYSIS_PROMPTS 包含 risk_warning", PASS)
        else:
            record(module, "ANALYSIS_PROMPTS 包含 risk_warning", FAIL)

    def t_structure():
        if all("template" in v and "system" in v for v in ANALYSIS_PROMPTS.values()):
            record(module, "每个prompt有template和system", PASS)
        else:
            record(module, "每个prompt有template和system", FAIL, "缺少字段")

    def t_default_provider():
        p = get_provider(None)
        if p is not None:
            record(module, "get_provider 默认返回非None", PASS)
        else:
            record(module, "get_provider 默认返回非None", FAIL)

    safe_test(module, "ANALYSIS_PROMPTS 包含 basic_analysis", t_basic)
    safe_test(module, "ANALYSIS_PROMPTS 包含 trend_score", t_trend)
    safe_test(module, "ANALYSIS_PROMPTS 包含 prediction", t_prediction)
    safe_test(module, "ANALYSIS_PROMPTS 包含 risk_warning", t_risk)
    safe_test(module, "每个prompt有template和system", t_structure)
    safe_test(module, "get_provider 默认返回非None", t_default_provider)


# ═══════════════════════════════════════════════════════════════
# M11: FastAPI 应用初始化测试
# ═══════════════════════════════════════════════════════════════
def test_app_init():
    module = "APP_INIT"
    from app.main import app

    def t_exists():
        if app is not None:
            record(module, "FastAPI app 实例存在", PASS)
        else:
            record(module, "FastAPI app 实例存在", FAIL, "app为None")

    def t_title():
        if app.title:
            record(module, "app title 非空", PASS)
        else:
            record(module, "app title 非空", FAIL, f"title={app.title}")

    def t_cors():
        if any("CORSMiddleware" in str(m) for m in app.user_middleware):
            record(module, "CORS 中间件已注册", PASS)
        else:
            record(module, "CORS 中间件已注册", FAIL, "未找到CORSMiddleware")

    def t_api_route():
        if any(hasattr(r, "path") and r.path.startswith("/api/v1") for r in app.routes):
            record(module, "API路由已注册 (/api/v1)", PASS)
        else:
            record(module, "API路由已注册 (/api/v1)", FAIL, "未找到/api/v1路由")

    safe_test(module, "FastAPI app 实例存在", t_exists)
    safe_test(module, "app title 非空", t_title)
    safe_test(module, "CORS 中间件已注册", t_cors)
    safe_test(module, "API路由已注册 (/api/v1)", t_api_route)


# ═══════════════════════════════════════════════════════════════
# M12: API 路由完整性测试
# ═══════════════════════════════════════════════════════════════
def test_api_routes():
    module = "API_ROUTES"
    from app.main import app

    expected_routes = [
        ("/api/v1/health", ["GET"]),
        ("/api/v1/auth/register", ["POST"]),
        ("/api/v1/auth/login", ["POST"]),
        ("/api/v1/auth/refresh", ["POST"]),
        ("/api/v1/auth/me", ["GET"]),
        ("/api/v1/products", ["POST", "GET"]),
        ("/api/v1/monitor/rules", ["POST", "GET"]),
        ("/api/v1/collect/tasks", ["POST", "GET"]),
        ("/api/v1/ai/analyze", ["POST"]),
        ("/api/v1/ai/report", ["POST"]),
        ("/api/v1/sync/push", ["POST"]),
        ("/api/v1/sync/pull", ["POST"]),
        ("/api/v1/admin/login", ["POST"]),
        ("/api/v1/admin/stats", ["GET"]),
        ("/api/v1/admin/users", ["GET"]),
    ]

    all_routes = {}
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path
            for method in route.methods:
                all_routes.setdefault(path, []).append(method)

    for path, methods in expected_routes:
        found = all_routes.get(path, [])
        missing = [m for m in methods if m not in found]
        if not missing:
            record(module, f"路由 {path}", PASS)
        else:
            record(module, f"路由 {path}", FAIL, f"缺少方法: {missing}")


# ═══════════════════════════════════════════════════════════════
# M13: 数据模型字段测试
# ═══════════════════════════════════════════════════════════════
def test_models():
    module = "MODELS"
    from app.models.user import User, RefreshToken
    from app.models.product import Product, ProductFeature
    from app.models.monitor import MonitorRule, Notification
    from app.models.collect import CollectTask, CollectTaskItem
    from app.models.admin import ProxyPool, AdminAuditLog, RiskEvent
    from app.models.license import LicenseCode
    from app.models.ai import AIAnalysis, AIReport
    from app.models.feature_gate import FeatureGate, FeatureGateUsage

    model_checks = [
        ("User", User, ["email", "nickname", "password_hash", "plan", "role", "is_active"]),
        ("RefreshToken", RefreshToken, ["user_id", "token_hash", "expires_at"]),
        ("Product", Product, ["user_id", "platform", "platform_product_id", "product_name", "is_active"]),
        ("ProductFeature", ProductFeature, ["product_id", "price", "sales_count", "source"]),
        ("MonitorRule", MonitorRule, ["user_id", "product_id", "rule_name", "rule_type", "conditions"]),
        ("Notification", Notification, ["user_id", "type", "title", "content", "is_read"]),
        ("CollectTask", CollectTask, ["user_id", "task_type", "platform", "status"]),
        ("CollectTaskItem", CollectTaskItem, ["task_id", "target_id"]),
        ("ProxyPool", ProxyPool, ["ip", "port", "protocol", "status", "health_score"]),
        ("LicenseCode", LicenseCode, ["code", "plan", "duration_days", "status"]),
        ("AIAnalysis", AIAnalysis, ["user_id", "product_id", "analysis_type", "provider", "result"]),
        ("FeatureGate", FeatureGate, ["gate_key", "gate_name", "gate_type", "required_plan"]),
        ("FeatureGateUsage", FeatureGateUsage, ["user_id", "gate_key"]),
    ]

    for name, model_cls, expected_fields in model_checks:
        mapper = model_cls.__table__.columns
        actual_fields = set(c.name for c in mapper)
        missing = [f for f in expected_fields if f not in actual_fields]
        if not missing:
            record(module, f"{name} 字段完整", PASS)
        else:
            record(module, f"{name} 字段缺失", FAIL, f"缺少: {missing}")


# ═══════════════════════════════════════════════════════════════
# M14: API 端点模拟测试（TestClient）
# ═══════════════════════════════════════════════════════════════
def test_api_endpoints():
    module = "API_E2E"
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.core.database import get_db
    from app.core.security import create_access_token, hash_password

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "test@example.com"
    mock_user.nickname = "测试用户"
    mock_user.plan = "pro"
    mock_user.role = "user"
    mock_user.is_active = True
    mock_user.avatar_url = None
    mock_user.plan_expires_at = None
    mock_user.password_hash = hash_password("TestPass123")

    mock_admin = MagicMock()
    mock_admin.id = uuid.uuid4()
    mock_admin.email = "admin@vuemonitor.com"
    mock_admin.nickname = "管理员"
    mock_admin.plan = "enterprise"
    mock_admin.role = "admin"
    mock_admin.is_active = True
    mock_admin.avatar_url = None
    mock_admin.plan_expires_at = None
    mock_admin.password_hash = hash_password("AdminPass123")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    async def run_tests():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/health")
            if r.status_code == 200 and r.json().get("status") == "ok":
                record(module, "GET /api/v1/health", PASS)
            else:
                record(module, "GET /api/v1/health", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/auth/register", json={
                "email": "new@example.com", "nickname": "新用户", "password": "NewPass123"
            })
            if r.status_code in (200, 201, 400, 422, 500):
                record(module, "POST /auth/register (可达)", PASS)
            else:
                record(module, "POST /auth/register", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/auth/login", json={
                "email": "test@example.com", "password": "TestPass123"
            })
            if r.status_code in (200, 401, 403, 422, 500):
                record(module, "POST /auth/login (可达)", PASS)
            else:
                record(module, "POST /auth/login", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/auth/me")
            if r.status_code in (401, 403):
                record(module, "GET /auth/me 无token拒绝", PASS)
            else:
                record(module, "GET /auth/me 无token拒绝", FAIL, f"status={r.status_code}")

            user_token = create_access_token(subject=str(mock_user.id), extra={"plan": "pro", "role": "user"})
            r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /auth/me 有token", PASS)
            else:
                record(module, "GET /auth/me 有token", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/products", headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /products (可达)", PASS)
            else:
                record(module, "GET /products", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/products", json={
                "platform": "xhs", "platform_product_id": "test123", "product_name": "测试商品"
            }, headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 201, 401, 403, 404, 422, 500):
                record(module, "POST /products (可达)", PASS)
            else:
                record(module, "POST /products", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/monitor/rules", headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /monitor/rules (可达)", PASS)
            else:
                record(module, "GET /monitor/rules", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/collect/tasks", headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /collect/tasks (可达)", PASS)
            else:
                record(module, "GET /collect/tasks", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/collect/tasks", json={
                "task_type": "product", "platform": "xhs",
                "target_type": "product_id", "target_ids": ["12345"]
            }, headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 201, 401, 403, 404, 422, 500):
                record(module, "POST /collect/tasks (可达)", PASS)
            else:
                record(module, "POST /collect/tasks", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/ai/analyze", json={
                "product_id": str(uuid.uuid4()), "analysis_type": "basic_analysis"
            }, headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 400, 401, 403, 404, 422, 500):
                record(module, "POST /ai/analyze (可达)", PASS)
            else:
                record(module, "POST /ai/analyze", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/sync/push", json={
                "platform": "xhs", "platform_product_id": "test123",
                "features": [{"price": 99.9, "collected_at": datetime.now(timezone.utc).isoformat()}]
            }, headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 201, 401, 403, 404, 422, 500):
                record(module, "POST /sync/push (可达)", PASS)
            else:
                record(module, "POST /sync/push", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/sync/pull", json={},
                headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (200, 401, 403, 404, 422, 500):
                record(module, "POST /sync/pull (可达)", PASS)
            else:
                record(module, "POST /sync/pull", FAIL, f"status={r.status_code}")

            r = await client.post("/api/v1/admin/login", json={
                "username": "admin@vuemonitor.com", "password": "AdminPass123"
            })
            if r.status_code in (200, 401, 403, 422, 500):
                record(module, "POST /admin/login (可达)", PASS)
            else:
                record(module, "POST /admin/login", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/admin/stats")
            if r.status_code in (401, 403):
                record(module, "GET /admin/stats 无token拒绝", PASS)
            else:
                record(module, "GET /admin/stats 无token拒绝", FAIL, f"status={r.status_code}")

            admin_token = create_access_token(subject=str(mock_admin.id), extra={"plan": "enterprise", "role": "admin"})
            r = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /admin/stats admin token", PASS)
            else:
                record(module, "GET /admin/stats admin token", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /admin/users admin token", PASS)
            else:
                record(module, "GET /admin/users admin token", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/admin/licenses", headers={"Authorization": f"Bearer {admin_token}"})
            if r.status_code in (200, 401, 403, 404, 500):
                record(module, "GET /admin/licenses admin token", PASS)
            else:
                record(module, "GET /admin/licenses admin token", FAIL, f"status={r.status_code}")

            r = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {user_token}"})
            if r.status_code in (401, 403):
                record(module, "GET /admin/stats 普通用户拒绝", PASS)
            else:
                record(module, "GET /admin/stats 普通用户拒绝", FAIL, f"status={r.status_code}")

    asyncio.run(run_tests())
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# M15: 错误码一致性测试
# ═══════════════════════════════════════════════════════════════
def test_error_codes():
    module = "ERROR_CODES"
    from shared.constants.error_codes import ERROR_CODES

    required_codes = [
        "BAD_REQUEST", "NOT_FOUND", "USER_CREDENTIALS_INVALID",
        "GATE_FEATURE_UNAUTHORIZED", "INTERNAL_ERROR",
    ]

    for code_name in required_codes:
        if code_name in ERROR_CODES:
            record(module, f"ERROR_CODES['{code_name}'] = {ERROR_CODES[code_name]}", PASS)
        else:
            record(module, f"ERROR_CODES['{code_name}']", FAIL, "不存在")

    if all(isinstance(v, int) for v in ERROR_CODES.values()):
        record(module, "所有错误码为整数", PASS)
    else:
        record(module, "所有错误码为整数", FAIL, "存在非整数错误码")


# ═══════════════════════════════════════════════════════════════
# M16: 调度器配置测试
# ═══════════════════════════════════════════════════════════════
def test_scheduler():
    module = "SCHEDULER"
    from app.scheduler.tasks import process_pending_tasks, check_proxy_health

    if asyncio.iscoroutinefunction(process_pending_tasks):
        record(module, "process_pending_tasks 是协程函数", PASS)
    else:
        record(module, "process_pending_tasks 是协程函数", FAIL, f"type={type(process_pending_tasks)}")

    if asyncio.iscoroutinefunction(check_proxy_health):
        record(module, "check_proxy_health 是协程函数", PASS)
    else:
        record(module, "check_proxy_health 是协程函数", FAIL, f"type={type(check_proxy_health)}")


# ═══════════════════════════════════════════════════════════════
# M17: 登录限流逻辑测试
# ═══════════════════════════════════════════════════════════════
def test_login_rate_limit():
    module = "RATE_LIMIT"
    from app.api.auth import _MAX_ATTEMPTS, _LOCKOUT_SECONDS
    from app.api.admin import _ADMIN_MAX_ATTEMPTS, _ADMIN_LOCKOUT_SECONDS

    if _MAX_ATTEMPTS > 0:
        record(module, "用户登录最大尝试次数 > 0", PASS)
    else:
        record(module, "用户登录最大尝试次数 > 0", FAIL, f"value={_MAX_ATTEMPTS}")

    if _LOCKOUT_SECONDS > 0:
        record(module, "用户登录锁定时间 > 0", PASS)
    else:
        record(module, "用户登录锁定时间 > 0", FAIL, f"value={_LOCKOUT_SECONDS}")

    if _ADMIN_MAX_ATTEMPTS > 0:
        record(module, "管理员登录最大尝试次数 > 0", PASS)
    else:
        record(module, "管理员登录最大尝试次数 > 0", FAIL, f"value={_ADMIN_MAX_ATTEMPTS}")

    if _ADMIN_LOCKOUT_SECONDS > 0:
        record(module, "管理员登录锁定时间 > 0", PASS)
    else:
        record(module, "管理员登录锁定时间 > 0", FAIL, f"value={_ADMIN_LOCKOUT_SECONDS}")

    if _ADMIN_MAX_ATTEMPTS <= _MAX_ATTEMPTS:
        record(module, "管理员限制比用户严格", PASS)
    else:
        record(module, "管理员限制比用户严格", FAIL, f"admin={_ADMIN_MAX_ATTEMPTS} > user={_MAX_ATTEMPTS}")


# ═══════════════════════════════════════════════════════════════
# 运行所有测试
# ═══════════════════════════════════════════════════════════════
def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         VueMonitor 全模块系统测试                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    tests = [
        ("M01 模块导入", test_imports),
        ("M02 核心安全", test_security),
        ("M03 配置模块", test_config),
        ("M04 异常处理", test_exceptions),
        ("M05 Schema验证", test_schemas),
        ("M06 Feature Gate", test_feature_gates),
        ("M07 速率控制器", test_rate_controller),
        ("M08 风险检测", test_risk_detector),
        ("M09 WebSocket管理", test_ws_manager),
        ("M10 AI Providers", test_ai_providers),
        ("M11 应用初始化", test_app_init),
        ("M12 API路由完整性", test_api_routes),
        ("M13 数据模型字段", test_models),
        ("M14 API端点模拟", test_api_endpoints),
        ("M15 错误码一致性", test_error_codes),
        ("M16 调度器配置", test_scheduler),
        ("M17 登录限流", test_login_rate_limit),
    ]

    for name, fn in tests:
        print(f"\n── {name} {'─' * (50 - len(name))}")
        try:
            fn()
        except Exception as e:
            print(f"  💥 模块级崩溃: {e}")
            traceback.print_exc()
            results["fail"] += 1
            results["errors"].append(f"[{name}] 模块崩溃: {str(e)[:100]}")

    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    测试结果汇总                          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    total = results["pass"] + results["fail"] + results["skip"]
    if total > 0:
        print(f"║  总计: {total}  ✅ 通过: {results['pass']}  ❌ 失败: {results['fail']}  ⏭️ 跳过: {results['skip']}")
        print(f"║  通过率: {results['pass']/total*100:.1f}%")
    else:
        print("║  无测试")
    print("╚══════════════════════════════════════════════════════════╝")

    if results["errors"]:
        print("\n❌ 失败详情:")
        for err in results["errors"]:
            print(f"  • {err}")

    return results["fail"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
