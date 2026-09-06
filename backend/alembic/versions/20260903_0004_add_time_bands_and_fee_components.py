"""Add departure time, time bands, and fee components (UDF, convenience fee).

Revision ID: 20260903_0004
Revises: 20260903_0003
Create Date: 2026-09-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260903_0004"
down_revision = "20260903_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. fare_observations
    fo_cols = {c["name"] for c in inspector.get_columns("fare_observations")}
    with op.batch_alter_table("fare_observations", schema=None) as batch_op:
        if "dep_time" not in fo_cols:
            batch_op.add_column(sa.Column("dep_time", sa.String(length=16), nullable=True))
        if "dep_time_band" not in fo_cols:
            batch_op.add_column(sa.Column("dep_time_band", sa.String(length=20), nullable=True))
        if "fare_udf" not in fo_cols:
            batch_op.add_column(sa.Column("fare_udf", sa.Numeric(12, 2), nullable=True))
        if "fare_convenience" not in fo_cols:
            batch_op.add_column(sa.Column("fare_convenience", sa.Numeric(12, 2), nullable=True))

    # 2. normalized_fares
    nf_cols = {c["name"] for c in inspector.get_columns("normalized_fares")}
    with op.batch_alter_table("normalized_fares", schema=None) as batch_op:
        if "dep_time_band" not in nf_cols:
            batch_op.add_column(sa.Column("dep_time_band", sa.String(length=20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fo_cols = {c["name"] for c in inspector.get_columns("fare_observations")}
    with op.batch_alter_table("fare_observations", schema=None) as batch_op:
        if "fare_convenience" in fo_cols:
            batch_op.drop_column("fare_convenience")
        if "fare_udf" in fo_cols:
            batch_op.drop_column("fare_udf")
        if "dep_time_band" in fo_cols:
            batch_op.drop_column("dep_time_band")
        if "dep_time" in fo_cols:
            batch_op.drop_column("dep_time")

    nf_cols = {c["name"] for c in inspector.get_columns("normalized_fares")}
    with op.batch_alter_table("normalized_fares", schema=None) as batch_op:
        if "dep_time_band" in nf_cols:
            batch_op.drop_column("dep_time_band")
