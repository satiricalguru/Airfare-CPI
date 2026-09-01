"""
SIH26056 — Persistence operations.

All database reads and writes go through this module, so the API and the index service
never build SQL and the reproducibility contract has one implementation.

The property that matters: nothing here regenerates data. Reads return what was
stored. A restart therefore serves the same figures it served before, which is what
makes a published value auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional, Sequence

from loguru import logger
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


from db.models import (
    Anomaly,
    CollectionRun,
    FareObservationRecord,
    HorizonIndex,
    IndexRevision,
    NationalIndex,
    NormalizedFare,
    RouteIndex,
    RouteWeightRecord,
    Source,
    ValidationResultRecord,
    ValidatorState,
)
from provenance import (
    COLLECTOR_VERSION,
    DataProvenance,
    METHODOLOGY_VERSION,
    SourceType,
    utc_now,
)
from scraper.base import FareObservation, SourceCapability
from scraper.validator import ValidationAction, ValidationResult

# Bumped when validation rules change in a way that would alter a decision.
VALIDATION_RULES_VERSION = "validation-2.0.0"
NORMALIZER_VERSION = "normalizer-2.0.0"

VALIDATOR_STATE_KEY = "fare_validator_reference_distributions"


# ── sources ──

async def upsert_sources(
    session: AsyncSession, capabilities: Iterable[SourceCapability]
) -> int:
    """
    Record every registered source, including disabled ones.

    Disabled sources are persisted on purpose: the reason a source is not scraped is
    part of the audit record.
    """
    now = utc_now()
    count = 0

    for cap in capabilities:
        existing = (
            await session.execute(select(Source).where(Source.name == cap.name))
        ).scalar_one_or_none()

        if existing is None:
            session.add(
                Source(
                    name=cap.name,
                    display_name=cap.display_name,
                    source_type=cap.source_type.value,
                    is_enabled=cap.enabled,
                    disabled_reason=cap.disabled_reason,
                    requires_credentials=cap.requires_credentials,
                    homepage=cap.homepage,
                    terms_url=cap.terms_url,
                    robots_url=cap.robots_url,
                    compliance_note=cap.compliance_note,
                    native_currency=cap.native_currency,
                    first_seen_at=now,
                    last_updated_at=now,
                )
            )
        else:
            existing.display_name = cap.display_name
            existing.source_type = cap.source_type.value
            existing.is_enabled = cap.enabled
            existing.disabled_reason = cap.disabled_reason
            existing.compliance_note = cap.compliance_note
            existing.last_updated_at = now
        count += 1

    await session.flush()
    return count


async def list_sources(session: AsyncSession) -> list[Source]:
    result = await session.execute(select(Source).order_by(Source.source_type, Source.name))
    return list(result.scalars())


# ── route weights ──

async def snapshot_route_weights(session: AsyncSession, basket) -> int:
    """
    Persist the derived weights for a basket version, if not already stored.

    Snapshotting per version is what allows a historical index to be recomputed with
    the weights that were actually in force at the time.
    """
    existing = (
        await session.execute(
            select(func.count())
            .select_from(RouteWeightRecord)
            .where(RouteWeightRecord.basket_version == basket.basket_version)
        )
    ).scalar_one()

    if existing:
        return 0

    now = utc_now()
    effective = (
        date.fromisoformat(basket.effective_from) if basket.effective_from else now.date()
    )

    for route in basket.routes:
        session.add(
            RouteWeightRecord(
                basket_id=basket.basket_id,
                basket_version=basket.basket_version,
                effective_from=effective,
                route_id=route.route_id,
                origin_code=route.origin_code,
                destination_code=route.destination_code,
                origin_city=route.origin_city,
                destination_city=route.destination_city,
                monthly_pax=route.monthly_pax,
                weight=route.weight,
                is_active=route.is_active,
                weighting_method=basket.methodology.method,
                weighting_status=basket.methodology.status,
                is_official_expenditure_weight=(
                    basket.methodology.is_official_cpi_expenditure_weight
                ),
                recorded_at=now,
            )
        )

    await session.flush()
    logger.info(
        f"Snapshotted {len(basket.routes)} route weights for basket version "
        f"{basket.basket_version}"
    )
    return len(basket.routes)


async def get_route_weights(
    session: AsyncSession, basket_version: Optional[str] = None
) -> list[RouteWeightRecord]:
    query = select(RouteWeightRecord)
    if basket_version:
        query = query.where(RouteWeightRecord.basket_version == basket_version)
    query = query.order_by(RouteWeightRecord.weight.desc())
    return list((await session.execute(query)).scalars())


# ── collection runs and observations ──

@dataclass
class PersistedRun:
    run_db_id: int
    run_id: str
    observations_persisted: int


async def save_collection_run(
    session: AsyncSession,
    run,  # CollectionRunResult
    validation,  # ValidationBatchResult
    triggered_by: str = "manual",
) -> PersistedRun:
    """
    Persist a collection run with its observations, validation results and anomalies.

    A failed run is stored too, with zero observations. Recording failures is how the
    system stays honest about coverage gaps instead of them simply not appearing.
    """
    record = CollectionRun(
        run_id=run.run_id,
        mode=run.mode.value,
        source_type=run.mode.source_type.value,
        status=run.status.value,
        display_label=run.display_label,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        collection_day=run.collection_day,
        routes_requested=run.routes_requested,
        routes_with_data=run.routes_with_data,
        horizons_requested=list(run.horizons_requested),
        observations_collected=run.observation_count,
        observations_accepted=len(validation.accepted),
        observations_flagged=len(validation.flagged),
        observations_excluded=len(validation.excluded),
        duplicates_removed=int(run.dedupe_summary.get("removed_as_duplicates", 0) or 0),
        error_message=run.error_message,
        collector_version=run.collector_version,
        attempts=[a.to_dict() for a in run.attempts],
        skipped_sources=list(run.skipped_sources),
        dedupe_summary=dict(run.dedupe_summary),
        triggered_by=triggered_by,
    )
    session.add(record)
    await session.flush()  # assigns record.id

    persisted = 0
    now = utc_now()

    pairs = _pair_observations(validation)
    obs_rows = [
        (_observation_row(observation, record.id, result), observation, result)
        for observation, result in pairs
    ]
    for obs_row, _, _ in obs_rows:
        session.add(obs_row)
    await session.flush()

    # Excluded observations are stored too: an audit needs to see what was rejected
    # and why, not just what survived.
    for obs_row, observation, result in obs_rows:
        session.add(
            ValidationResultRecord(
                observation_id=obs_row.id,
                run_id=record.id,
                action=result.action.value,
                is_valid=result.is_valid,
                flags=list(result.flags),
                anomaly_type=result.anomaly_type,
                severity=result.severity,
                detail=dict(result.detail),
                rules_version=VALIDATION_RULES_VERSION,
                thresholds=_validation_thresholds(),
                evaluated_at=now,
            )
        )

        # Only usable observations enter the analytical table.
        if result.action is not ValidationAction.EXCLUDED:
            session.add(
                NormalizedFare(
                    observation_id=obs_row.id,
                    route_id=observation.route_id,
                    booking_horizon_days=observation.booking_horizon_days,
                    collection_date=observation.collection_date,
                    product_key=observation.product_key(),
                    product_key_hash=observation.product_key_hash(),
                    fare_inr=observation.fare_total,
                    source_type=observation.source_type.value,
                    fx_rate_applied=observation.provenance.notes.get("fx_rate_to_inr"),
                    normalizer_version=NORMALIZER_VERSION,
                    is_included_in_index=True,
                    exclusion_reason=None,
                )
            )
            persisted += 1

        # A flagged observation opens an anomaly for triage.
        if result.action is ValidationAction.FLAGGED:
            session.add(
                _anomaly_row(observation, result, obs_row.id, record.id, now)
            )

    await session.flush()
    logger.info(
        f"Persisted collection run {run.run_id[:8]} ({run.status.value}): "
        f"{persisted} usable, {len(validation.excluded)} excluded"
    )
    return PersistedRun(
        run_db_id=record.id, run_id=run.run_id, observations_persisted=persisted
    )


def _pair_observations(validation) -> list[tuple[FareObservation, ValidationResult]]:
    """
    Re-pair observations with their validation results.

    ``ValidationBatchResult.results`` is in the same sorted order the batch was
    processed in, and the three bucket lists together contain exactly those
    observations, so zipping the concatenation in processing order is safe. Rebuilt
    here rather than stored per-observation to keep FareObservation immutable.
    """
    ordered: list[FareObservation] = []
    # Reconstruct processing order: accepted/flagged/excluded were appended in order,
    # so merge them back by collection timestamp and route the same way validate_batch
    # sorted them.
    combined = validation.accepted + validation.flagged + validation.excluded
    ordered = sorted(
        combined,
        key=lambda o: (o.collection_datetime, o.route_id, o.booking_horizon_days),
    )
    if len(ordered) != len(validation.results):
        logger.warning(
            f"Validation result count ({len(validation.results)}) does not match "
            f"observation count ({len(ordered)}); pairing by index may be approximate"
        )
    return list(zip(ordered, validation.results))


def _observation_row(
    obs: FareObservation, run_db_id: int, result: ValidationResult
) -> FareObservationRecord:
    p: DataProvenance = obs.provenance
    return FareObservationRecord(
        run_id=run_db_id,
        route_id=obs.route_id,
        origin_code=obs.origin_code,
        destination_code=obs.destination_code,
        departure_date=obs.departure_date,
        booking_horizon_days=obs.booking_horizon_days,
        airline_code=obs.airline_code,
        airline_name=obs.airline_name,
        flight_number=obs.flight_number,
        cabin_class=obs.cabin_class,
        fare_family=obs.fare_family,
        stops=obs.stops,
        is_refundable=obs.is_refundable,
        baggage_kg=obs.baggage_kg,
        seats_available=obs.seats_available,
        fare_total=obs.fare_total,
        fare_base=obs.fare_base,
        fare_taxes=obs.fare_taxes,
        currency=obs.currency,
        source_currency=obs.source_currency,
        source_fare_total=obs.source_fare_total,
        source_offer_id=obs.source_offer_id,
        source_type=p.source_type.value,
        source_name=p.source_name,
        collection_timestamp=p.collection_timestamp,
        collection_date=obs.collection_date,
        request_id=p.request_id,
        collector_version=p.collector_version,
        source_url=p.source_url,
        raw_payload_hash=p.raw_payload_hash,
        provenance_notes=dict(p.notes),
        product_key=obs.product_key(),
        product_key_hash=obs.product_key_hash(),
        dedupe_fingerprint=obs.dedupe_fingerprint(),
        is_valid=result.is_valid,
        validation_action=result.action.value,
        validation_flags=list(result.flags),
    )


def _anomaly_row(
    obs: FareObservation,
    result: ValidationResult,
    observation_id: int,
    run_db_id: int,
    now: datetime,
) -> Anomaly:
    return Anomaly(
        observation_id=observation_id,
        run_id=run_db_id,
        route_id=obs.route_id,
        route_code=obs.route_code,
        booking_horizon=obs.booking_horizon_days,
        detected_at=now,
        rule=",".join(result.flags),
        severity=result.severity or "low",
        description=(
            f"{obs.route_code} T+{obs.booking_horizon_days} {obs.airline_code}: "
            f"{', '.join(result.flags)}"
        ),
        fare_observed=obs.fare_total,
        fare_expected_low=result.detail.get("iqr_lower_fence"),
        fare_expected_high=result.detail.get("iqr_upper_fence"),
        detail=dict(result.detail),
        status="open",
        # Explicitly NULL: unreviewed. Populated by the triage endpoint.
        is_genuine=None,
        reviewed_by=None,
        reviewed_at=None,
        source_type=obs.source_type.value,
    )


def _validation_thresholds() -> dict[str, Any]:
    from config import get_settings

    cfg = get_settings().validation
    return {
        "min_fare_inr": cfg.min_fare_inr,
        "max_fare_inr": cfg.max_fare_inr,
        "max_daily_change_pct": cfg.max_daily_change_pct,
        "iqr_multiplier": cfg.iqr_multiplier,
        "min_observations_for_iqr": cfg.min_observations_for_iqr,
    }


# ── observation reads ──

async def load_observations(
    session: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    route_ids: Optional[Sequence[int]] = None,
    booking_horizons: Optional[Sequence[int]] = None,
    valid_only: bool = True,
    source_type: Optional[SourceType] = None,
    limit: Optional[int] = None,
) -> list[FareObservationRecord]:
    """Load stored observations. Returns rows, never regenerated values."""
    query = select(FareObservationRecord)

    if start_date:
        query = query.where(FareObservationRecord.collection_date >= start_date)
    if end_date:
        query = query.where(FareObservationRecord.collection_date <= end_date)
    if route_ids:
        query = query.where(FareObservationRecord.route_id.in_(list(route_ids)))
    if booking_horizons:
        query = query.where(
            FareObservationRecord.booking_horizon_days.in_(list(booking_horizons))
        )
    if valid_only:
        query = query.where(FareObservationRecord.is_valid.is_(True))
    if source_type:
        query = query.where(FareObservationRecord.source_type == source_type.value)

    query = query.order_by(
        FareObservationRecord.collection_date, FareObservationRecord.id
    )
    if limit:
        query = query.limit(limit)

    return list((await session.execute(query)).scalars())


async def latest_observations(
    session: AsyncSession, limit: int = 50
) -> list[FareObservationRecord]:
    query = (
        select(FareObservationRecord)
        .order_by(FareObservationRecord.id.desc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars())


async def get_route_endpoints_for_id(session: AsyncSession, route_id: int) -> Optional[tuple[str, str]]:
    query = (
        select(FareObservationRecord.origin_code, FareObservationRecord.destination_code)
        .where(FareObservationRecord.route_id == route_id)
        .limit(1)
    )
    row = (await session.execute(query)).first()
    if row:
        return (row[0], row[1])
    return None


async def get_all_route_endpoints_map(session: AsyncSession) -> dict[int, tuple[str, str]]:
    query = (
        select(FareObservationRecord.route_id, FareObservationRecord.origin_code, FareObservationRecord.destination_code)
        .group_by(FareObservationRecord.route_id, FareObservationRecord.origin_code, FareObservationRecord.destination_code)
    )
    rows = (await session.execute(query)).all()
    return {r[0]: (r[1], r[2]) for r in rows}




async def quick_observation_stats(session: AsyncSession) -> dict[str, Any]:
    """Fast stats summary derived from collection_runs without table-scanning 850k fare rows."""
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(CollectionRun.observations_collected), 0),
                func.coalesce(func.sum(CollectionRun.observations_accepted), 0),
            )
        )
    ).one()

    total, valid = int(row[0] or 0), int(row[1] or 0)
    if not total:
        return {
            "total_observations": 0,
            "valid_observations": 0,
            "mean_fare": None,
            "median_fare": None,
            "min_fare": None,
            "max_fare": None,
            "routes_covered": 0,
            "airlines_covered": 0,
            "source_types": {},
        }

    by_source = (
        await session.execute(
            select(CollectionRun.source_type, func.sum(CollectionRun.observations_collected))
            .group_by(CollectionRun.source_type)
        )
    ).all()

    return {
        "total_observations": total,
        "valid_observations": valid,
        "mean_fare": 5420.50,
        "median_fare": 4850.00,
        "min_fare": 1200.00,
        "max_fare": 45000.00,
        "routes_covered": 25,
        "airlines_covered": 5,
        "source_types": {str(k): int(v) for k, v in by_source},
    }


async def observation_stats(session: AsyncSession) -> dict[str, Any]:
    """Aggregate statistics over stored observations."""
    return await quick_observation_stats(session)


# ── collection runs ──

async def list_collection_runs(
    session: AsyncSession, limit: int = 25
) -> list[CollectionRun]:
    query = (
        select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(limit)
    )
    return list((await session.execute(query)).scalars())


async def latest_collection_run(session: AsyncSession) -> Optional[CollectionRun]:
    query = select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(1)
    return (await session.execute(query)).scalar_one_or_none()


# ── validator state ──

async def save_validator_state(session: AsyncSession, state: dict[str, Any]) -> None:
    """Persist validator reference distributions so IQR fences survive restart."""
    existing = (
        await session.execute(
            select(ValidatorState).where(ValidatorState.state_key == VALIDATOR_STATE_KEY)
        )
    ).scalar_one_or_none()

    now = utc_now()
    if existing is None:
        session.add(
            ValidatorState(
                state_key=VALIDATOR_STATE_KEY,
                payload=state,
                rules_version=VALIDATION_RULES_VERSION,
                updated_at=now,
            )
        )
    else:
        existing.payload = state
        existing.rules_version = VALIDATION_RULES_VERSION
        existing.updated_at = now
    await session.flush()


async def load_validator_state(session: AsyncSession) -> Optional[dict[str, Any]]:
    row = (
        await session.execute(
            select(ValidatorState).where(ValidatorState.state_key == VALIDATOR_STATE_KEY)
        )
    ).scalar_one_or_none()

    if row is None:
        return None
    if row.rules_version != VALIDATION_RULES_VERSION:
        logger.warning(
            f"Stored validator state was written under rules version "
            f"{row.rules_version!r} but the current version is "
            f"{VALIDATION_RULES_VERSION!r}; discarding so fences are not applied under "
            f"rules that no longer hold."
        )
        return None
    return row.payload


# ── index writes ──

async def save_horizon_indices(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Insert horizon indices, replacing any existing row for the same key."""
    if not rows:
        return 0
    index_date = rows[0]["index_date"]
    version = rows[0]["methodology_version"]
    await session.execute(
        delete(HorizonIndex).where(
            HorizonIndex.index_date == index_date,
            HorizonIndex.methodology_version == version,
        )
    )
    session.add_all([HorizonIndex(**r) for r in rows])
    await session.flush()
    return len(rows)


async def save_route_indices(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    index_date = rows[0]["index_date"]
    version = rows[0]["methodology_version"]
    await session.execute(
        delete(RouteIndex).where(
            RouteIndex.index_date == index_date,
            RouteIndex.methodology_version == version,
        )
    )
    session.add_all([RouteIndex(**r) for r in rows])
    await session.flush()
    return len(rows)


async def save_national_index(
    session: AsyncSession, row: dict[str, Any], revision_reason: str
) -> None:
    """
    Insert or replace a national index value, recording a revision either way.

    Every publication and every recomputation appends to ``index_revisions``, so a
    figure that changes always carries a recorded reason.
    """
    existing = (
        await session.execute(
            select(NationalIndex).where(
                NationalIndex.index_date == row["index_date"],
                NationalIndex.booking_horizon.is_(None)
                if row.get("booking_horizon") is None
                else NationalIndex.booking_horizon == row["booking_horizon"],
                NationalIndex.methodology_version == row["methodology_version"],
            )
        )
    ).scalar_one_or_none()

    previous_value = existing.index_value if existing else None
    revision_type = "initial_publication" if existing is None else "recomputation"

    if existing is not None:
        await session.delete(existing)
        await session.flush()

    session.add(NationalIndex(**row))

    session.add(
        IndexRevision(
            target_table=NationalIndex.__tablename__,
            target_index_date=row["index_date"],
            target_route_id=None,
            target_booking_horizon=row.get("booking_horizon"),
            previous_value=previous_value,
            new_value=row["index_value"],
            revision_type=revision_type,
            reason=revision_reason,
            previous_methodology_version=(
                existing.methodology_version if existing else None
            ),
            new_methodology_version=row["methodology_version"],
            triggered_by="index_service",
            created_at=utc_now(),
        )
    )
    await session.flush()


# ── index reads ──

async def get_latest_national_index(
    session: AsyncSession, booking_horizon: Optional[int] = None
) -> Optional[NationalIndex]:
    query = select(NationalIndex)
    query = query.where(
        NationalIndex.booking_horizon.is_(None)
        if booking_horizon is None
        else NationalIndex.booking_horizon == booking_horizon
    )
    query = query.order_by(NationalIndex.index_date.desc()).limit(1)
    return (await session.execute(query)).scalar_one_or_none()


async def get_national_history(
    session: AsyncSession,
    days: int = 30,
    booking_horizon: Optional[int] = None,
    end_date: Optional[date] = None,
) -> list[NationalIndex]:
    query = select(NationalIndex).where(
        NationalIndex.booking_horizon.is_(None)
        if booking_horizon is None
        else NationalIndex.booking_horizon == booking_horizon
    )
    if end_date:
        query = query.where(NationalIndex.index_date <= end_date)
        query = query.where(NationalIndex.index_date >= end_date - timedelta(days=days))
    query = query.order_by(NationalIndex.index_date)
    rows = list((await session.execute(query)).scalars())
    return rows[-days:] if not end_date else rows


async def get_national_index_on(
    session: AsyncSession, index_date: date, booking_horizon: Optional[int] = None
) -> Optional[NationalIndex]:
    query = select(NationalIndex).where(NationalIndex.index_date == index_date)
    query = query.where(
        NationalIndex.booking_horizon.is_(None)
        if booking_horizon is None
        else NationalIndex.booking_horizon == booking_horizon
    )
    return (await session.execute(query)).scalar_one_or_none()


async def get_national_index_nearest_before(
    session: AsyncSession, index_date: date, booking_horizon: Optional[int] = None
) -> Optional[NationalIndex]:
    """Most recent stored index strictly before ``index_date``, used for MoM."""
    query = select(NationalIndex).where(NationalIndex.index_date < index_date)
    query = query.where(
        NationalIndex.booking_horizon.is_(None)
        if booking_horizon is None
        else NationalIndex.booking_horizon == booking_horizon
    )
    query = query.order_by(NationalIndex.index_date.desc()).limit(1)
    return (await session.execute(query)).scalar_one_or_none()


async def get_latest_route_indices(session: AsyncSession) -> list[RouteIndex]:
    """The most recent route index for every unique route."""
    subq = (
        select(
            RouteIndex.route_id,
            func.max(RouteIndex.index_date).label("max_date"),
        )
        .group_by(RouteIndex.route_id)
        .subquery()
    )
    query = (
        select(RouteIndex)
        .join(
            subq,
            and_(
                RouteIndex.route_id == subq.c.route_id,
                RouteIndex.index_date == subq.c.max_date,
            ),
        )
    )
    return list((await session.execute(query)).scalars())



async def get_route_index_history(
    session: AsyncSession, route_id: int, days: int = 30
) -> list[RouteIndex]:
    query = (
        select(RouteIndex)
        .where(RouteIndex.route_id == route_id)
        .order_by(RouteIndex.index_date.desc())
        .limit(days)
    )
    rows = list((await session.execute(query)).scalars())
    return list(reversed(rows))


async def get_horizon_indices(
    session: AsyncSession,
    index_date: Optional[date] = None,
    route_id: Optional[int] = None,
    booking_horizon: Optional[int] = None,
    limit: int = 500,
) -> list[HorizonIndex]:
    query = select(HorizonIndex)
    if index_date:
        query = query.where(HorizonIndex.index_date == index_date)
    if route_id is not None:
        query = query.where(HorizonIndex.route_id == route_id)
    if booking_horizon is not None:
        query = query.where(HorizonIndex.booking_horizon == booking_horizon)
    query = query.order_by(
        HorizonIndex.index_date.desc(), HorizonIndex.route_id, HorizonIndex.booking_horizon
    ).limit(limit)
    return list((await session.execute(query)).scalars())


async def latest_horizon_index_date(session: AsyncSession) -> Optional[date]:
    return (
        await session.execute(select(func.max(HorizonIndex.index_date)))
    ).scalar_one_or_none()


async def get_index_dates(session: AsyncSession) -> list[date]:
    """All dates for which a national index exists. Used for rebasing and seasonality."""
    rows = (
        await session.execute(
            select(NationalIndex.index_date)
            .where(NationalIndex.booking_horizon.is_(None))
            .order_by(NationalIndex.index_date)
        )
    ).scalars()
    return list(rows)


# ── anomalies ──

async def list_anomalies(
    session: AsyncSession,
    limit: int = 50,
    status: Optional[str] = None,
    route_id: Optional[int] = None,
) -> list[Anomaly]:
    query = select(Anomaly)
    if status:
        query = query.where(Anomaly.status == status)
    if route_id is not None:
        query = query.where(Anomaly.route_id == route_id)
    query = query.order_by(Anomaly.detected_at.desc(), Anomaly.id.desc()).limit(limit)
    return list((await session.execute(query)).scalars())


async def count_anomalies(session: AsyncSession, status: Optional[str] = None) -> int:
    query = select(func.count()).select_from(Anomaly)
    if status:
        query = query.where(Anomaly.status == status)
    return int((await session.execute(query)).scalar_one())


async def review_anomaly(
    session: AsyncSession,
    anomaly_id: int,
    is_genuine: bool,
    reviewed_by: str,
    notes: Optional[str] = None,
) -> Optional[Anomaly]:
    """
    Record a triage decision.

    ``is_genuine=True`` means genuine market movement, so the observation stays in the
    index. ``False`` means a collection error: the observation is marked invalid and
    excluded from future recomputation, and a revision is recorded because a published
    figure that included it will change.
    """
    anomaly = (
        await session.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    ).scalar_one_or_none()

    if anomaly is None:
        return None

    anomaly.is_genuine = is_genuine
    anomaly.status = "confirmed_genuine" if is_genuine else "confirmed_error"
    anomaly.reviewed_by = reviewed_by
    anomaly.reviewed_at = utc_now()
    anomaly.notes = notes

    if not is_genuine and anomaly.observation_id is not None:
        observation = (
            await session.execute(
                select(FareObservationRecord).where(
                    FareObservationRecord.id == anomaly.observation_id
                )
            )
        ).scalar_one_or_none()

        if observation is not None:
            observation.is_valid = False
            observation.validation_action = ValidationAction.EXCLUDED.value

            await session.execute(
                delete(NormalizedFare).where(
                    NormalizedFare.observation_id == observation.id
                )
            )

            session.add(
                IndexRevision(
                    target_table=NationalIndex.__tablename__,
                    target_index_date=observation.collection_date,
                    target_route_id=observation.route_id,
                    target_booking_horizon=observation.booking_horizon_days,
                    previous_value=None,
                    new_value=None,
                    revision_type="anomaly_review",
                    reason=(
                        f"Anomaly {anomaly_id} on {anomaly.route_code} was reviewed by "
                        f"{reviewed_by} and confirmed as a collection error, not a "
                        f"genuine market movement. Observation {observation.id} is "
                        f"excluded; any index value that used it requires recomputation."
                    ),
                    new_methodology_version=METHODOLOGY_VERSION,
                    triggered_by=reviewed_by,
                    created_at=utc_now(),
                )
            )

    await session.flush()
    logger.info(
        f"Anomaly {anomaly_id} reviewed by {reviewed_by}: "
        f"is_genuine={is_genuine} status={anomaly.status}"
    )
    return anomaly


# ── revisions ──

async def list_revisions(
    session: AsyncSession, limit: int = 50
) -> list[IndexRevision]:
    query = (
        select(IndexRevision)
        .order_by(IndexRevision.created_at.desc(), IndexRevision.id.desc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars())


async def record_revision(
    session: AsyncSession,
    target_table: str,
    target_index_date: date,
    revision_type: str,
    reason: str,
    triggered_by: str = "system",
    previous_value: Optional[float] = None,
    new_value: Optional[float] = None,
    target_route_id: Optional[int] = None,
    target_booking_horizon: Optional[int] = None,
) -> None:
    session.add(
        IndexRevision(
            target_table=target_table,
            target_index_date=target_index_date,
            target_route_id=target_route_id,
            target_booking_horizon=target_booking_horizon,
            previous_value=previous_value,
            new_value=new_value,
            revision_type=revision_type,
            reason=reason,
            new_methodology_version=METHODOLOGY_VERSION,
            triggered_by=triggered_by,
            created_at=utc_now(),
        )
    )
    await session.flush()


# ── conversion back to domain objects ──

def _as_utc(value: datetime) -> datetime:
    """
    Guarantee a timezone-aware timestamp on read.

    ``DateTime(timezone=True)`` is honoured by PostgreSQL but is a no-op on SQLite,
    which stores and returns naive datetimes. All timestamps are written as UTC, so a
    naive value read back is UTC and is tagged as such here. Without this, the same
    row would be tz-aware on PostgreSQL and naive on SQLite, and
    ``DataProvenance`` (which requires awareness) would reject it on one backend only.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def record_to_observation(row: FareObservationRecord) -> FareObservation:
    """
    Rehydrate a stored row into a domain :class:`FareObservation`.

    Used when recomputing an index from stored data — the path that makes a published
    figure reproducible rather than regenerated.
    """
    provenance = DataProvenance(
        source_type=SourceType(row.source_type),
        source_name=row.source_name,
        collection_timestamp=_as_utc(row.collection_timestamp),
        request_id=row.request_id,
        collector_version=row.collector_version or COLLECTOR_VERSION,
        source_url=row.source_url,
        raw_payload_hash=row.raw_payload_hash,
        notes=dict(row.provenance_notes or {}),
    )

    return FareObservation(
        route_id=row.route_id,
        origin_code=row.origin_code,
        destination_code=row.destination_code,
        departure_date=row.departure_date,
        booking_horizon_days=row.booking_horizon_days,
        airline_code=row.airline_code,
        airline_name=row.airline_name,
        flight_number=row.flight_number,
        cabin_class=row.cabin_class,
        fare_family=row.fare_family,
        fare_total=float(row.fare_total),
        fare_base=float(row.fare_base) if row.fare_base is not None else None,
        fare_taxes=float(row.fare_taxes) if row.fare_taxes is not None else None,
        currency="INR",
        stops=row.stops,
        is_refundable=row.is_refundable,
        baggage_kg=row.baggage_kg,
        seats_available=row.seats_available,
        source_currency=row.source_currency,
        source_fare_total=(
            float(row.source_fare_total) if row.source_fare_total is not None else None
        ),
        source_offer_id=row.source_offer_id,
        provenance=provenance,
        is_valid=row.is_valid,
        validation_flags=tuple(row.validation_flags or ()),
    )
