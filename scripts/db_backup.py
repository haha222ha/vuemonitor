"""Database backup and restore utilities.

Usage:
    python scripts/db_backup.py backup
    python scripts/db_backup.py restore <backup_file>
    python scripts/db_backup.py list
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/backups"))
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "vuemonitor")
DB_USER = os.environ.get("DB_USER", "saas_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = BACKUP_DIR / f"vuemonitor_{timestamp}.dump"

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "pg_dump",
        "-Fc",
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", DB_NAME,
        "-f", str(filepath),
    ]

    print(f"Backing up to {filepath}...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = filepath.stat().st_size / 1024 / 1024
        print(f"[OK] Backup created: {filepath.name} ({size_mb:.1f} MB)")
        cleanup_old_backups()
    else:
        print(f"[FAIL] Backup failed: {result.stderr}")
        sys.exit(1)


def restore(backup_file: str):
    filepath = Path(backup_file)
    if not filepath.exists():
        filepath = BACKUP_DIR / backup_file
    if not filepath.exists():
        print(f"[FAIL] File not found: {backup_file}")
        sys.exit(1)

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "pg_restore",
        "-Fc",
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", DB_NAME,
        "--no-owner",
        "--no-privileges",
        str(filepath),
    ]

    print(f"Restoring from {filepath}...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode == 0:
        print("[OK] Restore completed")
    else:
        print(f"[WARN] Restore completed with warnings: {result.stderr[:200]}")


def list_backups():
    if not BACKUP_DIR.exists():
        print("No backups directory found")
        return

    backups = sorted(BACKUP_DIR.glob("vuemonitor_*.dump"), reverse=True)
    if not backups:
        print("No backups found")
        return

    print(f"{'File':<40} {'Size':>10}")
    print("-" * 52)
    for b in backups:
        size_mb = b.stat().st_size / 1024 / 1024
        print(f"{b.name:<40} {size_mb:>8.1f} MB")


def cleanup_old_backups(keep_days: int = 7):
    if not BACKUP_DIR.exists():
        return
    now = datetime.now().timestamp()
    count = 0
    for f in BACKUP_DIR.glob("vuemonitor_*.dump"):
        age_days = (now - f.stat().st_mtime) / 86400
        if age_days > keep_days:
            f.unlink()
            count += 1
    if count:
        print(f"Cleaned {count} backups older than {keep_days} days")


COMMANDS = {
    "backup": lambda: backup(),
    "restore": lambda: restore(sys.argv[2]) if len(sys.argv) > 2 else print("Usage: db_backup.py restore <file>"),
    "list": lambda: list_backups(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python scripts/db_backup.py <{'|'.join(COMMANDS.keys())}>")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
