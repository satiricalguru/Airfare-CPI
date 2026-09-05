"""
SIH26056 — Collection scheduler.

Replaces dead code. The previous module was imported by nothing, used a fixed
``asyncio.sleep(43200)`` interval rather than APScheduler despite claiming otherwise,
and the "10:00 and 18:00 IST" collection windows it documented did not exist.

This scheduler:

* uses APScheduler with a real cron trigger, in a configured timezone;
* runs at the configured collection hours (``SCHEDULER_COLLECTION_HOURS``);
* invokes the SAME :class:`IngestService` the manual trigger uses, so a scheduled run
  cannot behave differently from a manual one;
* is actually started from the API lifespan when ``SCHEDULER_ENABLED=true``, and
  reports honestly when it is not.

Everything configurable is configurable: frequency, windows, enabled sources, booking
horizons, retry policy and timeouts all come from :mod:`config`, which reads them from
the environment.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from config import Settings, get_settings
from db.engine import get_database
from engine.ingest_service import IngestResult, IngestService


class CollectionScheduler:
    """Runs collection cycles on the configured schedule."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._scheduler: Optional[AsyncIOScheduler] = None
        # Prevents a slow cycle from overlapping the next window: a second concurrent
        # run would double-collect and could double-count observations.
        self._lock = asyncio.Lock()
        self._last_result: Optional[IngestResult] = None
        self._last_error: Optional[str] = None
        self._run_count = 0
        self._last_success_at: Optional[datetime] = None
        self._last_duration_seconds: Optional[float] = None
        self._last_yield_count = 0
        self._selector_drift_detected = False

    # ── lifecycle ──

    @property
    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    def start(self) -> None:
        """Start the scheduler with a cron trigger per configured collection hour."""
        cfg = self.settings.scheduler

        if not cfg.enabled:
            logger.info("Scheduler is disabled; not starting")
            return

        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        try:
            timezone = ZoneInfo(cfg.timezone_name)
        except Exception as exc:
            logger.error(
                f"Unknown scheduler timezone {cfg.timezone_name!r} "
                f"({type(exc).__name__}); scheduler NOT started. Collection will only "
                f"run when triggered manually."
            )
            return

        if not cfg.collection_hours:
            logger.error(
                "SCHEDULER_ENABLED=true but SCHEDULER_COLLECTION_HOURS is empty; "
                "scheduler NOT started. An enabled scheduler with no windows would "
                "never collect while appearing active."
            )
            return

        self._scheduler = AsyncIOScheduler(timezone=timezone)

        hours = ",".join(str(h) for h in sorted(set(cfg.collection_hours)))
        self._scheduler.add_job(
            self.run_cycle,
            trigger=CronTrigger(hour=hours, minute=0, timezone=timezone),
            id="airfare_collection",
            name="Airfare collection cycle",
            # Skip a window rather than piling up missed runs after downtime: a burst
            # of catch-up collections would hammer the source.
            coalesce=True,
            max_instances=1,
            misfire_grace_time=1800,
        )

        self._scheduler.start()
        logger.info(
            f"Scheduler started: collection at {hours}:00 {cfg.timezone_name} "
            f"(mode={self.settings.mode.value}, "
            f"horizons={self.settings.scraper.booking_horizons})"
        )

    def stop(self) -> None:
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        self._scheduler = None

    def next_run_iso(self) -> Optional[str]:
        """Next scheduled fire time, or None when not scheduled."""
        if not self.is_running or self._scheduler is None:
            return None
        job = self._scheduler.get_job("airfare_collection")
        if job is None or job.next_run_time is None:
            return None
        return job.next_run_time.isoformat()

    # ── the scheduled work ──

    async def run_cycle(self) -> Optional[IngestResult]:
        """
        Run one collection cycle.

        Uses the same ingestion service as the manual trigger, so there is exactly one
        ingestion implementation and a scheduled run's provenance handling is identical.
        """
        if self._lock.locked():
            logger.warning(
                "A collection cycle is still running; skipping this window rather than "
                "starting a concurrent run"
            )
            return None

        async with self._lock:
            self._run_count += 1
            started = datetime.now()
            logger.info(
                f"Scheduled collection cycle #{self._run_count} starting "
                f"(mode={self.settings.mode.value})"
            )

            database = get_database()
            service = IngestService(self.settings)

            try:
                async with database.session() as session:
                    result = await asyncio.wait_for(
                        service.ingest(
                            session,
                            mode=self.settings.mode,
                            horizons=list(self.settings.scraper.booking_horizons),
                            compute_index=True,
                            triggered_by="scheduler",
                        ),
                        timeout=self.settings.scheduler.max_cycle_seconds,
                    )
                    await session.commit()

                self._last_result = result
                self._last_error = None

                elapsed = (datetime.now() - started).total_seconds()
                self._last_duration_seconds = round(elapsed, 2)
                self._selector_drift_detected = any(
                    getattr(a, "error_type", None) == "selector_drift" for a in result.run.attempts
                )

                if result.succeeded:
                    self._last_success_at = datetime.now(timezone.utc)
                    self._last_yield_count = result.observations_persisted
                    logger.info(
                        f"Scheduled cycle #{self._run_count} complete in {elapsed:.1f}s: "
                        f"{result.observations_persisted} observation(s) persisted, "
                        f"label={result.run.display_label}"
                    )
                else:
                    self._last_yield_count = 0
                    logger.warning(
                        f"Scheduled cycle #{self._run_count} produced no data in "
                        f"{elapsed:.1f}s: {result.run.error_message}. No data was "
                        f"substituted."
                    )
                return result

            except asyncio.TimeoutError:
                self._last_error = (
                    f"cycle exceeded the {self.settings.scheduler.max_cycle_seconds}s "
                    f"limit and was abandoned"
                )
                logger.error(f"Scheduled cycle #{self._run_count}: {self._last_error}")
                return None

            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                logger.exception(
                    f"Scheduled cycle #{self._run_count} failed: {self._last_error}"
                )
                return None

    # ── introspection ──

    def status(self) -> dict[str, Any]:
        """Scheduler state, surfaced on the collection status endpoint."""
        cfg = self.settings.scheduler
        return {
            "heartbeat": datetime.now(timezone.utc).isoformat(),
            "enabled": cfg.enabled,
            "running": self.is_running,
            "is_active_run": self._lock.locked(),
            "collection_hours": list(cfg.collection_hours),
            "timezone": cfg.timezone_name,
            "next_run": self.next_run_iso(),
            "max_cycle_seconds": cfg.max_cycle_seconds,
            "runs_completed": self._run_count,
            "last_success_at": self._last_success_at.isoformat() if self._last_success_at else None,
            "last_duration_seconds": self._last_duration_seconds,
            "observation_yield": self._last_yield_count,
            "selector_drift_status": "DRIFT_DETECTED" if self._selector_drift_detected else "HEALTHY",
            "last_error": self._last_error,
            "last_run": (
                self._last_result.run.to_dict() if self._last_result else None
            ),
            "mode": self.settings.mode.value,
            "booking_horizons": list(self.settings.scraper.booking_horizons),
            "enabled_sources": list(self.settings.scraper.enabled_sources),
        }
