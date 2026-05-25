#!/usr/bin/env python3
"""Create or reset XHS365 admin user (role=admin). Run on server with server venv."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

SERVER_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
sys.path.insert(0, SERVER_ROOT)
os.environ.setdefault("PYTHONPATH", SERVER_ROOT)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@xhs365.cn"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "Admin123!ChangeMe"))
    parser.add_argument("--nickname", default="xhs365admin")
    args = parser.parse_args()

    from sqlalchemy import select

    from app.core.database import async_session_factory, init_db
    from app.core.security import hash_password
    from app.models.user import User

    await init_db()

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == args.email))
        user = result.scalar_one_or_none()
        pwd_hash = hash_password(args.password)

        if user:
            user.password_hash = pwd_hash
            user.role = "admin"
            user.plan = "enterprise"
            user.is_active = True
            print(f"Updated admin: {args.email}")
        else:
            existing_nick = await db.execute(select(User).where(User.nickname == args.nickname))
            if existing_nick.scalar_one_or_none():
                args.nickname = f"{args.nickname}_{args.email.split('@')[0]}"

            user = User(
                email=args.email,
                nickname=args.nickname,
                password_hash=pwd_hash,
                role="admin",
                plan="enterprise",
                is_active=True,
            )
            db.add(user)
            print(f"Created admin: {args.email}")

        await db.commit()

    print("Done. Login at admin UI with email as username.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
