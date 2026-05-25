#!/usr/bin/env python3
"""Send one test email using server/.env SMTP settings. Usage:
  python3 scripts/test_smtp.py --to your@email.com
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from server_env import bootstrap

bootstrap()


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True, help="Recipient email")
    args = parser.parse_args()

    from app.services.email_service import email_service

    if not email_service.is_configured:
        print("SMTP not configured in server/.env (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)")
        return 1

    ok = await email_service.send_notification_email(
        args.to,
        "XHS365 SMTP 测试",
        "若收到此邮件，说明 SMTP 配置正确。",
    )
    print("sent:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
