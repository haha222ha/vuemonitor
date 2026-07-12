#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2: 类目 pgvector 嵌入批处理 → category_embeddings。

用法:
  cd /opt/xhs-cloud
  PYTHONPATH=/opt/xhs-cloud python3 cloud_deploy/scripts/run_category_embeddings.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

ROOT = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cloud_deploy.cloud_api.database_pg import _conn, init_db
from cloud_deploy.cloud_api.insight_settings import resolve_runtime_config

_MONITOR_SCHEMA = "xhs_monitor"


def _set_search_path(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SET search_path TO xhs_monitor, public")


def _fetch_categories(conn) -> list[str]:
    _set_search_path(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = 'daily_category_metrics'
            LIMIT 1
            """,
            (_MONITOR_SCHEMA,),
        )
        if cur.fetchone():
            cur.execute(
                """
                SELECT DISTINCT category FROM daily_category_metrics
                WHERE category IS NOT NULL AND category <> ''
                ORDER BY category
                """
            )
            rows = cur.fetchall()
            if rows:
                return [str(r[0] if not isinstance(r, dict) else r["category"]) for r in rows]

        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = 'category_embeddings'
            LIMIT 1
            """,
            (_MONITOR_SCHEMA,),
        )
        if not cur.fetchone():
            return []

    # 兜底：Shadow 磁盘类目（无 DCM 时）
    try:
        from cloud_deploy.cloud_api.insight_routes import _list_items_from_disk

        items = _list_items_from_disk()
        cats = sorted({str(it.get("category") or "") for it in items if it.get("category")})
        return [c for c in cats if c]
    except Exception:
        return []


def _embed_text(
    text: str, *, base_url: str, api_key: str, model: str, dimensions: int | None = None
) -> list[float]:
    url = base_url.rstrip("/") + "/embeddings"
    payload: dict[str, Any] = {"model": model, "input": text}
    if dimensions:
        payload["dimensions"] = dimensions
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    data = body.get("data") or []
    if not data:
        raise RuntimeError(f"embedding 空响应: {body!r:.200}")
    emb = data[0].get("embedding")
    if not isinstance(emb, list) or not emb:
        raise RuntimeError("embedding 格式异常")
    return [float(x) for x in emb]


def _upsert_embedding(
    conn,
    *,
    category: str,
    model: str,
    vector: list[float],
) -> None:
    _set_search_path(conn)
    vec_lit = "[" + ",".join(f"{x:.8f}" for x in vector) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO category_embeddings (category, sub_category, model, embedding, updated_at)
            VALUES (%s, '', %s, %s::vector, NOW())
            ON CONFLICT (category, sub_category, model)
            DO UPDATE SET embedding = EXCLUDED.embedding, updated_at = NOW()
            """,
            (category, model, vec_lit),
        )
    conn.commit()


def main() -> int:
    init_db()
    conn = _conn()
    try:
        _set_search_path(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
                """
            )
            if not cur.fetchone():
                print("[category-embed] pgvector 扩展未安装", flush=True)
                return 1
            cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = 'category_embeddings'
                LIMIT 1
                """,
                (_MONITOR_SCHEMA,),
            )
            if not cur.fetchone():
                print("[category-embed] category_embeddings 表不存在", flush=True)
                return 1

        categories = _fetch_categories(conn)
        if not categories:
            print("[category-embed] 无类目可嵌入", flush=True)
            return 1

        try:
            cfg: dict[str, Any] = resolve_runtime_config(conn)
        except Exception as e:
            cfg = {}
            print(f"[category-embed] LLM settings skipped: {e}", flush=True)

        api_key = (
            (cfg.get("api_key") or "").strip()
            or os.environ.get("INSIGHT_LLM_API_KEY", "").strip()
            or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        )
        if not api_key:
            print("[category-embed] 缺少 INSIGHT_LLM_API_KEY", flush=True)
            return 1

        base_url = (
            cfg.get("base_url")
            or os.environ.get("INSIGHT_LLM_BASE_URL")
            or "https://www.packyapi.com/v1"
        )
        model = os.environ.get("INSIGHT_EMBED_MODEL", "text-embedding-3-small")
        dim = int(os.environ.get("INSIGHT_EMBED_DIM", "768"))

        ok_n = 0
        for cat in categories:
            try:
                vec = _embed_text(
                    cat,
                    base_url=str(base_url),
                    api_key=api_key,
                    model=model,
                    dimensions=dim,
                )
                if len(vec) != dim:
                    print(
                        f"[category-embed] {cat}: dim={len(vec)} != {dim}，跳过",
                        flush=True,
                    )
                    continue
                _upsert_embedding(conn, category=cat, model=model, vector=vec)
                ok_n += 1
                print(f"[category-embed] ok {cat}", flush=True)
            except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as e:
                print(f"[category-embed] fail {cat}: {e}", flush=True)

        print(f"[category-embed] done {ok_n}/{len(categories)}", flush=True)
        return 0 if ok_n else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
