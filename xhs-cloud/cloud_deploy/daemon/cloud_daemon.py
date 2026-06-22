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
        self._risk_round_until = 0.0
        self._full_round_until = 0.0
        self._phase = "daily"
        self._scan_date = ""
        self._last_cooldown = max(0, int(self.config.get("web_cooldown_seconds", 30)))
        self.batch_size = max(50, min(int(self.config.get("batch_size", 1000)), 1500))
        self.concurrency = max(1, min(5, int(self.config.get("web_detail_concurrency", 3))))
        self.cooldown = max(0, int(self.config.get("web_cooldown_seconds", 30)))
        self.min_success_rate = float(self.config.get("min_success_rate", 0.08) or 0.08)
        self.auto_fallback = bool(self.config.get("auto_fallback", True))
        self._api_only_until = 0.0
        self._maybe_force_api_only_on_start()

    def _risk_cfg(self) -> dict:
        raw = self.config.get("risk_rescan") or {}
        if not isinstance(raw, dict):
            raw = {}
        enabled = raw.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() in ("1", "true", "yes")
        return {
            "enabled": bool(enabled),
            "min_age_hours": float(raw.get("min_age_hours", 2) or 2),
            "batch_size": max(
                50,
                min(int(raw.get("batch_size", 200) or 200), 1000),
            ),
            "batch_cooldown_seconds": max(
                10, int(raw.get("batch_cooldown_seconds", 60) or 60)
            ),
            "round_cooldown_seconds": max(
                300, int(raw.get("round_cooldown_seconds", 7200) or 7200)
            ),
            "claim_ttl_minutes": max(
                5, min(int(raw.get("claim_ttl_minutes", 25) or 25), 120)
            ),
        }

    def _pool_cycle_cfg(self) -> dict:
        raw = self.config.get("pool_cycle") or {}
        if not isinstance(raw, dict):
            raw = {}
        enabled = raw.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() in ("1", "true", "yes")
        return {
            "enabled": bool(enabled),
            "pause_hours": max(1.0, float(raw.get("pause_hours", 5) or 5)),
            "claim_ttl_minutes": max(
                5, min(int(raw.get("claim_ttl_minutes", 25) or 25), 120)
            ),
        }

    def _pool_cycle_enabled(self) -> bool:
        return bool(self._pool_cycle_cfg()["enabled"])

    def _risk_rescan_enabled(self) -> bool:
        if self._pool_cycle_enabled():
            return False
        return bool(self._risk_cfg()["enabled"])

    def _count_full_pool_pending(self) -> int:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db

        if not bool(self.config.get("skip_today", True)):
            return 1
        init_db()
        conn = _conn()
        try:
            with conn.cursor() as c:
                c.execute("SET search_path TO xhs_monitor, public")
                c.execute(
                    """SELECT COUNT(*) FROM monitor_goods
                       WHERE monitor_status IN ('active', 'idle')
                         AND (
                           last_scan_at IS NULL
                           OR last_scan_at::date < CURRENT_DATE
                         )"""
                )
                return int(c.fetchone()[0] or 0)
        finally:
            conn.close()

    def _pick_cycle_batch(self) -> list[dict]:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db
        from cloud_deploy.cloud_api.scan_claim import pick_and_claim_pool

        cfg = self._pool_cycle_cfg()
        init_db()
        conn = _conn()
        try:
            return pick_and_claim_pool(
                conn,
                self.batch_size,
                "cloud-daemon",
                claim_ttl_minutes=cfg["claim_ttl_minutes"],
            )
        finally:
            conn.close()

    def _pick_risk_batch(self) -> list[dict]:
        from cloud_deploy.cloud_api.database_pg import _conn, init_db
        from cloud_deploy.cloud_api.scan_claim import pick_and_claim_risk

        cfg = self._risk_cfg()
        init_db()
        conn = _conn()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            return pick_and_claim_risk(
                conn,
                today,
                cfg["batch_size"],
                "cloud-daemon",
                min_age_hours=cfg["min_age_hours"],
                claim_ttl_minutes=cfg["claim_ttl_minutes"],
            )
        finally:
            conn.close()

    def _rollover_scan_day(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._scan_date != today:
            self._scan_date = today
            self._phase = "daily"
            self._full_round_until = 0.0
            self._risk_round_until = 0.0

    def _log_pause_remain(self) -> None:
        remain = int(self._full_round_until - time.time())
        hrs, rem = divmod(max(0, remain), 3600)
        mins, secs = divmod(rem, 60)
        if hrs:
            eta = f"{hrs}h{mins}m"
        elif mins:
            eta = f"{mins}m{secs}s"
        else:
            eta = f"{secs}s"
        nxt = "risk 补扫" if self._phase == "pause" else "下一轮"
        self.log(f"[cloud-daemon] 轮间休息 {eta}，之后 {nxt}")

    def _schedule_pool_pause(self, reason: str) -> None:
        hrs = self._pool_cycle_cfg()["pause_hours"]
        self._full_round_until = time.time() + int(hrs * 3600)
        self._phase = "pause"
        risk_cfg = self._risk_cfg()
        self.log(
            f"[cloud-daemon] {reason}，休息 {hrs:g}h 后 risk 补扫 "
            f"(batch={risk_cfg['batch_size']} cd={risk_cfg['batch_cooldown_seconds']}s)"
        )

    def _run_pool_cycle_once(self) -> tuple[list[dict], str]:
        """大循环: 首轮全池 → 休5h → risk200/60s → risk休2h → 全池1000/30s → 休5h → …"""
        now = time.time()
        risk_cfg = self._risk_cfg()

        if self._phase == "pause":
            if now < self._full_round_until:
                self._log_pause_remain()
                self._last_cooldown = self.cooldown
                return [], "full"
            self._phase = "risk"
            self.log("[cloud-daemon] 休息结束，进入 risk 补扫")

        if self._phase == "risk_cooldown":
            if now < self._risk_round_until:
                remain = int(self._risk_round_until - now)
                self.log(f"[cloud-daemon] risk 整轮冷却 {remain}s，跳过")
                self._last_cooldown = self.cooldown
                return [], "risk"
            self._phase = "cycle_full"
            self.log(
                f"[cloud-daemon] risk 冷却结束，进入全池循环 "
                f"(batch={self.batch_size} cd={self.cooldown}s)"
            )

        if self._phase == "daily":
            batch = self._pick_batch()
            if batch:
                return batch, "full"
            if self._count_full_pool_pending() > 0:
                self.log(
                    f"[cloud-daemon] 待扫≈{self._count_full_pool_pending()} "
                    f"本批为空，{self.cooldown}s 后重试"
                )
                self._last_cooldown = self.cooldown
                return [], "full"
            self._schedule_pool_pause("今日首轮全池扫描完成")
            self._last_cooldown = self.cooldown
            return [], "full"

        if self._phase == "risk":
            batch = self._pick_risk_batch()
            if batch:
                self.log(
                    f"[cloud-daemon] risk 补扫 本批={len(batch)} "
                    f"(距上次≥{risk_cfg['min_age_hours']}h)"
                )
                return batch, "risk"
            hrs = risk_cfg["round_cooldown_seconds"] // 3600
            self._risk_round_until = now + risk_cfg["round_cooldown_seconds"]
            self._phase = "risk_cooldown"
            self.log(
                f"[cloud-daemon] risk 补扫完成，整轮冷却 {hrs}h "
                f"后全池循环 batch={self.batch_size}"
            )
            self._last_cooldown = risk_cfg["batch_cooldown_seconds"]
            return [], "risk"

        if self._phase == "cycle_full":
            batch = self._pick_cycle_batch()
            if batch:
                self.log(
                    f"[cloud-daemon] 全池循环补扫 本批={len(batch)} "
                    f"(claim 避让家庭 Agent)"
                )
                return batch, "cycle"
            self._schedule_pool_pause("本轮全池循环扫描完成")
            self._last_cooldown = self.cooldown
            return [], "cycle"

        self.log(f"[cloud-daemon] 未知阶段 {self._phase!r}，重置为 daily")
        self._phase = "daily"
        self._last_cooldown = self.cooldown
        return [], "full"

    def _setup_crawler_path(self) -> None:
        crawler = os.environ.get("XHS_CRAWLER_ROOT", "").strip()
        if crawler and os.path.isdir(crawler) and crawler not in sys.path:
            sys.path.insert(0, crawler)

    def _maybe_force_api_only_on_start(self) -> None:
        """最近多批全失败时，启动后直接 api 优先（probe 已证明 api 可用）。"""
        try:
            from cloud_deploy.cloud_api.database_pg import _conn

            conn = _conn()
            try:
                with conn.cursor() as c:
                    c.execute("SET search_path TO xhs_monitor, public")
                    c.execute("SELECT ok, fail FROM daemon_scan_stats ORDER BY id DESC LIMIT 2")
                    rows = c.fetchall()
            finally:
                conn.close()
            if len(rows) >= 2 and all(
                int(r[0] or 0) < max(10, int(r[1] or 0) // 100) for r in rows
            ):
                mins = int(self.config.get("api_only_minutes", 30) or 30)
                self._api_only_until = time.time() + mins * 60
                self.log(f"[cloud-daemon] 最近批次 dp 无效，{mins}min 内改 api 优先")
        except Exception:
            pass

    def _uses_api_only(self) -> bool:
        if time.time() < self._api_only_until:
            return True
        return os.environ.get("XHS_DAEMON_API_ONLY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    def _resolve_start_engine(self, goods: dict) -> str:
        from cloud_deploy.daemon.cloud_engine import pick_start_engine

        if self._uses_api_only():
            return "api"
        return pick_start_engine(goods, self.config)

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
                             AND (
                               last_scan_at IS NULL
                               OR last_scan_at::date < CURRENT_DATE
                             )
                           ORDER BY priority_score DESC NULLS LAST, last_v1d DESC NULLS LAST
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
        from cloud_deploy.daemon.cloud_engine import build_fallback_chain

        gid = str(goods["goods_id"])
        start = self._resolve_start_engine(goods)
        if self._uses_api_only():
            chain = ("api",)
        elif self.auto_fallback:
            chain = build_fallback_chain(start, self.config)
        else:
            chain = (start,)

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
            meta["detail"] = detail
            try:
                meta["deal_price"] = float(
                    detail.get("deal_price") or detail.get("product_price") or 0
                )
            except (TypeError, ValueError):
                meta["deal_price"] = 0.0
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
                record_cloud_scan(
                    conn,
                    goods_id,
                    sold,
                    data_source=ds,
                    deal_price=meta.get("deal_price"),
                    detail=meta.get("detail"),
                )
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
        self._rollover_scan_day()
        batch: list[dict] = []
        batch_mode = "full"

        if self._pool_cycle_enabled():
            batch, batch_mode = self._run_pool_cycle_once()
        else:
            batch = self._pick_batch()
            if not batch and self._risk_cfg()["enabled"]:
                risk_cfg = self._risk_cfg()
                pending_full = self._count_full_pool_pending()
                if pending_full > 0:
                    self.log(
                        f"[cloud-daemon] 全池扫描进行中(待扫≈{pending_full})，risk 补扫暂缓"
                    )
                    return {"batch": 0, "ok": 0, "fail": 0, "risk": 0, "frozen": 0}
                now = time.time()
                if now < self._risk_round_until:
                    remain = int(self._risk_round_until - now)
                    self.log(f"[cloud-daemon] risk 整轮冷却 {remain}s，跳过")
                    return {"batch": 0, "ok": 0, "fail": 0, "risk": 0, "frozen": 0}
                batch = self._pick_risk_batch()
                batch_mode = "risk"
                if not batch:
                    self._risk_round_until = time.time() + risk_cfg["round_cooldown_seconds"]
                    hrs = risk_cfg["round_cooldown_seconds"] // 3600
                    self.log(
                        f"[cloud-daemon] 无可补扫 risk(距上次≥{risk_cfg['min_age_hours']}h)，"
                        f"整轮冷却 {hrs}h"
                    )
                    return {"batch": 0, "ok": 0, "fail": 0, "risk": 0, "frozen": 0}
                self.log(
                    f"[cloud-daemon] risk 补扫 本批={len(batch)} "
                    f"(距上次≥{risk_cfg['min_age_hours']}h)"
                )

        if not batch:
            if not self._pool_cycle_enabled():
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
        prefix = "riskR" if batch_mode == "risk" else ("C" if batch_mode == "cycle" else "R")
        note = f"{prefix}{self._round} engines={eng_note}"
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
            f"[cloud-daemon] {prefix}{self._round} 批={len(batch)} ok={ok} fail={fail} "
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

        batch_total = len(batch)
        success_rate = (ok / batch_total) if batch_total else 0.0

        if batch_mode == "risk":
            risk_cfg = self._risk_cfg()
            self._last_cooldown = risk_cfg["batch_cooldown_seconds"]
            return result

        dp_dead = (
            batch_total >= 50
            and risk == 0
            and fail >= int(batch_total * 0.9)
            and success_rate < 0.01
        )
        if dp_dead:
            self._recover_drissionpage(wall_ms)
        elif batch_total >= 100 and success_rate < 0.01:
            mins = int(self.config.get("api_only_minutes", 30) or 30)
            self._api_only_until = time.time() + mins * 60
            self.log(
                f"[cloud-daemon] 本批成功率 {success_rate:.1%}，"
                f"接下来 {mins}min 改 api 优先（跳过 dp 限流）"
            )
        elif self._should_cooldown(ok, fail, risk):
            extra = min(600, max(120, self.cooldown * 3))
            self._wait_risk_cooldown(extra)

        self._last_cooldown = self.cooldown
        return result

    def _recover_drissionpage(self, wall_ms: int) -> None:
        """整批失败时重建 dp（长跑僵死自愈，无需人工 restart）。"""
        try:
            from xhs_full_sold_fetch import reset_drissionpage, warmup_drissionpage

            self.log(
                f"[cloud-daemon] 检测到整批失败 ({wall_ms}ms)，清除 profile 并重建浏览器 ..."
            )
            reset_drissionpage(log_func=self.log, clear_profile=True)
            warmup_drissionpage(log_func=self.log)
        except Exception as exc:
            self.log(f"[cloud-daemon] dp 自动重建失败: {exc}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop.clear()
        self._setup_crawler_path()
        cycle_note = ""
        if self._pool_cycle_enabled():
            pc = self._pool_cycle_cfg()
            rc = self._risk_cfg()
            cycle_note = (
                f" phase={self._phase} pause={pc['pause_hours']}h "
                f"risk={rc['batch_size']}/{rc['batch_cooldown_seconds']}s "
                f"full={self.batch_size}/{self.cooldown}s"
            )
        self.log(
            f"[cloud-daemon] 启动 batch={self.batch_size} conc={self.concurrency} "
            f"cooldown={self.cooldown}s pool_cycle={self._pool_cycle_enabled()}{cycle_note}"
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
            cd = max(0, int(self._last_cooldown or self.cooldown))
            for _ in range(cd):
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
