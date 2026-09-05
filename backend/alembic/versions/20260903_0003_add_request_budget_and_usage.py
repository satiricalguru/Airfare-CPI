"""Add request_budgets and request_usages tables for free quota and governance.

Revision ID: 20260903_0003
Revises: 20260903_0002
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260903_0003"
down_revision = "20260903_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "request_budgets" not in tables:
        op.create_table(
            "request_budgets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_id", sa.String(length=64), nullable=False),
            sa.Column("period_type", sa.String(length=16), nullable=False),
            sa.Column("limit_count", sa.Integer(), nullable=False),
            sa.Column("warning_threshold_pct", sa.Float(), nullable=False, server_default="80.0"),
            sa.Column("reduced_basket_threshold_pct", sa.Float(), nullable=False, server_default="95.0"),
            sa.Column("is_hard_stop", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source_id", "period_type", name="uq_request_budget_source_period"),
        )
        op.create_index("ix_budget_source", "request_budgets", ["source_id"])

    if "request_usages" not in tables:
        op.create_table(
            "request_usages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_id", sa.String(length=64), nullable=False),
            sa.Column("period_type", sa.String(length=16), nullable=False),
            sa.Column("period_key", sa.String(length=32), nullable=False),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("successful_requests", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_requests", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("source_id", "period_type", "period_key", name="uq_request_usage_period"),
        )
        op.create_index("ix_usage_source_key", "request_usages", ["source_id", "period_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "request_usages" in tables:
        op.drop_table("request_usages")
    if "request_budgets" in tables:
        op.drop_table("request_budgets")
