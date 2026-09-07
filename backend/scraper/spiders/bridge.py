"""
SIH26056 — Scrapy Runner Bridge.

Enables the core pipeline and test harness to dispatch Scrapy spiders
and collect structured FareObservation outputs.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from scraper.base import FareObservation
from scraper.spiders.flight_spiders import (
    CleartripSpider,
    IndigoSpider,
    MakeMyTripSpider,
    SCRAPY_AVAILABLE,
    ScrapedFlightItem,
)
from scraper.spiders.pipelines import CPIFarePipeline


class ScrapySpiderBridge:
    """Dispatches flight spiders and processes items through the CPI pipeline."""

    def __init__(self):
        self.pipeline = CPIFarePipeline()

    def run_direct_extraction(
        self,
        portal: str,
        origin: str,
        destination: str,
        departure_date: date,
        raw_card_texts: list[str],
        route_id: int = 1,
        booking_horizon_days: int = 7,
    ) -> list[FareObservation]:
        """Direct extraction bridge converting card texts through the spider parser and pipeline."""
        observations: list[FareObservation] = []
        for text in raw_card_texts:
            import re
            price_match = re.search(r"₹\s*([\d,]+)", text)
            if not price_match:
                continue
            try:
                fare = float(price_match.group(1).replace(",", ""))
            except ValueError:
                continue

            times = re.findall(r"(\d{1,2}:\d{2})", text)
            dep_time = times[0] if times else "08:00"

            item = ScrapedFlightItem(
                portal=portal,
                airline_code="6E" if "6E" in text.upper() or "INDIGO" in text.upper() else "AI",
                airline_name="IndiGo" if "6E" in text.upper() or "INDIGO" in text.upper() else "Air India",
                flight_number=f"6E-{origin}{destination}",
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                departure_time=dep_time,
                total_fare=fare,
                stops=0,
                raw_snippet=text[:200],
            )
            obs = self.pipeline.process_item(
                item=item,
                route_id=route_id,
                booking_horizon_days=booking_horizon_days,
            )
            if obs:
                observations.append(obs)

        return observations
