# -*- coding: utf-8 -*-
"""
数据源⑥ 全天挂机守护 — 对齐主面板 Web 端挂机思路。

- 补缺队列 seed 一次，每批毫秒取候选
- 批级风控：成功率过低 / 连续失败 → 递增冷却（30/60/90/120 分钟）
- 冷却期间每分钟探活，通过后自动恢复
- 队列为空 → 长休息后 re-seed
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from xhs_detail_enrich_db import append_panel_log
from xhs_full_sold_fetch import ENGINE_CHAIN, fetch_sold_detail, probe_engines_multi
from xhs_full_sold_queue_db import (
    ensure_queue_seeded,
    fetch_full_sold_queue_batch,
    queue_pending_sold_tiers,
    finalize_frozen_goods,
    mark_full_sold_sync_result,
    queue_stats,
)
from xhs_web_sold_sync_write import recalc_velocity_after_sync, sync_sold_to_main_db

_USE_BUFFER = False
buffer_sold_detail = None
from xhs_web_risk_cooldown_log import (
    begin_cooldown_event,
    close_open_events,
    end_cooldown_event,
    format_event_line,
)

TAG = "FULL-SOLD-DAEMON"
DATA_SOURCE = "web_full_sold_sync"

# 与 APIShopCollector 同级冷却梯度（秒）
RISK_COOLDOWNS = (30 * 60, 60 * 60, 90 * 60, 120 * 60)


class FullSoldSyncDaemon:
    """⑥ 主库补缺挂机调度器。"""

    def __init__(self, config=None, log_func=None, web_log_func=None):
        self.config = dict(config or {})
        self.log_func = log_func or print
        self.web_log_func = web_log_func or log_func or print
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

        self._risk_level = 0
        self._risk_until = 0.0
        self._bad_batch_streak = 0
        self._active_engine = self.config.get("shop_engine", "api") or "api"
        if self._active_engine not in ENGINE_CHAIN:
            self._active_engine = "api"
        self._config_engine = self._active_engine
        self._use_auto_fallback = bool(self.config.get("auto_fallback", True))
        self._round = 0
        self._cooldown_event_id = 0
        self._last_batch_snapshot = {}
        self._stats = {
            "rounds": 0,
            "batches": 0,
            "success": 0,
            "fail": 0,
            "updated": 0,
            "snapshot": 0,
            "cooldowns": 0,
            "last_batch_at": "",
            "phase": "idle",
        }

    def _log(self, msg, web=False):
        text = str(msg)
        if not text.startswith("["):
            text = f"[{TAG}] {text}"
        append_panel_log(TAG, text)
        fn = self.web_log_func if web else self.log_func
        try:
            fn(text)
        except Exception:
            pass

    def start(self):
        if self._running:
            self._log("已在运行中")
            return False
        self._running = True
        self._paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._main_loop, daemon=True, name="FullSoldDaemon")
        self._thread.start()
        self._log("⑥ 补缺挂机已启动", web=True)
        return True

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._cooldown_event_id:
            end_cooldown_event(
                self._cooldown_event_id,
                "daemon_stop",
                note="用户停止挂机",
            )
            self._cooldown_event_id = 0
        else:
            close_open_events(source="full_sold_daemon", recovery_mode="daemon_stop", note="用户停止挂机")
        self._log("⑥ 补缺挂机停止请求已发送", web=True)

    def pause(self):
        self._paused = True
        self._log("⑥ 补缺挂机已暂停", web=True)

    def resume(self):
        self._paused = False
        self._log("⑥ 补缺挂机已恢复", web=True)

    def get_status(self):
        with self._lock:
            st = dict(self._stats)
            st["running"] = self._running
            st["paused"] = self._paused
            st["round"] = self._round
            st["engine"] = self._active_engine
            st["in_cooldown"] = time.time() < self._risk_until
            if st["in_cooldown"]:
                st["cooldown_remain_sec"] = int(max(0, self._risk_until - time.time()))
            else:
                st["cooldown_remain_sec"] = 0
            try:
                qs = queue_stats()
                st["queue_pending"] = qs.get("pending", 0)
                st["queue_total"] = qs.get("total", 0)
            except Exception:
                st["queue_pending"] = 0
                st["queue_total"] = 0
            return st

    def _sleep(self, seconds):
        seconds = max(0, int(seconds))
        for _ in range(seconds):
            if self._stop_event.is_set() or not self._running:
                return False
            while self._paused and self._running and not self._stop_event.is_set():
                time.sleep(0.5)
            time.sleep(1)
        return True

    def _in_cooldown(self):
        return time.time() < self._risk_until

    def _cooldown_trigger_reason(self, batch):
        total = batch.get("ok", 0) + batch.get("fail", 0)
        if batch.get("risk", 0) >= max(10, total * 0.3):
            return f"risk_hits={batch.get('risk', 0)}/{total}"
        if batch.get("ok", 0) == 0:
            return f"zero_success_streak={self._bad_batch_streak}"
        rate = batch.get("success_rate", 0)
        return f"low_success_rate={rate:.1%}_streak={self._bad_batch_streak}"

    def _enter_risk_cooldown(self, batch=None):
        """设置冷却计划并写库，返回 (planned_sec, event_id)。"""
        batch = batch or self._last_batch_snapshot or {}
        if self._risk_level >= len(RISK_COOLDOWNS):
            self._risk_level = len(RISK_COOLDOWNS) - 1
        planned_sec = RISK_COOLDOWNS[self._risk_level]
        level_now = self._risk_level + 1
        self._risk_until = time.time() + planned_sec
        self._risk_level += 1
        reason = self._cooldown_trigger_reason(batch) if batch else "in_cooldown_resume"
        total = batch.get("ok", 0) + batch.get("fail", 0)
        event_id = begin_cooldown_event(
            source="full_sold_daemon",
            engine=self._active_engine,
            planned_sec=planned_sec,
            trigger_reason=reason,
            risk_level=level_now,
            batch_ok=batch.get("ok", 0),
            batch_fail=batch.get("fail", 0),
            batch_risk=batch.get("risk", 0),
            success_rate=batch.get("success_rate", 0) if total else 0,
            note=f"round={self._round}",
        )
        self._cooldown_event_id = event_id
        with self._lock:
            self._stats["cooldowns"] += 1
            self._stats["phase"] = "cooldown"
        mins = planned_sec // 60
        planned_until = datetime.fromtimestamp(self._risk_until).strftime("%Y-%m-%d %H:%M:%S")
        self._log(
            f"进入风控冷却 计划{mins}分钟 等级{level_now} 预计恢复≈{planned_until} "
            f"(事件#{event_id} 原因:{reason})",
            web=True,
        )
        return planned_sec, event_id

    def _finish_cooldown_event(self, recovery_mode, probe_engine="", probe_goods_id="", note=""):
        eid = self._cooldown_event_id
        if not eid:
            return
        end_cooldown_event(
            eid,
            recovery_mode,
            probe_engine=probe_engine,
            probe_goods_id=probe_goods_id,
            note=note,
        )
        try:
            from xhs_web_risk_cooldown_log import fetch_recent_events

            ev = fetch_recent_events(limit=1, source="full_sold_daemon")
            if ev and ev[0].get("id") == eid:
                self._log(f"冷却结束记录: {format_event_line(ev[0])}", web=True)
        except Exception:
            pass
        self._cooldown_event_id = 0

    def _wait_risk_cooldown(self, batch=None, already_scheduled=False):
        """
        等待风控冷却。
        already_scheduled=True：仅等待（不再重复递增等级/写开始事件）。
        """
        if not already_scheduled:
            self._enter_risk_cooldown(batch)

        probe_id = ""
        last_probe = 0.0
        while time.time() < self._risk_until:
            if self._stop_event.is_set() or not self._running:
                self._finish_cooldown_event("daemon_stop", note="冷却中被停止")
                return False
            while self._paused and self._running:
                time.sleep(0.5)
            remain = int(self._risk_until - time.time())
            now = time.time()
            if remain > 0 and now - last_probe >= 60:
                last_probe = now
                self._log(f"冷却剩余 {remain // 60} 分 {remain % 60} 秒，探测可用引擎...", web=True)
                probe_ids = []
                batch_rows = fetch_full_sold_queue_batch(limit=5)
                probe_ids = [r["goods_id"] for r in batch_rows]
                pid = self.config.get("probe_goods_id", "")
                if pid and pid not in probe_ids:
                    probe_ids.insert(0, pid)
                if probe_ids:
                    alive = probe_engines_multi(
                        probe_ids,
                        log_func=lambda m: self._log(m, web=True),
                        need_consecutive=2,
                    )
                    if alive:
                        self._active_engine = alive[0]
                        self._log(
                            f"探测通过，提前恢复采集 引擎={self._active_engine} "
                            f"(较计划提前约 {remain // 60}m{remain % 60}s)",
                            web=True,
                        )
                        self._finish_cooldown_event(
                            "probe_early",
                            probe_engine=self._active_engine,
                            probe_goods_id=probe_ids[0] if probe_ids else "",
                            note=f"提前{remain}s",
                        )
                        self._risk_level = max(0, self._risk_level - 1)
                        self._bad_batch_streak = 0
                        self._risk_until = 0.0
                        return True
            time.sleep(1)

        self._log("计划冷却时间到，恢复正常采集", web=True)
        self._finish_cooldown_event("timeout", probe_goods_id="", note="自然到期")
        self._risk_until = 0.0
        self._bad_batch_streak = 0
        return True

    def _process_one(self, item):
        if not self._running or self._stop_event.is_set():
            return None
        goods_id = item["goods_id"]
        chain = None
        if self._use_auto_fallback:
            chain = ENGINE_CHAIN
            if self._active_engine in ENGINE_CHAIN:
                chain = ENGINE_CHAIN[ENGINE_CHAIN.index(self._active_engine):]
        detail, status, meta = fetch_sold_detail(
            goods_id,
            engine=self._active_engine,
            fallback_chain=chain,
            auto_fallback=self._use_auto_fallback,
        )
        if status == "risk":
            mark_full_sold_sync_result(goods_id, ok=False)
            return ("risk", goods_id, meta.get("message", ""))
        if status == "frozen":
            sold_db = int(item.get("sold_num") or 0)
            snap_tag = "pure"
            if sold_db > 0:
                detail_db = {
                    "goods_id": goods_id,
                    "real_sales": sold_db,
                    "shop_id": "",
                    "shop_name": item.get("title") or "",
                    "data_source": "web_full_frozen_db",
                }
                if _USE_BUFFER and buffer_sold_detail:
                    ok, _st, _, _ = buffer_sold_detail(
                        goods_id, detail_db, data_source="web_full_frozen_db", enrich_missing=False
                    )
                else:
                    ok, _st, _, _ = sync_sold_to_main_db(
                        goods_id, detail_db, data_source="web_full_frozen_db", enrich_missing=False
                    )
                if ok:
                    snap_tag = "with_snapshot"
            finalize_frozen_goods(goods_id, code=600, log_func=None)
            return ("archived", goods_id, snap_tag)
        if status != "ok" or not detail:
            mark_full_sold_sync_result(goods_id, ok=False)
            return ("fail", goods_id, status)

        ok, sync_status, _old, _new = (
            buffer_sold_detail(goods_id, detail, data_source=DATA_SOURCE)
            if (_USE_BUFFER and buffer_sold_detail)
            else sync_sold_to_main_db(goods_id, detail, data_source=DATA_SOURCE)
        )
        if ok:
            mark_full_sold_sync_result(goods_id, ok=True)
            return ("success", goods_id, sync_status)

        if sync_status == "no_sales" and int(item.get("sold_num") or 0) > 0:
            detail_db = dict(detail)
            detail_db["real_sales"] = int(item.get("sold_num") or 0)
            if _USE_BUFFER and buffer_sold_detail:
                ok2, st2, _, _ = buffer_sold_detail(
                    goods_id, detail_db, data_source=f"{DATA_SOURCE}_db_sold"
                )
            else:
                ok2, st2, _, _ = sync_sold_to_main_db(
                    goods_id, detail_db, data_source=f"{DATA_SOURCE}_db_sold"
                )
            if ok2:
                mark_full_sold_sync_result(goods_id, ok=True)
                return ("success", goods_id, st2)

        mark_full_sold_sync_result(goods_id, ok=False)
        return ("fail", goods_id, sync_status)

    def _revert_engine_if_batch_dead(self, batch):
        """单条 fallback 不应永久切换主引擎；整批失败时回退到面板配置引擎。"""
        ok_n = int(batch.get("ok", 0) or 0)
        fail_n = int(batch.get("fail", 0) or 0)
        archived_n = int(batch.get("archived", batch.get("frozen", 0)) or 0)
        if ok_n > 0 or fail_n < 50:
            return
        if archived_n >= fail_n * 0.5:
            return
        target = self._config_engine
        if self._active_engine == target:
            if target == "playwright" and fail_n >= 100:
                self._log(
                    f"playwright 本批 0 成功({fail_n} 失败)，回退 api 继续",
                    web=True,
                )
                self._active_engine = "api"
            return
        self._log(
            f"本批主引擎 {self._active_engine} 不可用(成功=0 失败={fail_n})，"
            f"回退配置引擎 {target}",
            web=True,
        )
        self._active_engine = target

    def _run_one_batch(self):
        batch_size = max(100, min(int(self.config.get("batch_size", 800)), 2000))
        concurrency = max(1, min(10, int(self.config.get("web_detail_concurrency", 5))))
        skip_today = bool(self.config.get("skip_today", True))
        low_v1d_only = bool(self.config.get("low_v1d_only", False))
        seed_batch_size = int(self.config.get("seed_batch_size", 0) or 0)

        with self._lock:
            self._stats["phase"] = "fetch"

        t0 = time.time()
        ensure_queue_seeded(
            low_v1d_only=low_v1d_only,
            skip_today=skip_today,
            min_pending=50,
            log_func=lambda m: self._log(m, web=True),
            seed_limit=seed_batch_size,
        )
        seed_s = time.time() - t0
        queue_sort = str(self.config.get("queue_sort", "monitor_first"))
        sold_tier_min = max(1, int(self.config.get("sold_tier_min", 10)))
        t_fetch = time.time()
        rows = fetch_full_sold_queue_batch(
            limit=batch_size,
            queue_sort=queue_sort,
        )
        fetch_s = time.time() - t_fetch
        if not rows:
            return {
                "has_more": False,
                "ok": 0,
                "fail": 0,
                "risk": 0,
                "updated": 0,
                "snapshot": 0,
                "fetch_s": fetch_s,
                "http_s": 0.0,
            }

        qs = queue_stats()
        tier_part = ""
        if self._round == 1 or self._round % 5 == 0:
            tiers = queue_pending_sold_tiers(high_sold_min=sold_tier_min)
            tier_part = (
                f"( 高销>={tiers['threshold']} {tiers['high_sold']:,} "
                f"低销 {tiers['low_sold']:,})"
            )
        self._log(
            f"第 {self._round} 轮 | 候选 {len(rows)} "
            f"(seed {seed_s:.1f}s + 取批 {fetch_s:.1f}s) | "
            f"队列待扫 {qs['pending']:,}{tier_part} | 引擎={self._active_engine}",
            web=True,
        )

        with self._lock:
            self._stats["phase"] = "http"

        if not _USE_BUFFER:
            try:
                from xhs_db_idle import wait_main_db_idle

                ok_idle, waited = wait_main_db_idle(
                    max_wait_sec=120,
                    poll_sec=5,
                    log_func=lambda m: self._log(m, web=True),
                )
                if not ok_idle:
                    self._log(
                        "主库 120s 内仍不可写，本批跳过 HTTP（避免 800 条各自等 30s 锁）",
                        web=True,
                    )
                    return {
                        "has_more": True,
                        "ok": 0,
                        "fail": 0,
                        "risk": 0,
                        "updated": 0,
                        "snapshot": 0,
                        "fetch_s": seed_s + fetch_s,
                        "http_s": 0.0,
                        "db_skip": True,
                    }
            except Exception as e:
                self._log(f"主库空闲检测异常: {e}", web=True)
        else:
            self._log("buffer模式: 跳过主库锁检测，写入缓冲库", web=True)

        self._log(
            f"第 {self._round} 轮: 开始 HTTP {len(rows)} 个 "
            f"(并发={concurrency}, 首请求可能 10~30s)...",
            web=True,
        )
        if not _USE_BUFFER:
            try:
                from xhs_db_idle import try_db_write_lock

                if not try_db_write_lock():
                    self._log(
                        "警告: 主库当前不可写 (database locked)，"
                        "本批可能写库失败或极慢，请先停 ④详情补全/报告/其它写库任务",
                        web=True,
                    )
            except Exception:
                pass

        http_t0 = time.time()
        ok_n = fail_n = risk_n = archived_n = updated_n = snap_n = 0
        archived_snap_n = archived_pure_n = 0
        archived_samples = []
        synced_ids = []
        done_in_batch = 0
        last_progress_log = http_t0

        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="FullSoldD") as pool:
            futures = {pool.submit(self._process_one, item): item for item in rows}
            for fut in as_completed(futures):
                if not self._running or self._stop_event.is_set():
                    break
                try:
                    result = fut.result()
                except Exception as e:
                    gid = futures[fut]["goods_id"]
                    mark_full_sold_sync_result(gid, ok=False)
                    result = ("fail", gid, str(e))
                if not result:
                    continue
                done_in_batch += 1
                kind = result[0]
                if kind == "archived":
                    archived_n += 1
                    if len(archived_samples) < 3:
                        archived_samples.append(f"{result[1][:16]}…")
                    if result[2] == "with_snapshot":
                        archived_snap_n += 1
                    else:
                        archived_pure_n += 1
                elif kind == "success":
                    synced_ids.append(result[1])
                    ok_n += 1
                    if result[2] == "updated":
                        updated_n += 1
                    else:
                        snap_n += 1
                elif kind == "risk":
                    risk_n += 1
                    fail_n += 1
                else:
                    fail_n += 1

                now = time.time()
                if (
                    done_in_batch <= 3
                    or done_in_batch % 10 == 0
                    or (now - last_progress_log) >= 5
                ):
                    last_progress_log = now
                    elapsed = int(now - http_t0)
                    self._log(
                        f"第 {self._round} 轮 HTTP {done_in_batch}/{len(rows)} "
                        f"成功={ok_n} 失败={fail_n} 冻结={archived_n} ({elapsed}s)",
                        web=True,
                    )

        http_s = time.time() - http_t0
        if synced_ids and not _USE_BUFFER:
            vel_n = recalc_velocity_after_sync(synced_ids)
            self._log(f"velocity 重算 {vel_n}/{len(synced_ids)}", web=True)
        elif synced_ids and _USE_BUFFER:
            self._log(
                f"velocity 重算已延迟到缓冲回填线程 (本批 {len(synced_ids)} 条)",
                web=True,
            )

        total = ok_n + fail_n
        success_rate = (ok_n / total) if total else 0.0
        frozen_part = f" 冻结={archived_n}"
        if archived_n:
            frozen_part += f"(快照保留={archived_snap_n} 纯下架={archived_pure_n})"
            samples = " ".join(archived_samples)
            if samples:
                frozen_part += f" 例:{samples}"
        self._log(
            f"批完成: 成功={ok_n} 失败={fail_n}{frozen_part} 风控命中={risk_n} "
            f"上行={updated_n} 快照={snap_n} 成功率={success_rate:.1%} "
            f"HTTP={http_s:.0f}s",
            web=True,
        )

        with self._lock:
            self._stats["batches"] += 1
            self._stats["success"] += ok_n
            self._stats["fail"] += fail_n
            self._stats["updated"] += updated_n
            self._stats["snapshot"] += snap_n
            self._stats["last_batch_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "has_more": len(rows) >= batch_size and qs.get("pending", 0) > 0,
            "ok": ok_n,
            "fail": fail_n,
            "risk": risk_n,
            "archived": archived_n,
            "frozen": archived_n,
            "updated": updated_n,
            "snapshot": snap_n,
            "success_rate": success_rate,
            "fetch_s": fetch_s,
            "http_s": http_s,
        }

    def _should_cooldown(self, batch):
        archived = batch.get("archived", batch.get("frozen", 0))
        fail = batch.get("fail", 0)
        ok = batch.get("ok", 0)
        risk = batch.get("risk", 0)
        total = ok + fail
        if total < 30:
            return False
        risk_ratio = risk / total if total else 0
        if risk >= max(10, total * 0.3) and risk_ratio >= 0.15:
            return True
        if ok == 0 and risk == 0 and fail >= total * 0.9 and archived == 0:
            self._bad_batch_streak += 1
            if self._active_engine in ("playwright", "drissionpage", "mobile_http"):
                return self._bad_batch_streak >= 1
            return self._bad_batch_streak >= 3
        if ok == 0 and risk >= total * 0.5:
            self._bad_batch_streak += 1
            return self._bad_batch_streak >= 2
        rate = (ok / total) if total else 0
        min_rate = float(self.config.get("min_success_rate", 0.08))
        if rate < min_rate and risk >= max(5, total * 0.1):
            self._bad_batch_streak += 1
            return self._bad_batch_streak >= 2
        self._bad_batch_streak = 0
        return False

    def _main_loop(self):
        self._log("===== ⑥ 补缺挂机主循环 =====", web=True)
        queue_sort = str(self.config.get("queue_sort", "monitor_first"))
        sold_tier_min = max(1, int(self.config.get("sold_tier_min", 10)))
        sort_label = (
            "高销量优先→低销/死品靠后"
            if queue_sort in ("monitor_first", "sold_desc", "sold_first")
            else "低v1d清死品优先"
        )
        self._log(
            f"配置: 并发={self.config.get('web_detail_concurrency', 5)} "
            f"批大小={self.config.get('batch_size', 800)} "
            f"轮冷却={self.config.get('web_cooldown_seconds', 0)}s(0=连续扫) "
            f"风控冷却=30→60→90→120min "
            f"取批={sort_label} 高销阈值>={sold_tier_min} "
            f"引擎={self._active_engine}",
            web=True,
        )
        empty_rounds = 0

        while self._running and not self._stop_event.is_set():
            while self._paused and self._running:
                time.sleep(0.5)

            if self._in_cooldown():
                if not self._wait_risk_cooldown(already_scheduled=True):
                    break
                continue

            self._round += 1
            with self._lock:
                self._stats["rounds"] = self._round
                self._stats["phase"] = "batch"

            try:
                batch = self._run_one_batch()
            except Exception as e:
                self._log(f"批异常: {e}", web=True)
                import traceback
                self._log(traceback.format_exc(), web=True)
                if not self._sleep(300):
                    break
                continue

            if not batch.get("has_more") and batch.get("ok", 0) == 0 and batch.get("fail", 0) == 0:
                empty_rounds += 1
                wait = min(3600, 600 * empty_rounds)
                self._log(
                    f"队列已空或无候选，{wait // 60} 分钟后 re-seed（空轮 {empty_rounds}）",
                    web=True,
                )
                with self._lock:
                    self._stats["phase"] = "idle"
                if not self._sleep(wait):
                    break
                from xhs_full_sold_queue_db import seed_full_sold_queue

                seed_full_sold_queue(
                    low_v1d_only=bool(self.config.get("low_v1d_only", False)),
                    skip_today=bool(self.config.get("skip_today", True)),
                    log_func=lambda m: self._log(m, web=True),
                    limit=int(self.config.get("seed_batch_size", 0) or 0),
                )
                continue

            empty_rounds = 0

            self._revert_engine_if_batch_dead(batch)

            if self._should_cooldown(batch):
                self._last_batch_snapshot = dict(batch)
                self._log("批成功率过低/连续失败，触发风控冷却", web=True)
                if not self._wait_risk_cooldown(batch=batch):
                    break
                continue

            round_cd = max(0, int(self.config.get("web_cooldown_seconds", 0) or 0))
            if round_cd > 0:
                with self._lock:
                    self._stats["phase"] = "round_cooldown"
                self._log(f"轮间冷却 {round_cd}s...", web=True)
                if not self._sleep(round_cd):
                    break

        with self._lock:
            self._stats["phase"] = "stopped"
        self._running = False
        close_open_events(source="full_sold_daemon", recovery_mode="daemon_stop", note="主循环退出")
        self._log("===== ⑥ 补缺挂机已退出 =====", web=True)


_daemon_instance = None
_daemon_lock = threading.Lock()


def get_full_sold_daemon():
    with _daemon_lock:
        return _daemon_instance


def start_full_sold_daemon(config=None, log_func=None, web_log_func=None):
    global _daemon_instance
    with _daemon_lock:
        if _daemon_instance and _daemon_instance._running:
            return _daemon_instance
        _daemon_instance = FullSoldSyncDaemon(
            config=config or {},
            log_func=log_func,
            web_log_func=web_log_func,
        )
        _daemon_instance.start()
        return _daemon_instance


def stop_full_sold_daemon():
    global _daemon_instance
    with _daemon_lock:
        if _daemon_instance:
            _daemon_instance.stop()
        return True


def is_full_sold_daemon_running():
    d = get_full_sold_daemon()
    return bool(d and d._running)


def pause_full_sold_daemon():
    d = get_full_sold_daemon()
    if d:
        d.pause()


def resume_full_sold_daemon():
    d = get_full_sold_daemon()
    if d:
        d.resume()
