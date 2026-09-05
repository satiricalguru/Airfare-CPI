"""Regression tests for the non-destructive Alembic bootstrap guard."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.migration_guard import reject_unversioned_schema_bootstrap
from config import reload_settings


def test_unversioned_legacy_database_is_rejected_without_alembic_writes(tmp_path):
    """Never add Alembic metadata to a legacy store merely while rejecting it."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE legacy_fares (id INTEGER PRIMARY KEY)"))

            with pytest.raises(RuntimeError, match="unversioned database"):
                reject_unversioned_schema_bootstrap(connection)

            assert inspect(connection).get_table_names() == ["legacy_fares"]
    finally:
        engine.dispose()


def test_clean_migration_persists_its_revision_marker(tmp_path, monkeypatch):
    """A newly created schema must satisfy the API's Alembic startup gate."""
    database_path = tmp_path / "managed.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    reload_settings()

    alembic_config = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert revision == "20260903_0003"
    finally:
        engine.dispose()
