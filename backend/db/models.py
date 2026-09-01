"""
SIH26056 — Database schema.

Every table needed to make a published index figure reproducible. The audit's finding
Q1 was that storage was in-process Python lists, so a restart discarded everything and
regenerated it: a price index that cannot reproduce a published figure after a restart
is not auditable, and auditability is the entire point of official statistics.

Reproducibility contract
------------------------
For any published index value, the schema records:

* **which observations** — ``national_indices`` -> ``route_indices`` ->
  ``horizon_indices`` -> ``normalized_fares`` -> ``fare_observations``, with
  ``matched_product_keys`` naming the exact products compared;
* **which calculation version** — ``methodology_version`` on every index row;
* **which weights** — ``route_weights``, versioned by basket and effective date;
* **which base period** — ``base_period_start`` / ``base_period_end`` on every row;
* **which source** — provenance columns on every observation, plus ``sources`` and
  ``collection_runs``;
* **which validation rules** — ``validation_results`` plus ``rules_version``;
* **which timestamp** — ``collection_timestamp`` and ``computed_at``.

Portability: types are chosen to work on both PostgreSQL and SQLite. JSON is used for
nested audit detail via SQLAlchemy's dialect-neutral ``JSON`` type; monetary values use
``Numeric(12, 2)``, and floats are reserved for index levels where fractional
precision beyond 2dp matters.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ── reference data ──

class Source(Base):
    """
    A fare source, including ones assessed and NOT used.

    Disabled sources are persisted deliberately: the record of why a source is not
    scraped is part of the audit trail, not an omission.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 'live' | 'simulated' | 'offline'
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    requires_credentials: Mapped[bool] = mapped_column(Boolean, default=False)
    homepage: Mapped[str | None] = mapped_column(String(500))
    terms_url: Mapped[str | None] = mapped_column(String(500))
    robots_url: Mapped[str | None] = mapped_column(String(500))
    compliance_note: Mapped[str | None] = mapped_column(Text)
    native_currency: Mapped[str] = mapped_column(String(3), default="INR")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RouteWeightRecord(Base):
    """
    Versioned route weights.

    Weights are DERIVED from the basket file, then snapshotted here per basket version
    so a historical index can be recomputed with the weights that were actually in
    force. ``weighting_status`` carries the PROVISIONAL label through to storage.
    """

    __tablename__ = "route_weights"
    __table_args__ = (
        UniqueConstraint("basket_version", "route_id", name="uq_route_weight_version"),
        Index("ix_route_weights_effective", "effective_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    basket_id: Mapped[str] = mapped_column(String(64), nullable=False)
    basket_version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_code: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_code: Mapped[str] = mapped_column(String(3), nullable=False)
    origin_city: Mapped[str | None] = mapped_column(String(100))
    destination_city: Mapped[str | None] = mapped_column(String(100))
    monthly_pax: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    weighting_method: Mapped[str] = mapped_column(String(64), nullable=False)
    weighting_status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_official_expenditure_weight: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── collection ──

class CollectionRun(Base):
    """
    One collection cycle.

    ``status`` is stored verbatim from :class:`provenance.CollectionStatus`, so a
    failed LIVE run remains a failed run in the record forever. It is never rewritten
    to success, and no observations are attached to it.
    """

    __tablename__ = "collection_runs"
    __table_args__ = (
        Index("ix_collection_runs_day", "collection_day"),
        Index("ix_collection_runs_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # 'LIVE' | 'SIMULATED' | 'OFFLINE'
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    display_label: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_day: Mapped[date] = mapped_column(Date, nullable=False)

    routes_requested: Mapped[int] = mapped_column(Integer, default=0)
    routes_with_data: Mapped[int] = mapped_column(Integer, default=0)
    horizons_requested: Mapped[dict] = mapped_column(JSON, default=list)
    observations_collected: Mapped[int] = mapped_column(Integer, default=0)
    observations_accepted: Mapped[int] = mapped_column(Integer, default=0)
    observations_flagged: Mapped[int] = mapped_column(Integer, default=0)
    observations_excluded: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text)
    collector_version: Mapped[str] = mapped_column(String(32), nullable=False)
    # Per-source, per-route attempt records and skipped-source reasons.
    attempts: Mapped[dict] = mapped_column(JSON, default=list)
    skipped_sources: Mapped[dict] = mapped_column(JSON, default=list)
    dedupe_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    triggered_by: Mapped[str] = mapped_column(String(32), default="manual")

    observations: Mapped[list["FareObservationRecord"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class FareObservationRecord(Base):
    """
    A fare quote AS COLLECTED, with full provenance.

    Retains the source's own currency and amount alongside the canonical INR value so
    a conversion can be re-checked. ``raw_payload_hash`` allows verifying a stored
    observation against an archived payload without storing the payload itself.
    """

    __tablename__ = "fare_observations"
    __table_args__ = (
        Index("ix_fare_obs_route_day", "route_id", "collection_date"),
        Index("ix_fare_obs_horizon", "route_id", "booking_horizon_days", "collection_date"),
        Index("ix_fare_obs_product", "product_key_hash"),
        Index("ix_fare_obs_dedupe", "dedupe_fingerprint"),
        Index("ix_fare_obs_source_type", "source_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False
    )

    # ── routing ──
    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_code: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_code: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    booking_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── product ──
    airline_code: Mapped[str] = mapped_column(String(3), nullable=False)
    airline_name: Mapped[str | None] = mapped_column(String(100))
    flight_number: Mapped[str | None] = mapped_column(String(16))
    cabin_class: Mapped[str] = mapped_column(String(20), nullable=False)
    fare_family: Mapped[str | None] = mapped_column(String(64))
    stops: Mapped[int] = mapped_column(Integer, default=0)
    is_refundable: Mapped[bool | None] = mapped_column(Boolean)
    baggage_kg: Mapped[int | None] = mapped_column(Integer)
    seats_available: Mapped[int | None] = mapped_column(Integer)

    # ── price, canonical INR ──
    fare_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fare_base: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fare_taxes: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # ── price as the source gave it ──
    source_currency: Mapped[str | None] = mapped_column(String(3))
    source_fare_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    source_offer_id: Mapped[str | None] = mapped_column(String(128))

    # ── provenance (mandatory) ──
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collector_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64))
    provenance_notes: Mapped[dict] = mapped_column(JSON, default=dict)

    # ── identity ──
    product_key: Mapped[str] = mapped_column(String(300), nullable=False)
    product_key_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    dedupe_fingerprint: Mapped[str] = mapped_column(String(32), nullable=False)

    # ── validation outcome ──
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_action: Mapped[str] = mapped_column(String(16), default="accepted")
    validation_flags: Mapped[dict] = mapped_column(JSON, default=list)

    run: Mapped["CollectionRun"] = relationship(back_populates="observations")


class NormalizedFare(Base):
    """
    The canonical form the index consumes.

    Separate from ``fare_observations`` on purpose: observations are the audit record
    of what a source said, normalized fares are the analytical record of what the
    index used. Keeping them distinct means a change to normalization can be replayed
    against the untouched original.
    """

    __tablename__ = "normalized_fares"
    __table_args__ = (
        Index("ix_norm_route_horizon_day", "route_id", "booking_horizon_days", "collection_date"),
        Index("ix_norm_product", "product_key_hash", "collection_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("fare_observations.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_key: Mapped[str] = mapped_column(String(300), nullable=False)
    product_key_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    fare_inr: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Applied FX rate, or NULL when the source already quoted INR.
    fx_rate_applied: Mapped[float | None] = mapped_column(Float)
    normalizer_version: Mapped[str] = mapped_column(String(32), nullable=False)
    is_included_in_index: Mapped[bool] = mapped_column(Boolean, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(64))


class ValidationResultRecord(Base):
    """
    Why each observation was accepted, flagged, or excluded.

    ``rules_version`` and ``thresholds`` are stored so a historical decision can be
    re-derived even after thresholds change.
    """

    __tablename__ = "validation_results"
    __table_args__ = (
        Index("ix_validation_action", "action"),
        Index("ix_validation_obs", "observation_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("fare_observations.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[int] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    flags: Mapped[dict] = mapped_column(JSON, default=list)
    anomaly_type: Mapped[str | None] = mapped_column(String(32))
    severity: Mapped[str | None] = mapped_column(String(16))
    # The numbers behind the decision (fences, prior median, tax share).
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_version: Mapped[str] = mapped_column(String(32), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValidatorState(Base):
    """
    Serialised validator reference distributions.

    Persisted so IQR fences are continuous across restarts. Without this, the first
    N observations after every restart were unchecked and outlier decisions were not
    reproducible.
    """

    __tablename__ = "validator_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    rules_version: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── indices ──

class HorizonIndex(Base):
    """
    Booking-horizon-specific index for one route and period.

    The stratification layer the audit flagged as missing (M2). ``booking_horizon`` is
    NOT NULL here by design: this table exists precisely to hold horizon-specific
    values, and a NULL would mean pooled.
    """

    __tablename__ = "horizon_indices"
    __table_args__ = (
        UniqueConstraint(
            "route_id", "booking_horizon", "index_date", "methodology_version",
            name="uq_horizon_index",
        ),
        Index("ix_horizon_index_date", "index_date"),
        Index("ix_horizon_route", "route_id", "index_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    index_date: Mapped[date] = mapped_column(Date, nullable=False)

    index_value: Mapped[float] = mapped_column(Float, nullable=False)   # ratio, 1.0 = base
    index_100: Mapped[float] = mapped_column(Float, nullable=False)     # base = 100 scale

    matched_products: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    geometric_mean_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    base_geometric_mean_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    base_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    base_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Product churn diagnostics: how much of the base sample was still matchable.
    new_products: Mapped[int] = mapped_column(Integer, default=0)
    disappeared_products: Mapped[int] = mapped_column(Integer, default=0)
    reappeared_products: Mapped[int] = mapped_column(Integer, default=0)
    base_products: Mapped[int] = mapped_column(Integer, default=0)
    current_products: Mapped[int] = mapped_column(Integer, default=0)
    match_rate: Mapped[float | None] = mapped_column(Float)

    # Uncertainty: NULL when not estimable, with the reason recorded.
    standard_error: Mapped[float | None] = mapped_column(Float)
    confidence_interval_low: Mapped[float | None] = mapped_column(Float)
    confidence_interval_high: Mapped[float | None] = mapped_column(Float)
    uncertainty_basis: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The exact products compared, so the figure can be reproduced observation by
    # observation.
    matched_product_keys: Mapped[dict] = mapped_column(JSON, default=list)


class RouteIndex(Base):
    """
    Route index built by combining horizon indices with the policy weights.

    ``applied_horizon_weights`` records the weights actually used after
    renormalization, so a value computed with a horizon missing is still reproducible.
    """

    __tablename__ = "route_indices"
    __table_args__ = (
        UniqueConstraint(
            "route_id", "index_date", "methodology_version", name="uq_route_index"
        ),
        Index("ix_route_index_date", "index_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    index_date: Mapped[date] = mapped_column(Date, nullable=False)

    index_value: Mapped[float] = mapped_column(Float, nullable=False)
    index_100: Mapped[float] = mapped_column(Float, nullable=False)

    horizons_included: Mapped[dict] = mapped_column(JSON, default=list)
    horizons_missing: Mapped[dict] = mapped_column(JSON, default=list)
    applied_horizon_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    horizon_weighting_method: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_weighting_status: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)

    matched_products: Mapped[int] = mapped_column(Integer, default=0)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)

    standard_error: Mapped[float | None] = mapped_column(Float)
    confidence_interval_low: Mapped[float | None] = mapped_column(Float)
    confidence_interval_high: Mapped[float | None] = mapped_column(Float)
    uncertainty_basis: Mapped[str | None] = mapped_column(Text)

    base_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    base_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    is_publishable: Mapped[bool] = mapped_column(Boolean, default=True)
    suppression_reason: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NationalIndex(Base):
    """
    The headline national figure.

    Everything needed to defend the number is on the row: coverage, whether
    renormalization was applied, which routes were missing and why, the weight basket
    version, the base period, and the methodology version. ``mom_status`` and
    ``yoy_status`` are NOT NULL so a null change always carries a stated reason and can
    never be rendered as a fabricated percentage.
    """

    __tablename__ = "national_indices"
    __table_args__ = (
        UniqueConstraint(
            "index_date", "booking_horizon", "methodology_version",
            name="uq_national_index",
        ),
        Index("ix_national_index_date", "index_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_date: Mapped[date] = mapped_column(Date, nullable=False)
    # NULL = the all-horizons headline; an integer = a horizon-specific national index.
    booking_horizon: Mapped[int | None] = mapped_column(Integer)

    index_value: Mapped[float] = mapped_column(Float, nullable=False)  # base = 100

    routes_included: Mapped[int] = mapped_column(Integer, nullable=False)
    routes_in_basket: Mapped[int] = mapped_column(Integer, nullable=False)
    total_observations: Mapped[int] = mapped_column(Integer, nullable=False)
    total_matched_products: Mapped[int] = mapped_column(Integer, default=0)

    coverage_weight: Mapped[float] = mapped_column(Float, nullable=False)
    renormalization_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    is_publishable: Mapped[bool] = mapped_column(Boolean, default=True)
    suppression_reason: Mapped[str | None] = mapped_column(Text)

    mom_change_pct: Mapped[float | None] = mapped_column(Float)
    mom_status: Mapped[str] = mapped_column(String(32), nullable=False)
    yoy_change_pct: Mapped[float | None] = mapped_column(Float)
    yoy_status: Mapped[str] = mapped_column(String(32), nullable=False)

    standard_error: Mapped[float | None] = mapped_column(Float)
    confidence_interval_low: Mapped[float | None] = mapped_column(Float)
    confidence_interval_high: Mapped[float | None] = mapped_column(Float)
    uncertainty_basis: Mapped[str | None] = mapped_column(Text)

    # Seasonal adjustment status, stored so a historical row states what was (not) done.
    seasonal_adjustment: Mapped[str] = mapped_column(String(32), nullable=False)

    base_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    base_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    base_period_label: Mapped[str] = mapped_column(String(64), nullable=False)

    weight_basket_id: Mapped[str] = mapped_column(String(64), nullable=False)
    weight_basket_version: Mapped[str] = mapped_column(String(32), nullable=False)
    weighting_method: Mapped[str] = mapped_column(String(64), nullable=False)
    weighting_status: Mapped[str] = mapped_column(String(32), nullable=False)

    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    provenance_label: Mapped[str] = mapped_column(String(32), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_rules_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The collection runs whose observations fed this figure.
    contributing_run_ids: Mapped[dict] = mapped_column(JSON, default=list)
    route_contributions: Mapped[dict] = mapped_column(JSON, default=list)
    missing_routes: Mapped[dict] = mapped_column(JSON, default=list)


class Anomaly(Base):
    """
    Flagged observation awaiting or having received review.

    ``is_genuine`` was present in the old schema and never written. Here it is part of
    a real workflow: OPEN -> UNDER_REVIEW -> CONFIRMED_GENUINE / CONFIRMED_ERROR, with
    reviewer and timestamp recorded.
    """

    __tablename__ = "anomalies"
    __table_args__ = (
        Index("ix_anomaly_status", "status"),
        Index("ix_anomaly_route_date", "route_id", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int | None] = mapped_column(
        ForeignKey("fare_observations.id", ondelete="SET NULL")
    )
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="SET NULL")
    )

    route_id: Mapped[int] = mapped_column(Integer, nullable=False)
    route_code: Mapped[str] = mapped_column(String(8), nullable=False)
    booking_horizon: Mapped[int | None] = mapped_column(Integer)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The validation rule that fired, e.g. 'statistical_high_outlier_iqr3'.
    rule: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    fare_observed: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fare_expected_low: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fare_expected_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    # 'open' | 'under_review' | 'confirmed_genuine' | 'confirmed_error' | 'dismissed'
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)
    # NULL until reviewed. True = genuine market movement (kept in the index).
    # False = collection error (excluded, and a revision is recorded).
    is_genuine: Mapped[bool | None] = mapped_column(Boolean)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)


class IndexRevision(Base):
    """
    Audit log of every change to a published figure.

    A published statistic that changes without a recorded reason is not auditable.
    Rows are append-only: revisions are added, never edited.
    """

    __tablename__ = "index_revisions"
    __table_args__ = (
        Index("ix_revision_target", "target_table", "target_index_date"),
        Index("ix_revision_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_table: Mapped[str] = mapped_column(String(32), nullable=False)
    target_index_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_route_id: Mapped[int | None] = mapped_column(Integer)
    target_booking_horizon: Mapped[int | None] = mapped_column(Integer)

    previous_value: Mapped[float | None] = mapped_column(Float)
    new_value: Mapped[float | None] = mapped_column(Float)
    # 'initial_publication' | 'recomputation' | 'anomaly_review' | 'weight_change' |
    # 'base_period_change' | 'methodology_change' | 'late_data'
    revision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    previous_methodology_version: Mapped[str | None] = mapped_column(String(32))
    new_methodology_version: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


ALL_TABLES = [
    Source.__tablename__,
    RouteWeightRecord.__tablename__,
    CollectionRun.__tablename__,
    FareObservationRecord.__tablename__,
    NormalizedFare.__tablename__,
    ValidationResultRecord.__tablename__,
    ValidatorState.__tablename__,
    HorizonIndex.__tablename__,
    RouteIndex.__tablename__,
    NationalIndex.__tablename__,
    Anomaly.__tablename__,
    IndexRevision.__tablename__,
]
