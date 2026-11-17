# -*- coding: utf-8 -*-
"""垂类竞品细分（云端适配）。

本机权威：keywords → goods_keywords → goods_base（channel_board.board_vertical_niche）。
云端 PG 无热库词表，改查已同步的 board_inventory_goods，合同形状与原页一致：
任意搜词 → 多卖家/SKU 表。hub 只做导航，不另起短名单业务。
"""
from __future__ import annotations

import re
from typing import Any

VERTICAL_NICHE_PIN_GROUP = "vertical_niche_probe"
COMPETITOR_SAAS_PIN_GROUP = "competitor_saas_probe"
NICHE_NOTES_PREFIX = "niche="


def _norm_title(s: str) -> str:
    t = re.sub(r"\s+", "", str(s or ""))
    t = re.sub(r"[【】\[\]（）()·・\-_|/\\]+", "", t)
    return t.lower()


def _tokens(q: str) -> list[str]:
    raw = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", str(q or ""))
    out: list[str] = []
    for t in raw:
        t = t.strip().lower()
        if t and t not in out:
            out.append(t)
    return out[:8]


def niche_key_from_query(q: str) -> str:
    s = str(q or "").strip()
    if not s:
        return ""
    low = s.lower()
    if any(x in low for x in ("saas", "rag", "dify", "fastgpt", "知识库", "文档问答")):
        if "拼豆" not in s and "测评" not in s:
            return "saas"
    toks = _tokens(s)
    if not toks:
        return _norm_title(s)[:12]
    zh = [t for t in toks if re.search(r"[\u4e00-\u9fff]", t)]
    if zh:
        zh.sort(key=lambda x: (len(x), x))
        for t in zh:
            if 2 <= len(t) <= 6:
                return t
        return zh[0][:6]
    return toks[0][:12]


def _connect():
    from cloud_deploy.cloud_api.database_pg import _conn

    return _conn()


def _has_relation(cur, name: str) -> bool:
    try:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema='public' AND table_name=%s
            LIMIT 1
            """,
            (name,),
        )
        return bool(cur.fetchone())
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return False


def _pack_sellers_items(
    rows: list[tuple],
    *,
    tokens: list[str],
    niche_key: str,
    query: str,
    seed_gid: str,
    seed_title: str,
    via: str,
    drive_kws: list[str],
    note: str,
    limit: int,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for r in rows:
        title = str(r[1] or "")
        nt = _norm_title(title)
        hit = sum(1 for t in tokens if t in nt or t in title.lower())
        if niche_key and niche_key in title:
            hit = max(hit, 1)
        sold = int(r[4] or 0)
        delta = int(r[5] or 0)
        price = float(r[3] or 0)
        before = max(sold - delta, 0)
        actual_gr = round(delta / before * 100, 2) if before > 0 and delta > 0 else None
        touch = [x for x in str(r[7] or "").split("|") if x]
        items.append(
            {
                "goods_id": str(r[0] or ""),
                "title": title,
                "store_name": str(r[2] or "") or "（未知店）",
                "store_id": str(r[6] or ""),
                "price": price,
                "sold": sold,
                "delta": delta,
                "actual_gr": actual_gr,
                "token_hits": hit,
                "touch_keywords": touch,
            }
        )

    items.sort(
        key=lambda x: (
            -len(x.get("touch_keywords") or []),
            -int(x.get("token_hits") or 0),
            -int(x.get("delta") or 0),
        )
    )
    items = items[:limit]

    sellers_map: dict[str, dict[str, Any]] = {}
    for it in items:
        sn = it["store_name"]
        slot = sellers_map.setdefault(
            sn,
            {
                "store_name": sn,
                "sku_n": 0,
                "sum_delta": 0,
                "sum_sold": 0,
                "top_title": "",
                "top_delta": -1,
            },
        )
        slot["sku_n"] += 1
        slot["sum_delta"] += int(it.get("delta") or 0)
        slot["sum_sold"] += int(it.get("sold") or 0)
        if int(it.get("delta") or 0) > slot["top_delta"]:
            slot["top_delta"] = int(it.get("delta") or 0)
            slot["top_title"] = it.get("title") or ""

    sellers = sorted(sellers_map.values(), key=lambda x: -int(x["sum_delta"]))
    prices = sorted(float(it.get("price") or 0) for it in items if float(it.get("price") or 0) > 0)
    median_price = prices[len(prices) // 2] if prices else None

    return {
        "ok": True,
        "seed": {
            "q": query,
            "goods_id": seed_gid,
            "title": seed_title,
            "tokens": tokens,
            "niche": niche_key,
        },
        "search_keywords": {
            "pin_group": None,
            "pinned_n": 0,
            "candidate_n": 0,
            "active_n": 0,
            "drive_keywords": drive_kws[:24],
            "pinned": [],
            "candidates": [],
            "note": note,
        },
        "via": via,
        "summary": {
            "seller_n": len(sellers),
            "sku_n": len(items),
            "sum_delta": sum(int(it.get("delta") or 0) for it in items),
            "median_price": median_price,
            "niche": niche_key,
            "drive_kw_n": len(drive_kws),
        },
        "sellers": sellers[:40],
        "items": items,
    }


def _query_board_inventory(
    cur,
    *,
    niche_key: str,
    tokens: list[str],
    query: str,
    seed_gid: str,
    seed_title: str,
    limit: int,
) -> dict[str, Any]:
    """云端任意搜词：标题 / keyword / scene_l2|l3 命中 board_inventory_goods。"""
    needles: list[str] = []
    for t in ([niche_key] if niche_key else []) + list(tokens or []):
        t = str(t or "").strip()
        if t and t not in needles:
            needles.append(t)
    if not needles and query:
        needles = [query[:24]]
    if not needles:
        return {
            "ok": False,
            "error": "请提供关键词 q / niche 或有效 goods_id",
            "seed": {"q": query, "goods_id": seed_gid, "title": seed_title},
            "summary": {},
            "sellers": [],
            "items": [],
            "search_keywords": {},
        }

    # 精确 scene_l2 优先（有索引）
    rows: list[tuple] = []
    via = "board_inventory"
    for n in needles[:3]:
        try:
            cur.execute(
                """
                SELECT
                  goods_id::text,
                  COALESCE(title,''),
                  COALESCE(NULLIF(store_name,''), '（未知店）'),
                  COALESCE(deal_price, 0),
                  COALESCE(sold_num, 0),
                  COALESCE(sum_delta_7d, 0),
                  '',
                  COALESCE(NULLIF(keyword,''), NULLIF(scene_l2,''), '')
                FROM board_inventory_goods
                WHERE scene_l2 = %s OR scene_l3 = %s
                ORDER BY COALESCE(sum_delta_7d, 0) DESC NULLS LAST,
                         COALESCE(sold_num, 0) DESC
                LIMIT %s
                """,
                (n, n, limit * 2),
            )
            hit = list(cur.fetchall() or [])
            if hit:
                rows = hit
                via = "board_inventory.scene"
                break
        except Exception:
            try:
                cur.connection.rollback()
            except Exception:
                pass

    if len(rows) < 5:
        like_parts: list[str] = []
        params: list[Any] = []
        for n in needles[:5]:
            like = f"%{n}%"
            like_parts.append(
                "(title ILIKE %s OR COALESCE(keyword,'') ILIKE %s "
                "OR COALESCE(scene_l2,'') ILIKE %s OR COALESCE(scene_l3,'') ILIKE %s)"
            )
            params.extend([like, like, like, like])
        where = " OR ".join(like_parts)
        params.append(limit * 3)
        try:
            cur.execute(
                f"""
                SELECT
                  goods_id::text,
                  COALESCE(title,''),
                  COALESCE(NULLIF(store_name,''), '（未知店）'),
                  COALESCE(deal_price, 0),
                  COALESCE(sold_num, 0),
                  COALESCE(sum_delta_7d, 0),
                  '',
                  COALESCE(NULLIF(keyword,''), NULLIF(scene_l2,''), '')
                FROM board_inventory_goods
                WHERE {where}
                ORDER BY COALESCE(sum_delta_7d, 0) DESC NULLS LAST,
                         COALESCE(sold_num, 0) DESC
                LIMIT %s
                """,
                params,
            )
            more = list(cur.fetchall() or [])
            seen = {str(r[0]) for r in rows}
            for r in more:
                if str(r[0]) not in seen:
                    rows.append(r)
            if more and via == "board_inventory":
                via = "board_inventory.title"
            elif more and via.startswith("board_inventory.scene"):
                via = "board_inventory.scene+title"
        except Exception:
            try:
                cur.connection.rollback()
            except Exception:
                pass

    return _pack_sellers_items(
        rows,
        tokens=tokens or needles,
        niche_key=niche_key or (needles[0] if needles else ""),
        query=query,
        seed_gid=seed_gid,
        seed_title=seed_title,
        via=via,
        drive_kws=needles[:24],
        note="云端路径=board_inventory_goods 任意搜词（标题/keyword/scene）；本机仍走 keywords→goods_keywords",
        limit=limit,
    )


def list_vertical_niche_keywords(
    *,
    niche: str,
    limit: int = 80,
    include_candidates: bool = True,
) -> dict[str, Any]:
    """列出该垂类已挂搜词（仅热库有 keywords 表时可用）。"""
    niche = (niche or "").strip()
    if not niche:
        return {"ok": False, "error": "missing niche", "items": [], "pinned": [], "candidates": []}
    limit = max(10, min(int(limit or 80), 200))
    conn = _connect()
    try:
        cur = conn.cursor()
        if not _has_relation(cur, "keywords"):
            return {
                "ok": True,
                "niche": niche,
                "pin_group": VERTICAL_NICHE_PIN_GROUP,
                "pinned": [],
                "candidates": [],
                "pinned_n": 0,
                "candidate_n": 0,
                "active_n": 0,
                "note": "cloud: no keywords table",
            }
        pinned: list[dict[str, Any]] = []
        if niche == "saas":
            cur.execute(
                """
                SELECT keyword, COALESCE(is_active,0), COALESCE(pin_group,''),
                       COALESCE(pin_notes,''), COALESCE(source,'')
                FROM keywords
                WHERE COALESCE(pin_group,'')=%s
                ORDER BY COALESCE(is_active,0) DESC, keyword
                LIMIT %s
                """,
                (COMPETITOR_SAAS_PIN_GROUP, limit),
            )
        else:
            cur.execute(
                """
                SELECT keyword, COALESCE(is_active,0), COALESCE(pin_group,''),
                       COALESCE(pin_notes,''), COALESCE(source,'')
                FROM keywords
                WHERE COALESCE(pin_group,'')=%s
                  AND COALESCE(pin_notes,'') LIKE %s
                ORDER BY COALESCE(is_active,0) DESC, keyword
                LIMIT %s
                """,
                (VERTICAL_NICHE_PIN_GROUP, f"{NICHE_NOTES_PREFIX}{niche}|%", limit),
            )
        for r in cur.fetchall() or []:
            pinned.append(
                {
                    "keyword": str(r[0] or ""),
                    "is_active": int(r[1] or 0),
                    "pin_group": str(r[2] or ""),
                    "pin_notes": str(r[3] or ""),
                    "source": str(r[4] or ""),
                }
            )
        candidates: list[dict[str, Any]] = []
        if include_candidates and niche != "saas":
            cur.execute(
                """
                SELECT keyword, COALESCE(is_active,0), COALESCE(pin_group,''),
                       COALESCE(pin_notes,''), COALESCE(source,'')
                FROM keywords
                WHERE keyword ILIKE %s
                ORDER BY COALESCE(is_active,0) DESC, keyword
                LIMIT %s
                """,
                (f"%{niche}%", limit),
            )
            seen = {x["keyword"] for x in pinned}
            for r in cur.fetchall() or []:
                kw = str(r[0] or "")
                if not kw or kw in seen:
                    continue
                candidates.append(
                    {
                        "keyword": kw,
                        "is_active": int(r[1] or 0),
                        "pin_group": str(r[2] or ""),
                        "pin_notes": str(r[3] or ""),
                        "source": str(r[4] or ""),
                    }
                )
        active_n = sum(1 for x in pinned if int(x.get("is_active") or 0) == 1)
        return {
            "ok": True,
            "niche": niche,
            "pin_group": COMPETITOR_SAAS_PIN_GROUP if niche == "saas" else VERTICAL_NICHE_PIN_GROUP,
            "pinned": pinned,
            "candidates": candidates,
            "pinned_n": len(pinned),
            "candidate_n": len(candidates),
            "active_n": active_n,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _goods_via_keywords(cur, keywords: list[str], *, limit: int) -> list[tuple]:
    if not keywords:
        return []
    seen: set[str] = set()
    kws: list[str] = []
    for k in keywords:
        k = str(k or "").strip()
        if k and k not in seen:
            seen.add(k)
            kws.append(k)
    kws = kws[:60]
    if not kws:
        return []
    ph = ",".join(["%s"] * len(kws))
    sql = f"""
    WITH latest AS (
      SELECT DISTINCT ON (h.goods_id)
        h.goods_id::text AS goods_id,
        h.sold_num,
        h.delta
      FROM sold_history h
      WHERE h.snapshot_date >= (CURRENT_DATE - INTERVAL '14 days')
      ORDER BY h.goods_id, h.snapshot_date DESC
    ),
    hit AS (
      SELECT DISTINCT gk.goods_id::text AS goods_id, gk.keyword
      FROM goods_keywords gk
      WHERE gk.keyword IN ({ph})
    )
    SELECT
      g.goods_id::text,
      COALESCE(g.title,''),
      COALESCE(NULLIF(g.store_name,''), NULLIF(g.store_id::text,''), '（未知店）'),
      COALESCE(g.deal_price, 0),
      COALESCE(l.sold_num, g.sold_num, 0),
      COALESCE(l.delta, 0),
      COALESCE(g.store_id::text, ''),
      STRING_AGG(DISTINCT hit.keyword, '|')
    FROM hit
    JOIN goods_base g ON g.goods_id::text = hit.goods_id
    LEFT JOIN latest l ON l.goods_id = hit.goods_id
    GROUP BY g.goods_id, g.title, g.store_name, g.store_id, g.deal_price, g.sold_num, l.sold_num, l.delta
    ORDER BY COALESCE(l.delta, 0) DESC NULLS LAST,
             COALESCE(l.sold_num, g.sold_num, 0) DESC
    LIMIT %s
    """
    cur.execute(sql, [*kws, limit])
    return list(cur.fetchall() or [])


def query_vertical_niche(
    *,
    q: str = "",
    goods_id: str = "",
    niche: str = "",
    limit: int = 80,
) -> dict[str, Any]:
    """任意搜词 → 多卖家对照。云优先 board_inventory；有热库表则走原路径。"""
    limit = max(10, min(int(limit or 80), 200))
    seed_title = ""
    seed_gid = str(goods_id or "").strip()
    query = str(q or "").strip()

    conn = _connect()
    try:
        cur = conn.cursor()

        # 云端主路径：看板底账（已同步）
        if _has_relation(cur, "board_inventory_goods") and not (
            _has_relation(cur, "keywords") and _has_relation(cur, "goods_base")
        ):
            niche_key = (niche or "").strip() or niche_key_from_query(query or seed_title)
            tokens = _tokens(query) or _tokens(seed_title) or ([niche_key] if niche_key else [])
            return _query_board_inventory(
                cur,
                niche_key=niche_key,
                tokens=tokens,
                query=query or niche_key,
                seed_gid=seed_gid,
                seed_title=seed_title,
                limit=limit,
            )

        if seed_gid and not query and _has_relation(cur, "goods_base"):
            cur.execute(
                """
                SELECT COALESCE(title,''), COALESCE(goods_id::text,'')
                FROM goods_base WHERE goods_id::text=%s LIMIT 1
                """,
                (seed_gid,),
            )
            row = cur.fetchone()
            if row:
                seed_title = str(row[0] or "")
                query = seed_title

        niche_key = (niche or "").strip() or niche_key_from_query(query or seed_title)
        tokens = _tokens(query) or _tokens(seed_title) or ([niche_key] if niche_key else [])
        if not niche_key and not tokens:
            return {
                "ok": False,
                "error": "请提供关键词 q / niche 或有效 goods_id",
                "seed": {"q": q, "goods_id": seed_gid, "title": seed_title},
                "summary": {},
                "sellers": [],
                "items": [],
                "search_keywords": {},
            }

        # 有热库：尽量走原路径；keywords 缺失则跳过挂词
        drive_kws: list[str] = []
        kw_pack: dict[str, Any] = {
            "pinned": [],
            "candidates": [],
            "pinned_n": 0,
            "candidate_n": 0,
            "active_n": 0,
            "pin_group": None,
        }
        if _has_relation(cur, "keywords"):
            try:
                kw_pack = list_vertical_niche_keywords(
                    niche=niche_key or (tokens[0] if tokens else ""), limit=80
                )
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            pinned_kws = [x["keyword"] for x in (kw_pack.get("pinned") or []) if x.get("keyword")]
            cand_kws = [x["keyword"] for x in (kw_pack.get("candidates") or []) if x.get("keyword")]
            drive_kws = list(pinned_kws)
            for x in kw_pack.get("candidates") or []:
                if int(x.get("is_active") or 0) != 1:
                    continue
                if x["keyword"] not in drive_kws:
                    drive_kws.append(x["keyword"])
                if len(drive_kws) >= 24:
                    break
            if len(drive_kws) < 16:
                for kw in cand_kws:
                    if kw not in drive_kws:
                        drive_kws.append(kw)
                    if len(drive_kws) >= 24:
                        break
        if not drive_kws and tokens:
            drive_kws = list(tokens)[:8]

        rows: list[tuple] = []
        via = "goods_keywords"
        if _has_relation(cur, "goods_keywords") and _has_relation(cur, "goods_base"):
            try:
                rows = _goods_via_keywords(cur, drive_kws, limit=limit * 2)
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                rows = []
                via = "title_fallback"
        else:
            via = "title_fallback"

        if len(rows) < 5 and tokens and _has_relation(cur, "goods_base"):
            like_clauses = []
            params: list[Any] = []
            for tok in tokens[:5]:
                like_clauses.append("g.title ILIKE %s")
                params.append(f"%{tok}%")
            where_title = " OR ".join(like_clauses)
            params.append(limit * 3)
            sql = f"""
            WITH latest AS (
              SELECT DISTINCT ON (h.goods_id)
                h.goods_id::text AS goods_id, h.sold_num, h.delta
              FROM sold_history h
              WHERE h.snapshot_date >= (CURRENT_DATE - INTERVAL '14 days')
              ORDER BY h.goods_id, h.snapshot_date DESC
            )
            SELECT
              g.goods_id::text,
              COALESCE(g.title,''),
              COALESCE(NULLIF(g.store_name,''), NULLIF(g.store_id::text,''), '（未知店）'),
              COALESCE(g.deal_price, 0),
              COALESCE(l.sold_num, g.sold_num, 0),
              COALESCE(l.delta, 0),
              COALESCE(g.store_id::text, ''),
              ''
            FROM goods_base g
            LEFT JOIN latest l ON l.goods_id = g.goods_id::text
            WHERE ({where_title})
            ORDER BY COALESCE(l.delta, 0) DESC NULLS LAST,
                     COALESCE(l.sold_num, g.sold_num, 0) DESC
            LIMIT %s
            """
            try:
                cur.execute(sql, params)
                more = list(cur.fetchall() or [])
                seen_g = {str(r[0]) for r in rows}
                for r in more:
                    if str(r[0]) not in seen_g:
                        rows.append(r)
                if via == "goods_keywords" and more:
                    via = "goods_keywords+title"
                elif not rows:
                    via = "title_fallback"
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        # 热库仍空 → 回落看板底账
        if len(rows) < 3 and _has_relation(cur, "board_inventory_goods"):
            return _query_board_inventory(
                cur,
                niche_key=niche_key,
                tokens=tokens,
                query=query or niche_key,
                seed_gid=seed_gid,
                seed_title=seed_title,
                limit=limit,
            )

        out = _pack_sellers_items(
            rows,
            tokens=tokens,
            niche_key=niche_key,
            query=query,
            seed_gid=seed_gid,
            seed_title=seed_title,
            via=via,
            drive_kws=drive_kws,
            note="主路径=垂类搜词→goods_keywords；未挂词时用词库同主干候选/标题兜底。",
            limit=limit,
        )
        out["search_keywords"].update(
            {
                "pin_group": kw_pack.get("pin_group"),
                "pinned_n": kw_pack.get("pinned_n"),
                "candidate_n": kw_pack.get("candidate_n"),
                "active_n": kw_pack.get("active_n"),
                "pinned": (kw_pack.get("pinned") or [])[:40],
                "candidates": (kw_pack.get("candidates") or [])[:40],
            }
        )
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass
