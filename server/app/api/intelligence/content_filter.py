# AIGC START
import re

_DEMO_PATTERN = re.compile(
    r"测试|test\s|demo|示例数据|placeholder|mock|假数据",
    re.IGNORECASE,
)


def is_demo_content(*texts: str | None) -> bool:
    combined = " ".join(t for t in texts if t)
    return bool(_DEMO_PATTERN.search(combined))
# AIGC END
