#!/usr/bin/env python3
"""在服务器本机运行：验收发现库额度与搜索（127.0.0.1，不走 Cloudflare）。"""
import json
import os
import sys
import uuid
import urllib.error
import urllib.request

BASE = os.environ.get("VERIFY_API_BASE", "http://127.0.0.1:8000/api/v1")


def post(path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    nick = f"disc_{suffix}"
    password = "Test1234!"
    print(f"API: {BASE}")
    print(f"1) register {nick}")
    try:
        post("/auth/register", {"nickname": nick, "password": password})
    except urllib.error.HTTPError as e:
        print(f"   register HTTP {e.code}: {e.read()[:200]!r}")

    login = post("/auth/login", {"account": nick, "password": password})
    token = login.get("access_token") or login.get("data", {}).get("access_token")
    if not token:
        print("login failed:", login)
        return 1
    print("2) login OK")

    quota = get("/discovery/quota", token)
    q = quota.get("data", quota)
    print(
        "3) quota:",
        {
            "plan": q.get("plan"),
            "daily_limit": q.get("daily_limit"),
            "used_today": q.get("used_today"),
            "remaining": q.get("remaining"),
        },
    )
    goods = (q.get("db_stats") or {}).get("total_goods")
    print(f"   db_total_goods: {goods}")
    hint = (q.get("quota_hint") or "")[:100]
    print(f"   quota_hint: {hint}...")

    search = post("/discovery/search", {"keyword": "美妆", "page": 1, "page_size": 5}, token)
    d = search.get("data", {})
    print(f"4) search db_ready={d.get('db_ready')} items={len(d.get('items', []))}")
    if d.get("hint"):
        print(f"   hint: {d.get('hint')}")
    if not d.get("items"):
        return 0

    it = d["items"][0]
    print(f"   first: ref={it.get('ref')} title={(it.get('title') or '')[:40]}")
    add = post(
        "/discovery/add-to-monitor",
        {"ref_id": it["ref"], "product_name": it.get("title"), "mode": "goods"},
        token,
    )
    print(f"5) add code={add.get('code')} msg={(add.get('message') or '')[:80]}")

    q2 = get("/discovery/quota", token).get("data", {})
    print(
        f"6) quota after: used={q2.get('used_today')} limit={q2.get('daily_limit')} "
        f"remaining={q2.get('remaining')}"
    )
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
