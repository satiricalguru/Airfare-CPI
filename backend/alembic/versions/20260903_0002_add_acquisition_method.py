"""Add acquisition_method to observations, runs, indices, and anomalies.

Revision ID: 20260903_0002
Revises: 20260903_0001
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260903_0002"
down_revision = "20260903_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. collection_runs
    cr_cols = {c["name"] for c in inspector.get_columns("collection_runs")}
    if "acquisition_method" not in cr_cols:
        with op.batch_alter_table("collection_runs", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )
            batch_op.create_index(
                "ix_collection_runs_acq_method", ["acquisition_method"], unique=False
            )

    # 2. fare_observations
    fo_cols = {c["name"] for c in inspector.get_columns("fare_observations")}
    if "acquisition_method" not in fo_cols:
        with op.batch_alter_table("fare_observations", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )
            batch_op.create_index(
                "ix_fare_obs_acq_method", ["acquisition_method"], unique=False
            )

    # 3. normalized_fares
    nf_cols = {c["name"] for c in inspector.get_columns("normalized_fares")}
    if "acquisition_method" not in nf_cols:
        with op.batch_alter_table("normalized_fares", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )

    # 4. horizon_indices
    hi_cols = {c["name"] for c in inspector.get_columns("horizon_indices")}
    if "acquisition_method" not in hi_cols:
        with op.batch_alter_table("horizon_indices", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )
            try:
                batch_op.drop_constraint("uq_horizon_index", type_="unique")
            except Exception:
                pass
            batch_op.create_unique_constraint(
                "uq_horizon_index",
                [
                    "route_id",
                    "booking_horizon",
                    "index_date",
                    "source_type",
                    "acquisition_method",
                    "methodology_version",
                ],
            )

    # 5. route_indices
    ri_cols = {c["name"] for c in inspector.get_columns("route_indices")}
    if "acquisition_method" not in ri_cols:
        with op.batch_alter_table("route_indices", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )
            try:
                batch_op.drop_constraint("uq_route_index", type_="unique")
            except Exception:
                pass
            batch_op.create_unique_constraint(
                "uq_route_index",
                [
                    "route_id",
                    "index_date",
                    "source_type",
                    "acquisition_method",
                    "methodology_version",
                ],
            )

    # 6. national_indices
    ni_cols = {c["name"] for c in inspector.get_columns("national_indices")}
    if "acquisition_method" not in ni_cols:
        with op.batch_alter_table("national_indices", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )
            try:
                batch_op.drop_constraint("uq_national_index", type_="unique")
            except Exception:
                pass
            batch_op.create_unique_constraint(
                "uq_national_index",
                [
                    "index_date",
                    "booking_horizon",
                    "source_type",
                    "acquisition_method",
                    "methodology_version",
                ],
            )

    # 7. anomalies
    an_cols = {c["name"] for c in inspector.get_columns("anomalies")}
    if "acquisition_method" not in an_cols:
        with op.batch_alter_table("anomalies", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "acquisition_method",
                    sa.String(length=32),
                    server_default="WEB_SCRAPE",
                    nullable=False,
                )
            )


def downgrade() -> None:
    raise RuntimeError(
        "Destructive schema downgrade is intentionally disabled. Restore a tested "
        "database backup instead."
    )
