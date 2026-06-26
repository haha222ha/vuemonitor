# -*- coding: utf-8 -*-
"""
本地 vs 云端精品库对齐检查。

用法（需 D:\\xhs-data\\config\\local_sync.env + portable_paths.env）:
  python tools/check_premium_align.py
  python tools/check_premium_align.py --sample 5
"""
from __future__ import annotations

import os
import sys

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TOOLS)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from xhs_portable_paths import bootstrap_portable_env, bootstrap_sync_env

bootstrap_portable_env(_ROOT)
bootstrap_sync_env()


def _post_catalog(local_ids: list[str]) -> dict:
    import json
    import socket
    import urllib.error
    import urllib.request

    base = os.environ.get("XHS_CLOUD_API_URL", "").rstrip("/")
    key = os.environ.get("XHS_CLOUD_SYNC_KEY", "")
    if not base or not key:
        raise RuntimeError("请配置 XHS_CLOUD_API_URL + XHS_CLOUD_SYNC_KEY")
    body = json.dumps(
        {"local_ids": local_ids, "page": 0, "page_size": 50000},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/sync/premium-catalog",
        data=body,
        headers={"Content-Type": "application/json", "X-Sync-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode(errors="replace")) from e


def main():
    import argparse

    ap = argparse.ArgumentParser(description="本地 vs 云精品库对齐")
    ap.add_argument("--sample", type=int, default=8, help="打印样例 goods_id 数量")
    args = ap.parse_args()

    from xhs_premium_store import connect

    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM premium_goods WHERE lifecycle < 3")
    local_total = int(c.fetchone()[0] or 0)
    c.execute("SELECT goods_id FROM premium_goods WHERE lifecycle < 3")
    local_ids = [str(r[0]) for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM premium_goods_daily")
    local_daily = int(c.fetchone()[0] or 0)
    c.execute(
        """
        SELECT COUNT(*) FROM premium_sync_state
        WHERE snapshots_backfill_done=1
        """
    )
    local_backfill_done = int(c.fetchone()[0] or 0)
    conn.close()

    print("=== 本地精品库 ===")
    print(f"  premium_goods (lifecycle<3): {local_total:,}")
    print(f"  premium_goods_daily 总行:      {local_daily:,}")
    print(f"  历史 backfill 已完成:          {local_backfill_done:,}")

    cat = _post_catalog(local_ids)
    overlap = int(cat.get("overlap") or 0)
    cloud_total = int(cat.get("cloud_total") or cat.get("cloud_count") or 0)
    local_only = cat.get("local_only") or []
    cloud_only = cat.get("cloud_only") or []
    local_only_n = int(cat.get("local_only_count") or len(local_only))
    cloud_only_n = int(cat.get("cloud_only_count") or len(cloud_only))

    print("\n=== 云端对比 (premium-catalog) ===")
    print(f"  云 premium_goods (lifecycle<3):  {cloud_total:,}")
    print(f"  重叠 goods_id:                 {overlap:,}")
    print(f"  仅本地有 (local_only):         {local_only_n:,}")
    print(f"  仅云端有 (cloud_only):         {cloud_only_n:,}")

    aligned = local_only_n == 0 and cloud_only_n == 0 and overlap == local_total == cloud_total
    print("\n=== 结论 ===")
    if aligned:
        print("  ✓ 商品目录已完全对齐（goods_id 集合一致）")
    elif local_only_n == 0 and overlap == local_total:
        print("  ≈ 本地已全部上云；云可能多出一些 cloud_only 行（云侧补扫/历史）")
    elif local_only_n > 0:
        print(f"  ✗ 未完全对齐：还有 {local_only_n:,} 个 goods_id 只在本地，需 push")
    if local_daily > 0 and local_backfill_done < local_total * 0.5:
        print("  ! 日快照 backfill 覆盖率偏低，建议: cloud_sync_premium.py backfill --pending")

    n = max(0, args.sample)
    if n and local_only:
        print(f"\n  local_only 样例 ({min(n, len(local_only))}):")
        for gid in local_only[:n]:
            print(f"    {gid}")
    if n and cloud_only:
        print(f"\n  cloud_only 样例 ({min(n, len(cloud_only))}):")
        for gid in cloud_only[:n]:
            print(f"    {gid}")


if __name__ == "__main__":
    main()
