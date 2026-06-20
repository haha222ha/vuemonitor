# -*- coding: utf-8 -*-
"""销量快照驱动的 velocity 重算（与 APP 关键词扫描 batch 逻辑一致，供⑤⑥等模块复用）。"""
from __future__ import annotations

from datetime import datetime, timedelta

MIN_BASE_HOURS = 4
# 快照基准最早可追溯到全部历史（仅要求基准早于当前 >=4h，不再限制 14 天上限）
VELOCITY_CAP = 1.5
STALE_PENALTY_START_HOURS = 72
STALE_WEIGHT_FLOOR = 0.08


def _parse_dt(value):
    if not value:
        return None
    text = str(value).strip()
    if len(text) >= 19:
        try:
            return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    if len(text) >= 10:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        except Exception:
            pass
    return None


def _hours_between(base_at, now):
    if not base_at:
        return None
    return max(0.0, (now - base_at).total_seconds() / 3600.0)


def _stale_weight(hours):
    if hours is None or hours <= STALE_PENALTY_START_HOURS:
        return 1.0
    return max(STALE_WEIGHT_FLOOR, STALE_PENALTY_START_HOURS / hours)


def resolve_prev_snapshot(cursor, goods_id, now=None):
    """
    选取 velocity 基准快照（上次有效销量对照）。

    优先级:
      1. sold_snapshots: 早于当前 >=4h 的最近一条（不限最早上限）
      2. sold_history: 今天之前最近一天的 sold_num

    返回 (sold_prev, base_at_dt, base_at_str, source) 或 (None, None, None, None)
    """
    now = now or datetime.now()
    snap_max = (now - timedelta(hours=MIN_BASE_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "SELECT sold_num, snapshot_time FROM sold_snapshots WHERE goods_id=? "
        "AND snapshot_time <= ? ORDER BY snapshot_time DESC LIMIT 1",
        (goods_id, snap_max),
    )
    row = cursor.fetchone()
    if row and row[0] is not None and row[0] > 0:
        base_at = _parse_dt(row[1])
        if base_at:
            return int(row[0]), base_at, base_at.strftime("%Y-%m-%d %H:%M:%S"), "snapshot"

    today = now.strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT sold_num, snapshot_date FROM sold_history WHERE goods_id=? "
        "AND snapshot_date < ? AND sold_num IS NOT NULL AND sold_num > 0 "
        "ORDER BY snapshot_date DESC LIMIT 1",
        (goods_id, today),
    )
    row = cursor.fetchone()
    if row and row[0] is not None and row[0] > 0:
        base_at = _parse_dt(f"{row[1]} 23:59:59")
        if base_at:
            return int(row[0]), base_at, f"{row[1]} 23:59:59", "history"

    return None, None, None, None


def _calc_daily_metrics(current, sold_prev, base_at, now):
    """计算 actual_velocity_1d / velocity_1d / daily_growth_rate。"""
    actual = 0.0
    v_1d = 0.0
    daily_growth_rate = 0.0
    base_hours = None

    if sold_prev is None or current <= 0 or current <= sold_prev:
        return actual, v_1d, daily_growth_rate, base_hours

    actual = float(current - sold_prev)
    base_hours = _hours_between(base_at, now)
    if base_hours is None or base_hours < MIN_BASE_HOURS:
        return actual, 0.0, 0.0, base_hours

    v_1d = actual * min(24.0 / base_hours, VELOCITY_CAP)
    if v_1d > current:
        v_1d = float(current)

    if sold_prev > 0:
        daily_growth_rate = actual / sold_prev

    return actual, v_1d, daily_growth_rate, base_hours


def recalc_velocity_for_goods(cursor, goods_ids, emit_alerts=False):
    """
    根据 sold_snapshots / sold_history 重算 velocity_1h/6h/1d、actual_velocity_1d、burst_score、pool 等。
    emit_alerts=True 时写入 alert_events（App 关键词 batch 落库用）。
    """
    if not goods_ids:
        return 0

    unique_ids = list(dict.fromkeys(g for g in goods_ids if g))
    if not unique_ids:
        return 0

    from xhs_sold_sanity import is_dirty_sold_metrics

    vel_now = datetime.now()
    vel_h1_min = (vel_now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    vel_h1_max = (vel_now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    vel_h6_min = (vel_now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    vel_h6_max = (vel_now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
    vel_now_str = vel_now.strftime("%Y-%m-%d %H:%M:%S")
    updated = 0

    for gid in unique_ids:
        try:
            cursor.execute("SELECT sold_num, first_seen FROM goods WHERE goods_id=?", (gid,))
            row = cursor.fetchone()
            if not row or not row[0] or row[0] <= 0:
                continue

            current = row[0]
            first_seen = row[1] if len(row) > 1 else None

            v_1h = 0.0
            cursor.execute(
                "SELECT sold_num FROM sold_snapshots WHERE goods_id=? "
                "AND snapshot_time BETWEEN ? AND ? ORDER BY snapshot_time DESC LIMIT 1",
                (gid, vel_h1_min, vel_h1_max),
            )
            snap = cursor.fetchone()
            if snap and snap[0] is not None and snap[0] > 0 and current > snap[0]:
                v_1h = current - snap[0]

            v_6h = 0.0
            cursor.execute(
                "SELECT sold_num FROM sold_snapshots WHERE goods_id=? "
                "AND snapshot_time BETWEEN ? AND ? ORDER BY snapshot_time DESC LIMIT 1",
                (gid, vel_h6_min, vel_h6_max),
            )
            snap = cursor.fetchone()
            if snap and snap[0] is not None and snap[0] > 0 and current > snap[0]:
                v_6h = current - snap[0]

            sold_prev, base_at, base_at_str, _source = resolve_prev_snapshot(cursor, gid, vel_now)
            actual_v1d, v_1d, daily_growth_rate, base_hours = _calc_daily_metrics(
                current, sold_prev, base_at, vel_now
            )

            dirty, _reason = is_dirty_sold_metrics(current, actual_v1d, v_1d, sold_prev)
            if dirty:
                actual_v1d = v_1d = v_1h = v_6h = daily_growth_rate = 0.0
                acc = burst = 0.0
                pool = "WATCH"
                base_hours = 0
                base_at_str = ""
            else:
                acc = v_1h * 24 - v_6h * 4 if v_1h > 0 and v_6h > 0 else 0.0
                sv1h = min(v_1h * 24 / 200.0, 1.0) * 100
                sv1d = min(v_1d / 100.0, 1.0) * 100
                sacc = min(max(acc, 0) / 100.0, 1.0) * 100
                burst = 0.40 * sv1h + 0.55 * sv1d + 0.05 * sacc
                burst *= _stale_weight(base_hours)
                pool = "WATCH"
                if first_seen:
                    try:
                        fs_hours = (
                            datetime.now() - datetime.strptime(first_seen[:19], "%Y-%m-%d %H:%M:%S")
                        ).total_seconds() / 3600
                        if fs_hours < 24:
                            pool = "NEW"
                    except Exception:
                        pass
                if burst >= 50:
                    pool = "BURST"
                elif burst >= 25 and v_1d >= 5:
                    pool = "ACCEL"

            cursor.execute(
                "UPDATE goods SET velocity_1h=?, velocity_6h=?, velocity_1d=?, "
                "actual_velocity_1d=?, acceleration=?, burst_score=?, pool=?, "
                "daily_growth_rate=?, velocity_base_hours=?, velocity_base_at=? "
                "WHERE goods_id=?",
                (
                    v_1h,
                    v_6h,
                    v_1d,
                    actual_v1d,
                    acc,
                    burst,
                    pool,
                    daily_growth_rate,
                    base_hours if base_hours is not None else 0,
                    base_at_str or "",
                    gid,
                ),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO metrics_snapshots "
                "(goods_id, metric_time, S, V_1h, V_6h, V_1d, A, B, pool) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (gid, vel_now_str, current, v_1h, v_6h, v_1d, acc, burst, pool),
            )
            if emit_alerts:
                if burst >= 50:
                    alert_lvl = (
                        "LEVEL_4" if burst >= 80 and v_1h >= 10
                        else "LEVEL_3" if burst >= 80
                        else "LEVEL_2"
                    )
                    cursor.execute(
                        "INSERT INTO alert_events (goods_id, alert_level, burst_score, detail) "
                        "VALUES (?, ?, ?, ?)",
                        (gid, alert_lvl, burst, f"V1h={v_1h:.0f} V1d={v_1d:.0f} A={acc:.0f} pool={pool}"),
                    )
                elif v_1h > 0 and v_1d > 0 and v_1h * 24 > v_1d * 3:
                    cursor.execute(
                        "INSERT INTO alert_events (goods_id, alert_level, burst_score, detail) "
                        "VALUES (?, ?, ?, ?)",
                        (gid, "VELOCITY_SPIKE", burst, f"V1h*24={v_1h*24:.0f} >> V1d={v_1d:.0f}"),
                    )
            updated += 1
        except Exception:
            continue

    return updated
