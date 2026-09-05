"""
SIH26056 — Ingestion service.

The single traceable path from a source to a published figure:

    source -> collection run -> validation -> persistence -> index recomputation

Used by both the manual trigger endpoint and the scheduler, so there is exactly one
ingestion implementation and a scheduled run cannot behave differently from a manual
one.

Validator state is loaded before validation and saved after, so IQR reference
distributions are continuous across restarts and an outlier decision is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from db import repository as repo
from engine.index_service import IndexComputationResult, IndexService
from provenance import CollectionMode, CollectionStatus, SOURCE_UNAVAILABLE_LABEL
from scraper.pipeline import CollectionRunResult, run_collection
from scraper.validator import FareValidator, ValidationBatchResult


@dataclass
class IngestResult:
    """Outcome of one ingestion cycle."""

    run: CollectionRunResult
    validation: Optional[ValidationBatchResult] = None
    index: Optional[IndexComputationResult] = None
    observations_persisted: int = 0
    anomalies_opened: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> CollectionStatus:
        return self.run.status

    @property
    def succeeded(self) -> bool:
        """
        True only when observations were actually obtained.

        A LIVE run that collected nothing is not a success, regardless of whether the
        process completed without raising.
        """
        return self.run.observation_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection": self.run.to_dict(),
            "validation": self.validation.summary() if self.validation else None,
            "index": self.index.to_dict() if self.index else None,
            "observations_persisted": self.observations_persisted,
            "anomalies_opened": self.anomalies_opened,
            "errors": list(self.errors),
            # The honest badge for this cycle, computed once here so every consumer
            # renders the same thing.
            "display_label": self.run.display_label,
            "data_available": self.succeeded,
        }


class IngestService:
    """Runs a full ingestion cycle and persists everything it produced."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    async def ingest(
        self,
        session: AsyncSession,
        mode: Optional[CollectionMode] = None,
        route_ids: Optional[list[int]] = None,
        custom_routes: Optional[list[Any]] = None,
        horizons: Optional[list[int]] = None,
        collection_day: Optional[date] = None,
        compute_index: bool = True,
        triggered_by: str = "manual",
        source_kwargs: Optional[dict[str, Any]] = None,
    ) -> IngestResult:
        """
        Collect, validate, persist, and optionally recompute indices.

        A failed collection is still persisted as a failed run: recording the gap is
        how coverage stays honest instead of the gap simply not appearing anywhere.
        """
        effective_mode = mode or self.settings.mode

        run = await run_collection(
            mode=effective_mode,
            route_ids=route_ids,
            custom_routes=custom_routes,
            horizons=horizons,
            collection_day=collection_day,
            settings=self.settings,
            source_kwargs=source_kwargs,
        )

        result = IngestResult(run=run)

        if not run.observations:
            # Persist the failed run so the collection history shows the attempt.
            empty = ValidationBatchResult()
            await repo.save_collection_run(
                session, run, empty, triggered_by=triggered_by
            )
            result.validation = empty
            message = run.error_message or (
                f"{effective_mode.value} collection produced no observations."
            )
            result.errors.append(message)
            logger.warning(
                f"Ingestion produced no data ({run.status.value}): {message} "
                f"Label={SOURCE_UNAVAILABLE_LABEL}. No data has been substituted."
            )
            return result

        # ── validation, with reference distributions restored from storage ──
        validator = FareValidator(self.settings.validation)
        stored_state = await repo.load_validator_state(session)
        if stored_state:
            validator.restore_state(stored_state)

        validation = validator.validate_batch(run.observations)
        result.validation = validation

        await repo.save_validator_state(session, validator.export_state())

        persisted = await repo.save_collection_run(
            session, run, validation, triggered_by=triggered_by
        )
        result.observations_persisted = persisted.observations_persisted
        result.anomalies_opened = len(validation.flagged)

        # ── index recomputation from stored data ──
        if compute_index:
            try:
                index_service = IndexService(self.settings)
                recompute_day = collection_day or (run.collection_day if run else None)
                result.index = await index_service.recompute(
                    session,
                    start_date=recompute_day,
                    end_date=recompute_day,
                    source_type=effective_mode.source_type,
                    reason=(
                        f"recomputation after collection run {run.run_id[:8]} "
                        f"({effective_mode.value}, triggered by {triggered_by})"
                    ),
                )
            except Exception as exc:
                # Index failure must not discard the collected observations: they are
                # already persisted and can be recomputed later.
                message = f"index recomputation failed: {type(exc).__name__}: {exc}"
                logger.exception(message)
                result.errors.append(message)

        logger.info(
            f"Ingestion complete ({run.status.value}): "
            f"{result.observations_persisted} persisted, "
            f"{result.anomalies_opened} anomalies opened, "
            f"label={run.display_label}"
        )
        return result

    async def backfill_simulated_history(
        self,
        session: AsyncSession,
        start_date: date,
        end_date: date,
        route_ids: Optional[list[int]] = None,
        horizons: Optional[list[int]] = None,
    ) -> list[IngestResult]:
        """
        Seed a research database with a simulated series.

        Explicitly SIMULATED mode, one collection run per day, every observation
        labelled SIMULATED DATA. Provided so the methodology can be demonstrated over a
        span of dates without waiting for real collection to accumulate; it is never
        invoked as a fallback for a failed live run.
        """
        results: list[IngestResult] = []
        current = start_date

        while current <= end_date:
            # Stamp the simulated collection at 10:00 UTC on the day being seeded, so
            # the series carries the dates it represents. This is only legitimate
            # because the data is synthetic and labelled SIMULATED; a live observation's
            # timestamp is always the real retrieval moment.
            collected_at = datetime.combine(
                current, time(hour=10), tzinfo=timezone.utc
            )
            results.append(
                await self.ingest(
                    session,
                    mode=CollectionMode.SIMULATED,
                    route_ids=route_ids,
                    horizons=horizons,
                    collection_day=current,
                    # Recompute once at the end rather than per day: a single pass over
                    # the completed series is both faster and produces the same values.
                    compute_index=False,
                    triggered_by="simulated_backfill",
                    source_kwargs={"collection_datetime": collected_at},
                )
            )
            current += timedelta(days=1)

        logger.info(
            f"Simulated backfill: {len(results)} day(s) from {start_date} to {end_date} "
            f"(SIMULATED DATA)"
        )
        return results
