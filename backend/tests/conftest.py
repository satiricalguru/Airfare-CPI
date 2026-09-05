"""Shared test isolation for settings and persistent storage."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import reload_settings
from api.rate_limit import rate_limiter
from db.engine import set_database


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    """Never let an automated test read or mutate the developer's operational DB."""
    db_path = tmp_path / "airfare_cpi_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("DB_AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("COPILOT_API_KEY", "")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    set_database(None)
    rate_limiter.reset()
    reload_settings()

    yield

    set_database(None)
    rate_limiter.reset()
    reload_settings()
