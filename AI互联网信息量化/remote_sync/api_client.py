import hashlib
import json
import logging
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BATCH_MAX_SIZE = 50
DB_DIR = Path(__file__).resolve().parent.parent / "商业情报中转站" / "database"
TOPICS_DIR = Path(__file__).resolve().parent.parent / "商业情报中转站" / "topics"

SYNC_TARGETS = [
    {
        "file": "trend_db.json",
        "endpoint": "trends",
        "key_field": "title",
        "data_key": "trends",
        "field_map": {
            "trend_name": "title",
        },
        "drop_fields": ["id"],
    },
    {
        "file": "trend_db.json",
        "endpoint": "signals",
        "key_field": "platform",
        "data_key": "platform_signals",
    },
    {
        "file": "opportunity_db.json",
        "endpoint": "opportunities",
        "key_field": "name",
        "data_key": "opportunities",
        "drop_fields": ["id"],
    },
    {
        "file": "risk_db.json",
        "endpoint": "risks",
        "key_field": "name",
        "data_key": "eliminated",
        "drop_fields": ["id"],
    },
    {
        "file": "user_emotion_db.json",
        "endpoint": "emotions",
        "key_field": "keyword",
        "data_key": "emotions",
        "drop_fields": ["id", "first_observed", "related_opportunities", "persona_affected", "insight"],
    },
    {
        "file": "topics",
        "endpoint": "topics",
        "key_field": "title",
        "data_key": "topics",
        "is_directory": True,
        "field_map": {
            "topic_name": "title",
            "topic_id": "source_topic_id",
        },
        "drop_fields": ["id"],
    },
]


class IntelSyncClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self._api_token = api_token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "X-Sync-Source": "local_workstation",
            },
            timeout=60,
        )

    def _generate_batch_id(self) -> str:
        ts = int(time.time() * 1000)
        rand = secrets.token_hex(4)
        return f"SYNC-{ts}-{rand}"

    def _apply_field_map(self, item: dict, field_map: dict | None) -> dict:
        if not field_map:
            return item
        result = {}
        for k, v in item.items():
            mapped_key = field_map.get(k, k)
            result[mapped_key] = v
        return result

    def _process_emotion_item(self, item: dict) -> dict:
        result = dict(item)
        if "keyword" not in result:
            cluster = item.get("keyword_cluster", [])
            if isinstance(cluster, list) and cluster:
                result["keyword"] = cluster[0]
            elif item.get("id"):
                result["keyword"] = item["id"]
            else:
                result["keyword"] = item.get("emotion_type", "unknown")
        return result

    def _load_json(self, filename: str) -> dict:
        filepath = DB_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _read_items(self, data: dict, data_key: str) -> list[dict]:
        if data_key in data:
            if isinstance(data[data_key], list):
                return data[data_key]
            elif isinstance(data[data_key], dict):
                return [{"platform": k, **v} for k, v in data[data_key].items()]
        if isinstance(data, list):
            return data
        return []

    def _load_risk_items(self) -> list[dict]:
        data = self._load_json("risk_db.json")
        items: list[dict] = []
        severity_map = {"dead": "high", "dying": "medium", "monitoring": "medium", "escalating": "high"}

        for entry in data.get("eliminated", []):
            items.append({
                "name": entry["name"],
                "category": entry.get("category"),
                "severity": severity_map.get(entry.get("status"), "high"),
                "status": entry.get("status") or "dead",
                "reason": entry.get("reason"),
                "alternative": entry.get("alternative"),
                "risk_type": "eliminated",
                "source": entry.get("source"),
            })

        for warn in data.get("warnings", []):
            signals = warn.get("early_signals") or []
            items.append({
                "name": warn["name"],
                "category": warn.get("category"),
                "severity": severity_map.get(warn.get("status"), "medium"),
                "status": warn.get("status") or "monitoring",
                "reason": warn.get("risk_description"),
                "alternative": warn.get("recommended_action"),
                "risk_type": "warning",
                "risk_description": warn.get("risk_description"),
                "recommended_action": warn.get("recommended_action"),
                "early_signals": signals if isinstance(signals, list) else [signals],
            })

        return items

    def _load_topic_files(self) -> list[dict]:
        if not TOPICS_DIR.exists():
            raise FileNotFoundError(f"Topics directory not found: {TOPICS_DIR}")

        topic_files = sorted(TOPICS_DIR.glob("*.json"))
        if not topic_files:
            logger.warning(f"[Sync] no topic files found in {TOPICS_DIR}")
            return []

        items = []
        for filepath in topic_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items.append(data)
            except Exception as e:
                logger.warning(f"[Sync] failed to load {filepath.name}: {e}")

        logger.info(f"[Sync] loaded {len(items)} topic files from {TOPICS_DIR}")
        return items

    def _process_topic_item(self, item: dict) -> dict:
        result = dict(item)
        if "title" not in result:
            result["title"] = item.get("topic_name", "")
        result["source_topic_id"] = item.get("topic_id", "")
        target_platform = item.get("target_platform", [])
        if isinstance(target_platform, list):
            result["platform"] = ", ".join(target_platform)
        result["topic_data"] = dict(item)
        return result

    def _transform(self, items: list[dict], target: dict) -> list[dict]:
        field_map = target.get("field_map")
        drop_fields = target.get("drop_fields", [])
        if field_map:
            items = [self._apply_field_map(item, field_map) for item in items]
        if drop_fields:
            items = [{k: v for k, v in item.items() if k not in drop_fields} for item in items]
        if target["endpoint"] == "emotions":
            items = [self._process_emotion_item(item) for item in items]
        if target["endpoint"] == "topics":
            items = [self._process_topic_item(item) for item in items]
        return items

    def sync_target(self, target: dict) -> dict:
        file_name = target["file"]
        endpoint = target["endpoint"]
        key_field = target["key_field"]
        data_key = target["data_key"]
        is_directory = target.get("is_directory", False)

        logger.info(f"[Sync] loading {file_name} -> {endpoint} (key={key_field})")

        if endpoint == "risks":
            items = self._load_risk_items()
        elif is_directory:
            items = self._load_topic_files()
        else:
            data = self._load_json(file_name)
            items = self._read_items(data, data_key)

        if not items:
            logger.warning(f"[Sync] no items found in {file_name}:{data_key}")
            return {"target": endpoint, "status": "empty", "total": 0}

        items = self._transform(items, target)

        all_results = []
        total_created = total_updated = total_skipped = total_errors = 0

        for i in range(0, len(items), BATCH_MAX_SIZE):
            batch = items[i:i + BATCH_MAX_SIZE]
            batch_id = self._generate_batch_id()

            try:
                response = self.client.post(
                    f"/api/v1/intel/sync/{endpoint}",
                    json={
                        "sync_batch_id": batch_id,
                        "key_field": key_field,
                        "items": batch,
                    },
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "duplicate":
                    logger.info(f"[Sync] batch {batch_id} already processed, skipping")
                    continue

                summary = result.get("summary", {})
                total_created += summary.get("created", 0)
                total_updated += summary.get("updated", 0)
                total_skipped += summary.get("skipped", 0)
                total_errors += summary.get("errors", 0)

                all_results.append({
                    "batch_id": batch_id,
                    "summary": summary,
                })

                logger.info(
                    f"[Sync] {endpoint} batch {batch_id}: "
                    f"created={summary.get('created')} updated={summary.get('updated')} "
                    f"skipped={summary.get('skipped')} errors={summary.get('errors')}"
                )

            except httpx.HTTPStatusError as e:
                logger.error(f"[Sync] {endpoint} HTTP error: {e.response.status_code} {e.response.text[:200]}")
                total_errors += len(batch)
            except Exception as e:
                logger.error(f"[Sync] {endpoint} error: {e}", exc_info=True)
                total_errors += len(batch)

        return {
            "target": endpoint,
            "status": "success" if total_errors == 0 else "partial",
            "total": len(items),
            "created": total_created,
            "updated": total_updated,
            "skipped": total_skipped,
            "errors": total_errors,
        }

    def sync_all(self, targets_config: dict | None = None) -> dict[str, Any]:
        logger.info("[Sync] starting full sync")
        start_time = time.time()
        results = {}

        for target in SYNC_TARGETS:
            endpoint = target["endpoint"]
            if targets_config is not None:
                if not targets_config.get(endpoint, True):
                    logger.info(f"[Sync] skipping {endpoint} (disabled in config)")
                    continue

            try:
                results[endpoint] = self.sync_target(target)
            except FileNotFoundError as e:
                logger.warning(f"[Sync] {e}")
                results[endpoint] = {"status": "file_not_found", "error": str(e)}
            except Exception as e:
                logger.error(f"[Sync] unexpected error in {endpoint}: {e}", exc_info=True)
                results[endpoint] = {"status": "error", "error": str(e)}

        elapsed = time.time() - start_time

        summary = {
            "sync_time": datetime.now().isoformat(),
            "duration_seconds": round(elapsed, 2),
            "targets": len(results),
            "success_count": sum(1 for r in results.values() if r.get("status") in ("success", "partial")),
            "detail": results,
        }

        total_items = sum(r.get("total", 0) for r in results.values())
        total_errors = sum(r.get("errors", 0) for r in results.values())

        logger.info(
            f"[Sync] complete. {total_items} items across {len(results)} targets. "
            f"errors={total_errors} duration={elapsed:.1f}s"
        )

        return summary

    def upload_report(
        self,
        file_path: str | Path,
        report_type: str = "weekly",
        title: str | None = None,
        week_number: str | None = None,
        report_date: str | None = None,
    ) -> dict:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Report file not found: {file_path}")

        if not title:
            title = file_path.stem
        if not report_date:
            report_date = datetime.now().strftime("%Y-%m-%d")

        with open(file_path, "rb") as f:
            upload_client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "X-Sync-Source": "local_workstation",
                },
                timeout=120,
            )
            try:
                response = upload_client.post(
                    "/api/v1/intel/reports/upload",
                    files={"file": (file_path.name, f)},
                    data={
                        "report_type": report_type,
                        "title": title,
                        "week_number": week_number or "",
                        "report_date": report_date,
                    },
                )
                response.raise_for_status()
            finally:
                upload_client.close()

        result = response.json()
        logger.info(f"[Sync] Report uploaded: {file_path.name} -> {result.get('url', 'N/A')}")
        return result

    def upload_reports_from_dir(
        self,
        reports_dir: str | Path,
        report_type: str = "weekly",
        week_number: str | None = None,
    ) -> list[dict]:
        reports_dir = Path(reports_dir)
        if not reports_dir.exists():
            raise FileNotFoundError(f"Reports directory not found: {reports_dir}")

        topic_id = ""
        parent = reports_dir.parent
        if parent.name.startswith("T") and len(parent.name) >= 10:
            topic_id = parent.name

        results = []
        for fp in sorted(reports_dir.glob("*.html")):
            try:
                rtype = report_type
                title = fp.stem
                wk = week_number
                if topic_id:
                    rtype = "topic"
                    title = f"{topic_id} · 副业决策报告"
                    wk = None
                result = self.upload_report(
                    file_path=fp,
                    report_type=rtype,
                    title=title,
                    week_number=wk,
                )
                results.append({"file": fp.name, "status": "ok", "result": result})
            except Exception as e:
                logger.error(f"[Sync] Failed to upload report {fp.name}: {e}")
                results.append({"file": fp.name, "status": "error", "error": str(e)})

        for fp in sorted(reports_dir.glob("*.pdf")):
            try:
                rtype = report_type
                title = fp.stem
                wk = week_number
                if topic_id:
                    rtype = "topic"
                    title = f"{topic_id} · 副业决策报告"
                    wk = None
                result = self.upload_report(
                    file_path=fp,
                    report_type=rtype,
                    title=title,
                    week_number=wk,
                )
                results.append({"file": fp.name, "status": "ok", "result": result})
            except Exception as e:
                logger.error(f"[Sync] Failed to upload report {fp.name}: {e}")
                results.append({"file": fp.name, "status": "error", "error": str(e)})

        logger.info(f"[Sync] Reports upload complete: {len(results)} files processed")
        return results

    def health_check(self) -> dict:
        resp = self.client.get("/api/v1/health")
        resp.raise_for_status()
        return resp.json()


def run_sync(base_url: str, api_token: str) -> dict:
    return IntelSyncClient(base_url, api_token).sync_all()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    base_url = os.environ.get("INTEL_SYNC_URL", "")
    api_token = os.environ.get("INTEL_SYNC_API_KEY", "")

    if not base_url or not api_token:
        print("Usage: set INTEL_SYNC_URL and INTEL_SYNC_API_KEY env vars")
        sys.exit(1)

    result = run_sync(base_url, api_token)
    print(json.dumps(result, ensure_ascii=False, indent=2))