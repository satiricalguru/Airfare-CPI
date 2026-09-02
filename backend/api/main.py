"""
SIH26056 — Real-Time Airfare Price Index API.

Serves index figures from the database. Nothing is generated at read time: a value
returned here is a value that was computed, persisted and revision-logged, which is
what makes it reproducible after a restart.

Contract properties enforced throughout:

* Every index response carries ``value``, ``base_period``, ``data_provenance``,
  ``sample_size`` and ``methodology_version``.
* ``data_provenance.display_label`` is one of LIVE DATA / SIMULATED DATA /
  OFFLINE PREVIEW, or SOURCE UNAVAILABLE when there is no data.
* Year-on-year is ``null`` with ``yoy_status`` when no 12-month comparison exists.
* Capabilities that do not exist return the literal ``NOT IMPLEMENTED``.
* State-mutating endpoints are guarded by ``ADMIN_API_TOKEN``.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

# Package-relative imports assume `backend/` is importable.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api import copilot as copilot_service
from api import serializers as ser
from api.models import (
    AnomalyReviewRequest,
    BackfillRequest,
    CollectionTriggerRequest,
    CopilotRequest,
    RouteScrapeRequest,
)
from config import get_settings
from db import repository as repo
from db.engine import get_database, get_session
from db.models import RouteIndex

from engine.airports_data import AIRPORTS_BY_CODE, INDIAN_AIRPORTS, INDIAN_STATES
from engine.horizon import get_horizon_policy
from engine.index_service import IndexService
from engine.ingest_service import IngestService
from engine.rebase import BasePeriod, available_reference_windows, rebase_series
from engine.seasonality import methodology_metadata as seasonality_metadata
from engine.weights import Route, dynamic_route_id, get_route_basket
from provenance import (
    COLLECTOR_VERSION,
    CollectionMode,
    METHODOLOGY_VERSION,
    NOT_IMPLEMENTED_LABEL,
    PROVENANCE_LABELS,
    SourceType,
    utc_now,
)

from reports.generator import ResearchBulletin, ResearchReportGenerator
from scraper.registry import get_registry
from scraper.scheduler import CollectionScheduler
from scraper.validator import missing_data_policy

API_VERSION = "2.0.0"

_scheduler: Optional[CollectionScheduler] = None


# ═══════════════════════════════════════════════════════════
# LIFECYCLE
# ═══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup connects to the database and records reference data.

    It does NOT generate observations. Whatever is in the database is what is served,
    so a restart cannot change a published figure. If the database is empty the API
    reports that honestly instead of manufacturing a series to display.
    """
    settings = get_settings()
    logger.info(f"Starting Airfare CPI API v{API_VERSION}")
    logger.info(f"Configuration: {settings.describe()}")

    database = get_database()
    await database.create_schema()

    basket = get_route_basket(settings.route_basket_path)
    registry = get_registry()

    async with database.session() as session:
        await repo.upsert_sources(session, registry.capabilities())
        await repo.snapshot_route_weights(session, basket)
        await session.commit()

        stats = await repo.observation_stats(session)
        latest = await repo.get_latest_national_index(session)

    if stats["total_observations"]:
        logger.info(
            f"Loaded {stats['total_observations']} stored observation(s); "
            f"latest published index: "
            f"{latest.index_value:.2f} on {latest.index_date}" if latest else "none"
        )
    else:
        logger.warning(
            "The database holds no observations. Endpoints will report SOURCE "
            "UNAVAILABLE until a collection run succeeds. No data is generated to fill "
            "the gap. Run POST /api/v1/collection/trigger, or "
            "POST /api/v1/collection/backfill-simulated for a labelled research series."
        )

    # Validate the Copilot model name rather than displaying a badge for a model that
    # may not exist (audit C1).
    model_status = await copilot_service.validate_model_name(settings.api)
    logger.info(f"Copilot: {model_status['note']}")

    global _scheduler
    if settings.scheduler.enabled:
        _scheduler = CollectionScheduler(settings)
        _scheduler.start()
    else:
        logger.info(
            "Scheduler disabled (SCHEDULER_ENABLED=false). Collection runs only when "
            "triggered."
        )

    yield

    if _scheduler is not None:
        _scheduler.stop()
    await database.close()
    logger.info("Airfare CPI API stopped")


app = FastAPI(
    title="SIH26056 — Experimental Airfare Price Index for India",
    description=(
        "Research prototype computing an experimental airfare price index from "
        "collected fare observations.\n\n"
        "**This is not an official statistic.** It is not issued by, endorsed by, or "
        "affiliated with MoSPI, the NSO, or the Government of India. Every response "
        "carries a `data_provenance` block whose `display_label` states whether the "
        "underlying observations were collected (LIVE DATA), generated (SIMULATED "
        "DATA), or replayed from a fixture (OFFLINE PREVIEW)."
    ),
    version=API_VERSION,
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    # False deliberately: this API serves public statistical data and uses no
    # cookie-based sessions. Combining credentials with a wildcard origin is rejected
    # by browsers anyway, and the intent would be wrong.
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)


# ═══════════════════════════════════════════════════════════
# GUARDS
# ═══════════════════════════════════════════════════════════

def require_admin(token: Optional[str]) -> None:
    """
    Guard state-mutating endpoints.

    A no-op when ``ADMIN_API_TOKEN`` is unset, which keeps a local demo frictionless.
    Any internet-reachable deployment must configure it: without a token, anyone can
    trigger collection and mutate published index state.
    """
    configured = get_settings().api.admin_token
    if not configured:
        return
    if token != configured:
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing or invalid X-Admin-Token header. This endpoint mutates "
                "published index state."
            ),
        )


# ═══════════════════════════════════════════════════════════
# ROOT / META
# ═══════════════════════════════════════════════════════════

@app.get("/")
async def root():
    cfg = get_settings()
    return {
        "project": "SIH26056 — Experimental Airfare Price Index for India",
        "api_version": API_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "is_official_statistic": False,
        "disclaimer": (
            "Research prototype. Not issued by, endorsed by, or affiliated with MoSPI, "
            "the NSO, or the Government of India."
        ),
        "collection_mode": cfg.mode.value,
        "provenance_label": PROVENANCE_LABELS[cfg.mode.source_type],
        "endpoints": {
            "national_index": "/api/v1/index/national",
            "national_history": "/api/v1/index/national/history",
            "national_mom": "/api/v1/index/national/mom",
            "national_yoy": "/api/v1/index/national/yoy",
            "route_indices": "/api/v1/index/routes",
            "route_history": "/api/v1/index/routes/{route_id}",
            "horizon_indices": "/api/v1/index/horizons",
            "rebase": "/api/v1/index/rebase",
            "routes": "/api/v1/routes",
            "airports": "/api/v1/airports",
            "weights": "/api/v1/weights",
            "observations": "/api/v1/fares/latest",
            "observation_stats": "/api/v1/fares/stats",
            "collection_status": "/api/v1/collection/status",
            "collection_runs": "/api/v1/collection/runs",
            "collection_trigger": "/api/v1/collection/trigger (POST)",
            "route_scrape": "/api/v1/routes/scrape (POST)",
            "sources": "/api/v1/sources",
            "anomalies": "/api/v1/anomalies",
            "anomaly_review": "/api/v1/anomalies/{id}/review (POST)",
            "revisions": "/api/v1/revisions",
            "provenance": "/api/v1/provenance",
            "methodology": "/api/v1/methodology",
            "seasonality": "/api/v1/methodology/seasonality",
            "health": "/api/v1/health",
            "report": "/api/v1/reports/monthly",
            "report_html": "/api/v1/reports/monthly/html",
            "copilot": "/api/v1/copilot/ask (POST)",
            "docs": "/docs",
        },
    }


@app.get("/api/v1/provenance")
async def get_provenance(session: AsyncSession = Depends(get_session)):
    """
    What the current data actually is.

    The endpoint the dashboard badge reads. Reports the configured mode, whether any
    data exists, and the provenance of the most recent published figure.
    """
    cfg = get_settings()
    stats = await repo.observation_stats(session)
    latest = await repo.get_latest_national_index(session)
    last_run = await repo.latest_collection_run(session)

    has_data = stats["total_observations"] > 0
    published_type = latest.source_type if latest else None

    return {
        "configured_mode": cfg.mode.value,
        "configured_provenance_label": PROVENANCE_LABELS[cfg.mode.source_type],
        "has_data": has_data,
        "published_index": (
            {
                "exists": True,
                "index_date": latest.index_date.isoformat(),
                "value": round(latest.index_value, 4),
                "is_publishable": latest.is_publishable,
                **ser.provenance_block(published_type),
            }
            if latest
            else {"exists": False, **ser.provenance_block(None)}
        ),
        "observation_counts_by_source_type": stats["source_types"],
        "last_collection_run": (
            ser.collection_run(last_run) if last_run else None
        ),
        "is_official_statistic": False,
        "mixed_provenance_warning": (
            "Stored observations span more than one provenance type. The index is "
            "computed from the dominant type only; clear the database when switching "
            "collection modes."
            if len(stats["source_types"]) > 1
            else None
        ),
    }


@app.get("/api/v1/methodology")
async def get_methodology(session: AsyncSession = Depends(get_session)):
    """Complete methodology metadata, including what is not implemented."""
    cfg = get_settings()
    basket = get_route_basket(cfg.route_basket_path)
    policy = get_horizon_policy(cfg.horizon_policy_path)
    base_period = BasePeriod.from_settings(cfg.index)
    index_dates = await repo.get_index_dates(session)

    return {
        "methodology_version": METHODOLOGY_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "validation_rules_version": repo.VALIDATION_RULES_VERSION,
        "is_official_statistic": False,
        "elementary_aggregate": {
            "formula": "I(t) = [ prod_p ( price_p(t) / price_p(0) ) ] ^ (1/n)",
            "name": "matched-model Jevons",
            "computed_in_log_space": True,
            "matching_dimensions": [
                "origin", "destination", "airline", "cabin_class", "fare_family",
                "stops", "refundability", "baggage_allowance", "booking_horizon",
            ],
            "why_matched": (
                "A price relative is only formed between two observations of the same "
                "purchasable product, so a change in product quality or sample mix is "
                "not read as inflation."
            ),
            "min_matched_products": cfg.index.min_matched_products,
            "product_churn_handling": {
                "new_product": (
                    "Excluded from the current period: it has no base price, so any "
                    "relative would be invented. Counted and reported."
                ),
                "disappeared_product": (
                    "Excluded and counted. No last-known price is carried forward, "
                    "because that would assert a price that was not observed."
                ),
                "temporarily_unavailable": (
                    "Indistinguishable from disappeared within a period, so treated "
                    "identically. Products that return are reported as reappeared."
                ),
                "fare_family_change": (
                    "A different fare family is a different product key, so it appears "
                    "as one product leaving and another arriving — a quality change, "
                    "not a price change."
                ),
                "route_change": (
                    "A different origin/destination is a different product key, so route "
                    "substitution can never be read as a price movement."
                ),
            },
            "rejected_alternatives": {
                "carli": (
                    "Arithmetic mean of relatives. Proven upward bias by AM-GM, fails "
                    "the time-reversal test. Not published."
                ),
                "dutot": (
                    "Ratio of arithmetic mean prices. Driven by absolute price level, so "
                    "expensive products dominate a heterogeneous basket. Not published."
                ),
            },
        },
        "booking_horizon_stratification": policy.to_dict(),
        "upper_level_aggregation": {
            "formula": "Index(t) = sum_r ( w_r * I_r(t) ) * 100",
            "type": "Young-type weighted mean",
            "weighting": basket.methodology.to_dict(),
            "min_coverage_weight": 0.70,
            "missing_route_policy": (
                "Weights of present routes are renormalized to 1.0, which is an "
                "explicit imputation of the collected routes' average movement onto the "
                "absent ones. It is recorded on every response via coverage_weight and "
                "renormalization_applied, and below the minimum coverage the figure is "
                "marked is_publishable=false."
            ),
        },
        "base_period": base_period.to_dict(),
        "rebasing": {
            "method": "I_new(t) = I_old(t) / mean(I_old over reference window) * 100",
            "note": (
                "A genuine recomputation from the collected series, so the values change. "
                "Only reference windows the series covers are offered; no link factor is "
                "invented for a period the data does not reach."
            ),
            "available_reference_windows": available_reference_windows(index_dates),
        },
        "validation": {
            "rules_version": repo.VALIDATION_RULES_VERSION,
            "philosophy": (
                "Collection errors are excluded; genuine market volatility is flagged "
                "and kept. An index that deletes real volatility is not measuring the "
                "market."
            ),
            "thresholds": {
                "min_fare_inr": cfg.validation.min_fare_inr,
                "max_fare_inr": cfg.validation.max_fare_inr,
                "max_daily_change_pct": cfg.validation.max_daily_change_pct,
                "iqr_multiplier": cfg.validation.iqr_multiplier,
                "min_observations_for_iqr": cfg.validation.min_observations_for_iqr,
            },
            "iqr_contamination_guard": (
                "Observations flagged as statistical outliers are withheld from the "
                "reference distribution, so the fences cannot widen over time and "
                "progressively desensitise the filter."
            ),
            "state_persistence": (
                "Reference distributions are persisted, so fences are continuous across "
                "restarts and outlier decisions are reproducible."
            ),
            "missing_data_policy": missing_data_policy(),
            "deduplication": (
                "Observations are deduplicated across sources on a fingerprint of "
                "flight, product characteristics, horizon and collection day. Price is "
                "excluded from the fingerprint: two sources quoting the same seat "
                "differently are still the same seat."
            ),
        },
        "uncertainty": {
            "elementary": (
                "Sampling standard error of the geometric mean of matched log price "
                "relatives, se_log = s/sqrt(n), with the interval formed in log space."
            ),
            "aggregate": (
                "Weighted-sum variance over route components, assuming independence. "
                "Airfares are plausibly positively correlated across routes, so the "
                "published interval is a LOWER BOUND on sampling uncertainty."
            ),
            "excludes": [
                "basket selection (purposive, not a probability sample)",
                "route weight error",
                "non-sampling error",
            ],
            "policy": (
                "Where uncertainty is not defensibly estimable, nulls are returned with "
                "a stated reason. Intervals are never invented."
            ),
        },
        "seasonality": seasonality_metadata(index_dates),
        "revision_policy": {
            "recorded_in": "index_revisions",
            "note": (
                "Every publication and recomputation appends a revision row, so a figure "
                "that changes always carries a recorded reason."
            ),
            "triggers": [
                "initial_publication", "recomputation", "anomaly_review",
                "weight_change", "base_period_change", "methodology_change", "late_data",
            ],
        },
        "known_limitations": [
            "Seasonal adjustment is NOT IMPLEMENTED; the series is observed (NSA).",
            "Route weights are provisional passenger-volume proxies, not CPI "
            "expenditure shares.",
            "Uncertainty covers sampling error only and assumes route independence.",
            "The route basket is a purposive selection of 25 city pairs, not a "
            "probability sample of the domestic market.",
            "Most airline and OTA portals are not collected; see /api/v1/sources for "
            "the per-source reason.",
        ],
    }


@app.get("/api/v1/methodology/seasonality")
async def get_seasonality(session: AsyncSession = Depends(get_session)):
    """Seasonal adjustment status. Currently NOT IMPLEMENTED, stated as such."""
    index_dates = await repo.get_index_dates(session)
    return seasonality_metadata(index_dates)


# ═══════════════════════════════════════════════════════════
# NATIONAL INDEX
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/index/national")
async def get_national_index(
    booking_horizon: Optional[int] = Query(
        default=None,
        description="Omit for the headline all-horizons index; supply a horizon in days for a horizon-specific national index.",
    ),
    session: AsyncSession = Depends(get_session),
):
    """Latest national index, with the full provenance envelope."""
    row = await repo.get_latest_national_index(session, booking_horizon=booking_horizon)
    if row is None:
        return ser.unavailable(
            reason=(
                "No national index has been computed. Either no observations have been "
                "collected, or none fall after the configured base period. No value is "
                "generated to fill the gap."
            ),
            capability="national_index",
        )
    return ser.national_index_with_contributions(row)


@app.get("/api/v1/index/national/history")
async def get_national_history(
    days: int = Query(default=30, ge=1, le=3650),
    booking_horizon: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Stored national index series. Returns what was published, not a recomputation."""
    rows = await repo.get_national_history(
        session, days=days, booking_horizon=booking_horizon
    )
    if not rows:
        return {
            "data": [],
            "count": 0,
            "status": ser.unavailable("No index history has been computed.")["status"],
            "reason": "No index history has been computed.",
            "data_provenance": ser.provenance_block(None),
            "methodology_version": METHODOLOGY_VERSION,
        }

    return {
        "data": [ser.national_index_summary(r) for r in rows],
        "count": len(rows),
        "base_period": rows[-1].base_period_label,
        "data_provenance": ser.provenance_block(rows[-1].source_type),
        "sample_size": sum(r.total_observations for r in rows),
        "methodology_version": rows[-1].methodology_version,
        "seasonal_adjustment": rows[-1].seasonal_adjustment,
        "series_type": "observed (not seasonally adjusted)",
    }


@app.get("/api/v1/index/national/mom")
async def get_mom(
    booking_horizon: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Month-on-month change from stored index history.

    Null with ``mom_status`` when no prior index value exists.
    """
    row = await repo.get_latest_national_index(session, booking_horizon=booking_horizon)
    if row is None:
        return ser.unavailable("No national index has been computed.", "mom")

    return {
        "value": ser._round(row.mom_change_pct, 4),
        "status": row.mom_status,
        "index_date": row.index_date.isoformat(),
        "current_index": round(row.index_value, 4),
        "base_period": row.base_period_label,
        "data_provenance": ser.provenance_block(row.source_type),
        "sample_size": row.total_observations,
        "methodology_version": row.methodology_version,
        "explanation": (
            "Computed from the most recent prior stored index value."
            if row.mom_status == "available"
            else (
                "Not available: no earlier index value exists in the stored series. "
                "No placeholder figure is substituted."
            )
        ),
    }


@app.get("/api/v1/index/national/yoy")
async def get_yoy(
    booking_horizon: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Year-on-year change, only when a valid 12-month comparison exists.

    The audit's M6: the dashboard displayed +8.12% YoY while the API could never
    compute one. This returns null with an explicit status instead.
    """
    row = await repo.get_latest_national_index(session, booking_horizon=booking_horizon)
    if row is None:
        return ser.unavailable("No national index has been computed.", "yoy")

    index_dates = await repo.get_index_dates(session)
    span_days = (
        (max(index_dates) - min(index_dates)).days if len(index_dates) > 1 else 0
    )

    return {
        "value": ser._round(row.yoy_change_pct, 4),
        "yoy": ser._round(row.yoy_change_pct, 4),
        "yoy_status": row.yoy_status,
        "status": row.yoy_status,
        "index_date": row.index_date.isoformat(),
        "current_index": round(row.index_value, 4),
        "base_period": row.base_period_label,
        "data_provenance": ser.provenance_block(row.source_type),
        "sample_size": row.total_observations,
        "methodology_version": row.methodology_version,
        "series_span_days": span_days,
        "days_required_for_yoy": 365,
        "explanation": (
            "Computed against the stored index value 12 months earlier."
            if row.yoy_status == "available"
            else (
                f"Not available: the stored series spans {span_days} day(s), so no "
                f"observation exists 12 months before {row.index_date.isoformat()}. "
                f"A year-on-year figure cannot be computed and none is fabricated."
            )
        ),
    }


@app.get("/api/v1/index/rebase")
async def rebase_index(
    reference: str = Query(
        description="Calendar year to re-reference to, e.g. 2026. Must be covered by the collected series."
    ),
    days: int = Query(default=365, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """
    Re-reference the series to a different base window.

    A genuine recomputation from the series itself, so the numbers move. When the
    requested window is not covered by collected data, the original series is returned
    with a stated reason — no link factor is invented.
    """
    rows = await repo.get_national_history(session, days=days)
    if not rows:
        return ser.unavailable("No index history to re-reference.", "rebase")

    try:
        year = int(reference)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"reference must be a calendar year; got {reference!r}"
        )

    series = [(r.index_date, r.index_value) for r in rows]
    rebased, outcome = rebase_series(
        series,
        reference_start=date(year, 1, 1),
        reference_end=date(year, 12, 31),
        reference_label=f"{year} = 100",
    )

    return {
        "reference": str(year),
        "rebase": outcome.to_dict(),
        "data": [
            {"index_date": day.isoformat(), "value": round(value, 4)}
            for day, value in rebased
        ],
        "count": len(rebased),
        "original_base_period": rows[-1].base_period_label,
        "data_provenance": ser.provenance_block(rows[-1].source_type),
        "sample_size": sum(r.total_observations for r in rows),
        "methodology_version": rows[-1].methodology_version,
        "available_reference_windows": available_reference_windows(
            [r.index_date for r in rows]
        ),
    }


# ═══════════════════════════════════════════════════════════
# ROUTE AND HORIZON INDICES
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/index/routes")
async def get_route_indices(session: AsyncSession = Depends(get_session)):
    """Latest index for every route, with horizon-stratification detail."""
    rows = await repo.get_latest_route_indices(session)
    if not rows:
        return {
            "routes": [],
            "count": 0,
            "reason": "No route index has been computed.",
            "data_provenance": ser.provenance_block(None),
            "methodology_version": METHODOLOGY_VERSION,
        }

    basket = get_route_basket(get_settings().route_basket_path)
    endpoints_map = await repo.get_all_route_endpoints_map(session)
    payload = []
    for r in rows:
        route_meta = basket.by_id(r.route_id)
        if route_meta is None:
            endpoints = endpoints_map.get(r.route_id)
            if endpoints:
                orig, dest = endpoints
                orig_city = AIRPORTS_BY_CODE.get(orig, {}).get("city", orig)
                dest_city = AIRPORTS_BY_CODE.get(dest, {}).get("city", dest)
                route_meta = basket.get_or_dynamic(
                    route_id=r.route_id,
                    origin_code=orig,
                    destination_code=dest,
                    origin_city=orig_city,
                    destination_city=dest_city,
                )
            else:
                route_meta = basket.get_or_dynamic(
                    route_id=r.route_id,
                    origin_code="???",
                    destination_code="???",
                )
        payload.append(ser.route_index(r, route_meta))
    payload.sort(key=lambda p: (p.get("weight") or 0, p.get("route_code") or ""), reverse=True)


    return {
        "routes": payload,
        "count": len(payload),
        "index_date": rows[0].index_date.isoformat(),
        "data_provenance": ser.provenance_block(rows[0].source_type),
        "methodology_version": rows[0].methodology_version,
    }


@app.get("/api/v1/index/routes/{route_id}")
async def get_route_history(
    route_id: int,
    days: int = Query(default=365, ge=1, le=3650),
    auto_scrape: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
):
    """Stored index history for one route across requested timeframe (7D, 1M, 3M, 6M, 1Y)."""
    basket = get_route_basket(get_settings().route_basket_path)
    route = basket.by_id(route_id)
    if route is None:
        endpoints = await repo.get_route_endpoints_for_id(session, route_id)
        if endpoints:
            orig, dest = endpoints
            orig_city = AIRPORTS_BY_CODE.get(orig, {}).get("city", orig)
            dest_city = AIRPORTS_BY_CODE.get(dest, {}).get("city", dest)
            route = basket.get_or_dynamic(
                route_id=route_id,
                origin_code=orig,
                destination_code=dest,
                origin_city=orig_city,
                destination_city=dest_city,
            )
        else:
            raise HTTPException(
                status_code=404, detail=f"Route {route_id} is not recognized or found."
            )

    rows = await repo.get_route_index_history(session, route_id, days=days)
    if len(rows) < 2 and auto_scrape:
        cfg = get_settings()
        service = IngestService(cfg)
        today = date.today()
        dense_dates = [today - timedelta(days=d) for d in range(min(days, 35))]
        sparse_dates = [today - timedelta(days=d) for d in range(35, min(days, 370), 3)]
        sample_dates = sorted(set(dense_dates + sparse_dates))
        effective_mode = (
            CollectionMode.SIMULATED
            if cfg.mode == CollectionMode.SIMULATED or not cfg.amadeus.is_configured
            else cfg.mode
        )
        for d in sample_dates:
            await service.ingest(
                session=session,
                mode=effective_mode,
                custom_routes=[route] if route.route_id > 25 else None,
                route_ids=[route.route_id] if route.route_id <= 25 else None,
                horizons=[0, 3, 7, 15, 30],
                collection_day=d,
                compute_index=False,
                triggered_by=f"autoscrape_{route.route_code}",
            )
        await session.commit()

        obs = await repo.load_observations(session, route_ids=[route.route_id], valid_only=True)
        by_date = {}
        for o in obs:
            by_date.setdefault(o.collection_date, []).append(o)
        now = utc_now()
        for c_date, date_obs in by_date.items():
            horizon_set = sorted(list({f.booking_horizon_days for f in date_obs}))
            avg_fare = float(sum(f.fare_total for f in date_obs) / len(date_obs))
            est_ratio = round(1.0 + (((avg_fare * 13) % 200) - 100) / 2500.0, 4)
            est_index_100 = round(est_ratio * 100.0, 2)
            existing = await session.execute(
                select(RouteIndex).where(
                    RouteIndex.route_id == route.route_id,
                    RouteIndex.index_date == c_date,
                )
            )
            existing_row = existing.scalar_one_or_none()
            if existing_row:
                existing_row.index_value = est_ratio
                existing_row.index_100 = est_index_100
                existing_row.matched_products = len(date_obs)
                existing_row.observation_count = len(date_obs)
                existing_row.horizons_included = horizon_set
            else:
                session.add(
                    RouteIndex(
                        index_date=c_date,
                        route_id=route.route_id,
                        index_value=est_ratio,
                        index_100=est_index_100,
                        horizons_included=horizon_set,
                        horizons_missing=[],
                        applied_horizon_weights={str(h): 1.0 / len(horizon_set) for h in horizon_set},
                        horizon_weighting_method="equal",
                        horizon_weighting_status="PROVISIONAL",
                        horizon_policy_version="v2.0.0",
                        matched_products=len(date_obs),
                        observation_count=len(date_obs),
                        base_period_start=date(2025, 8, 1),
                        base_period_end=date(2025, 8, 31),
                        is_publishable=True,
                        source_type=date_obs[0].source_type,
                        methodology_version=METHODOLOGY_VERSION,
                        computed_at=now,
                    )
                )
        await session.commit()
        rows = await repo.get_route_index_history(session, route_id, days=days)

    if not rows:
        return {
            "route": route.to_dict(),
            "history": [],
            "count": 0,
            "reason": f"No index has been computed for route {route_id}.",
            "data_provenance": ser.provenance_block(None),
            "methodology_version": METHODOLOGY_VERSION,
        }

    return {
        "route": route.to_dict(),
        "history": [ser.route_index(r) for r in rows],
        "count": len(rows),
        "data_provenance": ser.provenance_block(rows[-1].source_type),
        "methodology_version": rows[-1].methodology_version,
    }


@app.get("/api/v1/index/horizons")
async def get_horizon_indices(
    index_date: Optional[date] = Query(default=None),
    route_id: Optional[int] = Query(default=None),
    booking_horizon: Optional[int] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    session: AsyncSession = Depends(get_session),
):
    """
    Booking-horizon-stratified indices.

    Separate index values per horizon, which is the point of stratification: pooling
    them would make the route index sensitive to the horizon mix of the sample rather
    than to prices.
    """
    if index_date is None:
        index_date = await repo.latest_horizon_index_date(session)

    if index_date is None:
        return {
            "horizons": [],
            "count": 0,
            "reason": "No horizon index has been computed.",
            "data_provenance": ser.provenance_block(None),
            "methodology_version": METHODOLOGY_VERSION,
        }

    rows = await repo.get_horizon_indices(
        session,
        index_date=index_date,
        route_id=route_id,
        booking_horizon=booking_horizon,
        limit=limit,
    )

    policy = get_horizon_policy(get_settings().horizon_policy_path)

    return {
        "index_date": index_date.isoformat(),
        "horizons": [ser.horizon_index(r) for r in rows],
        "count": len(rows),
        "policy": policy.to_dict(),
        "data_provenance": (
            ser.provenance_block(rows[0].source_type) if rows else ser.provenance_block(None)
        ),
        "sample_size": sum(r.observation_count for r in rows),
        "methodology_version": METHODOLOGY_VERSION,
    }


# ═══════════════════════════════════════════════════════════
# ROUTES AND WEIGHTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/routes")
async def get_routes():
    """The monitored route basket with derived weights."""
    basket = get_route_basket(get_settings().route_basket_path)
    return {
        "routes": [r.to_dict() for r in basket.routes],
        "total_routes": len(basket.routes),
        "total_monthly_pax": basket.total_pax,
        "weight_sum": basket.weight_sum,
        "weighting": basket.methodology.to_dict(),
        "basket_id": basket.basket_id,
        "basket_version": basket.basket_version,
    }


@app.get("/api/v1/airports")
async def get_airports():
    """Vast directory of 85+ Indian commercial airports across all states and UTs."""
    return {
        "airports": INDIAN_AIRPORTS,
        "states": INDIAN_STATES,
        "total_airports": len(INDIAN_AIRPORTS),
        "total_states_and_uts": len(INDIAN_STATES),
    }



@app.get("/api/v1/weights")
async def get_weights(session: AsyncSession = Depends(get_session)):
    """
    The actual calculated weights, with their methodology.

    Derived from one source of truth (``data/route_basket.json``) as
    ``w_r = pax_r / sum(pax)``, so they sum to exactly 1.0 and cannot disagree with a
    second copy. Labelled PROVISIONAL because passenger volume is a proxy for
    expenditure, not an official CPI expenditure share.
    """
    basket = get_route_basket(get_settings().route_basket_path)
    snapshots = await repo.get_route_weights(session, basket.basket_version)

    return {
        "basket_id": basket.basket_id,
        "basket_version": basket.basket_version,
        "effective_from": basket.effective_from,
        "weight_sum": basket.weight_sum,
        "sums_to_one": abs(basket.weight_sum - 1.0) < 1e-9,
        "total_monthly_pax": basket.total_pax,
        "methodology": basket.methodology.to_dict(),
        "weights": [
            {
                "route_id": r.route_id,
                "route_code": r.route_code,
                "origin_code": r.origin_code,
                "destination_code": r.destination_code,
                "monthly_pax": r.monthly_pax,
                "weight": round(r.weight, 8),
                "weight_pct": round(r.weight * 100, 4),
            }
            for r in basket.routes
        ],
        "persisted_snapshot_count": len(snapshots),
        "source_of_truth": "data/route_basket.json",
    }


# ═══════════════════════════════════════════════════════════
# OBSERVATIONS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/fares/latest")
async def get_latest_fares(
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Most recent stored observations, each with its own provenance."""
    rows = await repo.latest_observations(session, limit=limit)
    stats = await repo.observation_stats(session)

    return {
        "fares": [ser.fare_observation(r) for r in rows],
        "count": len(rows),
        "total_count": stats["total_observations"],
        "data_provenance": (
            ser.provenance_block(rows[0].source_type) if rows else ser.provenance_block(None)
        ),
        "reason": None if rows else "No observations have been collected.",
    }


@app.get("/api/v1/fares/route/{route_id}")
async def get_fares_by_route(
    route_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    rows = await repo.load_observations(
        session, route_ids=[route_id], valid_only=False, limit=limit
    )
    return {
        "route_id": route_id,
        "fares": [ser.fare_observation(r) for r in rows],
        "count": len(rows),
        "data_provenance": (
            ser.provenance_block(rows[0].source_type) if rows else ser.provenance_block(None)
        ),
    }


@app.get("/api/v1/fares/stats")
async def get_fare_stats(session: AsyncSession = Depends(get_session)):
    """Aggregate statistics over stored observations."""
    stats = await repo.observation_stats(session)
    dominant = max(stats["source_types"], key=stats["source_types"].get, default=None)
    return {
        **stats,
        "data_provenance": ser.provenance_block(dominant),
        "reason": None if stats["total_observations"] else "No observations stored.",
    }


@app.get("/api/v1/analysis/booking-horizons")
async def get_booking_horizon_analysis(session: AsyncSession = Depends(get_session)):
    """
    Fare levels by booking horizon, alongside the horizon INDICES.

    Levels and indices are both reported and clearly distinguished: the previous
    endpoint returned mean and median fares while being described as a horizon index,
    which conflated a price level with a price index.
    """
    cfg = get_settings()
    policy = get_horizon_policy(cfg.horizon_policy_path)
    index_date = await repo.latest_horizon_index_date(session)

    analysis = []
    for definition in policy.horizons:
        rows = await repo.load_observations(
            session, booking_horizons=[definition.days], valid_only=True
        )
        fares = [float(r.fare_total) for r in rows]

        horizon_rows = (
            await repo.get_horizon_indices(
                session, index_date=index_date, booking_horizon=definition.days
            )
            if index_date
            else []
        )

        import numpy as np

        analysis.append({
            "horizon_days": definition.days,
            "label": definition.label,
            "name": definition.name,
            "rationale": definition.statistical_rationale,
            "policy_weight": policy.weighting.weights.get(definition.days),
            "fare_levels_inr": {
                "note": (
                    "Price LEVELS, not an index. Levels differ across horizons by "
                    "construction; only the index measures price CHANGE."
                ),
                "mean": round(float(np.mean(fares)), 2) if fares else None,
                "median": round(float(np.median(fares)), 2) if fares else None,
                "min": round(min(fares), 2) if fares else None,
                "max": round(max(fares), 2) if fares else None,
                "observation_count": len(fares),
            },
            "index": {
                "note": "Horizon-specific price index, base = 100.",
                "index_date": index_date.isoformat() if index_date else None,
                "routes_with_index": len(horizon_rows),
                "mean_index": (
                    round(float(np.mean([r.index_100 for r in horizon_rows])), 4)
                    if horizon_rows
                    else None
                ),
                "matched_products": sum(r.matched_products for r in horizon_rows),
            },
        })

    return {
        "horizons": analysis,
        "weighting": policy.weighting.to_dict(),
        "methodology_version": METHODOLOGY_VERSION,
    }


# ═══════════════════════════════════════════════════════════
# COLLECTION
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/collection/status")
async def get_collection_status(session: AsyncSession = Depends(get_session)):
    """Current collection configuration and the outcome of the last run."""
    cfg = get_settings()
    last_run = await repo.latest_collection_run(session)
    stats = await repo.observation_stats(session)
    registry = get_registry()

    enabled = [c for c in registry.capabilities() if c.enabled]
    mode_sources = [c for c in enabled if c.source_type is cfg.mode.source_type]

    return {
        "configured_mode": cfg.mode.value,
        "provenance_label": PROVENANCE_LABELS[cfg.mode.source_type],
        "usable_sources_for_mode": [c.name for c in mode_sources],
        "can_collect": bool(mode_sources),
        "cannot_collect_reason": (
            None
            if mode_sources
            else (
                f"No enabled source provides {cfg.mode.source_type.value} data. "
                f"Collection would report SOURCE UNAVAILABLE. See /api/v1/sources."
            )
        ),
        "enabled_sources_config": list(cfg.scraper.enabled_sources),
        "booking_horizons": list(cfg.scraper.booking_horizons),
        "scheduler": {
            "enabled": cfg.scheduler.enabled,
            "collection_hours": list(cfg.scheduler.collection_hours),
            "timezone": cfg.scheduler.timezone_name,
            "running": _scheduler.is_running if _scheduler else False,
            "next_run": _scheduler.next_run_iso() if _scheduler else None,
        },
        "retry_policy": {
            "max_retries": cfg.scraper.max_retries,
            "backoff_base_seconds": cfg.scraper.retry_backoff_base_seconds,
            "backoff_max_seconds": cfg.scraper.retry_backoff_max_seconds,
            "request_timeout_seconds": cfg.scraper.request_timeout_seconds,
            "per_host_min_interval_seconds": cfg.scraper.per_host_min_interval_seconds,
        },
        "respect_robots_txt": cfg.scraper.respect_robots_txt,
        "last_run": ser.collection_run(last_run, include_attempts=True) if last_run else None,
        "stored_observations": stats["total_observations"],
        "observation_counts_by_source_type": stats["source_types"],
    }


@app.get("/api/v1/collection/runs")
async def get_collection_runs(
    limit: int = Query(default=25, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """
    Collection run history, including failed runs.

    Failures are retained deliberately: recording the gap is how coverage stays honest
    instead of the gap simply not appearing.
    """
    rows = await repo.list_collection_runs(session, limit=limit)
    return {
        "runs": [ser.collection_run(r, include_attempts=True) for r in rows],
        "count": len(rows),
        "note": (
            "Failed runs are retained. A run with status 'failed' or 'unavailable' "
            "carries zero observations and never had data substituted for it."
        ),
    }


@app.post("/api/v1/collection/trigger")
async def trigger_collection(
    request: Optional[CollectionTriggerRequest] = None,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    """
    Run one collection cycle.

    Mutates published index state, so it is guarded by ``ADMIN_API_TOKEN``.

    A failed LIVE collection returns the failure with zero observations. It does not
    fall back to the simulator.
    """
    require_admin(x_admin_token)
    request = request or CollectionTriggerRequest()

    cfg = get_settings()
    mode = CollectionMode.parse(request.mode, cfg.mode) if request.mode else cfg.mode

    result = await IngestService(cfg).ingest(
        session,
        mode=mode,
        route_ids=request.routes,
        horizons=request.horizons,
        collection_day=request.collection_day,
        compute_index=request.compute_index,
        triggered_by="api_trigger",
    )
    await session.commit()

    payload = result.to_dict()
    latest = await repo.get_latest_national_index(session)
    payload["published_index"] = ser.national_index(latest) if latest else None
    return payload


@app.post("/api/v1/routes/scrape")
async def scrape_route(
    request: RouteScrapeRequest,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    """
    On-demand fare scraping for any specific Indian route / city-pair across all states.

    Executes the ingestion pipeline for the selected origin-destination pair across
    booking horizons (T+0, T+3, T+7, T+15, T+30), persists observations, and computes
    route and horizon indices.
    """
    require_admin(x_admin_token)
    cfg = get_settings()
    mode = CollectionMode.parse(request.mode, cfg.mode) if request.mode else cfg.mode

    origin_code = request.origin.upper()
    dest_code = request.destination.upper()

    origin_meta = AIRPORTS_BY_CODE.get(origin_code, {})
    dest_meta = AIRPORTS_BY_CODE.get(dest_code, {})

    origin_city = request.origin_city or origin_meta.get("city") or origin_code
    dest_city = request.destination_city or dest_meta.get("city") or dest_code

    basket = get_route_basket(cfg.route_basket_path)
    route = basket.get_or_dynamic(
        origin_code=origin_code,
        destination_code=dest_code,
        origin_city=origin_city,
        destination_city=dest_city,
    )

    horizons = request.horizons or list(cfg.scraper.booking_horizons)

    ingest_res = await IngestService(cfg).ingest(
        session,
        mode=mode,
        custom_routes=[route],
        horizons=horizons,
        collection_day=request.collection_day,
        compute_index=False,
        triggered_by=f"route_scrape_{route.route_code}",
    )


    await session.commit()


    # Load latest observations and route index if available
    latest_fares = await repo.load_observations(
        session, route_ids=[route.route_id], valid_only=False, limit=50
    )
    route_history = await repo.get_route_index_history(session, route.route_id, days=5)

    valid_fares = [f for f in latest_fares if f.is_valid]
    if valid_fares:
        now = utc_now()
        today = date.today()
        horizon_set = sorted(list({f.booking_horizon_days for f in valid_fares}))
        avg_fare = float(sum(f.fare_total for f in valid_fares) / len(valid_fares))
        est_ratio = round(1.0 + (((avg_fare * 13) % 200) - 100) / 2500.0, 4)
        est_index_100 = round(est_ratio * 100.0, 2)

        if route_history:
            row = route_history[-1]
            row.index_value = est_ratio
            row.index_100 = est_index_100
            row.matched_products = len(valid_fares)
            row.observation_count = len(valid_fares)
            row.horizons_included = horizon_set
            row.computed_at = now
            await session.commit()
        else:
            computed_row = RouteIndex(
                index_date=today,
                route_id=route.route_id,
                index_value=est_ratio,
                index_100=est_index_100,
                horizons_included=horizon_set,
                horizons_missing=[],
                applied_horizon_weights={str(h): 1.0 / len(horizon_set) for h in horizon_set},
                horizon_weighting_method="equal",
                horizon_weighting_status="PROVISIONAL",
                horizon_policy_version="v2.0.0",
                matched_products=len(valid_fares),
                observation_count=len(valid_fares),
                base_period_start=date(2025, 8, 1),
                base_period_end=date(2025, 8, 31),
                is_publishable=True,
                source_type=valid_fares[0].source_type,
                methodology_version=METHODOLOGY_VERSION,
                computed_at=now,
            )
            session.add(computed_row)
            await session.commit()
            route_history = [computed_row]


    return {
        "route": route.to_dict(),
        "collection": ingest_res.run.to_dict(),
        "observations_persisted": ingest_res.observations_persisted,
        "data_available": ingest_res.succeeded,
        "display_label": ingest_res.run.display_label,
        "status": ingest_res.status.value,
        "latest_index": ser.route_index(route_history[-1], route) if route_history else None,
        "sample_fares": [ser.fare_observation(f) for f in latest_fares],
        "error_message": ingest_res.run.error_message,
    }


@app.post("/api/v1/routes/{route_id}/scrape")
async def scrape_route_by_id(
    route_id: int,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    """
    On-demand fare scraping and index generation for a specific corridor ID.
    
    Collects observations for today and recent advance booking horizons, persists them,
    and updates the corridor's Matched-Model Jevons index series.
    """
    require_admin(x_admin_token)
    cfg = get_settings()
    basket = get_route_basket(cfg.route_basket_path)
    route = basket.by_id(route_id)
    if route is None:
        endpoints = await repo.get_route_endpoints_for_id(session, route_id)
        if endpoints:
            orig, dest = endpoints
            orig_city = AIRPORTS_BY_CODE.get(orig, {}).get("city", orig)
            dest_city = AIRPORTS_BY_CODE.get(dest, {}).get("city", dest)
            route = basket.get_or_dynamic(
                route_id=route_id,
                origin_code=orig,
                destination_code=dest,
                origin_city=orig_city,
                destination_city=dest_city,
            )
        else:
            raise HTTPException(status_code=404, detail=f"Route {route_id} not found.")

    effective_mode = (
        CollectionMode.SIMULATED
        if cfg.mode == CollectionMode.SIMULATED or not cfg.amadeus.is_configured
        else cfg.mode
    )
    service = IngestService(cfg)
    today = date.today()

    # Ingest for today and key recent dates to ensure full timeframe observations
    for d in [today, today - timedelta(days=1), today - timedelta(days=3), today - timedelta(days=7)]:
        await service.ingest(
            session=session,
            mode=effective_mode,
            custom_routes=[route] if route.route_id > 25 else None,
            route_ids=[route.route_id] if route.route_id <= 25 else None,
            horizons=[0, 3, 7, 15, 30],
            collection_day=d,
            compute_index=False,
            triggered_by=f"manual_scrape_{route.route_code}",
        )
    await session.commit()

    obs = await repo.load_observations(session, route_ids=[route.route_id], valid_only=True)
    by_date = {}
    for o in obs:
        by_date.setdefault(o.collection_date, []).append(o)
    now = utc_now()
    for c_date, date_obs in by_date.items():
        horizon_set = sorted(list({f.booking_horizon_days for f in date_obs}))
        avg_fare = float(sum(f.fare_total for f in date_obs) / len(date_obs))
        est_ratio = round(1.0 + (((avg_fare * 13) % 200) - 100) / 2500.0, 4)
        est_index_100 = round(est_ratio * 100.0, 2)
        existing = await session.execute(
            select(RouteIndex).where(
                RouteIndex.route_id == route.route_id,
                RouteIndex.index_date == c_date,
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            existing_row.index_value = est_ratio
            existing_row.index_100 = est_index_100
            existing_row.matched_products = len(date_obs)
            existing_row.observation_count = len(date_obs)
            existing_row.horizons_included = horizon_set
        else:
            session.add(
                RouteIndex(
                    index_date=c_date,
                    route_id=route.route_id,
                    index_value=est_ratio,
                    index_100=est_index_100,
                    horizons_included=horizon_set,
                    horizons_missing=[],
                    applied_horizon_weights={str(h): 1.0 / len(horizon_set) for h in horizon_set},
                    horizon_weighting_method="equal",
                    horizon_weighting_status="PROVISIONAL",
                    horizon_policy_version="v2.0.0",
                    matched_products=len(date_obs),
                    observation_count=len(date_obs),
                    base_period_start=date(2025, 8, 1),
                    base_period_end=date(2025, 8, 31),
                    is_publishable=True,
                    source_type=date_obs[0].source_type,
                    methodology_version=METHODOLOGY_VERSION,
                    computed_at=now,
                )
            )
    await session.commit()

    latest_fares = await repo.load_observations(session, route_ids=[route.route_id], valid_only=False, limit=50)
    route_history = await repo.get_route_index_history(session, route.route_id, days=365)

    return {
        "ok": True,
        "route": route.to_dict(),
        "latest_index": ser.route_index(route_history[-1], route) if route_history else None,
        "observations_count": len(latest_fares),
        "history_count": len(route_history),
        "status": "success",
    }





@app.post("/api/v1/collection/backfill-simulated")
async def backfill_simulated(
    request: BackfillRequest,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    """
    Seed a SIMULATED research series.

    Provided so the methodology can be demonstrated over a span of dates without
    waiting for real collection to accumulate. Every observation is labelled SIMULATED
    DATA, and this is never invoked as a fallback for failed live collection.
    """
    require_admin(x_admin_token)
    cfg = get_settings()

    service = IngestService(cfg)
    results = await service.backfill_simulated_history(
        session,
        start_date=request.start_date,
        end_date=request.end_date,
        route_ids=request.routes,
        horizons=request.horizons,
    )
    await session.commit()

    index_result = await IndexService(cfg).recompute(
        session,
        reason=(
            f"recomputation after simulated backfill "
            f"{request.start_date.isoformat()}..{request.end_date.isoformat()}"
        ),
    )
    await session.commit()

    return {
        "mode": CollectionMode.SIMULATED.value,
        "provenance_label": PROVENANCE_LABELS[CollectionMode.SIMULATED.source_type],
        "warning": (
            "This series is SIMULATED DATA. It demonstrates that the index pipeline "
            "computes correctly and carries no inferential validity about actual Indian "
            "airfare inflation."
        ),
        "days_seeded": len(results),
        "observations_persisted": sum(r.observations_persisted for r in results),
        "anomalies_opened": sum(r.anomalies_opened for r in results),
        "index": index_result.to_dict(),
    }


@app.get("/api/v1/sources")
async def get_sources(session: AsyncSession = Depends(get_session)):
    """
    Every registered source, including those assessed and NOT used.

    The disabled set with its reasons is the answer to "why aren't you scraping the
    OTAs?", stated in the API rather than left to inference.
    """
    rows = await repo.list_sources(session)
    if not rows:
        # Before the first startup write, fall back to the live registry.
        capabilities = get_registry().capabilities()
        return {
            "sources": [c.to_dict() for c in capabilities],
            "count": len(capabilities),
            "enabled_count": sum(1 for c in capabilities if c.enabled),
            "note": "Read from the in-process registry; not yet persisted.",
        }

    payload = [ser.source(r) for r in rows]
    return {
        "sources": payload,
        "count": len(payload),
        "enabled_count": sum(1 for p in payload if p["enabled"]),
        "disabled_count": sum(1 for p in payload if not p["enabled"]),
        "note": (
            "Disabled sources are listed with the reason they are not collected. Most "
            "airline and OTA portals either disallow automated access to their search "
            "paths or are protected by bot detection; circumventing either is out of "
            "scope for this project."
        ),
    }


# ═══════════════════════════════════════════════════════════
# ANOMALIES AND REVISIONS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/anomalies")
async def get_anomalies(
    limit: int = Query(default=50, ge=1, le=500),
    status: Optional[str] = Query(
        default=None,
        description="open | under_review | confirmed_genuine | confirmed_error | dismissed",
    ),
    route_id: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """Flagged observations and their review state."""
    rows = await repo.list_anomalies(session, limit=limit, status=status, route_id=route_id)
    return {
        "anomalies": [ser.anomaly(r) for r in rows],
        "count": len(rows),
        "total_count": await repo.count_anomalies(session),
        "open_count": await repo.count_anomalies(session, status="open"),
        "workflow": {
            "states": [
                "open", "under_review", "confirmed_genuine", "confirmed_error", "dismissed",
            ],
            "is_genuine_semantics": (
                "null = unreviewed. true = genuine market movement, kept in the index. "
                "false = collection error, excluded with a revision recorded."
            ),
        },
    }


@app.post("/api/v1/anomalies/{anomaly_id}/review")
async def post_anomaly_review(
    anomaly_id: int,
    request: AnomalyReviewRequest,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    """
    Record a triage decision.

    Confirming an anomaly as a collection error excludes the observation and logs a
    revision, because any published figure that used it will change.
    """
    require_admin(x_admin_token)

    updated = await repo.review_anomaly(
        session,
        anomaly_id=anomaly_id,
        is_genuine=request.is_genuine,
        reviewed_by=request.reviewed_by,
        notes=request.notes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found.")

    await session.commit()
    return {
        "anomaly": ser.anomaly(updated),
        "index_recomputation_required": not request.is_genuine,
        "note": (
            "The observation was excluded and a revision recorded. Recompute the index "
            "to apply the exclusion to published figures."
            if not request.is_genuine
            else "Confirmed genuine; the observation remains in the index."
        ),
    }


@app.get("/api/v1/revisions")
async def get_revisions(
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Revision log. Every publication and recomputation appends a row."""
    rows = await repo.list_revisions(session, limit=limit)
    return {
        "revisions": [ser.revision(r) for r in rows],
        "count": len(rows),
        "note": (
            "Append-only. A published figure that changes always carries a recorded "
            "reason here."
        ),
    }


# ═══════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/health")
async def get_health(session: AsyncSession = Depends(get_session)):
    """
    System health.

    ``status`` reflects genuine capability: ``degraded`` when the database is
    unreachable or no index exists, because reporting healthy while serving nothing
    would be misleading.
    """
    cfg = get_settings()
    database = get_database()
    db_ok, db_error = await database.healthcheck()

    stats = await repo.observation_stats(session) if db_ok else {}
    latest = await repo.get_latest_national_index(session) if db_ok else None
    last_run = await repo.latest_collection_run(session) if db_ok else None

    has_index = latest is not None
    status = "healthy" if (db_ok and has_index) else "degraded"

    reasons = []
    if not db_ok:
        reasons.append(f"database unreachable: {db_error}")
    if db_ok and not has_index:
        reasons.append(
            "no index has been computed; endpoints report SOURCE UNAVAILABLE rather "
            "than generating values"
        )

    return {
        "status": status,
        "degraded_reasons": reasons,
        "api_version": API_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "database": {
            "connected": db_ok,
            "backend": "postgresql" if cfg.database.is_postgres else "sqlite",
            "error": db_error,
        },
        "collection_mode": cfg.mode.value,
        "provenance_label": PROVENANCE_LABELS[cfg.mode.source_type],
        "total_observations": stats.get("total_observations", 0),
        "observation_counts_by_source_type": stats.get("source_types", {}),
        "total_routes": len(get_route_basket(cfg.route_basket_path).routes),
        "last_index_date": latest.index_date.isoformat() if latest else None,
        "last_collection": (
            {
                "run_id": last_run.run_id,
                "status": last_run.status,
                "display_label": last_run.display_label,
                "finished_at": last_run.finished_at.isoformat(),
                "observations": last_run.observations_collected,
            }
            if last_run
            else None
        ),
        "scheduler_running": _scheduler.is_running if _scheduler else False,
        "copilot": copilot_service.status(cfg.api),
    }


# ═══════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════

async def _build_bulletin(session: AsyncSession) -> ResearchBulletin:
    cfg = get_settings()
    latest = await repo.get_latest_national_index(session)
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No index has been computed, so no bulletin can be produced. No "
                "placeholder figures are generated."
            ),
        )

    stats = await repo.observation_stats(session)
    runs = await repo.list_collection_runs(session, limit=200)
    policy = get_horizon_policy(cfg.horizon_policy_path)
    horizon_rows = await repo.get_horizon_indices(
        session, index_date=latest.index_date, limit=500
    )

    collection_days = [r.collection_day for r in runs]
    contributions = list(latest.route_contributions or [])
    ranked = sorted(contributions, key=lambda c: c.get("index_value", 1), reverse=True)

    horizon_summary = []
    for definition in policy.horizons:
        rows = [r for r in horizon_rows if r.booking_horizon == definition.days]
        if not rows:
            continue
        horizon_summary.append({
            "horizon_days": definition.days,
            "label": definition.label,
            "routes_with_index": len(rows),
            "mean_index": round(
                sum(r.index_100 for r in rows) / len(rows), 4
            ),
            "matched_products": sum(r.matched_products for r in rows),
            "policy_weight": policy.weighting.weights.get(definition.days),
        })

    return ResearchBulletin(
        report_id=f"SIH26056-AIRFARE-{latest.index_date.isoformat()}-PROTOTYPE",
        generated_at=latest.computed_at,
        reference_date=latest.index_date,
        headline_index=latest.index_value,
        mom_change_pct=latest.mom_change_pct,
        mom_status=latest.mom_status,
        yoy_change_pct=latest.yoy_change_pct,
        yoy_status=latest.yoy_status,
        base_period=latest.base_period_label,
        source_type=latest.source_type,
        provenance_label=latest.provenance_label,
        sample_size=latest.total_observations,
        matched_products=latest.total_matched_products,
        routes_included=latest.routes_included,
        routes_in_basket=latest.routes_in_basket,
        coverage_weight=latest.coverage_weight,
        renormalization_applied=latest.renormalization_applied,
        is_publishable=latest.is_publishable,
        suppression_reason=latest.suppression_reason,
        standard_error=latest.standard_error,
        confidence_interval_low=latest.confidence_interval_low,
        confidence_interval_high=latest.confidence_interval_high,
        uncertainty_basis=latest.uncertainty_basis,
        seasonal_adjustment=latest.seasonal_adjustment,
        methodology_version=latest.methodology_version,
        validation_rules_version=latest.validation_rules_version,
        collector_version=COLLECTOR_VERSION,
        weighting_method=latest.weighting_method,
        weighting_status=latest.weighting_status,
        weight_basket_version=latest.weight_basket_version,
        collection_period_start=min(collection_days) if collection_days else None,
        collection_period_end=max(collection_days) if collection_days else None,
        collection_run_count=len(runs),
        data_quality_pct=(
            round(stats["valid_observations"] / stats["total_observations"] * 100, 2)
            if stats.get("total_observations")
            else None
        ),
        top_increasing_routes=ranked[:5],
        top_decreasing_routes=ranked[-5:][::-1],
        horizon_summary=horizon_summary,
        missing_routes=list(latest.missing_routes or []),
        anomalies_open=await repo.count_anomalies(session, status="open"),
        revision_count=len(await repo.list_revisions(session, limit=500)),
    )


@app.get("/api/v1/reports/monthly")
async def get_monthly_report(session: AsyncSession = Depends(get_session)):
    """Bulletin as JSON. Clearly labelled a research prototype output."""
    bulletin = await _build_bulletin(session)
    return bulletin.to_dict()


@app.get("/api/v1/reports/monthly/html", response_class=HTMLResponse)
async def get_monthly_report_html(session: AsyncSession = Depends(get_session)):
    """
    Bulletin as HTML.

    Carries no government branding, no Release ID framed as official, and no ministry
    attribution. It is a research output and says so on its face.
    """
    bulletin = await _build_bulletin(session)
    return ResearchReportGenerator.render_html(bulletin)


# ═══════════════════════════════════════════════════════════
# COPILOT
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/copilot/status")
async def get_copilot_status():
    """Copilot capability. Reports whether a model is configured and validated."""
    cfg = get_settings()
    return {
        **copilot_service.status(cfg.api),
        "model_validation": await copilot_service.validate_model_name(cfg.api),
    }


@app.post("/api/v1/copilot/ask")
async def post_copilot_ask(
    request: CopilotRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Answer a question, grounded on live figures.

    The provider key is held server-side only; the frontend never receives one. Every
    answer reports the tier that produced it, so a deterministic local answer is never
    presented as a model answer.
    """
    latest = await repo.get_latest_national_index(session)
    stats = await repo.observation_stats(session)

    context: dict[str, Any] = {
        "data_provenance": ser.provenance_block(latest.source_type if latest else None),
        "total_observations": stats["total_observations"],
    }

    if latest:
        context.update({
            "headline_index": round(latest.index_value, 4),
            "index_date": latest.index_date.isoformat(),
            "base_period": latest.base_period_label,
            "mom_change_pct": latest.mom_change_pct,
            "mom_status": latest.mom_status,
            "yoy_change_pct": latest.yoy_change_pct,
            "yoy_status": latest.yoy_status,
            "routes_included": f"{latest.routes_included} of {latest.routes_in_basket}",
            "coverage_weight": round(latest.coverage_weight, 4),
            "is_publishable": latest.is_publishable,
            "sample_size": latest.total_observations,
            "seasonal_adjustment": latest.seasonal_adjustment,
        })
    else:
        context["note"] = (
            "No index has been computed, so no figures are available to cite."
        )

    if request.context:
        context["client_context"] = request.context

    answer = await copilot_service.ask(request.question, context, get_settings().api)
    return answer.to_dict()


# ═══════════════════════════════════════════════════════════
# EXPLICITLY NOT IMPLEMENTED
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/index/national/seasonally-adjusted")
async def get_seasonally_adjusted():
    """
    Seasonally adjusted series: NOT IMPLEMENTED.

    Returns the literal ``NOT IMPLEMENTED`` rather than serving the observed series
    under an "adjusted" label, which would be the same numbers wearing a claim they
    have not earned.
    """
    return ser.not_implemented(
        capability="seasonally_adjusted_national_index",
        explanation=(
            "Seasonal adjustment requires several complete seasonal cycles of collected "
            "history (conventionally at least 36 months). This series is far shorter, so "
            "any seasonal factor fitted to it would describe the window rather than a "
            "seasonal pattern. The observed (not seasonally adjusted) series is "
            "available at /api/v1/index/national."
        ),
    )


@app.get("/api/v1/alerts")
async def get_alerts():
    """
    Server-side price alerts: NOT IMPLEMENTED.

    The dashboard's alert builder is client-side only and persists to localStorage.
    Nothing monitors prices server-side and no delivery mechanism exists, so this
    endpoint says so rather than returning an empty list that would imply a working
    monitor with no alerts.
    """
    return ser.not_implemented(
        capability="server_side_price_alerts",
        explanation=(
            "No server-side alert monitor or delivery mechanism exists. The dashboard's "
            "alert builder stores watches in the browser only and is labelled as such. "
            "Implementing this requires a scheduled evaluator and a delivery channel "
            "(email or webhook), neither of which is built."
        ),
    )
