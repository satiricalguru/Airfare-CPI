"""
SIH26056 — Mock Fare Data Generator

Generates statistically realistic synthetic airfare data for:
1. Demo reliability (primary demo path — works even if live scraping fails)
2. Statistical validation (test index properties with known inputs)
3. Development (build dashboard/API without waiting for real scrapes)

The generator produces fare observations that realistically model:
- Route-specific base fare levels (DEL-BOM costs more than DEL-JAI)
- Booking-window price curves (T+0 >> T+30)
- Airline-specific pricing patterns (LCC vs full-service)
- Day-of-week effects (weekend premium)
- Seasonal patterns (Diwali spike, summer surge)
- Random noise and occasional fare spikes
- Gradual inflation trends over time
"""

import numpy as np
import json
from datetime import date, datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger


@dataclass
class FareObservation:
    """A single fare observation — the atomic unit of the system."""
    route_id: int
    origin_code: str
    destination_code: str
    airline_code: str
    airline_name: str
    flight_number: str
    departure_date: str       # ISO format
    booking_horizon_days: int
    cabin_class: str
    fare_base: float
    fare_taxes: float
    fare_total: float
    is_direct: bool
    stops: int
    baggage_kg: int
    is_refundable: bool
    fare_family: str
    source_platform: str
    scraper_version: str
    scrape_timestamp: str     # ISO format


# Route-specific base fares (economy, direct, T+30 reference in ₹)
ROUTE_BASE_FARES = {
    "DEL-BOM": 5500, "DEL-BLR": 6200, "BOM-BLR": 4800, "DEL-HYD": 5800,
    "DEL-CCU": 5000, "BOM-HYD": 4200, "DEL-MAA": 6000, "BOM-CCU": 5500,
    "BLR-HYD": 3500, "DEL-GOI": 5200, "BOM-MAA": 4500, "BLR-CCU": 5800,
    "DEL-PNQ": 4800, "BOM-GOI": 3800, "DEL-AMD": 4000, "BLR-MAA": 3200,
    "DEL-JAI": 3500, "BOM-AMD": 3200, "DEL-LKO": 3800, "BLR-GOI": 3500,
    "HYD-CCU": 5200, "DEL-PAT": 4500, "BOM-JAI": 4200, "DEL-COK": 6500,
    "BOM-PNQ": 2800,
}

# Airline characteristics
AIRLINES = [
    {
        "code": "6E", "name": "IndiGo", "type": "lcc",
        "price_multiplier": 1.0, "market_share": 0.55,
        "baggage_kg": 15, "refundable": False,
        "fare_families": ["Saver", "Flexi", "Flexi Plus"],
    },
    {
        "code": "AI", "name": "Air India", "type": "fsc",
        "price_multiplier": 1.25, "market_share": 0.12,
        "baggage_kg": 25, "refundable": True,
        "fare_families": ["Value", "Flex", "Premium"],
    },
    {
        "code": "SG", "name": "SpiceJet", "type": "lcc",
        "price_multiplier": 0.92, "market_share": 0.10,
        "baggage_kg": 15, "refundable": False,
        "fare_families": ["Regular", "Flex Fare"],
    },
    {
        "code": "UK", "name": "Vistara", "type": "fsc",
        "price_multiplier": 1.30, "market_share": 0.08,
        "baggage_kg": 25, "refundable": True,
        "fare_families": ["Economy Lite", "Economy Flexi", "Economy Premium"],
    },
    {
        "code": "QP", "name": "Akasa Air", "type": "lcc",
        "price_multiplier": 0.88, "market_share": 0.08,
        "baggage_kg": 15, "refundable": False,
        "fare_families": ["Saver", "Flexi", "Super Saver"],
    },
    {
        "code": "I5", "name": "AirAsia India", "type": "lcc",
        "price_multiplier": 0.90, "market_share": 0.07,
        "baggage_kg": 15, "refundable": False,
        "fare_families": ["Value Pack", "Premium Flex"],
    },
]

# Booking horizon multipliers (how much more expensive vs. T+30)
HORIZON_MULTIPLIERS = {
    0: 2.5,   # Same-day: 2.5x base
    3: 2.0,   # 3-day: 2.0x
    7: 1.5,   # 7-day: 1.5x
    15: 1.2,  # 15-day: 1.2x
    30: 1.0,  # 30-day: base price
}

# Day-of-week multipliers (0=Mon, 6=Sun)
DOW_MULTIPLIERS = {
    0: 1.05,  # Monday: slightly higher (business)
    1: 1.00,  # Tuesday: lowest
    2: 1.00,  # Wednesday
    3: 1.02,  # Thursday
    4: 1.10,  # Friday: weekend getaway premium
    5: 1.08,  # Saturday
    6: 1.12,  # Sunday: return travel premium
}

# Festival/seasonal spikes (month, day_start, day_end, multiplier)
SEASONAL_EVENTS = [
    # Diwali period (approximate — varies yearly)
    {"name": "Diwali", "month": 10, "day_start": 20, "day_end": 31, "multiplier": 1.8},
    {"name": "Diwali", "month": 11, "day_start": 1, "day_end": 5, "multiplier": 1.6},
    # Christmas/New Year
    {"name": "Christmas", "month": 12, "day_start": 20, "day_end": 31, "multiplier": 1.5},
    {"name": "NewYear", "month": 1, "day_start": 1, "day_end": 5, "multiplier": 1.4},
    # Summer holidays
    {"name": "Summer", "month": 5, "day_start": 1, "day_end": 31, "multiplier": 1.3},
    {"name": "Summer", "month": 6, "day_start": 1, "day_end": 15, "multiplier": 1.25},
    # Holi
    {"name": "Holi", "month": 3, "day_start": 10, "day_end": 18, "multiplier": 1.3},
]


class MockFareGenerator:
    """
    Generates realistic synthetic airfare data.
    
    This is not a toy — the generator models real airline pricing dynamics
    to produce data that exercises the full statistical pipeline.
    """
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.flight_counter = 0
    
    def generate_fare(
        self,
        route_id: int,
        origin_code: str,
        destination_code: str,
        departure_date: date,
        booking_horizon: int,
        scrape_time: Optional[datetime] = None,
        inflation_rate: float = 0.05,  # 5% annual inflation
        days_since_base: int = 0,
    ) -> list[FareObservation]:
        """
        Generate fare observations for one route/date/horizon combination
        across multiple airlines.
        
        Returns one observation per airline that operates this route.
        """
        route_key = f"{origin_code}-{destination_code}"
        base_fare = ROUTE_BASE_FARES.get(
            route_key,
            ROUTE_BASE_FARES.get(f"{destination_code}-{origin_code}", 4500)
        )
        
        if scrape_time is None:
            scrape_time = datetime.now()
        
        observations = []
        
        # Select airlines for this route (not all airlines fly all routes)
        route_airlines = self._select_airlines_for_route(route_key)
        
        for airline in route_airlines:
            # Base fare with airline multiplier
            fare = base_fare * airline["price_multiplier"]
            
            # Booking horizon effect (major factor)
            fare *= HORIZON_MULTIPLIERS.get(booking_horizon, 1.0)
            
            # Day-of-week effect
            fare *= DOW_MULTIPLIERS.get(departure_date.weekday(), 1.0)
            
            # Seasonal/festival effect
            fare *= self._get_seasonal_multiplier(departure_date)
            
            # Gradual inflation
            daily_inflation = (1 + inflation_rate) ** (1 / 365)
            fare *= daily_inflation ** days_since_base
            
            # Random noise (±15% — airfares are volatile)
            noise = self.rng.normal(1.0, 0.15)
            noise = max(0.5, min(2.0, noise))  # Clip extreme noise
            fare *= noise
            
            # Occasional fare spikes (2% chance of 2-4x spike)
            if self.rng.random() < 0.02:
                spike = self.rng.uniform(2.0, 4.0)
                fare *= spike
            
            # Occasional deep discount (3% chance — flash sales)
            if self.rng.random() < 0.03:
                discount = self.rng.uniform(0.4, 0.7)
                fare *= discount
            
            fare = max(fare, 800)  # Floor: ₹800 minimum
            fare = round(fare, 2)
            
            # Compute base/taxes split (taxes ~20-30% of total)
            tax_pct = self.rng.uniform(0.20, 0.30)
            fare_taxes = round(fare * tax_pct, 2)
            fare_base = round(fare - fare_taxes, 2)
            
            # Generate flight number
            self.flight_counter += 1
            flight_num = f"{airline['code']}-{self.rng.integers(100, 9999)}"
            
            obs = FareObservation(
                route_id=route_id,
                origin_code=origin_code,
                destination_code=destination_code,
                airline_code=airline["code"],
                airline_name=airline["name"],
                flight_number=flight_num,
                departure_date=departure_date.isoformat(),
                booking_horizon_days=booking_horizon,
                cabin_class="Economy",
                fare_base=fare_base,
                fare_taxes=fare_taxes,
                fare_total=fare,
                is_direct=self.rng.random() > 0.15,  # 85% direct
                stops=0 if self.rng.random() > 0.15 else 1,
                baggage_kg=airline["baggage_kg"],
                is_refundable=airline["refundable"],
                fare_family=self.rng.choice(airline["fare_families"]),
                source_platform="mock_generator",
                scraper_version="mock-v1.0",
                scrape_timestamp=scrape_time.isoformat(),
            )
            observations.append(obs)
        
        return observations
    
    def generate_day(
        self,
        routes: list[dict],
        target_date: date,
        booking_horizons: list[int] = None,
        scrape_time: Optional[datetime] = None,
        base_date: Optional[date] = None,
    ) -> list[FareObservation]:
        """
        Generate a full day of fare observations across all routes and horizons.
        
        Args:
            routes: List of route dicts with route_id, origin_code, destination_code
            target_date: The date for which to generate fares
            booking_horizons: List of horizons (default: [0, 3, 7, 15, 30])
            scrape_time: Simulated scrape timestamp
            base_date: Base period start date for inflation calculation
        """
        if booking_horizons is None:
            booking_horizons = [0, 3, 7, 15, 30]
        
        if base_date is None:
            base_date = target_date
        
        days_since_base = (target_date - base_date).days
        all_observations = []
        
        for route in routes:
            for horizon in booking_horizons:
                departure = target_date + timedelta(days=horizon)
                obs = self.generate_fare(
                    route_id=route["route_id"],
                    origin_code=route["origin_code"],
                    destination_code=route["destination_code"],
                    departure_date=departure,
                    booking_horizon=horizon,
                    scrape_time=scrape_time,
                    days_since_base=days_since_base,
                )
                all_observations.extend(obs)
        
        logger.info(
            f"Mock: Generated {len(all_observations)} observations for "
            f"{target_date} across {len(routes)} routes × "
            f"{len(booking_horizons)} horizons"
        )
        
        return all_observations
    
    def generate_historical(
        self,
        routes: list[dict],
        start_date: date,
        end_date: date,
        booking_horizons: list[int] = None,
    ) -> list[FareObservation]:
        """
        Generate a full historical dataset for backtesting.
        Generates one scrape per day for the date range.
        """
        all_obs = []
        current = start_date
        
        while current <= end_date:
            scrape_time = datetime.combine(current, datetime.min.time().replace(hour=10))
            day_obs = self.generate_day(
                routes=routes,
                target_date=current,
                booking_horizons=booking_horizons,
                scrape_time=scrape_time,
                base_date=start_date,
            )
            all_obs.extend(day_obs)
            current += timedelta(days=1)
        
        logger.info(
            f"Mock: Generated {len(all_obs)} total observations "
            f"from {start_date} to {end_date}"
        )
        
        return all_obs
    
    def _select_airlines_for_route(self, route_key: str) -> list[dict]:
        """
        Select which airlines operate a given route.
        Major routes get all airlines, minor routes get fewer.
        """
        major_routes = {
            "DEL-BOM", "BOM-DEL", "DEL-BLR", "BLR-DEL",
            "BOM-BLR", "BLR-BOM", "DEL-HYD", "HYD-DEL",
            "DEL-CCU", "CCU-DEL",
        }
        
        if route_key in major_routes:
            return AIRLINES  # All airlines
        
        # Minor routes: randomly select 3-5 airlines (IndiGo always present)
        n_airlines = self.rng.integers(3, min(6, len(AIRLINES)) + 1)
        indigo = AIRLINES[0]  # IndiGo always present
        others = self.rng.choice(AIRLINES[1:], size=n_airlines - 1, replace=False)
        return [indigo] + list(others)
    
    def _get_seasonal_multiplier(self, d: date) -> float:
        """Check if the date falls in a festival/seasonal period."""
        for event in SEASONAL_EVENTS:
            if d.month == event["month"]:
                if event["day_start"] <= d.day <= event["day_end"]:
                    return event["multiplier"]
        return 1.0


def observations_to_dicts(observations: list[FareObservation]) -> list[dict]:
    """Convert FareObservation list to list of dicts for JSON/DB insertion."""
    return [asdict(obs) for obs in observations]
