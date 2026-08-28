"""
SIH26056 — Airfare Scraping Scheduler

Orchestrates periodic price collection cycles using APScheduler:
- Default runs at 10:00 AM and 6:00 PM IST (aligning with MoSPI price collection standards)
- Cycles through all 25 DGCA basket routes
- Evaluates the 5 booking horizons (T+0, T+3, T+7, T+15, T+30)
- Triggers automatic validation and index recomputation
"""

import os
import asyncio
from datetime import date, timedelta
from typing import Callable, Optional
from loguru import logger

from .scrapers.live_scraper import ResilientAirlineScraper
from .validator import FareValidator


class ScrapingScheduler:
    """
    Manages automated periodic background scraping runs with controlled concurrency.
    """

    def __init__(
        self,
        routes: list[dict],
        on_data_collected: Optional[Callable[[list[dict]], None]] = None,
        booking_horizons: Optional[list[int]] = None,
        interval_seconds: Optional[int] = None,
        max_concurrency: int = 6,
    ):
        self.routes = routes
        self.on_data_collected = on_data_collected
        self.booking_horizons = booking_horizons or [0, 3, 7, 15, 30]
        self.interval_seconds = interval_seconds or int(os.getenv("SCRAPER_INTERVAL_SECONDS", "43200"))
        self.max_concurrency = max_concurrency
        self.scraper = ResilientAirlineScraper()
        self.validator = FareValidator()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def _fetch_with_semaphore(self, sem: asyncio.Semaphore, route: dict, horizon: int, today: date):
        dep_date = today + timedelta(days=horizon)
        async with sem:
            return await self.scraper.fetch_route_fares(
                route_id=route["route_id"],
                origin_code=route["origin_code"],
                destination_code=route["destination_code"],
                departure_date=dep_date,
                booking_horizon=horizon,
            )

    async def run_single_cycle(self) -> dict:
        """
        Executes one complete collection pass over all routes and horizons using concurrent worker tasks.
        """
        logger.info(f"Starting concurrent scraping cycle across {len(self.routes)} routes & {len(self.booking_horizons)} horizons...")
        today = date.today()
        sem = asyncio.Semaphore(self.max_concurrency)

        tasks = [
            self._fetch_with_semaphore(sem, route, horizon, today)
            for route in self.routes
            for horizon in self.booking_horizons
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_collected = []

        for r in results:
            if not isinstance(r, Exception) and getattr(r, "status", None) == "success":
                all_collected.extend(r.observations)

        # Validate the batch
        accepted, flagged, excluded = self.validator.validate_batch(all_collected)
        valid_obs = accepted + flagged

        if self.on_data_collected and valid_obs:
            self.on_data_collected(valid_obs)

        summary = {
            "total_collected": len(all_collected),
            "accepted": len(accepted),
            "flagged": len(flagged),
            "excluded": len(excluded),
            "timestamp": today.isoformat(),
        }
        logger.info(f"Scheduled scraping cycle complete: {summary}")
        return summary

    async def _loop(self):
        while self.is_running:
            try:
                await self.run_single_cycle()
            except Exception as e:
                logger.error(f"Error during scheduled scraping run: {e}")
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        """Starts the recurring background scraping loop."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._loop())
            logger.info(f"Scraping scheduler background loop started (interval: {self.interval_seconds}s)")

    def stop(self):
        """Stops the background scheduler."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Scraping scheduler stopped")
