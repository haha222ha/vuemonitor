# -*- coding: utf-8
"""
云端监控扫描守护（写 PG，不调用 xhs_full_sold_daemon）。

需配置 XHS_CRAWLER_ROOT 指向爬虫仓库以复用 fetch_sold_detail。
2G 机器默认不 enable systemd；本地挂机可开。

环境:
  XHS_CRAWLER_ROOT=/path/to/爬虫
  XHS_DAEMON_BATCH_SIZE=20
  XHS_DAEMON_COOLDOWN_SEC=120
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUD_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if CLOUD_ROOT not in sys.path:
    sys.path.insert(0, CLOUD_ROOT)


class CloudMonitorDaemon:
    def __init__(self, config: dict | None = None, log_func=None):
        self.config = dict(config or {})
        self.log = log_func or print
        self._stop = threading.Event()
        self._running = False
        self.batch_size = int(self.config.get("batch_size", 20))
        self.concurrency = int(self.config.get("web_detail_concurrency", 2))
        self.cooldown = int(self.config.get("web_cooldown_seconds", 120))
        self.engine = self.config.get("shop_engine", "api")

    def _fetch_one(self, goods_id: str) -> tuple[str, str, int | None]:
        fetcher = _load_fetcher()
        if not fetcher:
            return goods_id, "no_fetcher", None
        try:
            raw, status, _meta = fetcher(goods_id, engine=self.engine)
            if status == "frozen":
                return goods_id, "frozen", None
            if not raw:
                return goods_id, "fail", None
            sold = int(raw.get("real_sales") or raw.get("product_sales") or 0)
            return goods_id, "ok", sold
        except Exception as e:
            return goods_id, f"err:{e}", None

    def _write_pg(self, goods_id: str, status: str, sold: int | None) -> None:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db
        from cloud_deploy.cloud_api.sync_service import record_cloud_scan
        from cloud_deploy.rules.rule_engine import evaluate_rules

        init_db()
        conn = _conn()
        try:
            if status == "ok" and sold is not None:
                record_cloud_scan(conn, goods_id, sold, data_source="cloud_daemon")
                evaluate_rules(conn, goods_id)
            elif status == "frozen":
                with conn.cursor() as c:
                    c.execute("SET search_path TO xhs_monitor, public")
                    c.execute(
                        "UPDATE monitor_goods SET monitor_status='delisted', updated_at=NOW() WHERE goods_id=%s",
                        (goods_id,),
                    )
                conn.commit()
                evaluate_rules(conn, goods_id, extra_ctx={"scan_status": "frozen"})
            else:
                conn.rollback()
        finally:
            conn.close()

    def _pick_batch(self) -> list[str]:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db

        init_db()
        conn = _conn()
        try:
            with conn.cursor() as c:
                c.execute("SET search_path TO xhs_monitor, public")
                c.execute(
                    """SELECT goods_id FROM monitor_goods
                       WHERE monitor_status='active'
                       ORDER BY priority_score DESC, last_v1d DESC
                       LIMIT %s""",
                    (self.batch_size,),
                )
                return [r[0] for r in c.fetchall()]
        finally:
            conn.close()

    def run_once(self) -> dict:
        batch = self._pick_batch()
        if not batch:
            self.log("[cloud-daemon] 监控池为空，跳过")
            return {"batch": 0, "ok": 0}

        ok = fail = frozen = 0
        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futures = {ex.submit(self._fetch_one, gid): gid for gid in batch}
            for fut in as_completed(futures):
                gid, status, sold = fut.result()
                self._write_pg(gid, status, sold)
                if status == "ok":
                    ok += 1
                elif status == "frozen":
                    frozen += 1
                else:
                    fail += 1
        result = {"batch": len(batch), "ok": ok, "fail": fail, "frozen": frozen}
        self.log(f"[cloud-daemon] {datetime.now():%H:%M:%S} {result}")
        return result

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop.clear()
        self.log(f"[cloud-daemon] 启动 batch={self.batch_size} conc={self.concurrency}")

        while not self._stop.is_set():
            self.run_once()
            for _ in range(self.cooldown):
                if self._stop.wait(1):
                    break
        self._running = False

    def stop(self):
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


def start_cloud_daemon(config: dict | None = None, log_func=None) -> CloudMonitorDaemon:
    daemon = CloudMonitorDaemon(config, log_func)
    thread = threading.Thread(target=daemon.start, daemon=True, name="CloudMonitorDaemon")
    thread.start()
    return daemon
