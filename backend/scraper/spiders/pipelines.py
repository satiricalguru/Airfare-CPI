"""
SIH26056 — Scrapy CPI Item Pipeline.

Processes items yielded by Scrapy flight spiders:
- Validates fare ranges (removes negative, zero, or extreme outlier fares).
- Decomposes statutory Indian civil aviation fees using AERA Tariff Orders.
- Converts items into valid FareObservation records with full DataProvenance.
"""

from __future__ import annotations

from typing import Any, Optional

from provenance import (
    AcquisitionMethod,
    DataProvenance,
    new_request_id,
    utc_now,
)
from scraper.base import FareObservation, classify_time_band
from scraper.spiders.flight_spiders import ScrapedFlightItem
from scraper.tariff_orders import unbundle_statutory_tariff


class CPIFarePipeline:
    """Scrapy pipeline unbundling fees and producing FareObservations."""

    def process_item(
        self,
        item: ScrapedFlightItem,
        spider: Any = None,
        route_id: int = 1,
        booking_horizon_days: int = 7,
    ) -> Optional[FareObservation]:
        if item.total_fare < 500 or item.total_fare > 95000:
            return None

        decomp = unbundle_statutory_tariff(
            total_fare=item.total_fare,
            origin_code=item.origin,
            convenience_fee=350.0,
        )

        dep_time_band = classify_time_band(item.departure_time)

        prov = DataProvenance.for_web_scrape(
            source_name=item.portal,
            source_url=f"scrapy://{item.portal}/{item.origin}-{item.destination}",
            request_id=new_request_id(),
            raw_payload=f"{item.flight_number}|{item.airline_code}|{item.total_fare}|{item.departure_time}",
            timestamp=utc_now(),
            notes={
                "collector": "ScrapyPipeline",
                "spider": getattr(spider, "name", "unknown_spider"),
                "horizon": booking_horizon_days,
                "dep_time": item.departure_time,
                "time_band": dep_time_band,
                "decomposition_method": decomp["decomposition_method"],
                "is_estimated": decomp["is_estimated"],
                "is_surrogate": item.is_surrogate,
            },
        )

        return FareObservation(
            route_id=route_id,
            origin_code=item.origin,
            destination_code=item.destination,
            departure_date=item.departure_date,
            booking_horizon_days=booking_horizon_days,
            airline_code=item.airline_code,
            airline_name=item.airline_name,
            flight_number=item.flight_number,
            cabin_class=item.cabin,
            fare_family=item.fare_family,
            stops=item.stops,
            is_refundable=False,
            baggage_kg=15,
            fare_base=decomp["base_fare"],
            fare_taxes=decomp["taxes"],
            fare_udf=decomp["udf"],
            fare_convenience=decomp["convenience"],
            fare_total=item.total_fare,
            currency="INR",
            source_currency="INR",
            source_fare_total=item.total_fare,
            seats_available=None,
            dep_time=item.departure_time,
            dep_time_band=dep_time_band,
            provenance=prov,
        )
