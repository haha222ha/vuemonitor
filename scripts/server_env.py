"""Load server/.env and cwd for standalone scripts (same as systemd WorkingDirectory)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "server"


def bootstrap() -> Path:
    """Call before importing app.* so pydantic reads server/.env."""
    os.chdir(SERVER)
    sys.path.insert(0, str(SERVER))
    os.environ.setdefault("PYTHONPATH", str(SERVER))
    return SERVER
