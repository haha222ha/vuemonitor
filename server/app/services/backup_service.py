import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

_BACKUP_DIR = "data/backups"
_RETENTION_DAYS = 30


class BackupService:
    def __init__(self):
        self._backup_dir = Path(_BACKUP_DIR)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self, label: str | None = None) -> dict:
        settings = get_settings()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{label or 'auto'}_{timestamp}"
        backup_path = self._backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        db_url = settings.DATABASE_URL
        if "postgresql" in db_url or "postgres" in db_url:
            result = await self._backup_postgresql(backup_path)
        else:
            result = await self._backup_sqlite(backup_path)

        redis_result = await self._backup_redis(backup_path)

        metadata = {
            "backup_name": backup_name,
            "timestamp": timestamp,
            "database": result,
            "redis": redis_result,
            "label": label,
        }

        metadata_path = backup_path / "metadata.json"
        import json
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Backup created: {backup_name}")
        return metadata

    async def _backup_postgresql(self, backup_path: Path) -> dict:
        settings = get_settings()
        db_url = settings.DATABASE_URL
        dump_file = backup_path / "database.dump"

        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DB_PASSWORD if hasattr(settings, "DB_PASSWORD") else ""

        cmd = (
            f"pg_dump --no-owner --no-acl --format=custom "
            f"--host={settings.DB_HOST if hasattr(settings, 'DB_HOST') else 'localhost'} "
            f"--port={settings.DB_PORT if hasattr(settings, 'DB_PORT') else 5432} "
            f"--username={settings.DB_USER if hasattr(settings, 'DB_USER') else 'postgres'} "
            f"--dbname={settings.DB_NAME if hasattr(settings, 'DB_NAME') else 'vuemonitor'} "
            f"--file={dump_file}"
        )

        proc = await asyncio.create_subprocess_shell(
            cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"PostgreSQL backup failed: {stderr.decode()}")
            return {"status": "failed", "error": stderr.decode()}

        size = dump_file.stat().st_size if dump_file.exists() else 0
        return {"status": "success", "file": str(dump_file), "size_bytes": size}

    async def _backup_sqlite(self, backup_path: Path) -> dict:
        db_file = backup_path / "database.sqlite"
        settings = get_settings()
        source = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

        if source and os.path.exists(source):
            shutil.copy2(source, str(db_file))
            size = db_file.stat().st_size
            return {"status": "success", "file": str(db_file), "size_bytes": size}

        return {"status": "skipped", "reason": "no sqlite file found"}

    async def _backup_redis(self, backup_path: Path) -> dict:
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            await redis.bgrewriteaof()
            return {"status": "triggered_save"}
        except Exception as e:
            return {"status": "skipped", "reason": str(e)}

    async def restore_backup(self, backup_name: str) -> dict:
        backup_path = self._backup_dir / backup_name
        if not backup_path.exists():
            return {"status": "error", "message": f"Backup not found: {backup_name}"}

        dump_file = backup_path / "database.dump"
        if not dump_file.exists():
            return {"status": "error", "message": "Database dump not found in backup"}

        settings = get_settings()
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DB_PASSWORD if hasattr(settings, "DB_PASSWORD") else ""

        cmd = (
            f"pg_restore --clean --if-exists --no-owner --no-acl "
            f"--host={settings.DB_HOST if hasattr(settings, 'DB_HOST') else 'localhost'} "
            f"--port={settings.DB_PORT if hasattr(settings, 'DB_PORT') else 5432} "
            f"--username={settings.DB_USER if hasattr(settings, 'DB_USER') else 'postgres'} "
            f"--dbname={settings.DB_NAME if hasattr(settings, 'DB_NAME') else 'vuemonitor'} "
            f"{dump_file}"
        )

        proc = await asyncio.create_subprocess_shell(
            cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {"status": "failed", "error": stderr.decode()}

        return {"status": "success", "backup_name": backup_name}

    async def list_backups(self) -> list[dict]:
        backups = []
        import json

        for d in sorted(self._backup_dir.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            meta_file = d / "metadata.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    backups.append(json.load(f))
            else:
                backups.append({"backup_name": d.name, "label": "unknown"})

        return backups

    async def cleanup_old_backups(self, retention_days: int = _RETENTION_DAYS) -> int:
        import json
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        removed = 0

        for d in self._backup_dir.iterdir():
            if not d.is_dir():
                continue

            meta_file = d / "metadata.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    meta = json.load(f)
                ts_str = meta.get("timestamp", "")
                if ts_str:
                    try:
                        ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
                        if ts < cutoff:
                            shutil.rmtree(str(d))
                            removed += 1
                    except ValueError:
                        pass

        logger.info(f"Cleaned up {removed} old backups (retention={retention_days}d)")
        return removed


backup_service = BackupService()
