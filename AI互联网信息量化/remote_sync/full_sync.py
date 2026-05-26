#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from api_client import IntelSyncClient

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PACKAGE_DIR / "sync_config.json"
LOG_DIR = PACKAGE_DIR / "logs"


def setup_logging(log_level: str = "INFO", log_dir: Path | None = None):
    if log_dir is None:
        log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"full_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    return log_file


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        example = config_path.parent / "sync_config.example.json"
        if example.exists():
            import shutil

            shutil.copy(example, config_path)
            print(f"[INFO] 已从模板创建 {config_path}，请配置环境变量 INTEL_SYNC_API_KEY")
        else:
            print(f"[ERROR] config file not found: {config_path}")
            print("[INFO] copy sync_config.example.json to sync_config.json")
            sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_credentials(config: dict, args) -> tuple[str, str]:
    base_url = args.base_url or os.environ.get("INTEL_SYNC_URL") or config.get("remote_host", "")
    raw_token = args.api_token or config.get("api_token", "") or ""
    if raw_token in ("", "REDACTED_INTEL_SYNC_KEY"):
        raw_token = ""
    api_token = raw_token or os.environ.get("INTEL_SYNC_API_KEY") or ""

    if not base_url:
        print("[ERROR] remote_host not set. Use --base-url or set INTEL_SYNC_URL env var")
        sys.exit(1)
    if not api_token:
        print("[ERROR] api_token not set. Use --api-token or set INTEL_SYNC_API_KEY env var")
        sys.exit(1)

    return base_url, api_token


def print_config(base_url: str, api_token: str):
    masked = api_token[:4] + "****" + api_token[-4:] if len(api_token) > 8 else "****"
    print(f"  Remote Host : {base_url}")
    print(f"  API Token   : {masked}")
    print()


def run_health_check(client: IntelSyncClient) -> bool:
    try:
        result = client.health_check()
        print(f"  Health Check: OK ({json.dumps(result, ensure_ascii=False)})")
        return True
    except Exception as e:
        print(f"  Health Check: FAILED ({e})")
        return False


def format_summary(summary: dict) -> None:
    print()
    print("=" * 60)
    print("  SYNC SUMMARY")
    print("=" * 60)
    print(f"  Time     : {summary.get('sync_time', 'N/A')}")
    print(f"  Duration : {summary.get('duration_seconds', 0):.1f}s")
    print(f"  Targets  : {summary.get('targets', 0)}")
    print(f"  Success  : {summary.get('success_count', 0)}")
    print()

    detail = summary.get("detail", {})
    if not detail:
        print("  No detail available")
        return

    print(f"  {'Target':<20} {'Status':<15} {'Total':>6} {'Created':>8} {'Updated':>8} {'Errors':>6}")
    print(f"  {'-'*20} {'-'*15} {'-'*6} {'-'*8} {'-'*8} {'-'*6}")

    total_all = created_all = updated_all = errors_all = 0
    for target_name, result in detail.items():
        status = result.get("status", "unknown")
        total_t = result.get("total", 0)
        created_t = result.get("created", 0)
        updated_t = result.get("updated", 0)
        errors_t = result.get("errors", 0)

        status_icon = {"success": "OK", "partial": "PARTIAL", "empty": "EMPTY", "error": "ERROR", "file_not_found": "NOFILE"}.get(status, status.upper())

        print(f"  {target_name:<20} {status_icon:<15} {total_t:>6} {created_t:>8} {updated_t:>8} {errors_t:>6}")

        total_all += total_t
        created_all += created_t
        updated_all += updated_t
        errors_all += errors_t

    print(f"  {'-'*20} {'-'*15} {'-'*6} {'-'*8} {'-'*8} {'-'*6}")
    print(f"  {'TOTAL':<20} {'':<15} {total_all:>6} {created_all:>8} {updated_all:>8} {errors_all:>6}")
    print()

    if errors_all == 0:
        print("  RESULT: All targets synced successfully!")
    else:
        print(f"  RESULT: Completed with {errors_all} errors across {total_all} items")
    print("=" * 60)


def _repo_root() -> Path:
    return PACKAGE_DIR.parent.parent


def _load_intel_production_config() -> dict:
    path = _repo_root() / "config" / "intel_production.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_output_root(config: dict, prod: dict) -> Path | None:
    ru = prod.get("report_upload") or config.get("report_upload") or {}
    if not ru.get("enabled", False):
        return None
    raw = ru.get("output_root", "AI互联网信息量化/AI内容工厂/output")
    root = Path(raw)
    if not root.is_absolute():
        root = _repo_root() / root
    return root if root.exists() else None


def run_scheduled_report_upload(client: IntelSyncClient, config: dict, prod: dict) -> list[dict]:
    log = logging.getLogger(__name__)
    output_root = _resolve_output_root(config, prod)
    if not output_root:
        log.info("[Scheduled] Report upload disabled or output dir missing")
        return []

    ru = prod.get("report_upload") or config.get("report_upload") or {}
    max_topics = int(ru.get("max_topics", 2))
    report_type = ru.get("report_type", "weekly")

    topic_dirs = sorted(
        [p for p in output_root.iterdir() if p.is_dir() and p.name.startswith("T")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:max_topics]

    all_results: list[dict] = []
    week_number = datetime.now().strftime("%Y-W%W")

    for topic_dir in topic_dirs:
        html_dir = topic_dir / "html"
        if not html_dir.is_dir():
            continue
        log.info(f"[Scheduled] Uploading reports from {html_dir}")
        print(f"[Scheduled] Reports: {topic_dir.name}")
        try:
            results = client.upload_reports_from_dir(
                reports_dir=html_dir,
                report_type=report_type,
                week_number=week_number,
            )
            all_results.extend(results)
        except Exception as e:
            log.error(f"[Scheduled] Report upload failed for {topic_dir.name}: {e}")
            print(f"  [ERR] {topic_dir.name}: {e}")

    ok = sum(1 for r in all_results if r.get("status") == "ok")
    err = sum(1 for r in all_results if r.get("status") == "error")
    print(f"[Scheduled] Reports uploaded: {ok} ok, {err} errors")
    return all_results


def run_dry_run(config: dict, base_url: str, api_token: str):
    print("[DRY RUN] Validating configuration and data files...")
    print()

    targets_config = config.get("targets", {})
    if not targets_config:
        targets_config = {t: True for t in ["trends", "signals", "opportunities", "risks", "emotions", "xhs_topics"]}

    from api_client import DB_DIR, TOPICS_DIR

    data_files = {
        "trends": DB_DIR / "trend_db.json",
        "signals": DB_DIR / "trend_db.json",
        "opportunities": DB_DIR / "opportunity_db.json",
        "risks": DB_DIR / "risk_db.json",
        "emotions": DB_DIR / "user_emotion_db.json",
        "xhs_topics": TOPICS_DIR,
    }

    data_keys = {
        "trends": "trends",
        "signals": "platform_signals",
        "opportunities": "opportunities",
        "risks": "eliminated",
        "emotions": "emotions",
        "xhs_topics": None,
    }

    total_items = 0
    all_ok = True

    for target_name, file_path in data_files.items():
        if not targets_config.get(target_name, True):
            print(f"  [{target_name}] SKIPPED (disabled in config)")
            continue

        exists = file_path.exists()
        icon = "OK" if exists else "MISSING"
        if not exists:
            all_ok = False

        if target_name == "xhs_topics" and exists:
            topic_files = list(file_path.glob("*.json"))
            count = len(topic_files)
            print(f"  [{target_name}] {icon} - {file_path} ({count} topic files)")
            total_items += count
        elif exists and file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data_key = data_keys.get(target_name, "")
            if data_key and data_key in data:
                if isinstance(data[data_key], list):
                    count = len(data[data_key])
                elif isinstance(data[data_key], dict):
                    count = len(data[data_key])
                else:
                    count = 1
            else:
                count = 1
            print(f"  [{target_name}] {icon} - {file_path} ({count} items)")
            total_items += count
        else:
            print(f"  [{target_name}] {icon} - {file_path}")

    print()
    print(f"  Total items to sync: {total_items}")
    print(f"  Remote host: {base_url}")

    if not all_ok:
        print()
        print("[DRY RUN] Some data files are missing. Fix before running actual sync.")
    else:
        print()
        print("[DRY RUN] Validation passed. Ready to sync.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="AI Intelligence OS - Remote Sync Client")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG), help="Path to sync_config.json")
    parser.add_argument("--base-url", type=str, default="", help="Remote host base URL (overrides config)")
    parser.add_argument("--api-token", type=str, default="", help="API token for authentication (overrides config)")
    parser.add_argument("--target", type=str, default="", help="Sync single target (trends|signals|opportunities|risks|emotions|xhs_topics)")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and data files without pushing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-health-check", action="store_true", help="Skip health check before sync")
    parser.add_argument("--upload-reports", type=str, default="", help="Upload report files from directory")
    parser.add_argument("--report-type", type=str, default="weekly", help="Report type for upload (weekly|monthly)")
    parser.add_argument("--week-number", type=str, default="", help="Week number for report upload")
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Scheduled run: full sync + optional report upload from production config",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PACKAGE_DIR / config_path

    config = load_config(config_path)

    log_config = config.get("logging", {})
    log_level = "DEBUG" if args.verbose else log_config.get("level", "INFO")
    log_dir = Path(log_config.get("log_dir", "logs"))
    if not log_dir.is_absolute():
        log_dir = PACKAGE_DIR / log_dir

    log_file = setup_logging(log_level, log_dir)
    logger = logging.getLogger(__name__)

    base_url, api_token = resolve_credentials(config, args)

    logger.info("=" * 60)
    logger.info("AI Intelligence OS - Remote Sync Client")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    print_config(base_url, api_token)

    if args.dry_run:
        run_dry_run(config, base_url, api_token)
        return

    client = IntelSyncClient(base_url, api_token)

    if not args.no_health_check:
        print("[Health Check]")
        if not run_health_check(client):
            logger.error("Health check failed. Aborting sync.")
            print()
            print("[ABORT] Health check failed. Check remote host connectivity and API token.")
            print("[TIP] Use --no-health-check to skip health check and force sync.")
            sys.exit(1)
        print()

    all_target_names = ["trends", "signals", "opportunities", "risks", "emotions", "xhs_topics"]
    if args.target:
        if args.target not in all_target_names:
            print(f"[ERROR] Unknown target: {args.target}. Choose from: {', '.join(all_target_names)}")
            sys.exit(1)
        targets_config = {name: (name == args.target) for name in all_target_names}
        logger.info(f"Single target sync: {args.target}")
    else:
        targets_config = config.get("targets", {})

    if args.upload_reports:
        print("[Reports] Uploading report files...")
        client = IntelSyncClient(base_url, api_token)
        try:
            results = client.upload_reports_from_dir(
                reports_dir=args.upload_reports,
                report_type=args.report_type,
                week_number=args.week_number or None,
            )
            ok_count = sum(1 for r in results if r["status"] == "ok")
            err_count = sum(1 for r in results if r["status"] == "error")
            print(f"  Uploaded: {ok_count} ok, {err_count} errors")
            for r in results:
                icon = "OK" if r["status"] == "ok" else "ERR"
                print(f"  [{icon}] {r['file']}")
        except Exception as e:
            logger.error(f"Report upload failed: {e}", exc_info=True)
            print(f"\n[FATAL] Report upload failed: {e}")
            sys.exit(1)
        return

    logger.info("Starting full sync...")
    print("[Sync] Starting...")
    start_time = time.time()
    prod_cfg = _load_intel_production_config() if args.scheduled else {}

    try:
        summary = client.sync_all(targets_config)

        elapsed = time.time() - start_time
        summary["duration_seconds"] = round(elapsed, 2)

        format_summary(summary)

        total_errors = sum(
            r.get("errors", 0) for r in summary.get("detail", {}).values()
        )

        if args.scheduled:
            print()
            print("[Scheduled] Post-sync report upload...")
            report_results = run_scheduled_report_upload(client, config, prod_cfg)
            report_errors = sum(1 for r in report_results if r.get("status") == "error")
            total_errors += report_errors

        logger.info(f"Sync complete. Duration: {elapsed:.1f}s, Errors: {total_errors}")
        logger.info(f"Full summary: {json.dumps(summary, ensure_ascii=False)}")

        if total_errors > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        print(f"\n[FATAL] Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()