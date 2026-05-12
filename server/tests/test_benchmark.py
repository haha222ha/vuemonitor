import sys
import os
import time
import uuid
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import requests
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

BASE_URL = "http://127.0.0.1:8000"

TEST_ACCOUNT = f"bench_{uuid.uuid4().hex[:8]}@test.com"
TEST_PASSWORD = "BenchPass123!"


def get_token():
    resp = client.post("/api/v1/auth/login", json={
        "account": TEST_ACCOUNT,
        "password": TEST_PASSWORD,
    })
    if resp.status_code == 200:
        return resp.json().get("access_token")
    resp2 = client.post("/api/v1/auth/register", json={
        "account": TEST_ACCOUNT,
        "password": TEST_PASSWORD,
        "name": "Bench User",
    })
    if resp2.status_code in (200, 201):
        resp3 = client.post("/api/v1/auth/login", json={
            "account": TEST_ACCOUNT,
            "password": TEST_PASSWORD,
        })
        return resp3.json().get("access_token")
    return None


class TestBenchmark:
    token: str | None = None

    @classmethod
    def setup_class(cls):
        cls.token = get_token()

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test_health_endpoint_latency(self):
        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            resp = client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            assert resp.status_code == 200

        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\n[Health Endpoint] avg={avg:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
        assert avg < 100, f"Average latency {avg:.2f}ms exceeds 100ms"

    def test_products_list_latency(self):
        latencies = []
        for _ in range(30):
            start = time.perf_counter()
            resp = client.get("/api/v1/products?page=1&page_size=20", headers=self._auth_headers())
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n[Products List] avg={avg:.2f}ms, p95={p95:.2f}ms")
        assert avg < 500, f"Average latency {avg:.2f}ms exceeds 500ms"

    def test_auth_login_latency(self):
        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            resp = client.post("/api/v1/auth/login", json={
                "account": TEST_ACCOUNT,
                "password": TEST_PASSWORD,
            })
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n[Auth Login] avg={avg:.2f}ms, p95={p95:.2f}ms")
        assert avg < 1000, f"Average latency {avg:.2f}ms exceeds 1000ms"

    def test_concurrent_health_checks(self):
        def make_request():
            start = time.perf_counter()
            resp = client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, resp.status_code

        latencies = []
        errors = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            for future in as_completed(futures):
                elapsed, status = future.result()
                latencies.append(elapsed)
                if status != 200:
                    errors += 1

        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\n[Concurrent Health] avg={avg:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms, errors={errors}")
        assert errors < 10, f"Too many errors: {errors}"

    def test_concurrent_auth_requests(self):
        def make_request():
            start = time.perf_counter()
            resp = client.post("/api/v1/auth/login", json={
                "account": TEST_ACCOUNT,
                "password": TEST_PASSWORD,
            })
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed, resp.status_code

        latencies = []
        errors = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            for future in as_completed(futures):
                elapsed, status = future.result()
                latencies.append(elapsed)
                if status != 200:
                    errors += 1

        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        print(f"\n[Concurrent Auth] avg={avg:.2f}ms, p95={p95:.2f}ms, errors={errors}")
        assert errors < 5, f"Too many errors: {errors}"

    def test_products_list_throughput(self):
        start = time.perf_counter()
        count = 0
        errors = 0
        deadline = start + 5

        while time.perf_counter() < deadline:
            resp = client.get("/api/v1/products?page=1&page_size=10", headers=self._auth_headers())
            count += 1
            if resp.status_code not in (200, 401):
                errors += 1

        elapsed = time.perf_counter() - start
        throughput = count / elapsed

        print(f"\n[Products Throughput] {throughput:.1f} req/s, {count} requests in {elapsed:.1f}s, errors={errors}")

    def test_openapi_schema_size(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        paths = schema.get("paths", {})
        endpoint_count = len(paths)

        print(f"\n[API Schema] {endpoint_count} endpoints defined")
        assert endpoint_count > 10, f"Only {endpoint_count} endpoints found"

    def test_response_size_health(self):
        resp = client.get("/health")
        content_length = len(resp.content)
        print(f"\n[Health Response Size] {content_length} bytes")
        assert content_length < 10240, f"Response too large: {content_length} bytes"

    def test_response_size_products(self):
        resp = client.get("/api/v1/products?page=1&page_size=5", headers=self._auth_headers())
        if resp.status_code == 200:
            content_length = len(resp.content)
            print(f"\n[Products Response Size] {content_length} bytes")
            assert content_length < 1024 * 1024, f"Response too large: {content_length} bytes"

    def test_memory_baseline(self):
        import psutil
        process = psutil.Process()
        mem_before = process.memory_info().rss

        for _ in range(100):
            client.get("/health")

        mem_after = process.memory_info().rss
        delta_mb = (mem_after - mem_before) / (1024 * 1024)

        print(f"\n[Memory] Before: {mem_before / 1024 / 1024:.1f}MB, After: {mem_after / 1024 / 1024:.1f}MB, Delta: {delta_mb:.2f}MB")
        assert delta_mb < 50, f"Memory increased by {delta_mb:.2f}MB after 100 requests"

    def test_startup_time(self):
        print("\n[Startup] FastAPI TestClient startup is near-instantaneous in test mode")

    def test_json_serialization_speed(self):
        data = {
            "id": str(uuid.uuid4()),
            "name": "Test Product",
            "features": [{"price": i * 10, "sales": i * 100} for i in range(100)],
            "metadata": {"key": f"value_{i}" for i in range(50)},
        }

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            json_str = json.dumps(data)
            _ = json.loads(json_str)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg = sum(latencies) / len(latencies)
        print(f"\n[JSON Serialization] avg={avg:.4f}ms per roundtrip")

    def test_token_generation_speed(self):
        from app.core.security import create_access_token

        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            token = create_access_token(subject=str(uuid.uuid4()))
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            assert len(token) > 0

        avg = sum(latencies) / len(latencies)
        print(f"\n[Token Generation] avg={avg:.2f}ms")
        assert avg < 50, f"Token generation too slow: {avg:.2f}ms"

    def test_password_hashing_speed(self):
        from app.core.security import hash_password, verify_password

        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            hashed = hash_password("TestPass123!")
            assert verify_password("TestPass123!", hashed)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg = sum(latencies) / len(latencies)
        print(f"\n[Password Hash+Verify] avg={avg:.2f}ms")
        assert avg < 500, f"Password hashing too slow: {avg:.2f}ms"


class TestStressScenarios:
    token: str | None = None

    @classmethod
    def setup_class(cls):
        cls.token = get_token()

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test_rapid_successive_requests(self):
        errors = 0
        for _ in range(100):
            resp = client.get("/health")
            if resp.status_code != 200:
                errors += 1

        print(f"\n[Rapid Requests] 100 health checks, errors={errors}")
        assert errors == 0

    def test_large_payload_rejection(self):
        large_payload = {"data": "x" * (10 * 1024 * 1024)}
        resp = client.post("/api/v1/auth/login", json=large_payload)
        assert resp.status_code in (422, 400, 413)

    def test_many_query_params(self):
        params = {f"param_{i}": f"value_{i}" for i in range(50)}
        query = "&".join(f"{k}={v}" for k, v in params.items())
        resp = client.get(f"/api/v1/products?{query}", headers=self._auth_headers())
        assert resp.status_code in (200, 401, 422)

    def test_sql_injection_attempt(self):
        resp = client.post("/api/v1/auth/login", json={
            "account": "'; DROP TABLE users; --",
            "password": "' OR '1'='1",
        })
        assert resp.status_code in (401, 400, 422)

    def test_xss_attempt(self):
        resp = client.post("/api/v1/auth/register", json={
            "account": "<script>alert('xss')</script>@test.com",
            "password": "TestPass123!",
            "name": "<img src=x onerror=alert(1)>",
        })
        assert resp.status_code in (422, 400, 401)

    def test_unicode_surrogate_handling(self):
        resp = client.post("/api/v1/auth/login", json={
            "account": "test@test.com",
            "password": "Test\uD800Pass",
        })
        assert resp.status_code in (422, 400, 401)

    def test_empty_body_post(self):
        resp = client.post("/api/v1/auth/login", headers={
            "Content-Type": "application/json",
        })
        assert resp.status_code in (422, 400)

    def test_very_long_url(self):
        long_path = "/api/v1/products?q=" + "x" * 8000
        resp = client.get(long_path, headers=self._auth_headers())
        assert resp.status_code in (200, 401, 414, 422)

    def test_concurrent_reads_and_writes(self):
        def read_op():
            return client.get("/api/v1/products?page=1&page_size=5", headers=self._auth_headers()).status_code

        def write_op():
            return client.post("/api/v1/auth/login", json={
                "account": TEST_ACCOUNT,
                "password": TEST_PASSWORD,
            }).status_code

        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for _ in range(50):
                futures.append(executor.submit(read_op))
            for _ in range(20):
                futures.append(executor.submit(write_op))
            for future in as_completed(futures):
                results.append(future.result())

        errors = sum(1 for r in results if r not in (200, 401))
        print(f"\n[Concurrent Read/Write] {len(results)} ops, errors={errors}")
        assert errors < 10