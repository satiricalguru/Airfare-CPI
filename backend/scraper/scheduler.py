"""
SIH26056 — Airfare Scraping Scheduler

Orchestrates periodic price collection cycles using APScheduler:
- Default runs at 10:00 AM and 6:00 PM IST (aligning with MoSPI price collection standards)
- Cycles through all 25 DGCA basket routes
- Evaluates the 5 booking horizons (T+0, T+3, T+7, T+15, T+30)
- Triggers automatic validation and index recomputation
"""

import asyncio
from datetime import date, timedelta
from typing import Callable, Optional
from loguru import logger

from .scrapers.live_scraper import ResilientAirlineScraper
from .validator import FareValidator


class ScrapingScheduler:
    """
    Manages automated background scraping runs.
    """

    def __init__(
        self,
        routes: list[dict],
        on_data_collected: Optional[Callable[[list[dict]], None]] = None,
        booking_horizons: Optional[list[int]] = None,
    ):
        self.routes = routes
        self.on_data_collected = on_data_collected
        self.booking_horizons = booking_horizons or [0, 3, 7, 15, 30]
        self.scraper = ResilientAirlineScraper()
        self.validator = FareValidator()
        self.is_running = False

    async def run_single_cycle(self) -> dict:
        """
        Executes one complete collection pass over all routes and horizons.
        """
        logger.info(f"Starting scheduled scraping cycle across {len(self.routes)} routes...")
        today = date.today()
        all_collected = []

        for route in self.routes:
            for horizon in self.booking_horizons:
                dep_date = today + timedelta(days=horizon)
                result = await self.scraper.fetch_route_fares(
                    route_id=route["route_id"],
                    origin_code=route["origin_code"],
                    destination_code=route["destination_code"],
                    departure_date=dep_date,
                    booking_horizon=horizon,
                )
                if result.status == "success":
                    all_collected.extend(result.observations)

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
