import asyncio
import json
import time
import uuid
import statistics
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

import aiohttp
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.collect.engine import CollectEngine, RiskDetector
from app.collect.session_manager import SessionManager
from app.collect.rate_controller import AdaptiveRateController
from app.models.collect import CollectTask, CollectTaskItem
from app.models.admin import RiskEvent


@dataclass
class BenchmarkResult:
    concurrency: int
    total_requests: int
    successful: int
    failed: int
    risk_detected: int
    avg_response_ms: float
    p50_response_ms: float
    p90_response_ms: float
    p99_response_ms: float
    min_response_ms: float
    max_response_ms: float
    qps: float
    error_rate: float
    risk_rate: float
    duration_seconds: float
    risk_types: dict = field(default_factory=dict)
    platform: str = "xhs"
    timestamp: str = ""

    def __post_init__(self):
        self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ProxyBenchmarkResult:
    total_proxies: int
    available_proxies: int
    avg_health_score: float
    banned_during_test: int
    proxy_response_times: list = field(default_factory=list)


async def run_concurrency_benchmark(
    concurrency: int,
    total_items: int,
    platform: str = "xhs",
    target_ids: list[str] | None = None,
) -> BenchmarkResult:
    if not target_ids:
        target_ids = [f"bench_{uuid.uuid4().hex[:8]}" for _ in range(total_items)]

    session_manager = SessionManager()
    rate_controller = AdaptiveRateController()
    response_times: list[float] = []
    results = {"success": 0, "failed": 0, "risk": 0}
    risk_types: dict[str, int] = {}
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(session: aiohttp.ClientSession, target_id: str):
        async with semaphore:
            await rate_controller.acquire()
            start = time.monotonic()
            try:
                fingerprint = session_manager.generate_fingerprint(platform)
                headers = dict(fingerprint)
                headers["Referer"] = f"https://www.xiaohongshu.com/explore/{target_id}"
                headers["Origin"] = "https://www.xiaohongshu.com"
                headers["Content-Type"] = "application/json;charset=UTF-8"

                payload = {"source_note_id": target_id, "image_scenes": ["CRD_WM_WEBP"]}

                try:
                    async with session.post(
                        "https://edith.xiaohongshu.com/api/sns/web/v1/feed",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=20),
                        ssl=False,
                    ) as resp:
                        text = await resp.text()
                        elapsed = (time.monotonic() - start) * 1000
                        response_times.append(elapsed)

                        risk = RiskDetector.detect(text, resp.status)
                        if risk:
                            results["risk"] += 1
                            rt = risk["risk_type"]
                            risk_types[rt] = risk_types.get(rt, 0) + 1
                            rate_controller.on_risk_detected()
                        else:
                            results["success"] += 1
                            rate_controller.on_success()
                except asyncio.TimeoutError:
                    elapsed = (time.monotonic() - start) * 1000
                    response_times.append(elapsed)
                    results["failed"] += 1
                    rate_controller.on_error()
                except aiohttp.ClientError:
                    elapsed = (time.monotonic() - start) * 1000
                    response_times.append(elapsed)
                    results["failed"] += 1
                    rate_controller.on_error()
            except Exception:
                elapsed = (time.monotonic() - start) * 1000
                response_times.append(elapsed)
                results["failed"] += 1
                rate_controller.on_error()

    overall_start = time.monotonic()

    async with aiohttp.ClientSession() as http_session:
        tasks = [fetch_one(http_session, tid) for tid in target_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    duration = time.monotonic() - overall_start

    await session_manager.close_all()

    response_times.sort()
    total = results["success"] + results["failed"] + results["risk"]

    return BenchmarkResult(
        concurrency=concurrency,
        total_requests=total,
        successful=results["success"],
        failed=results["failed"],
        risk_detected=results["risk"],
        avg_response_ms=round(statistics.mean(response_times), 2) if response_times else 0,
        p50_response_ms=round(statistics.median(response_times), 2) if response_times else 0,
        p90_response_ms=round(response_times[int(len(response_times) * 0.9)], 2) if response_times else 0,
        p99_response_ms=round(response_times[int(len(response_times) * 0.99)], 2) if response_times else 0,
        min_response_ms=round(min(response_times), 2) if response_times else 0,
        max_response_ms=round(max(response_times), 2) if response_times else 0,
        qps=round(total / duration, 2) if duration > 0 else 0,
        error_rate=round(results["failed"] / total * 100, 2) if total > 0 else 0,
        risk_rate=round(results["risk"] / total * 100, 2) if total > 0 else 0,
        duration_seconds=round(duration, 2),
        risk_types=risk_types,
        platform=platform,
    )


async def run_proxy_benchmark(db: AsyncSession) -> ProxyBenchmarkResult:
    from app.models.admin import ProxyPool

    total_result = await db.execute(select(func.count()).select_from(ProxyPool))
    total = total_result.scalar() or 0

    available_result = await db.execute(
        select(func.count()).select_from(ProxyPool).where(ProxyPool.status == "available")
    )
    available = available_result.scalar() or 0

    avg_score_result = await db.execute(
        select(func.avg(ProxyPool.health_score)).where(ProxyPool.status == "available")
    )
    avg_score = avg_score_result.scalar() or 0

    banned_result = await db.execute(
        select(func.count()).select_from(ProxyPool).where(ProxyPool.status == "banned")
    )
    banned = banned_result.scalar() or 0

    proxy_times: list[float] = []
    proxies_result = await db.execute(
        select(ProxyPool).where(ProxyPool.status == "available").limit(10)
    )
    proxies = proxies_result.scalars().all()

    for proxy in proxies:
        proxy_url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
        start = time.monotonic()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.xiaohongshu.com",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False,
                ) as resp:
                    await resp.text()
                    elapsed = (time.monotonic() - start) * 1000
                    proxy_times.append(elapsed)
        except Exception:
            proxy_times.append(-1)

    return ProxyBenchmarkResult(
        total_proxies=total,
        available_proxies=available,
        avg_health_score=round(float(avg_score), 2),
        banned_during_test=banned,
        proxy_response_times=[round(t, 2) for t in proxy_times],
    )


async def run_risk_threshold_test(platform: str = "xhs") -> dict:
    session_manager = SessionManager()
    rate_controller = AdaptiveRateController()

    risk_timeline: list[dict] = []
    consecutive_risks = 0
    request_count = 0
    first_risk_at: int | None = None

    async with aiohttp.ClientSession() as http_session:
        for i in range(100):
            await rate_controller.acquire()
            request_count += 1
            start = time.monotonic()

            try:
                fingerprint = session_manager.generate_fingerprint(platform)
                headers = dict(fingerprint)
                target_id = f"risk_test_{uuid.uuid4().hex[:8]}"
                headers["Referer"] = f"https://www.xiaohongshu.com/explore/{target_id}"

                async with http_session.post(
                    "https://edith.xiaohongshu.com/api/sns/web/v1/feed",
                    headers=headers,
                    json={"source_note_id": target_id, "image_scenes": ["CRD_WM_WEBP"]},
                    timeout=aiohttp.ClientTimeout(total=15),
                    ssl=False,
                ) as resp:
                    text = await resp.text()
                    elapsed = (time.monotonic() - start) * 1000

                    risk = RiskDetector.detect(text, resp.status)
                    if risk:
                        consecutive_risks += 1
                        rate_controller.on_risk_detected()
                        if first_risk_at is None:
                            first_risk_at = request_count
                        risk_timeline.append({
                            "request": request_count,
                            "risk_type": risk["risk_type"],
                            "risk_level": risk["risk_level"],
                            "response_ms": round(elapsed, 2),
                        })
                    else:
                        consecutive_risks = max(0, consecutive_risks - 1)
                        rate_controller.on_success()
            except Exception:
                consecutive_risks += 1
                rate_controller.on_error()

            await asyncio.sleep(0.5)

    return {
        "total_requests": request_count,
        "first_risk_at_request": first_risk_at,
        "total_risks": len(risk_timeline),
        "risk_timeline": risk_timeline[:20],
        "consecutive_risks_at_end": consecutive_risks,
    }


async def run_full_benchmark() -> dict:
    results = {}

    for concurrency in [10, 50, 100]:
        print(f"\n{'='*60}")
        print(f"Running benchmark: concurrency={concurrency}, items=50")
        print(f"{'='*60}")
        result = await run_concurrency_benchmark(concurrency, 50)
        results[f"concurrency_{concurrency}"] = asdict(result)
        print(f"  QPS: {result.qps}")
        print(f"  Avg Response: {result.avg_response_ms}ms")
        print(f"  P90 Response: {result.p90_response_ms}ms")
        print(f"  Error Rate: {result.error_rate}%")
        print(f"  Risk Rate: {result.risk_rate}%")

    async with async_session_factory() as db:
        print(f"\n{'='*60}")
        print("Running proxy benchmark...")
        print(f"{'='*60}")
        proxy_result = await run_proxy_benchmark(db)
        results["proxy"] = asdict(proxy_result)
        print(f"  Total Proxies: {proxy_result.total_proxies}")
        print(f"  Available: {proxy_result.available_proxies}")
        print(f"  Avg Health: {proxy_result.avg_health_score}")

    print(f"\n{'='*60}")
    print("Running risk threshold test...")
    print(f"{'='*60}")
    risk_result = await run_risk_threshold_test()
    results["risk_threshold"] = risk_result
    print(f"  First Risk At: request #{risk_result['first_risk_at_request']}")
    print(f"  Total Risks: {risk_result['total_risks']}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmarks": results,
        "summary": {
            "max_safe_concurrency": _determine_safe_concurrency(results),
            "recommendations": _generate_recommendations(results),
        },
    }

    report_path = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")

    return report


def _determine_safe_concurrency(results: dict) -> int:
    safe = 10
    for key, data in results.items():
        if key.startswith("concurrency_") and isinstance(data, dict):
            error_rate = data.get("error_rate", 100)
            risk_rate = data.get("risk_rate", 100)
            if error_rate < 5 and risk_rate < 10:
                conc = int(key.split("_")[1])
                safe = max(safe, conc)
    return safe


def _generate_recommendations(results: dict) -> list[str]:
    recs = []
    for key, data in results.items():
        if key.startswith("concurrency_") and isinstance(data, dict):
            conc = int(key.split("_")[1])
            if data.get("error_rate", 0) > 10:
                recs.append(f"并发{conc}时错误率过高({data['error_rate']}%)，建议降低并发数")
            if data.get("risk_rate", 0) > 15:
                recs.append(f"并发{conc}时风控触发率过高({data['risk_rate']}%)，建议增加请求间隔")
            if data.get("p99_response_ms", 0) > 5000:
                recs.append(f"并发{conc}时P99延迟过高({data['p99_response_ms']}ms)，建议优化超时设置")

    proxy_data = results.get("proxy", {})
    if proxy_data.get("available_proxies", 0) < 5:
        recs.append("可用代理数量不足，建议补充代理池")
    if proxy_data.get("avg_health_score", 100) < 60:
        recs.append("代理平均健康分数偏低，建议清理低质量代理")

    risk_data = results.get("risk_threshold", {})
    if risk_data.get("first_risk_at_request") and risk_data["first_risk_at_request"] < 20:
        recs.append("风控触发过早，建议增加请求间隔或使用更高质量的代理")

    if not recs:
        recs.append("系统表现良好，当前配置可以安全使用")

    return recs


if __name__ == "__main__":
    report = asyncio.run(run_full_benchmark())
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Max Safe Concurrency: {report['summary']['max_safe_concurrency']}")
    for rec in report["summary"]["recommendations"]:
        print(f"  - {rec}")
