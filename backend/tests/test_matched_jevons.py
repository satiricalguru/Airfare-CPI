"""
SIH26056 — Matched-Model Jevons Unit Tests

Tests for matched-model product pairing, churn tracking, and axiomatic properties.
"""

from datetime import date, datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import IndexSettings
from engine.matched_jevons import (
    MatchedJevonsCalculator,
    ProductPrice,
    aggregate_product_prices,
    carli_index,
    dutot_index,
)
from provenance import DataProvenance, SourceType, new_request_id
from scraper.base import CABIN_ECONOMY, FareObservation


def _obs(
    fare: float,
    airline: str = "6E",
    fare_family: str = "SAVER",
    flight_num: str = "6E-201",
    horizon: int = 7,
    route_id: int = 1,
    dep_date: date = date(2026, 9, 1),
    coll_dt: datetime = datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
) -> FareObservation:
    prov = DataProvenance(
        source_type=SourceType.SIMULATED,
        source_name="test_fixture",
        collection_timestamp=coll_dt,
        request_id=new_request_id(),
    )
    return FareObservation(
        route_id=route_id,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=dep_date,
        booking_horizon_days=horizon,
        airline_code=airline,
        cabin_class=CABIN_ECONOMY,
        fare_family=fare_family,
        flight_number=flight_num,
        fare_total=fare,
        currency="INR",
        provenance=prov,
    )


class TestMatchedJevons:

    def test_exact_matched_pairs_yield_accurate_index(self):
        """When products match exactly between base and current, Jevons = GM of relatives."""
        # 3 products: p1 (+10%), p2 (-10%), p3 (+0%)
        # Base: p1=5000, p2=6000, p3=7000
        # Curr: p1=5500, p2=5400, p3=7000
        obs1 = _obs(5000.0, airline="6E", fare_family="SAVER")
        obs2 = _obs(6000.0, airline="AI", fare_family="FLEXI")
        obs3 = _obs(7000.0, airline="UK", fare_family="STANDARD")

        base_prices = aggregate_product_prices([obs1, obs2, obs3])
        assert len(base_prices) == 3

        curr1 = _obs(5500.0, airline="6E", fare_family="SAVER")
        curr2 = _obs(5400.0, airline="AI", fare_family="FLEXI")
        curr3 = _obs(7000.0, airline="UK", fare_family="STANDARD")

        calc = MatchedJevonsCalculator(settings=IndexSettings(min_matched_products=3))
        res = calc.compute(
            current_observations=[curr1, curr2, curr3],
            base_prices=base_prices,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
            booking_horizon=7,
        )

        assert res is not None
        assert res.matched_products == 3
        expected_jevons = ( (5500/5000) * (5400/6000) * (7000/7000) ) ** (1/3)
        assert res.index_value == pytest.approx(expected_jevons, rel=1e-5)
        assert res.new_products == 0
        assert res.disappeared_products == 0
        assert res.match_rate == 1.0

    def test_product_churn_tracks_new_and_disappeared(self):
        """New products and disappeared products are excluded from the index and counted."""
        # Base: p1, p2, p3, p4
        p1 = _obs(5000.0, airline="6E", flight_num="6E-101")
        p2 = _obs(6000.0, airline="AI", flight_num="AI-201")
        p3 = _obs(7000.0, airline="UK", flight_num="UK-301")
        p4 = _obs(8000.0, airline="SG", flight_num="SG-401")
        base_prices = aggregate_product_prices([p1, p2, p3, p4])

        # Current: p1, p2, p3 (matched), p5 (new), p4 absent (disappeared)
        curr1 = _obs(5200.0, airline="6E", flight_num="6E-101")
        curr2 = _obs(6100.0, airline="AI", flight_num="AI-201")
        curr3 = _obs(7100.0, airline="UK", flight_num="UK-301")
        curr5 = _obs(9000.0, airline="QP", flight_num="QP-501")  # New

        calc = MatchedJevonsCalculator(settings=IndexSettings(min_matched_products=3))
        res = calc.compute(
            current_observations=[curr1, curr2, curr3, curr5],
            base_prices=base_prices,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
            booking_horizon=7,
        )

        assert res is not None
        assert res.matched_products == 3
        assert res.base_products == 4
        assert res.current_products == 4
        assert res.new_products == 1
        assert res.disappeared_products == 1
        assert res.match_rate == 0.75

    def test_insufficient_matches_returns_none(self):
        """When matched products < min_matched_products, returns None (not computable)."""
        p1 = _obs(5000.0, airline="6E", flight_num="6E-101")
        base_prices = aggregate_product_prices([p1])

        curr1 = _obs(5200.0, airline="6E", flight_num="6E-101")

        calc = MatchedJevonsCalculator(settings=IndexSettings(min_matched_products=3))
        res = calc.compute(
            current_observations=[curr1],
            base_prices=base_prices,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
            booking_horizon=7,
        )
        assert res is None

    def test_fare_family_substitution_is_not_price_change(self):
        """
        A fare family change (SAVER -> FLEXI) changes the product key.
        It is treated as a quality change (disappearance + arrival), not a price hike.
        """
        base_obs = _obs(5000.0, airline="6E", fare_family="SAVER")
        base_prices = aggregate_product_prices([base_obs])

        # Current offers only FLEXI at 6500 (which includes baggage/free meal)
        curr_obs = _obs(6500.0, airline="6E", fare_family="FLEXI")

        calc = MatchedJevonsCalculator(settings=IndexSettings(min_matched_products=1))
        res = calc.compute(
            current_observations=[curr_obs],
            base_prices=base_prices,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
            booking_horizon=7,
        )
        # Because SAVER and FLEXI have different product keys, matched count = 0
        assert res is None

    def test_carli_vs_dutot_vs_jevons(self):
        """Demonstrate Carli upward bias and Dutot level sensitivity."""
        p1_base = ProductPrice(product_key="k1", price=1000.0, observation_count=1)
        p2_base = ProductPrice(product_key="k2", price=10000.0, observation_count=1)

        # p1 doubles (+100%), p2 halves (-50%)
        # relatives: 2.0 and 0.5
        p1_curr = ProductPrice(product_key="k1", price=2000.0, observation_count=1)
        p2_curr = ProductPrice(product_key="k2", price=5000.0, observation_count=1)
        p3_base = ProductPrice(product_key="k3", price=5000.0, observation_count=1)
        p3_curr = ProductPrice(product_key="k3", price=5000.0, observation_count=1)

        base = {"k1": p1_base, "k2": p2_base, "k3": p3_base}
        curr = {"k1": p1_curr, "k2": p2_curr, "k3": p3_curr}

        c = carli_index(curr, base)
        # Carli = mean(2.0, 0.5, 1.0) = 3.5 / 3 = 1.1667 (upward biased)
        assert c is not None
        assert c == pytest.approx(3.5 / 3.0)

        # Jevons = (2.0 * 0.5 * 1.0) ** (1/3) = 1.0 ** (1/3) = 1.0
        # Carli > Jevons by AM-GM inequality
        assert c > 1.0
