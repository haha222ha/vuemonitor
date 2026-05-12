import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.redis import get_redis

_metrics: dict[str, dict] = {}


def _get_or_create_metric(name: str, metric_type: str, labels: list[str], help_text: str) -> dict:
    if name not in _metrics:
        _metrics[name] = {
            "type": metric_type,
            "help": help_text,
            "labels": labels,
            "samples": {},
        }
    return _metrics[name]


def counter_inc(name: str, value: float = 1, **labels):
    metric = _get_or_create_metric(name, "counter", list(labels.keys()), "")
    key = tuple(labels.values())
    metric["samples"][key] = metric["samples"].get(key, 0) + value


def gauge_set(name: str, value: float, **labels):
    metric = _get_or_create_metric(name, "gauge", list(labels.keys()), "")
    key = tuple(labels.values())
    metric["samples"][key] = value


def histogram_observe(name: str, value: float, **labels):
    buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    metric = _get_or_create_metric(name, "histogram", list(labels.keys()), "")
    key = tuple(labels.values())

    if key not in metric["samples"]:
        metric["samples"][key] = {"buckets": {b: 0 for b in buckets}, "sum": 0, "count": 0}

    sample = metric["samples"][key]
    sample["sum"] += value
    sample["count"] += 1
    for b in buckets:
        if value <= b:
            sample["buckets"][b] += 1


def generate_prometheus_output() -> str:
    lines = []
    for name, metric in sorted(_metrics.items()):
        lines.append(f"# HELP {name} {metric.get('help', '')}")
        lines.append(f"# TYPE {name} {metric['type']}")

        for key, value in metric["samples"].items():
            label_parts = []
            for i, label_name in enumerate(metric["labels"]):
                if i < len(key):
                    label_parts.append(f'{label_name}="{key[i]}"')

            label_str = "{" + ",".join(label_parts) + "}" if label_parts else ""

            if metric["type"] == "histogram":
                sample = value
                for bucket, count in sorted(sample["buckets"].items()):
                    le_labels = label_str.rstrip("}") + f',le="{bucket}"' + "}" if label_str else f'{{le="{bucket}"}}'
                    lines.append(f"{name}_bucket{le_labels} {count}")
                lines.append(f"{name}_sum{label_str} {sample['sum']}")
                lines.append(f"{name}_count{label_str} {sample['count']}")
            else:
                lines.append(f"{name}{label_str} {value}")

    return "\n".join(lines) + "\n"


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in ("/metrics", "/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        start = time.time()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            counter_inc("http_requests_total", method=method, path=path, status="500")
            raise

        duration = time.time() - start
        counter_inc("http_requests_total", method=method, path=path, status=str(status))
        histogram_observe("http_request_duration_seconds", duration, method=method, path=path)

        if status >= 500:
            counter_inc("http_errors_total", method=method, path=path, status=str(status))

        return response


async def collect_system_metrics():
    import asyncio
    import psutil

    try:
        process = psutil.Process()
        gauge_set("process_cpu_percent", process.cpu_percent())
        mem = process.memory_info()
        gauge_set("process_memory_rss_bytes", mem.rss)
        gauge_set("process_memory_vms_bytes", mem.vms)

        try:
            from app.core.database import get_pool_stats
            pool_stats = await get_pool_stats()
            gauge_set("db_pool_size", pool_stats["pool_size"])
            gauge_set("db_pool_checked_out", pool_stats["checked_out"])
            gauge_set("db_pool_overflow", pool_stats["overflow"])
        except Exception:
            pass

        try:
            redis = await get_redis()
            info = await redis.info()
            gauge_set("redis_connected_clients", info.get("connected_clients", 0))
            gauge_set("redis_used_memory_bytes", info.get("used_memory", 0))
            gauge_set("redis_keys_count", info.get("db0", {}).get("keys", 0) if isinstance(info.get("db0"), dict) else 0)
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass
