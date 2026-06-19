import os
import secrets
import warnings
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_docker_secret(name: str) -> str | None:
    secret_path = Path(f"/run/secrets/{name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    return None


class Settings(BaseSettings):
    APP_NAME: str = "XHS365"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "vuemonitor"
    DB_USER: str = "saas_user"
    DB_PASSWORD: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_SLOW_QUERY_THRESHOLD: float = 2.0
    DB_POOL_LEAK_THRESHOLD: float = 0.9

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if os.getenv("ENVIRONMENT") == "production":
            if not self.DB_PASSWORD:
                self.DB_PASSWORD = _read_docker_secret("db_password") or ""
            if not self.REDIS_PASSWORD:
                self.REDIS_PASSWORD = _read_docker_secret("redis_password") or ""
            if not self.JWT_SECRET:
                self.JWT_SECRET = _read_docker_secret("jwt_secret") or ""
            if not self.JWT_REFRESH_SECRET:
                self.JWT_REFRESH_SECRET = _read_docker_secret("jwt_refresh_secret") or ""
            if not self.ENCRYPTION_KEY:
                self.ENCRYPTION_KEY = _read_docker_secret("encryption_key") or ""

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = ""
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL_RESOLVED(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    JWT_SECRET: str = ""
    JWT_REFRESH_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENCRYPTION_KEY: str = ""

    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    AI_DEFAULT_PROVIDER: str = "deepseek"
    AI_DEFAULT_MODEL: str = "deepseek-v4-flash"

    INTEL_SYNC_API_KEY: str = ""

    XHS_CLOUD_API_URL: str = "http://127.0.0.1:8080"
    XHS_CLOUD_SYNC_KEY: str = ""
    XHS_CLOUD_MEMBER_PORTAL_URL: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@xhs365.cn"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    SUPPORT_QQ: str = "898382699"
    SUPPORT_QQ_QR_URL: str = "/support-qq.png"
    SUPPORT_SITE_URL: str = "https://www.xhs365.cn"
    SUPPORT_TITLE: str = "QQ 客服"
    SUPPORT_HINT: str = "注册、授权码、套餐问题请扫码或搜索 QQ 添加客服（无需邮箱验证）"

    CLIENT_VERSION: str = "0.1.0"
    CLIENT_INSTALLER_PATH: str = "deploy/downloads/XHS365-Setup-latest.exe"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]

    DISCOVERY_DB_PATH: str = ""

    AIPIC_ENABLED: bool = True
    AIPIC_OPENAI_API_KEY: str = ""
    AIPIC_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AIPIC_OPENAI_MODEL: str = "gpt-image-2"
    AIPIC_OPENAI_TIMEOUT: int = 180
    AIPIC_WORKER_COUNT: int = 3
    AIPIC_WORKER_INTERVAL: float = 1.0
    AIPIC_MAX_QUEUE_SIZE: int = 1000
    AIPIC_OUTPUTS_DIR: str = ""
    AIPIC_TEMP_DIR: str = ""
    AIPIC_CONTENT_FILTER: bool = True
    AIPIC_STUCK_TASK_TIMEOUT_MINUTES: int = 10
    AIPIC_CLEANUP_INTERVAL_SECONDS: int = 3600

    @property
    def CORS_ORIGINS_SAFE(self) -> list[str]:
        if self.is_production:
            localhost_origins = {"http://localhost:5173", "http://localhost:5174", "http://localhost:5175"}
            return [o for o in self.CORS_ORIGINS if o not in localhost_origins]
        return self.CORS_ORIGINS

    LOG_LEVEL: str = "info"
    LOG_FORMAT: str = "json"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def validate_production(self) -> list[str]:
        issues = []
        if not self.JWT_SECRET:
            issues.append("JWT_SECRET is required")
        elif "change-me" in self.JWT_SECRET:
            issues.append("JWT_SECRET must be changed from default value")
        elif len(self.JWT_SECRET) < 32:
            issues.append("JWT_SECRET should be at least 32 characters")
        if not self.JWT_REFRESH_SECRET:
            issues.append("JWT_REFRESH_SECRET is required")
        elif "change-me" in self.JWT_REFRESH_SECRET:
            issues.append("JWT_REFRESH_SECRET must be changed from default value")
        elif len(self.JWT_REFRESH_SECRET) < 32:
            issues.append("JWT_REFRESH_SECRET should be at least 32 characters")
        if not self.ENCRYPTION_KEY:
            issues.append("ENCRYPTION_KEY is required")
        elif self.ENCRYPTION_KEY == "0123456789abcdef0123456789abcdef":
            issues.append("ENCRYPTION_KEY must be changed from default value")
        if not self.DB_PASSWORD:
            issues.append("DB_PASSWORD is required")
        elif self.DB_PASSWORD == "saas_pass":
            issues.append("DB_PASSWORD must be changed from default value")
        if self.is_production:
            if self.DEBUG:
                issues.append("DEBUG should be False in production")
            if not self.REDIS_PASSWORD:
                issues.append("REDIS_PASSWORD must be set in production")
            localhost_in_cors = [o for o in self.CORS_ORIGINS if "localhost" in o]
            if localhost_in_cors:
                issues.append(f"CORS_ORIGINS contains localhost origins in production: {localhost_in_cors}")
        return issues

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    issues = settings.validate_production()
    if issues:
        for issue in issues:
            warnings.warn(f"SECURITY: {issue}", stacklevel=2)
    return settings


def generate_secret_key(length: int = 64) -> str:
    return secrets.token_hex(length)
