"""Create the clean, provenance-aware Airfare CPI schema.

Revision ID: 20260903_0001
Revises:
Create Date: 2026-09-03

This is deliberately a *clean-database* initial migration. It refuses a legacy
schema rather than guessing how to transform contaminated historical observations.
That transformation requires a separately reviewed, evidence-preserving migration.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from db.models import Base


revision = "20260903_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    unexpected = existing - {"alembic_version"}
    if unexpected:
        raise RuntimeError(
            "Initial migration only supports a clean database. Found existing "
            f"tables: {sorted(unexpected)}. Do not overwrite or relabel a legacy "
            "series; use a separately reviewed migration."
        )
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    raise RuntimeError(
        "Destructive schema downgrade is intentionally disabled. Restore a tested "
        "database backup instead."
    )
