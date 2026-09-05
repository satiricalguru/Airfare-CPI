"""Alembic environment for the async SQLAlchemy database URL used by the API."""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.models import Base  # noqa: E402
from db.migration_guard import reject_unversioned_schema_bootstrap  # noqa: E402
from config import get_settings  # noqa: E402


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Docker and local use the exact same URL as the API, including values read from
# the project's .env. Do not put credentials in alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().database.url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a database connection when `--sql` is requested."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # `begin()` is required here: SQLite persists DDL without implicitly committing
    # Alembic's INSERT into `alembic_version`. A plain connection created all ORM
    # tables but rolled that revision marker back on close, making a fresh API fail
    # its own startup revision check.
    async with connectable.begin() as connection:
        # This must happen before Alembic creates `alembic_version`; otherwise a
        # rejected legacy database would still be modified by its bookkeeping.
        await connection.run_sync(reject_unversioned_schema_bootstrap)
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
