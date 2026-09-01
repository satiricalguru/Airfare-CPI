"""
SIH26056 — Calibrated fare simulator.

A research instrument, not a data source. Its purpose is to exercise the index
pipeline with inputs whose true properties are known, so the mathematics can be
validated independently of live data availability.

Every observation it produces carries ``SourceType.SIMULATED`` and every result
reports ``CollectionStatus.SIMULATED``. ``SourceResult`` structurally refuses to let
it claim success, so nothing it emits can be presented as a collected fare.

What it deliberately does NOT license
------------------------------------
Because the generator injects a known annual drift and known festival multipliers,
an index computed from its output recovers the generator's own configuration. That
demonstrates the pipeline computes correctly. It says nothing about actual Indian
airfare inflation, and any figure derived from it must be labelled SIMULATED DATA.

Stable product catalogue
------------------------
Unlike the previous generator, which invented a fresh random flight number on every
call, this one builds a deterministic per-route product catalogue: fixed flights,
cabins, fare families, baggage and refundability. Products therefore persist across
collection days, which is what makes matched-model comparison meaningful — the
matched-model index needs the same product observable in two periods. Product entry
and exit are simulated explicitly and sparingly, so the new/disappeared-product code
paths get exercised too.

The horizon multipliers below are SIMULATOR CALIBRATION PARAMETERS. They describe how
this generator prices each advance-purchase horizon. They are not, and must never be
used as, methodological index weights: the horizon weighting policy lives in
``data/booking_horizons.json`` and is stated independently.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger

from config import get_settings
from provenance import (
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
)
from scraper.base import (
    BaseFareSource,
    CABIN_BUSINESS,
    CABIN_ECONOMY,
    FareObservation,
    SourceCapability,
    SourceResult,
)


SOURCE_NAME = "simulator"

# ── calibration parameters (simulator-internal; NOT index weights) ──

# Reference fare level per city pair: economy, direct, 30-day advance, in INR.
ROUTE_BASE_FARES: dict[str, int] = {
    "DEL-BOM": 5500, "DEL-BLR": 6200, "BOM-BLR": 4800, "DEL-HYD": 5800,
    "DEL-CCU": 5000, "BOM-HYD": 4200, "DEL-MAA": 6000, "BOM-CCU": 5500,
    "BLR-HYD": 3500, "DEL-GOI": 5200, "BOM-MAA": 4500, "BLR-CCU": 5800,
    "DEL-PNQ": 4800, "BOM-GOI": 3800, "DEL-AMD": 4000, "BLR-MAA": 3200,
    "DEL-JAI": 3500, "BOM-AMD": 3200, "DEL-LKO": 3800, "BLR-GOI": 3500,
    "HYD-CCU": 5200, "DEL-PAT": 4500, "BOM-JAI": 4200, "DEL-COK": 6500,
    "BOM-PNQ": 2800,
}
DEFAULT_BASE_FARE = 4500

# Advance-purchase price curve used by the generator.
HORIZON_MULTIPLIERS: dict[int, float] = {0: 2.5, 3: 2.0, 7: 1.5, 15: 1.2, 30: 1.0}

# Day-of-week effect on the departure date (0 = Monday).
DOW_MULTIPLIERS: dict[int, float] = {
    0: 1.05, 1: 1.00, 2: 1.00, 3: 1.02, 4: 1.10, 5: 1.08, 6: 1.12,
}

# Festival and holiday surges. These are seasonal effects, NOT inflation, and the
# index makes no attempt to remove them: seasonal adjustment is not implemented and
# is reported as such (see engine/seasonality.py).
SEASONAL_EVENTS: list[dict[str, Any]] = [
    {"name": "Diwali", "month": 10, "day_start": 20, "day_end": 31, "multiplier": 1.8},
    {"name": "Diwali", "month": 11, "day_start": 1, "day_end": 5, "multiplier": 1.6},
    {"name": "Christmas", "month": 12, "day_start": 20, "day_end": 31, "multiplier": 1.5},
    {"name": "NewYear", "month": 1, "day_start": 1, "day_end": 5, "multiplier": 1.4},
    {"name": "SummerPeak", "month": 5, "day_start": 1, "day_end": 31, "multiplier": 1.3},
    {"name": "SummerPeak", "month": 6, "day_start": 1, "day_end": 15, "multiplier": 1.25},
    {"name": "Holi", "month": 3, "day_start": 10, "day_end": 18, "multiplier": 1.3},
]

# Known annual drift injected by the generator. The index should recover roughly
# this figure from simulated data; that is a self-consistency check on the pipeline,
# not a measurement of the market.
ANNUAL_DRIFT_RATE = 0.05

AIRLINES: list[dict[str, Any]] = [
    {"code": "6E", "name": "IndiGo", "multiplier": 1.00, "baggage_kg": 15,
     "refundable": False, "families": ["SAVER", "FLEXI"]},
    {"code": "AI", "name": "Air India", "multiplier": 1.25, "baggage_kg": 25,
     "refundable": True, "families": ["VALUE", "FLEX"]},
    {"code": "SG", "name": "SpiceJet", "multiplier": 0.92, "baggage_kg": 15,
     "refundable": False, "families": ["REGULAR"]},
    {"code": "UK", "name": "Vistara", "multiplier": 1.30, "baggage_kg": 25,
     "refundable": True, "families": ["ECOLITE", "ECOFLEX"]},
    {"code": "QP", "name": "Akasa Air", "multiplier": 0.88, "baggage_kg": 15,
     "refundable": False, "families": ["SAVER"]},
]

MAJOR_ROUTES = {
    "DEL-BOM", "DEL-BLR", "BOM-BLR", "DEL-HYD", "DEL-CCU",
}


def describe() -> SourceCapability:
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="Calibrated fare simulator (research instrument)",
        source_type=SourceType.SIMULATED,
        enabled=True,
        disabled_reason=None,
        requires_credentials=False,
        homepage=None,
        terms_url=None,
        robots_url=None,
        compliance_note=(
            "Generates synthetic fares locally. No external system is contacted. Output "
            "is labelled SIMULATED DATA everywhere it appears and can never be reported "
            "as a collected observation."
        ),
        supports_cabin=(CABIN_ECONOMY, CABIN_BUSINESS),
        native_currency="INR",
    )


@dataclass(frozen=True)
class SimulatedProduct:
    """
    A fixed, purchasable product in the simulated market.

    Deterministic per route so it recurs across collection days, which is the
    precondition for matched-model comparison.
    """

    airline_code: str
    airline_name: str
    flight_number: str
    cabin_class: str
    fare_family: str
    stops: int
    is_refundable: bool
    baggage_kg: int
    price_multiplier: float
    # Simulated lifecycle. A product outside this window is absent from the market,
    # which exercises the new-product and disappeared-product index paths.
    available_from: Optional[date] = None
    available_until: Optional[date] = None

    def is_available_on(self, day: date) -> bool:
        if self.available_from and day < self.available_from:
            return False
        if self.available_until and day > self.available_until:
            return False
        return True


def _stable_rng(*parts: Any) -> np.random.Generator:
    """
    Deterministic RNG seeded from its arguments.

    Reproducibility matters here: the same route and day must always yield the same
    catalogue and the same noise draw, so a simulated run can be replayed exactly.
    """
    key = "|".join(str(p) for p in parts).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
    return np.random.default_rng(seed)


def build_product_catalogue(
    route_code: str,
    seed: int,
    include_lifecycle_events: bool = True,
) -> list[SimulatedProduct]:
    """
    Deterministic product catalogue for a route.

    Major trunk routes carry every carrier; thinner routes carry a stable subset.
    """
    rng = _stable_rng("catalogue", route_code, seed)

    if route_code in MAJOR_ROUTES or _reverse(route_code) in MAJOR_ROUTES:
        carriers = AIRLINES
    else:
        count = int(rng.integers(3, min(5, len(AIRLINES)) + 1))
        others = list(rng.choice(AIRLINES[1:], size=count - 1, replace=False))
        carriers = [AIRLINES[0]] + others

    products: list[SimulatedProduct] = []
    for carrier in carriers:
        for family_index, family in enumerate(carrier["families"]):
            flight_digits = int(rng.integers(100, 9999))
            # Flexible families cost more than the saver family: a real quality
            # difference, and the reason the index must not compare across families.
            family_premium = 1.0 + 0.18 * family_index
            products.append(
                SimulatedProduct(
                    airline_code=carrier["code"],
                    airline_name=carrier["name"],
                    flight_number=f"{carrier['code']}-{flight_digits}",
                    cabin_class=CABIN_ECONOMY,
                    fare_family=family,
                    stops=0,
                    # Flexible fares are refundable regardless of carrier default.
                    is_refundable=bool(carrier["refundable"] or family_index > 0),
                    baggage_kg=int(carrier["baggage_kg"]),
                    price_multiplier=float(carrier["multiplier"]) * family_premium,
                )
            )

        # One connecting product per carrier on thinner routes: a genuinely different
        # product, kept distinct in the product key rather than pooled with non-stops.
        if route_code not in MAJOR_ROUTES and rng.random() < 0.5:
            products.append(
                SimulatedProduct(
                    airline_code=carrier["code"],
                    airline_name=carrier["name"],
                    flight_number=f"{carrier['code']}-{int(rng.integers(100, 9999))}",
                    cabin_class=CABIN_ECONOMY,
                    fare_family=carrier["families"][0],
                    stops=1,
                    is_refundable=bool(carrier["refundable"]),
                    baggage_kg=int(carrier["baggage_kg"]),
                    # Connecting itineraries price below non-stops.
                    price_multiplier=float(carrier["multiplier"]) * 0.82,
                )
            )

    if include_lifecycle_events and products and rng.random() < 0.25:
        # Give one product a bounded lifetime so entry/exit handling is exercised.
        victim = int(rng.integers(0, len(products)))
        product = products[victim]
        products[victim] = SimulatedProduct(
            **{
                **product.__dict__,
                "available_until": date(2026, 8, 20),
            }
        )

    return products


def _reverse(route_code: str) -> str:
    origin, _, destination = route_code.partition("-")
    return f"{destination}-{origin}"


def base_fare_for(route_code: str) -> int:
    return ROUTE_BASE_FARES.get(
        route_code, ROUTE_BASE_FARES.get(_reverse(route_code), DEFAULT_BASE_FARE)
    )


def seasonal_multiplier(day: date) -> float:
    for event in SEASONAL_EVENTS:
        if day.month == event["month"] and event["day_start"] <= day.day <= event["day_end"]:
            return float(event["multiplier"])
    return 1.0


class SimulatorFareSource(BaseFareSource):
    """Fare source that generates calibrated synthetic observations."""

    def __init__(
        self,
        seed: Optional[int] = None,
        drift_origin: Optional[date] = None,
        annual_drift_rate: float = ANNUAL_DRIFT_RATE,
        noise_sigma: float = 0.06,
        collection_datetime: Optional[datetime] = None,
    ):
        super().__init__(describe())
        settings = get_settings()
        self.seed = seed if seed is not None else settings.simulator_seed
        self.drift_origin = drift_origin or settings.index.base_period_start
        self.annual_drift_rate = annual_drift_rate
        # Modest noise: enough to be realistic, small enough that the matched-model
        # index still recovers the injected drift over a short series.
        self.noise_sigma = noise_sigma
        self._collection_datetime = collection_datetime

    def _now(self) -> datetime:
        return self._collection_datetime or datetime.now(timezone.utc)

    async def _search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
    ) -> SourceResult:
        collected_at = self._now()
        observations = self.generate(
            route_id=route_id,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            booking_horizon_days=booking_horizon_days,
            collection_datetime=collected_at,
        )

        if not observations:
            return SourceResult.failed(
                SOURCE_NAME,
                f"Simulator produced no products for {origin}-{destination} "
                f"T+{booking_horizon_days} on {departure_date.isoformat()}.",
                error_type="no_products_available",
            )

        return SourceResult(
            source_name=SOURCE_NAME,
            status=CollectionStatus.SIMULATED,
            observations=tuple(observations),
            request_id=observations[0].provenance.request_id,
            # No network round trip occurred, so reporting a response time would
            # fabricate a latency metric.
            response_time_ms=None,
        )

    def generate(
        self,
        route_id: int,
        origin: str,
        destination: str,
        departure_date: date,
        booking_horizon_days: int,
        collection_datetime: Optional[datetime] = None,
    ) -> list[FareObservation]:
        """Generate observations for one route / horizon / collection moment."""
        collected_at = collection_datetime or self._now()
        collection_day = collected_at.date()
        route_code = f"{origin}-{destination}"

        catalogue = build_product_catalogue(route_code, self.seed)
        available = [p for p in catalogue if p.is_available_on(collection_day)]
        if not available:
            return []

        base_fare = base_fare_for(route_code)
        horizon_multiplier = HORIZON_MULTIPLIERS.get(booking_horizon_days, 1.0)
        dow_multiplier = DOW_MULTIPLIERS.get(departure_date.weekday(), 1.0)
        season_multiplier = seasonal_multiplier(departure_date)

        days_since_origin = (collection_day - self.drift_origin).days
        daily_drift = (1.0 + self.annual_drift_rate) ** (1.0 / 365.0)
        drift = daily_drift ** days_since_origin

        provenance = DataProvenance(
            source_type=SourceType.SIMULATED,
            source_name=SOURCE_NAME,
            collection_timestamp=collected_at,
            request_id=new_request_id(),
            source_url=None,
            raw_payload_hash=None,
            notes={
                "seed": self.seed,
                "annual_drift_rate": self.annual_drift_rate,
                "drift_origin": self.drift_origin.isoformat(),
                "seasonal_multiplier": season_multiplier,
                "horizon_multiplier": horizon_multiplier,
                "calibration_note": (
                    "Synthetic fares. Injected drift and festival multipliers mean any "
                    "index computed from these values reflects generator configuration, "
                    "not the Indian airfare market."
                ),
            },
        )

        observations: list[FareObservation] = []
        for product in available:
            rng = _stable_rng(
                "price",
                self.seed,
                route_code,
                product.flight_number,
                product.fare_family,
                product.stops,
                booking_horizon_days,
                collection_day.isoformat(),
            )

            fare = (
                base_fare
                * product.price_multiplier
                * horizon_multiplier
                * dow_multiplier
                * season_multiplier
                * drift
            )

            noise = float(np.clip(rng.normal(1.0, self.noise_sigma), 0.75, 1.35))
            fare *= noise

            # Occasional revenue-management jumps and flash sales, kept rare so they
            # read as outliers to the validator rather than as the central tendency.
            if rng.random() < 0.015:
                fare *= float(rng.uniform(1.8, 2.6))
            elif rng.random() < 0.02:
                fare *= float(rng.uniform(0.55, 0.75))

            fare = round(max(fare, 800.0), 2)
            tax_share = float(rng.uniform(0.20, 0.30))
            taxes = round(fare * tax_share, 2)

            observations.append(
                FareObservation(
                    route_id=route_id,
                    origin_code=origin,
                    destination_code=destination,
                    departure_date=departure_date,
                    booking_horizon_days=booking_horizon_days,
                    airline_code=product.airline_code,
                    airline_name=product.airline_name,
                    flight_number=product.flight_number,
                    cabin_class=product.cabin_class,
                    fare_family=product.fare_family,
                    fare_total=fare,
                    fare_base=round(fare - taxes, 2),
                    fare_taxes=taxes,
                    currency="INR",
                    stops=product.stops,
                    is_refundable=product.is_refundable,
                    baggage_kg=product.baggage_kg,
                    seats_available=int(rng.integers(1, 9)),
                    source_currency="INR",
                    source_fare_total=fare,
                    source_offer_id=None,
                    provenance=provenance,
                )
            )

        return observations

    def generate_history(
        self,
        routes: list[dict[str, Any]],
        start_date: date,
        end_date: date,
        booking_horizons: list[int],
        collection_hour: int = 10,
    ) -> list[FareObservation]:
        """
        Backfill a simulated series, one collection per day.

        Used to seed a research/demo database so the methodology can be shown over a
        span of dates without waiting for real collection to accumulate.
        """
        all_obs: list[FareObservation] = []
        current = start_date

        while current <= end_date:
            collected_at = datetime.combine(
                current, datetime.min.time().replace(hour=collection_hour), tzinfo=timezone.utc
            )
            for route in routes:
                for horizon in booking_horizons:
                    all_obs.extend(
                        self.generate(
                            route_id=route["route_id"],
                            origin=route["origin_code"],
                            destination=route["destination_code"],
                            departure_date=current + timedelta(days=horizon),
                            booking_horizon_days=horizon,
                            collection_datetime=collected_at,
                        )
                    )
            current += timedelta(days=1)

        logger.info(
            f"Simulator generated {len(all_obs)} synthetic observations from "
            f"{start_date} to {end_date} across {len(routes)} routes "
            f"x {len(booking_horizons)} horizons (SIMULATED DATA)"
        )
        return all_obs


def create(**kwargs: Any) -> SimulatorFareSource:
    """Registry factory."""
    return SimulatorFareSource(**kwargs)
