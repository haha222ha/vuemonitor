import json
import logging
import re
from typing import Any

SENSITIVE_PATTERNS = {
    "password": re.compile(r'(["\']?password["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "token": re.compile(r'(["\']?(?:auth[_\-]?token|access[_\-]?token|refresh[_\-]?token)["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "api_key": re.compile(r'(["\']?(?:api[_\-]?key|apikey|api_secret)["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "secret": re.compile(r'(["\']?(?:secret|client[_\-]?secret)["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "authorization": re.compile(r'(Authorization["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "bearer": re.compile(r'(Bearer\s+)([a-zA-Z0-9\-_.~+/]+=*)', re.IGNORECASE),
    "cookie": re.compile(r'(Cookie["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE),
    "email": re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
    "phone": re.compile(r'(\b1[3-9]\d{9}\b)'),
    "id_card": re.compile(r'(\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b)'),
    "credit_card": re.compile(r'(\b(?:\d{4}[-\s]?){3}\d{4}\b)'),
    "jwt": re.compile(r'(eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*)'),
}

MASK = "***REDACTED***"


class LogSanitizer:
    def __init__(self):
        self.compiled_patterns = {
            key: (pattern, pattern.match)
            for key, pattern in SENSITIVE_PATTERNS.items()
        }

    def sanitize_string(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        result = text
        for key, pattern in SENSITIVE_PATTERNS.items():
            result = pattern.sub(r'\1' + MASK, result)
        return result

    def sanitize_dict(self, data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        if depth > 10:
            return {"_depth_exceeded": True}

        sensitive_keys = {
            "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
            "auth_token", "access_token", "refresh_token", "client_secret",
            "authorization", "cookie", "session", "x_api_key", "api_secret",
            "private_key", " encryption_key", "DB_PASSWORD", "REDIS_PASSWORD",
            "jwt_secret", "jwt_refresh_secret", "sql_password", "connection_string",
            "credit_card", "card_number", "cvv", "ssn", "national_id"
        }

        result = {}
        for key, value in data.items():
            key_lower = key.lower()

            if any(sensitive in key_lower for sensitive in sensitive_keys):
                result[key] = MASK
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value, depth + 1)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize_dict(item, depth + 1) if isinstance(item, dict)
                    else self.sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self.sanitize_string(value)
            else:
                result[key] = value

        return result

    def sanitize_json(self, json_str: str) -> str:
        try:
            data = json.loads(json_str)
            sanitized = self.sanitize_dict(data)
            return json.dumps(sanitized, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return self.sanitize_string(json_str)


class SanitizedFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sanitizer = LogSanitizer()

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            record.msg = self.sanitizer.sanitize_dict(record.msg)
        elif isinstance(record.msg, str):
            record.msg = self.sanitizer.sanitize_string(record.msg)

        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self.sanitizer.sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self.sanitizer.sanitize_dict(arg) if isinstance(arg, dict)
                    else self.sanitizer.sanitize_string(arg) if isinstance(arg, str)
                    else arg
                    for arg in record.args
                )

        return super().format(record)


def setup_sanitized_logging():
    root_logger = logging.getLogger()

    if root_logger.handlers:
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(SanitizedFormatter(
                    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                ))

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


sanitizer = LogSanitizer()
