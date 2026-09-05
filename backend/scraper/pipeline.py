"""
SIH26056 — Collection pipeline.

Dispatches a collection run to the sources appropriate for the configured mode:

    LIVE       -> real permitted sources only
    SIMULATED  -> the calibrated simulator only
    OFFLINE    -> the checked-in fixture only

The single most important property of this module: **there is no fallback between
modes.** If ``LIVE`` collection fails, the run reports ``FAILED`` with an error and
zero observations. It does not consult the simulator. That is enforced in three
independent places, so removing any one of them does not open the hole:

1. :meth:`CollectionPipeline._select_sources` resolves sources filtered by
   ``mode.source_type``, so a LIVE run cannot even instantiate the simulator.
2. :class:`SourceResult` refuses to attach non-live observations to a success status.
3. :meth:`CollectionRunResult.__post_init__` asserts every observation's source type
   matches the run's mode.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from loguru import logger

from config import SUPPORTED_BOOKING_HORIZONS, Settings, get_settings
from provenance import (
    COLLECTOR_VERSION,
    CollectionMode,
    CollectionStatus,
    SOURCE_UNAVAILABLE_LABEL,
    SourceType,
    new_request_id,
    resolve_display_label,
    utc_now,
)
from engine.weights import Route, get_route_basket
from db.engine import get_database
from scraper.base import FareObservation, FareSource, SourceResult
from scraper.budget import BudgetController, TRACER_BASKET_ROUTE_CODES
from scraper.dedupe import DedupeStrategy, deduplicate
from scraper.governance import check_source_permitted
from scraper.registry import get_registry


@dataclass
class CollectionRequest:
    """One collection cycle's scope."""

    mode: CollectionMode
    routes: list[Route]
    booking_horizons: list[int]
    passengers: int = 1
    cabin: str = "ECONOMY"
    # Collection reference day. Departure dates are computed as
    # collection_day + horizon, which is what makes the horizon meaningful.
    collection_day: Optional[date] = None
    source_names: Optional[list[str]] = None
    # Construction options forwarded to the source factory.
    #
    # Used by the simulated backfill to set a historical collection timestamp, so a
    # seeded research series carries the dates it represents rather than the wall
    # clock. A LIVE source must ignore any such hint: a quote cannot be retrieved for
    # a day that has already passed, and stamping one would falsify provenance.
    source_kwargs: dict[str, Any] = field(default_factory=dict)

    def resolved_collection_day(self) -> date:
        return self.collection_day or date.today()

    def departure_date_for(self, horizon: int) -> date:
        return self.resolved_collection_day() + timedelta(days=horizon)

    @property
    def task_count(self) -> int:
        return len(self.routes) * len(self.booking_horizons)


@dataclass
class SourceAttempt:
    """Audit record of one source's outcome for one route/horizon."""

    source_name: str
    route_id: int
    booking_horizon_days: int
    status: CollectionStatus
    observation_count: int
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "route_id": self.route_id,
            "booking_horizon_days": self.booking_horizon_days,
            "status": self.status.value,
            "observation_count": self.observation_count,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "response_time_ms": self.response_time_ms,
            "attempts": self.attempts,
        }


@dataclass
class CollectionRunResult:
    """
    Outcome of one collection cycle.

    ``status`` describes what actually happened and is never upgraded. A LIVE run
    that retrieved nothing is FAILED or UNAVAILABLE, and ``observations`` is empty.
    """

    run_id: str
    mode: CollectionMode
    status: CollectionStatus
    started_at: datetime
    finished_at: datetime
    collection_day: date
    observations: list[FareObservation] = field(default_factory=list)
    attempts: list[SourceAttempt] = field(default_factory=list)
    skipped_sources: list[dict[str, str]] = field(default_factory=list)
    dedupe_summary: dict[str, Any] = field(default_factory=dict)
    routes_requested: int = 0
    routes_with_data: int = 0
    horizons_requested: list[int] = field(default_factory=list)
    error_message: Optional[str] = None
    collector_version: str = COLLECTOR_VERSION

    def __post_init__(self):
        # Defence in depth: no observation may carry a source type that disagrees
        # with the run's mode. This is the assertion that would fire if a future
        # change reintroduced cross-mode substitution.
        expected = self.mode.source_type
        offenders = sorted(
            {o.source_type.value for o in self.observations if o.source_type is not expected}
        )
        if offenders:
            raise ValueError(
                f"Collection run {self.run_id} in mode {self.mode.value} produced "
                f"observations with source types {offenders}; expected only "
                f"{expected.value!r}. Cross-mode data substitution is not permitted."
            )
        if self.status.is_failure and self.observations:
            raise ValueError(
                f"Collection run {self.run_id} reports {self.status.value} but carries "
                f"{len(self.observations)} observations."
            )

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def source_type(self) -> Optional[SourceType]:
        return self.mode.source_type if self.observations else None

    @property
    def display_label(self) -> str:
        """The honest badge for this run: LIVE DATA / SIMULATED DATA / OFFLINE PREVIEW / SOURCE UNAVAILABLE."""
        if not self.observations:
            return SOURCE_UNAVAILABLE_LABEL
        return resolve_display_label(self.mode.source_type, self.status)

    def to_dict(self) -> dict[str, Any]:
        failure_attempts = [a for a in self.attempts if a.status.is_failure]
        return {
            "run_id": self.run_id,
            "mode": self.mode.value,
            "source_type": self.mode.source_type.value,
            "status": self.status.value,
            "display_label": self.display_label,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_ms": self.duration_ms,
            "collection_day": self.collection_day.isoformat(),
            "observation_count": self.observation_count,
            "routes_requested": self.routes_requested,
            "routes_with_data": self.routes_with_data,
            "horizons_requested": list(self.horizons_requested),
            "attempt_count": len(self.attempts),
            "failed_attempt_count": len(failure_attempts),
            "skipped_sources": list(self.skipped_sources),
            "dedupe": dict(self.dedupe_summary),
            "error_message": self.error_message,
            "collector_version": self.collector_version,
        }


class CollectionPipeline:
    """Orchestrates a collection cycle across the sources valid for the mode."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    # ── source selection ──

    def _select_sources(
        self, request: CollectionRequest
    ) -> tuple[list[FareSource], list[dict[str, str]]]:
        """
        Resolve sources for the run's mode.

        Filtering by ``mode.source_type`` is the first of the three guards against
        cross-mode substitution: in LIVE mode the simulator is not merely unused, it
        is not resolvable.
        """
        registry = get_registry()
        mode = request.mode

        requested = request.source_names
        if requested is None:
            if mode is CollectionMode.LIVE:
                requested = list(self.settings.scraper.enabled_sources)
            elif mode is CollectionMode.SIMULATED:
                requested = ["simulator"]
            else:
                requested = ["offline_fixture"]

        # LIVE sources never receive construction hints about collection time: their
        # provenance timestamp must be the real moment of retrieval.
        kwargs = {} if mode is CollectionMode.LIVE else dict(request.source_kwargs)

        sources, skipped = registry.resolve(requested, source_type=mode.source_type, **kwargs)

        if mode is CollectionMode.LIVE:
            permitted: list[FareSource] = []
            for src in sources:
                gate = check_source_permitted(src.capability.name)
                if not gate.is_permitted:
                    logger.warning(
                        f"Source '{src.capability.name}' blocked by source governance: {gate.reason}"
                    )
                    skipped.append({"source": src.capability.name, "reason": gate.reason})
                else:
                    permitted.append(src)
            sources = permitted

        return sources, skipped

    # ── execution ──

    async def run(self, request: CollectionRequest) -> CollectionRunResult:
        run_id = new_request_id()
        started = utc_now()
        collection_day = request.resolved_collection_day()

        invalid_horizons = sorted(
            set(request.booking_horizons) - set(SUPPORTED_BOOKING_HORIZONS)
        )
        if invalid_horizons or not request.booking_horizons:
            raise ValueError(
                "Collection horizons must be a non-empty subset of "
                f"{list(SUPPORTED_BOOKING_HORIZONS)}; got "
                f"{request.booking_horizons}"
            )

        # Historical live collection is impossible: an external quote retrieved now
        # cannot truthfully be stamped as if it was observed on another day.
        if request.mode is CollectionMode.LIVE and request.collection_day is not None:
            actual_day = started.date()
            if request.collection_day != actual_day:
                message = (
                    "LIVE collection_day must be the actual retrieval date "
                    f"{actual_day.isoformat()}; requested "
                    f"{request.collection_day.isoformat()}. Historical backfill is "
                    "available only in explicitly labelled SIMULATED/OFFLINE modes."
                )
                return CollectionRunResult(
                    run_id=run_id,
                    mode=request.mode,
                    status=CollectionStatus.UNAVAILABLE,
                    started_at=started,
                    finished_at=utc_now(),
                    collection_day=actual_day,
                    observations=[],
                    routes_requested=len(request.routes),
                    horizons_requested=list(request.booking_horizons),
                    error_message=message,
                )

        logger.info(
            f"Collection run {run_id[:8]} | mode={request.mode.value} | "
            f"{len(request.routes)} routes x {len(request.booking_horizons)} horizons"
        )

        sources, skipped = self._select_sources(request)

        if not sources:
            reasons = "; ".join(f"{s['source']}: {s['reason']}" for s in skipped) or (
                "no sources were requested"
            )
            message = (
                f"No usable source for mode {request.mode.value}. {reasons}. "
                f"No observations were produced and none were substituted."
            )
            logger.error(message)
            return CollectionRunResult(
                run_id=run_id,
                mode=request.mode,
                status=CollectionStatus.UNAVAILABLE,
                started_at=started,
                finished_at=utc_now(),
                collection_day=collection_day,
                observations=[],
                attempts=[],
                skipped_sources=skipped,
                routes_requested=len(request.routes),
                horizons_requested=list(request.booking_horizons),
                error_message=message,
            )

        target_routes = list(request.routes)
        if request.mode is CollectionMode.LIVE and sources:
            projected = len(target_routes) * len(request.booking_horizons)
            try:
                db = get_database()
                session = db.session()
                try:
                    for src in sources:
                        b_eval = await BudgetController.evaluate_budget(
                            session, src.capability.name, projected_count=projected
                        )
                        if not b_eval.can_proceed:
                            err_msg = f"QUOTA_EXHAUSTED: {b_eval.reason}"
                            logger.error(err_msg)
                            return CollectionRunResult(
                                run_id=run_id,
                                mode=request.mode,
                                status=CollectionStatus.FAILURE,
                                started_at=started,
                                finished_at=utc_now(),
                                collection_day=collection_day,
                                observations=[],
                                attempts=[],
                                skipped_sources=skipped,
                                routes_requested=len(request.routes),
                                horizons_requested=list(request.booking_horizons),
                                error_message=err_msg,
                            )
                        if b_eval.is_reduced_basket:
                            target_routes = [
                                r for r in target_routes
                                if r.route_code in TRACER_BASKET_ROUTE_CODES
                            ]
                            logger.warning(
                                f"Reduced basket mode: trimmed routes to {len(target_routes)} tracer routes."
                            )
                finally:
                    await session.close()
            except Exception as exc:
                logger.warning(f"Could not verify budget against DB: {exc}")

        semaphore = asyncio.Semaphore(max(1, self.settings.scraper.max_concurrent_requests))
        tasks = [
            self._collect_one(semaphore, source, request, route, horizon)
            for source in sources
            for route in target_routes
            for horizon in request.booking_horizons
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            for source in sources:
                try:
                    await source.aclose()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(f"Error closing source {source.capability.name}: {exc}")

        if request.mode is CollectionMode.LIVE:
            try:
                db = get_database()
                session = db.session()
                try:
                    for item in results:
                        if isinstance(item, SourceResult):
                            await BudgetController.record_usage(
                                session, item.source_name, count=1, success=item.success
                            )
                    await session.commit()
                finally:
                    await session.close()
            except Exception as exc:
                logger.warning(f"Could not record usage in DB: {exc}")

        observations: list[FareObservation] = []
        attempts: list[SourceAttempt] = []
        routes_with_data: set[int] = set()

        for item in results:
            if isinstance(item, BaseException):
                # A source that raises is a defect in that adapter. Recorded as a
                # failed attempt so the run stays auditable, and never as data.
                logger.error(f"Source raised during collection: {item!r}")
                attempts.append(
                    SourceAttempt(
                        source_name="unknown",
                        route_id=-1,
                        booking_horizon_days=-1,
                        status=CollectionStatus.FAILED,
                        observation_count=0,
                        error_message=f"{type(item).__name__}: {item}",
                        error_type="adapter_exception",
                    )
                )
                continue

            attempt, result = item
            attempts.append(attempt)
            if result.observations:
                observations.extend(result.observations)
                routes_with_data.add(attempt.route_id)

        # Cross-source dedup, meaningful whenever more than one source ran.
        dedupe_summary: dict[str, Any] = {}
        if observations:
            dedupe = deduplicate(
                observations,
                strategy=DedupeStrategy.SOURCE_PRIORITY,
                source_priority=[s.capability.name for s in sources],
            )
            observations = dedupe.kept
            dedupe_summary = dedupe.summary()

        status, error_message = self._resolve_status(
            request=request, observations=observations, attempts=attempts
        )

        result = CollectionRunResult(
            run_id=run_id,
            mode=request.mode,
            status=status,
            started_at=started,
            finished_at=utc_now(),
            collection_day=collection_day,
            observations=observations,
            attempts=attempts,
            skipped_sources=skipped,
            dedupe_summary=dedupe_summary,
            routes_requested=len(request.routes),
            routes_with_data=len(routes_with_data),
            horizons_requested=list(request.booking_horizons),
            error_message=error_message,
        )

        logger.info(
            f"Collection run {run_id[:8]} finished: status={status.value} | "
            f"{result.observation_count} observations | "
            f"{result.routes_with_data}/{result.routes_requested} routes | "
            f"label={result.display_label}"
        )
        return result

    async def _collect_one(
        self,
        semaphore: asyncio.Semaphore,
        source: FareSource,
        request: CollectionRequest,
        route: Route,
        horizon: int,
    ) -> tuple[SourceAttempt, SourceResult]:
        async with semaphore:
            departure = request.departure_date_for(horizon)
            try:
                result = await asyncio.wait_for(
                    source.search(
                        origin=route.origin_code,
                        destination=route.destination_code,
                        departure_date=departure,
                        passengers=request.passengers,
                        cabin=request.cabin,
                        route_id=route.route_id,
                        booking_horizon_days=horizon,
                    ),
                    timeout=self.settings.scraper.request_timeout_seconds
                    * max(1, self.settings.scraper.max_retries + 1)
                    + 30,
                )
            except asyncio.TimeoutError:
                result = SourceResult.failed(
                    source.capability.name,
                    f"Collection for {route.route_code} T+{horizon} exceeded the "
                    f"configured timeout.",
                    error_type="timeout",
                )

        return (
            SourceAttempt(
                source_name=result.source_name,
                route_id=route.route_id,
                booking_horizon_days=horizon,
                status=result.status,
                observation_count=result.observation_count,
                error_message=result.error_message,
                error_type=result.error_type,
                http_status=result.http_status,
                response_time_ms=result.response_time_ms,
                attempts=result.attempts,
            ),
            result,
        )

    def _resolve_status(
        self,
        request: CollectionRequest,
        observations: list[FareObservation],
        attempts: list[SourceAttempt],
    ) -> tuple[CollectionStatus, Optional[str]]:
        """
        Decide the run's status from what actually happened.

        Only a LIVE run that retrieved data may report SUCCESS. Simulated and offline
        runs report their own statuses, so downstream consumers cannot conflate them
        with collection.
        """
        failures = [a for a in attempts if a.status.is_failure]

        if not observations:
            reasons = sorted({a.error_type or "unknown" for a in failures})
            detail = "; ".join(
                dict.fromkeys(a.error_message for a in failures if a.error_message)
            )[:600]
            message = (
                f"{request.mode.value} collection produced no observations "
                f"({len(failures)} failed attempt(s); reasons: {reasons or ['none recorded']}). "
                f"{detail}"
            ).strip()

            if request.mode is CollectionMode.LIVE:
                # The explicit contract from the requirements: a failed live scrape is
                # a failure state, not an occasion to generate data.
                only_unavailable = failures and all(
                    a.status is CollectionStatus.UNAVAILABLE for a in failures
                )
                return (
                    CollectionStatus.UNAVAILABLE if only_unavailable else CollectionStatus.FAILED,
                    message,
                )
            return CollectionStatus.FAILED, message

        if request.mode is CollectionMode.SIMULATED:
            return CollectionStatus.SIMULATED, None
        if request.mode is CollectionMode.OFFLINE:
            return CollectionStatus.OFFLINE, None

        # LIVE with data.
        if failures:
            return (
                CollectionStatus.PARTIAL,
                f"{len(failures)} of {len(attempts)} collection attempt(s) failed; "
                f"the index for affected routes is computed from fewer observations.",
            )
        return CollectionStatus.SUCCESS, None


# ── convenience entry point ──

async def run_collection(
    mode: Optional[CollectionMode] = None,
    route_ids: Optional[list[int]] = None,
    custom_routes: Optional[list[Route]] = None,
    horizons: Optional[list[int]] = None,
    collection_day: Optional[date] = None,
    settings: Optional[Settings] = None,
    source_kwargs: Optional[dict[str, Any]] = None,
) -> CollectionRunResult:
    """Run one collection cycle using configured defaults for anything unspecified."""
    settings = settings or get_settings()

    if custom_routes:
        routes = list(custom_routes)
    else:
        basket = get_route_basket(settings.route_basket_path)
        routes = [r for r in basket.routes if r.is_active]
        if route_ids:
            wanted = set(route_ids)
            routes = [r for r in routes if r.route_id in wanted]

    request = CollectionRequest(
        mode=mode or settings.mode,
        routes=routes,
        booking_horizons=horizons or list(settings.scraper.booking_horizons),
        passengers=settings.scraper.passengers,
        cabin=settings.scraper.cabin,
        collection_day=collection_day,
        source_kwargs=dict(source_kwargs or {}),
    )
    return await CollectionPipeline(settings).run(request)
