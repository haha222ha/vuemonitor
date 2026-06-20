# -*- coding: utf-8
"""
香港云主机 PG 监控扫描守护（cloud_daemon）。

- 直接从 monitor_goods 取批（今日未扫优先）
- 分层引擎：高爆 → drissionpage，低销 → api，失败自动降级
- 写 PG：goods_sold_snapshots / goods_sold_daily + last_scan_*
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

CLOUD_ROOT = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)


class CloudMonitorDaemon:
    def __init__(self, config: dict | None = None, log_func=None):
        self.config = dict(config or {})
        self.log = log_func or print
        self._stop = threading.Event()
        self._running = False
        self._round = 0
        self._risk_until = 0.0
        self.batch_size = max(50, min(int(self.config.get("batch_size", 200)), 500))
        self.concurrency = max(1, min(4, int(self.config.get("web_detail_concurrency", 2))))
        self.cooldown = max(0, int(self.config.get("web_cooldown_seconds", 60)))
        self.min_success_rate = float(self.config.get("min_success_rate", 0.08) or 0.08)
        self.auto_fallback = bool(self.config.get("auto_fallback", True))

    def _setup_crawler_path(self) -> None:
        crawler = os.environ.get("XHS_CRAWLER_ROOT", "").strip()
        if crawler and os.path.isdir(crawler) and crawler not in sys.path:
            sys.path.insert(0, crawler)

    def _pick_batch(self) -> list[dict]:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db

        skip_today = bool(self.config.get("skip_today", True))
        init_db()
        conn = _conn()
        try:
            with conn.cursor() as c:
                c.execute("SET search_path TO xhs_monitor, public")
                if skip_today:
                    c.execute(
                        """SELECT goods_id, title, last_v1d, last_sold, tier, pool, priority_score
                           FROM monitor_goods
                           WHERE monitor_status IN ('active', 'idle')
                           ORDER BY
                             NOT (
                               last_scan_status = 'ok'
                               AND last_scan_at IS NOT NULL
                               AND last_scan_at::date = CURRENT_DATE
                             ) DESC,
                             priority_score DESC NULLS LAST,
                             last_v1d DESC NULLS LAST
                           LIMIT %s""",
                        (self.batch_size,),
                    )
                else:
                    c.execute(
                        """SELECT goods_id, title, last_v1d, last_sold, tier, pool, priority_score
                           FROM monitor_goods
                           WHERE monitor_status IN ('active', 'idle')
                           ORDER BY priority_score DESC NULLS LAST, last_v1d DESC NULLS LAST
                           LIMIT %s""",
                        (self.batch_size,),
                    )
                cols = (
                    "goods_id",
                    "title",
                    "last_v1d",
                    "last_sold",
                    "tier",
                    "pool",
                    "priority_score",
                )
                return [dict(zip(cols, row)) for row in c.fetchall()]
        finally:
            conn.close()

    def _fetch_goods(self, goods: dict) -> tuple[dict, str, int | None, dict]:
        from cloud_deploy.daemon.cloud_engine import build_fallback_chain, pick_start_engine

        gid = str(goods["goods_id"])
        start = pick_start_engine(goods, self.config)
        chain = build_fallback_chain(start, self.config) if self.auto_fallback else (start,)

        fetcher = _load_fetcher()
        if not fetcher:
            return goods, "no_fetcher", None, {"won_engine": "", "message": "fetcher missing"}

        try:
            detail, status, meta = fetcher(
                gid,
                engine=start,
                fallback_chain=chain,
                auto_fallback=self.auto_fallback,
            )
        except Exception as exc:
            return goods, "fail", None, {"won_engine": start, "message": str(exc)}

        meta = dict(meta or {})
        if status == "ok" and detail:
            sold = int(detail.get("real_sales") or detail.get("product_sales") or 0)
            return goods, "ok", sold, meta
        if status == "frozen":
            return goods, "frozen", None, meta
        if status == "risk":
            return goods, "risk", None, meta
        if status == "no_store":
            return goods, "frozen", None, meta
        return goods, "fail", None, meta

    def _write_result(
        self,
        goods_id: str,
        status: str,
        sold: int | None,
        meta: dict,
    ) -> None:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db
        from cloud_deploy.cloud_api.sync_service import mark_scan_result, record_cloud_scan
        from cloud_deploy.rules.rule_engine import evaluate_rules

        engine = str(meta.get("won_engine") or meta.get("engine") or "")[:32]
        init_db()
        conn = _conn()
        try:
            if status == "ok" and sold is not None:
                ds = f"cloud_{engine}" if engine else "cloud_scan"
                record_cloud_scan(conn, goods_id, sold, data_source=ds)
                mark_scan_result(conn, goods_id, "ok", engine=engine)
                evaluate_rules(conn, goods_id)
            elif status == "frozen":
                with conn.cursor() as c:
                    c.execute("SET search_path TO xhs_monitor, public")
                    c.execute(
                        "UPDATE monitor_goods SET monitor_status='delisted', updated_at=NOW() WHERE goods_id=%s",
                        (goods_id,),
                    )
                conn.commit()
                mark_scan_result(conn, goods_id, "frozen", engine=engine)
                evaluate_rules(conn, goods_id, extra_ctx={"scan_status": "frozen"})
            else:
                mark_scan_result(conn, goods_id, status, engine=engine)
        finally:
            conn.close()

    def _should_cooldown(self, ok: int, fail: int, risk: int) -> bool:
        total = ok + fail + risk
        if total <= 0:
            return False
        if ok == 0 and total >= 10:
            return True
        rate = ok / total
        return rate < self.min_success_rate and total >= max(20, self.batch_size // 4)

    def _wait_risk_cooldown(self, seconds: int) -> bool:
        self._risk_until = time.time() + seconds
        self.log(f"[cloud-daemon] 风控冷却 {seconds}s ...")
        for _ in range(seconds):
            if self._stop.is_set():
                return False
            time.sleep(1)
        self._risk_until = 0.0
        return True

    def run_once(self) -> dict:
        t0 = time.time()
        batch = self._pick_batch()
        if not batch:
            self.log("[cloud-daemon] 监控池为空，跳过")
            return {"batch": 0, "ok": 0, "fail": 0, "risk": 0, "frozen": 0}

        ok = fail = risk = frozen = 0
        engine_hits: Counter[str] = Counter()

        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futures = {ex.submit(self._fetch_goods, row): row for row in batch}
            for fut in as_completed(futures):
                if self._stop.is_set():
                    break
                goods, status, sold, meta = fut.result()
                gid = str(goods["goods_id"])
                self._write_result(gid, status, sold, meta)
                won = str(meta.get("won_engine") or meta.get("engine") or "unknown")
                if status == "ok":
                    ok += 1
                    engine_hits[won] += 1
                elif status == "frozen":
                    frozen += 1
                elif status == "risk":
                    risk += 1
                else:
                    fail += 1

        wall_ms = int((time.time() - t0) * 1000)
        self._round += 1
        eng_note = dict(engine_hits)
        note = f"R{self._round} engines={eng_note}"
        result = {
            "batch": len(batch),
            "ok": ok,
            "fail": fail,
            "risk": risk,
            "frozen": frozen,
            "wall_ms": wall_ms,
            "engines": eng_note,
        }
        self.log(
            f"[cloud-daemon] R{self._round} 批={len(batch)} ok={ok} fail={fail} "
            f"risk={risk} frozen={frozen} {wall_ms}ms 引擎={eng_note}"
        )

        try:
            from cloud_deploy.cloud_api.database_pg import _conn, init_db
            from cloud_deploy.cloud_api.sync_service import record_daemon_batch_stats

            init_db()
            conn = _conn()
            try:
                record_daemon_batch_stats(
                    conn,
                    len(batch),
                    ok,
                    fail,
                    risk,
                    frozen,
                    wall_ms,
                    note,
                )
            finally:
                conn.close()
        except Exception as exc:
            self.log(f"[cloud-daemon] stats 写入失败: {exc}")

        dp_dead = (
            ok == 0
            and fail >= max(50, self.batch_size // 2)
            and wall_ms < 20000
            and risk == 0
        )
        if dp_dead:
            self._recover_drissionpage(wall_ms)
        elif self._should_cooldown(ok, fail, risk):
            extra = min(600, max(120, self.cooldown * 3))
            self._wait_risk_cooldown(extra)

        return result

    def _recover_drissionpage(self, wall_ms: int) -> None:
        """整批秒失败时重建 dp（长跑僵死自愈，无需人工 restart）。"""
        fast_fail = wall_ms < 20000
        if not fast_fail:
            return
        try:
            from xhs_full_sold_fetch import reset_drissionpage, warmup_drissionpage

            self.log("[cloud-daemon] 检测到 dp 僵死，自动重建浏览器 ...")
            reset_drissionpage(log_func=self.log)
            warmup_drissionpage(log_func=self.log)
        except Exception as exc:
            self.log(f"[cloud-daemon] dp 自动重建失败: {exc}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop.clear()
        self._setup_crawler_path()
        self.log(
            f"[cloud-daemon] 启动 batch={self.batch_size} conc={self.concurrency} "
            f"cooldown={self.cooldown}s"
        )

        try:
            from xhs_full_sold_fetch import warmup_drissionpage

            warmup_drissionpage(log_func=self.log)
        except Exception as exc:
            self.log(f"[cloud-daemon] dp 预热跳过: {exc}")

        while not self._stop.is_set():
            if time.time() < self._risk_until:
                time.sleep(1)
                continue
            self.run_once()
            for _ in range(self.cooldown):
                if self._stop.wait(1):
                    break
        self._running = False
        self.log("[cloud-daemon] 已停止")

    def stop(self) -> None:
        self._stop.set()


def _load_fetcher():
    crawler = os.environ.get("XHS_CRAWLER_ROOT", "")
    if crawler and os.path.isdir(crawler) and crawler not in sys.path:
        sys.path.insert(0, crawler)
    try:
        from xhs_full_sold_fetch import fetch_sold_detail

        return fetch_sold_detail
    except ImportError:
        return None


def run_cloud_daemon_main(config: dict | None = None) -> None:
    daemon = CloudMonitorDaemon(config, print)

    def _on_sig(_sig, _frame):
        print("[cloud-daemon] 收到停止信号", flush=True)
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    daemon.start()


def start_cloud_daemon(config: dict | None = None, log_func=None) -> CloudMonitorDaemon:
    """兼容 lite 模式：后台线程。"""
    daemon = CloudMonitorDaemon(config, log_func)
    thread = threading.Thread(target=daemon.start, daemon=True, name="CloudMonitorDaemon")
    thread.start()
    return daemon
