"""Non-destructive preflight checks for the initial Alembic migration."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def reject_unversioned_schema_bootstrap(connection: Connection) -> None:
    """Refuse legacy schemas *before* Alembic creates its bookkeeping table.

    Alembic normally creates ``alembic_version`` before running the first revision.
    An initial migration can then reject pre-existing application tables, but that
    would already have modified the legacy store. This guard must run before
    ``context.run_migrations()`` so a rejected database is byte-for-byte unchanged.
    """
    existing_tables = set(inspect(connection).get_table_names())
    if not existing_tables:
        return

    if "alembic_version" not in existing_tables:
        raise RuntimeError(
            "Refusing Alembic bootstrap on an unversioned database with existing "
            f"tables: {sorted(existing_tables)}. Do not overwrite, relabel, or add "
            "metadata to a legacy fare series; use a separately reviewed migration."
        )

    revisions = [
        str(value)
        for value in connection.execute(text("SELECT version_num FROM alembic_version"))
        .scalars()
        .all()
    ]
    unexpected_tables = existing_tables - {"alembic_version"}
    if not revisions and unexpected_tables:
        raise RuntimeError(
            "Refusing Alembic bootstrap on an unversioned database with existing "
            f"tables: {sorted(unexpected_tables)}. Its empty alembic_version table "
            "may be residue from an earlier failed attempt; use a separately reviewed "
            "migration."
        )
