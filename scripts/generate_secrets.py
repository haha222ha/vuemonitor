"""Generate production secrets for .env file.

Usage:
    python scripts/generate_secrets.py > .env.production
    python scripts/generate_secrets.py --check .env
"""

import secrets
import sys
import os


def generate_secret(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def generate_hex(length: int = 32) -> str:
    return secrets.token_hex(length)


def generate_env():
    db_password = generate_secret(24)
    redis_password = generate_secret(24)
    jwt_secret = generate_secret(48)
    jwt_refresh_secret = generate_secret(48)
    encryption_key = generate_hex(16)

    env_content = f"""# ============================================================
# XHS365 生产环境变量 — 自动生成
# 生成时间: {os.popen('date /t & time /t').read().strip() if sys.platform == 'win32' else __import__('datetime').datetime.now().isoformat()}
# [WARNING] 此文件包含敏感信息，切勿提交到版本控制！
# ============================================================

# --- 应用 ---
APP_NAME=XHS365
APP_VERSION=0.1.0
DEBUG=false
ENVIRONMENT=production

# --- 安全密钥 ---
JWT_SECRET={jwt_secret}
JWT_REFRESH_SECRET={jwt_refresh_secret}
ENCRYPTION_KEY={encryption_key}

# --- 数据库 ---
DB_HOST=postgres
DB_PORT=5432
DB_NAME=vuemonitor
DB_USER=saas_user
DB_PASSWORD={db_password}

# --- Redis ---
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD={redis_password}

# --- AI 服务 ---
AI_DEFAULT_PROVIDER=deepseek
AI_DEFAULT_MODEL=deepseek-v4-flash
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

# --- SMTP 邮件 ---
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@xhs365.cn
SMTP_USE_TLS=true

# --- CORS ---
CORS_ORIGINS=["https://www.xhs365.cn","https://xhs365.cn","https://admin.xhs365.cn"]

# --- 日志 ---
LOG_LEVEL=warning
LOG_FORMAT=json
"""
    return env_content


def check_env(filepath: str) -> list[str]:
    issues = []
    if not os.path.exists(filepath):
        return [f"文件不存在: {filepath}"]

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    insecure_values = {
        "JWT_SECRET": ["change-me-in-production", ""],
        "JWT_REFRESH_SECRET": ["change-me-refresh-in-production", ""],
        "ENCRYPTION_KEY": ["0123456789abcdef0123456789abcdef", ""],
        "DB_PASSWORD": ["saas_pass", ""],
    }

    for key, bad_values in insecure_values.items():
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip()
                if value in bad_values:
                    issues.append(f"[FAIL] {key} 使用了不安全的默认值")
                elif len(value) < 16:
                    issues.append(f"[WARN] {key} 长度不足 (当前{len(value)}字符，建议至少32字符)")
                break

    if "DEBUG=true" in content or "DEBUG=True" in content:
        issues.append("[FAIL] 生产环境不应开启 DEBUG=true")

    if "localhost" in content and "CORS_ORIGINS" in content:
        issues.append("[WARN] CORS_ORIGINS 包含 localhost，生产环境应使用实际域名")

    if not issues:
        issues.append("[OK] 所有安全检查通过")

    return issues


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            filepath = sys.argv[2] if len(sys.argv) > 2 else ".env"
            issues = check_env(filepath)
            for issue in issues:
                print(issue)
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python generate_secrets.py [--check <filepath>]")
            sys.exit(1)
    else:
        print(generate_env())


if __name__ == "__main__":
    main()
