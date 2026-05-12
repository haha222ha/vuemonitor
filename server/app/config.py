import secrets
import warnings
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "XHS365"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "vuemonitor"
    DB_USER: str = "saas_user"
    DB_PASSWORD: str = "saas_pass"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

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

    JWT_SECRET: str = "change-me-in-production"
    JWT_REFRESH_SECRET: str = "change-me-refresh-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef"

    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    AI_DEFAULT_PROVIDER: str = "deepseek"
    AI_DEFAULT_MODEL: str = "deepseek-v4-flash"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@xhs365.cn"
    SMTP_USE_TLS: bool = True

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174"]

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
        if self.is_production:
            if "change-me" in self.JWT_SECRET:
                issues.append("JWT_SECRET must be changed in production")
            if len(self.JWT_SECRET) < 32:
                issues.append("JWT_SECRET should be at least 32 characters")
            if "change-me" in self.JWT_REFRESH_SECRET:
                issues.append("JWT_REFRESH_SECRET must be changed in production")
            if len(self.JWT_REFRESH_SECRET) < 32:
                issues.append("JWT_REFRESH_SECRET should be at least 32 characters")
            if self.ENCRYPTION_KEY == "0123456789abcdef0123456789abcdef":
                issues.append("ENCRYPTION_KEY must be changed in production")
            if self.DEBUG:
                issues.append("DEBUG should be False in production")
            if self.DB_PASSWORD == "saas_pass":
                issues.append("DB_PASSWORD must be changed in production")
        return issues

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    issues = settings.validate_production()
    if issues:
        for issue in issues:
            warnings.warn(f"SECURITY: {issue}", stacklevel=2)
    return settings


def generate_secret_key(length: int = 64) -> str:
    return secrets.token_hex(length)
