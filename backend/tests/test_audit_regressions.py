"""
SIH26056 — Regression tests for issues found in the project audit (AUDIT.md)

Each test here pins a specific defect that was fixed, so it cannot silently return.
Test names reference the audit finding IDs.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api import main as api_main
from api.models import BackfillRequest, CollectionTriggerRequest, RouteScrapeRequest
from config import IndexSettings, ValidationSettings, get_settings, reload_settings
from engine.aggregator import NationalAggregator, RouteIndexInput
from engine.index_service import IndexService, _previous_month_anchor
from engine.rebase import BasePeriod, compute_base_prices, rebase_series
from engine.weights import get_route_basket
from db import repository as repo
from provenance import (
    CollectionMode,
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
)
from reports.generator import ResearchBulletin, ResearchReportGenerator
from scraper.base import CABIN_ECONOMY, FareObservation, SourceResult
from scraper.pipeline import CollectionPipeline, CollectionRequest
from scraper.validator import FareValidator, ValidationAction


# ═══════════════════════════════════════════════════════════
# M4 — Base-period & Rebasing
# ═══════════════════════════════════════════════════════════

def _make_obs(
    fare: float,
    coll_date: date,
    route_id: int = 1,
    horizon: int = 7,
    source_type: SourceType = SourceType.SIMULATED,
) -> FareObservation:
    prov = DataProvenance(
        source_type=source_type,
        source_name="test_fixture",
        collection_timestamp=datetime(coll_date.year, coll_date.month, coll_date.day, 10, 0, tzinfo=timezone.utc),
        request_id=new_request_id(),
    )
    return FareObservation(
        route_id=route_id,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=coll_date + timedelta(days=horizon),
        booking_horizon_days=horizon,
        airline_code="6E",
        cabin_class=CABIN_ECONOMY,
        fare_total=fare,
        currency="INR",
        provenance=prov,
    )


def test_m4_base_period_filters_strictly_by_date_window():
    """
    compute_base_prices must use observations falling strictly within the base period
    window, ignoring out-of-window observations regardless of order.
    """
    base_period = BasePeriod(start=date(2026, 8, 1), days=7)
    inside_obs = _make_obs(5000.0, date(2026, 8, 3))
    outside_obs = _make_obs(99000.0, date(2026, 9, 15))

    base_prices = compute_base_prices([outside_obs, inside_obs], base_period=base_period)
    key = (1, 7)
    assert key in base_prices
    assert base_prices[key].observation_count == 1
    assert base_prices[key].geometric_mean_price == pytest.approx(5000.0)


def test_m4_rebase_series_actually_recalculates_values():
    """
    rebase_series must divide the series by the mean in the reference window,
    so that re-referencing actually moves the numbers.
    """
    # Series with 3 days: 100.0, 110.0, 120.0
    series = [
        (date(2026, 8, 1), 100.0),
        (date(2026, 8, 2), 110.0),
        (date(2026, 8, 3), 120.0),
    ]
    # Rebase on day 2 alone (value 110.0)
    rebased, meta = rebase_series(
        series=series,
        reference_start=date(2026, 8, 2),
        reference_end=date(2026, 8, 2),
    )
    assert meta.is_applied is True
    assert meta.divisor == pytest.approx(110.0)
    assert rebased[1][1] == pytest.approx(100.0)  # Reference day becomes 100.0
    assert rebased[0][1] == pytest.approx(100.0 / 110.0 * 100.0)


def test_m4_rebase_fails_gracefully_when_window_not_in_series():
    """If the reference window has no data, rebase_series refuses rather than inventing a link."""
    series = [(date(2026, 8, 1), 100.0)]
    rebased, meta = rebase_series(
        series=series,
        reference_start=date(2020, 1, 1),
        reference_end=date(2020, 1, 7),
    )
    assert meta.is_applied is False
    assert "no index points" in (meta.reason or "").lower()
    assert rebased == series


# ═══════════════════════════════════════════════════════════
# M5 — Route weights derived from passenger volume and sum to 1.0
# ═══════════════════════════════════════════════════════════

def test_m5_route_weights_sum_to_exactly_one():
    basket = get_route_basket()
    assert abs(basket.weight_sum - 1.0) < 1e-9


def test_m5_weights_are_derived_from_passenger_volume():
    """Weights must be pax / total_pax."""
    basket = get_route_basket()
    total_pax = sum(r.monthly_pax for r in basket.routes)
    assert total_pax > 0
    for r in basket.routes:
        assert r.weight == pytest.approx(r.monthly_pax / total_pax, abs=1e-9)


def test_m5_basket_contains_25_routes():
    basket = get_route_basket()
    assert len(basket.routes) == 25


# ═══════════════════════════════════════════════════════════
# M6 — Year-over-year change honest reporting
# ═══════════════════════════════════════════════════════════

def test_m6_yoy_returns_none_when_series_too_short():
    """
    When no prior year comparison exists, the aggregator reports None with
    yoy_status='insufficient_history', never an invented percentage.
    """
    basket = get_route_basket()
    aggregator = NationalAggregator(basket=basket)
    res = aggregator.aggregate(
        route_indices=[
            RouteIndexInput(route_id=r.route_id, index_value=1.05, matched_products=10, observation_count=20)
            for r in basket.routes
        ],
        index_date=date(2026, 8, 30),
        base_period_label="2026-08-01 to 2026-08-07",
        previous_year_index=None,
    )
    assert res.yoy_change_pct is None
    assert res.yoy_status == "insufficient_history"


def test_m6_yoy_computed_when_prior_year_provided():
    basket = get_route_basket()
    aggregator = NationalAggregator(basket=basket)
    res = aggregator.aggregate(
        route_indices=[
            RouteIndexInput(route_id=r.route_id, index_value=1.10, matched_products=10, observation_count=20)
            for r in basket.routes
        ],
        index_date=date(2026, 8, 30),
        base_period_label="2026-08-01 to 2026-08-07",
        previous_year_index=100.0,
    )
    assert res.yoy_change_pct is not None
    assert abs(res.yoy_change_pct - 10.0) < 0.01
    assert res.yoy_status == "available"


# ═══════════════════════════════════════════════════════════
# Q2 — Day-over-day movement validation
# ═══════════════════════════════════════════════════════════

def test_q2_extreme_day_over_day_spike_is_flagged():
    validator = FareValidator(
        settings=ValidationSettings(max_daily_change_pct=300.0, min_observations_for_iqr=10)
    )
    # Day 1: median ~5000
    day1 = [_make_obs(5000.0, date(2026, 8, 1), route_id=1, horizon=7)]
    validator.validate_batch(day1)

    # Day 2: 25000 (+400% jump over 5000)
    day2_obs = _make_obs(25000.0, date(2026, 8, 2), route_id=1, horizon=7)
    res = validator.validate(day2_obs)

    assert res.is_valid is True  # Flagged, kept for volatility
    assert res.action is ValidationAction.FLAGGED
    assert any("daily_change_spike" in f for f in res.flags)


def test_q2_normal_day_over_day_movement_is_not_flagged():
    validator = FareValidator(
        settings=ValidationSettings(max_daily_change_pct=300.0, min_observations_for_iqr=10)
    )
    day1 = [_make_obs(5000.0, date(2026, 8, 1), route_id=1, horizon=7)]
    validator.validate_batch(day1)

    day2_obs = _make_obs(5800.0, date(2026, 8, 2), route_id=1, horizon=7)  # +16%
    res = validator.validate(day2_obs)
    assert not any("daily_change" in f for f in res.flags)


def test_validation_pairs_survive_duplicate_sort_keys():
    """A rejected fare must not transfer its decision to a clean fare with the same timestamp."""
    validator = FareValidator(
        settings=ValidationSettings(max_fare_inr=80000.0, min_observations_for_iqr=10)
    )
    rejected = _make_obs(90000.0, date(2026, 8, 2))
    accepted = _make_obs(5000.0, date(2026, 8, 2))

    batch = validator.validate_batch([rejected, accepted])
    pairs = repo._pair_observations(batch)

    assert pairs[0][0].fare_total == 90000.0
    assert pairs[0][1].action is ValidationAction.EXCLUDED
    assert pairs[1][0].fare_total == 5000.0
    assert pairs[1][1].action is ValidationAction.ACCEPTED


def test_index_service_refuses_mixed_provenance_base(monkeypatch):
    """A larger live sample must never hide simulator rows inside its base prices."""
    service = IndexService()
    service.base_period = BasePeriod(start=date(2026, 8, 1), days=7)

    base_live = _make_obs(
        5000.0, date(2026, 8, 2), source_type=SourceType.LIVE
    )
    base_simulated = _make_obs(
        5100.0, date(2026, 8, 2), source_type=SourceType.SIMULATED
    )
    target_live = _make_obs(
        5200.0, date(2026, 8, 10), source_type=SourceType.LIVE
    )

    async def fake_load(_session, start_date=None, **_kwargs):
        if start_date == service.base_period.start:
            return [base_live, base_simulated]
        return [target_live]

    monkeypatch.setattr(repo, "load_observations", fake_load)
    monkeypatch.setattr(repo, "record_to_observation", lambda row: row)

    result = asyncio.run(service.recompute(session=object()))

    assert result.dates_computed == []
    assert result.skipped_dates[0]["reason"] == "mixed_provenance"
    assert result.skipped_dates[0]["source_types"] == ["live", "simulated"]


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (date(2026, 3, 31), date(2026, 2, 28)),
        (date(2024, 3, 31), date(2024, 2, 29)),
        (date(2026, 1, 15), date(2025, 12, 15)),
        (date(2026, 9, 3), date(2026, 8, 3)),
    ],
)
def test_month_on_month_anchor_is_previous_calendar_month(current, expected):
    assert _previous_month_anchor(current) == expected


def test_route_history_get_is_read_only(monkeypatch):
    """A read of an empty route series must never start ingestion as a side effect."""
    async def empty_history(_session, _route_id, days=365, **_kwargs):
        return []

    async def forbidden_ingest(*_args, **_kwargs):
        raise AssertionError("GET route history attempted to mutate collection state")

    monkeypatch.setattr(repo, "get_route_index_history", empty_history)
    monkeypatch.setattr(api_main.IngestService, "ingest", forbidden_ingest)

    payload = asyncio.run(
        api_main.get_route_history(route_id=1, days=365, session=object())
    )
    assert payload["history"] == []
    assert payload["count"] == 0


@pytest.mark.parametrize(
    "model, payload",
    [
        (CollectionTriggerRequest, {"horizons": [0, 7]}),
        (
            RouteScrapeRequest,
            {"origin": "DEL", "destination": "BOM", "horizons": [3]},
        ),
        (
            BackfillRequest,
            {
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "horizons": [60],
            },
        ),
    ],
)
def test_api_rejects_horizons_outside_policy(model, payload):
    """Old or arbitrary horizons cannot silently create a different series."""
    with pytest.raises(ValueError, match="must be selected from"):
        model(**payload)


def test_live_collection_cannot_backdate_observations():
    """A quote retrieved now cannot be represented as a historical live quote."""
    route = get_route_basket().routes[0]
    request = CollectionRequest(
        mode=CollectionMode.LIVE,
        routes=[route],
        booking_horizons=[1],
        collection_day=date(2020, 1, 1),
    )

    result = asyncio.run(CollectionPipeline().run(request))

    assert result.status is CollectionStatus.UNAVAILABLE
    assert result.observations == []
    assert "Historical backfill" in (result.error_message or "")


def test_unconfigured_live_source_never_falls_back_to_simulator(monkeypatch):
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)
    cfg = reload_settings()
    route = get_route_basket().routes[0]

    result = asyncio.run(
        CollectionPipeline(cfg).run(
            CollectionRequest(
                mode=CollectionMode.LIVE,
                routes=[route],
                booking_horizons=[1],
            )
        )
    )

    assert result.status is CollectionStatus.UNAVAILABLE
    assert result.observations == []
    assert all(item["source"] != "simulator" for item in result.skipped_sources)
    assert "No observations were produced and none were substituted" in (
        result.error_message or ""
    )


# ═══════════════════════════════════════════════════════════
# C2 — Research report / Bulletin honesty (No fake MoSPI branding)
# ═══════════════════════════════════════════════════════════

def _sample_bulletin(**overrides) -> ResearchBulletin:
    defaults = dict(
        report_id="SIH26056-AIRFARE-2026-08-PROTOTYPE",
        generated_at=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
        reference_date=date(2026, 8, 30),
        headline_index=101.23,
        base_period="2026-08-01 to 2026-08-07",
        source_type="simulated",
        provenance_label="SIMULATED DATA",
        sample_size=500,
        methodology_version="methodology-2.0.0",
        validation_rules_version="validation-2.0.0",
        collector_version="collector-2.0.0",
    )
    defaults.update(overrides)
    return ResearchBulletin(**defaults)


def test_c2_report_carries_prototype_disclaimer():
    html = ResearchReportGenerator.render_html(_sample_bulletin())
    assert "PROTOTYPE" in html.upper()
    assert "NOT AN OFFICIAL STATISTICAL RELEASE" in html.upper()


def test_c2_report_does_not_claim_government_authorship():
    html = ResearchReportGenerator.render_html(_sample_bulletin())
    assert "Issued by: Price Statistics Division" not in html
    assert '<div class="govt-title">Government of India</div>' not in html


def test_c2_report_renders_provenance_label():
    html = ResearchReportGenerator.render_html(_sample_bulletin(provenance_label="SIMULATED DATA"))
    assert "SIMULATED DATA" in html


def test_c2_report_never_prints_hardcoded_inflation():
    html = ResearchReportGenerator.render_html(_sample_bulletin(mom_change_pct=None, mom_status="insufficient_history"))
    assert "+2.84%" not in html
    assert "Not available" in html


# ═══════════════════════════════════════════════════════════
# C4 — SourceResult provenance invariants
# ═══════════════════════════════════════════════════════════

def test_c4_source_result_forbids_success_for_non_live():
    """
    SourceResult invariant: status=SUCCESS requires live observations.
    Attaching simulated observations raises ValueError.
    """
    sim_obs = _make_obs(5000.0, date(2026, 8, 1))
    with pytest.raises(ValueError, match="requires every observation to carry live provenance"):
        SourceResult(
            source_name="simulator",
            status=CollectionStatus.SUCCESS,
            observations=(sim_obs,),
        )


def test_c4_failed_live_fetch_cannot_contain_observations():
    """A failed live collection cannot attach observations."""
    with pytest.raises(ValueError, match="must carry zero observations"):
        SourceResult(
            source_name="amadeus",
            status=CollectionStatus.FAILED,
            error_message="Network timeout",
            observations=(_make_obs(5000.0, date(2026, 8, 1)),),
        )


# ═══════════════════════════════════════════════════════════
# C5 — CORS configuration
# ═══════════════════════════════════════════════════════════

def test_c5_cors_does_not_combine_wildcard_with_credentials():
    from starlette.middleware.cors import CORSMiddleware

    cors = [m for m in api_main.app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "CORS middleware should be configured"
    options = getattr(cors[0], "options", None) or getattr(cors[0], "kwargs", {})

    if "*" in options.get("allow_origins", []):
        assert not options.get("allow_credentials"), (
            "Wildcard origins must never be combined with allow_credentials=True"
        )


# ═══════════════════════════════════════════════════════════
# Admin Guard (Token authentication)
# ═══════════════════════════════════════════════════════════

def test_admin_guard_rejects_bad_token_when_configured(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv("ADMIN_API_TOKEN", "secret-token-123")
    reload_settings()

    try:
        with pytest.raises(HTTPException) as exc:
            api_main.require_admin("wrong-token")
        assert exc.value.status_code == 401

        api_main.require_admin("secret-token-123")  # Correct token passes
    finally:
        monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
        reload_settings()


def test_admin_guard_fails_closed_when_unconfigured(monkeypatch):
    """A missing deployment secret disables mutation instead of making it public."""
    from fastapi import HTTPException

    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    reload_settings()
    try:
        with pytest.raises(HTTPException) as exc:
            api_main.require_admin(None)
        assert exc.value.status_code == 503
    finally:
        reload_settings()
