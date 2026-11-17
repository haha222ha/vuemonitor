# -*- coding: utf-8 -*-
"""垂类竞品细分：垂类产品搜索词 ↔ 同簇多卖家对照（零详情）。

搜词权威 pin_group:
  - vertical_niche_probe   通用垂类产品搜索词（pin_notes 含 niche=<key>|…）
  - competitor_saas_probe  SaaS 对标垂类（见 docs/对标竞品_产品搜索词库_*.md）

看板主路径：垂类搜词 → goods_keywords 触达商品 → 按店汇总；标题 ILIKE 仅兜底。
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
    """垂类键：优先 2–6 字中文主干；SaaS 对标专用 saas。"""
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
    # 取最短且信息量大的中文词作 niche（如 拼豆）
    zh = [t for t in toks if re.search(r"[\u4e00-\u9fff]", t)]
    if zh:
        zh.sort(key=lambda x: (len(x), x))
        for t in zh:
            if 2 <= len(t) <= 6:
                return t
        return zh[0][:6]
    return toks[0][:12]


def niche_pin_notes(niche: str, extra: str = "") -> str:
    n = (niche or "").strip()
    base = f"{NICHE_NOTES_PREFIX}{n}|垂类产品搜索词"
    if extra:
        return (base + "|" + str(extra))[:500]
    return base[:500]


def _connect():
    from cloud_deploy.cloud_api.database_pg import _conn

    return _conn()


def list_vertical_niche_keywords(
    *,
    niche: str,
    limit: int = 80,
    include_candidates: bool = True,
) -> dict[str, Any]:
    """列出该垂类已挂搜词 + 词库内同主干候选（未挂 pin 的）。"""
    niche = (niche or "").strip()
    if not niche:
        return {"ok": False, "error": "missing niche", "items": [], "pinned": [], "candidates": []}
    limit = max(10, min(int(limit or 80), 200))
    conn = _connect()
    try:
        cur = conn.cursor()
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
                    "role": "pinned",
                }
            )

        candidates: list[dict[str, Any]] = []
        if include_candidates and niche != "saas":
            pinned_set = {p["keyword"] for p in pinned}
            cur.execute(
                """
                SELECT keyword, COALESCE(is_active,0), COALESCE(pin_group,''),
                       COALESCE(pin_notes,''), COALESCE(source,'')
                FROM keywords
                WHERE keyword ILIKE %s
                  AND COALESCE(kw_type,'virtual')='virtual'
                ORDER BY COALESCE(is_active,0) DESC, LENGTH(keyword), keyword
                LIMIT %s
                """,
                (f"%{niche}%", limit),
            )
            for r in cur.fetchall() or []:
                kw = str(r[0] or "")
                if not kw or kw in pinned_set:
                    continue
                pg = str(r[2] or "")
                # 已挂在别的探针组的不抢
                if pg and pg not in ("", VERTICAL_NICHE_PIN_GROUP):
                    continue
                candidates.append(
                    {
                        "keyword": kw,
                        "is_active": int(r[1] or 0),
                        "pin_group": pg,
                        "pin_notes": str(r[3] or ""),
                        "source": str(r[4] or ""),
                        "role": "candidate",
                    }
                )

        items = pinned + candidates
        return {
            "ok": True,
            "niche": niche,
            "pin_group": COMPETITOR_SAAS_PIN_GROUP if niche == "saas" else VERTICAL_NICHE_PIN_GROUP,
            "pinned": pinned,
            "candidates": candidates,
            "items": items,
            "pinned_n": len(pinned),
            "candidate_n": len(candidates),
            "active_n": sum(1 for x in items if int(x.get("is_active") or 0) == 1),
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _goods_via_keywords(cur, keywords: list[str], *, limit: int) -> list[tuple]:
    if not keywords:
        return []
    # 去重保序
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
    """垂类搜词触达优先 → 同簇多卖家；标题匹配兜底。"""
    limit = max(10, min(int(limit or 80), 200))
    seed_title = ""
    seed_gid = str(goods_id or "").strip()
    query = str(q or "").strip()

    conn = _connect()
    try:
        cur = conn.cursor()
        if seed_gid and not query:
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

        kw_pack = list_vertical_niche_keywords(niche=niche_key or (tokens[0] if tokens else ""), limit=80)
        pinned_kws = [x["keyword"] for x in (kw_pack.get("pinned") or []) if x.get("keyword")]
        cand_kws = [x["keyword"] for x in (kw_pack.get("candidates") or []) if x.get("keyword")]
        # 看板触达：已挂优先；再补活跃候选；再补同主干候选（读 goods_keywords 不依赖 is_active）
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
        try:
            rows = _goods_via_keywords(cur, drive_kws, limit=limit * 2)
        except Exception:
            conn.rollback()
            rows = []
            via = "title_fallback"

        if len(rows) < 5 and tokens:
            # 标题兜底补齐
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
                conn.rollback()

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
                "pin_group": kw_pack.get("pin_group"),
                "pinned_n": kw_pack.get("pinned_n"),
                "candidate_n": kw_pack.get("candidate_n"),
                "active_n": kw_pack.get("active_n"),
                "drive_keywords": drive_kws[:24],
                "pinned": (kw_pack.get("pinned") or [])[:40],
                "candidates": (kw_pack.get("candidates") or [])[:40],
                "note": "主路径=垂类搜词→goods_keywords；未挂词时用词库同主干候选/标题兜底。挂词: python tools/pin_vertical_niche_keywords.py --niche … --apply",
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
    finally:
        try:
            conn.close()
        except Exception:
            pass
