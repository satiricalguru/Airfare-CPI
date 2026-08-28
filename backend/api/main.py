"""
SIH26056 — Real-Time Airfare CPI — FastAPI Application

Main API server providing endpoints for:
- National and route-level CPI indices
- Raw fare observations
- Pipeline triggers (for live demo)
- System health monitoring
- Report generation
"""

import os
import json
import numpy as np
from datetime import date, datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from loguru import logger

from .models import (
    RouteResponse, RouteListResponse,
    FareObservationResponse, FareListResponse,
    NationalIndexResponse, NationalIndexHistoryResponse,
    NationalIndexDetailResponse, RouteContributionResponse,
    RouteIndexResponse,
    SystemHealthResponse, ScraperHealthResponse,
    AnomalyResponse, AnomalyListResponse,
    ScrapeRequest, ScrapeResponse,
    MonthlyReportResponse,
)

# Import engine and scraper
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from engine.jevons import JevonsIndexCalculator
from engine.aggregator import NationalAggregator, RouteWeight
from scraper.scrapers.mock_scraper import MockFareGenerator, observations_to_dicts
from scraper.validator import FareValidator
from reports.generator import MoSPIReportGenerator, MonthlyBulletin


# ── In-Memory Data Store ──
# For the SIH prototype, we use in-memory storage alongside PostgreSQL
# This ensures the demo works even without a database connection

class DataStore:
    """In-memory data store for prototype demo reliability."""
    
    def __init__(self):
        self.routes: list[dict] = []
        self.fare_observations: list[dict] = []
        self.route_indices: list[dict] = []
        self.national_indices: list[dict] = []
        self.scraper_health: list[dict] = []
        self.anomalies: list[dict] = []
        self._obs_counter = 0
        self._anomaly_counter = 0
    
    def add_observation(self, obs: dict) -> int:
        self._obs_counter += 1
        obs["observation_id"] = self._obs_counter
        self.fare_observations.append(obs)
        return self._obs_counter
    
    def add_anomaly(self, anomaly: dict) -> int:
        self._anomaly_counter += 1
        anomaly["id"] = self._anomaly_counter
        self.anomalies.append(anomaly)
        return self._anomaly_counter


# Global instances
store = DataStore()
mock_generator = MockFareGenerator(seed=42)
validator = FareValidator()
jevons_calculator = JevonsIndexCalculator()


def load_routes():
    """Load route data from seed configuration."""
    # Routes matching our seed_routes.sql
    routes_data = [
        {"route_id": 1, "origin_code": "DEL", "destination_code": "BOM", "origin_city": "New Delhi", "destination_city": "Mumbai", "dgca_monthly_pax": 1200000, "weight": 0.0784},
        {"route_id": 2, "origin_code": "DEL", "destination_code": "BLR", "origin_city": "New Delhi", "destination_city": "Bengaluru", "dgca_monthly_pax": 950000, "weight": 0.0621},
        {"route_id": 3, "origin_code": "BOM", "destination_code": "BLR", "origin_city": "Mumbai", "destination_city": "Bengaluru", "dgca_monthly_pax": 870000, "weight": 0.0569},
        {"route_id": 4, "origin_code": "DEL", "destination_code": "HYD", "origin_city": "New Delhi", "destination_city": "Hyderabad", "dgca_monthly_pax": 780000, "weight": 0.0510},
        {"route_id": 5, "origin_code": "DEL", "destination_code": "CCU", "origin_city": "New Delhi", "destination_city": "Kolkata", "dgca_monthly_pax": 740000, "weight": 0.0484},
        {"route_id": 6, "origin_code": "BOM", "destination_code": "HYD", "origin_city": "Mumbai", "destination_city": "Hyderabad", "dgca_monthly_pax": 650000, "weight": 0.0425},
        {"route_id": 7, "origin_code": "DEL", "destination_code": "MAA", "origin_city": "New Delhi", "destination_city": "Chennai", "dgca_monthly_pax": 600000, "weight": 0.0392},
        {"route_id": 8, "origin_code": "BOM", "destination_code": "CCU", "origin_city": "Mumbai", "destination_city": "Kolkata", "dgca_monthly_pax": 520000, "weight": 0.0340},
        {"route_id": 9, "origin_code": "BLR", "destination_code": "HYD", "origin_city": "Bengaluru", "destination_city": "Hyderabad", "dgca_monthly_pax": 480000, "weight": 0.0314},
        {"route_id": 10, "origin_code": "DEL", "destination_code": "GOI", "origin_city": "New Delhi", "destination_city": "Goa", "dgca_monthly_pax": 450000, "weight": 0.0294},
        {"route_id": 11, "origin_code": "BOM", "destination_code": "MAA", "origin_city": "Mumbai", "destination_city": "Chennai", "dgca_monthly_pax": 430000, "weight": 0.0281},
        {"route_id": 12, "origin_code": "BLR", "destination_code": "CCU", "origin_city": "Bengaluru", "destination_city": "Kolkata", "dgca_monthly_pax": 400000, "weight": 0.0261},
        {"route_id": 13, "origin_code": "DEL", "destination_code": "PNQ", "origin_city": "New Delhi", "destination_city": "Pune", "dgca_monthly_pax": 390000, "weight": 0.0255},
        {"route_id": 14, "origin_code": "BOM", "destination_code": "GOI", "origin_city": "Mumbai", "destination_city": "Goa", "dgca_monthly_pax": 380000, "weight": 0.0248},
        {"route_id": 15, "origin_code": "DEL", "destination_code": "AMD", "origin_city": "New Delhi", "destination_city": "Ahmedabad", "dgca_monthly_pax": 370000, "weight": 0.0242},
        {"route_id": 16, "origin_code": "BLR", "destination_code": "MAA", "origin_city": "Bengaluru", "destination_city": "Chennai", "dgca_monthly_pax": 340000, "weight": 0.0222},
        {"route_id": 17, "origin_code": "DEL", "destination_code": "JAI", "origin_city": "New Delhi", "destination_city": "Jaipur", "dgca_monthly_pax": 320000, "weight": 0.0209},
        {"route_id": 18, "origin_code": "BOM", "destination_code": "AMD", "origin_city": "Mumbai", "destination_city": "Ahmedabad", "dgca_monthly_pax": 310000, "weight": 0.0203},
        {"route_id": 19, "origin_code": "DEL", "destination_code": "LKO", "origin_city": "New Delhi", "destination_city": "Lucknow", "dgca_monthly_pax": 300000, "weight": 0.0196},
        {"route_id": 20, "origin_code": "BLR", "destination_code": "GOI", "origin_city": "Bengaluru", "destination_city": "Goa", "dgca_monthly_pax": 280000, "weight": 0.0183},
        {"route_id": 21, "origin_code": "HYD", "destination_code": "CCU", "origin_city": "Hyderabad", "destination_city": "Kolkata", "dgca_monthly_pax": 270000, "weight": 0.0176},
        {"route_id": 22, "origin_code": "DEL", "destination_code": "PAT", "origin_city": "New Delhi", "destination_city": "Patna", "dgca_monthly_pax": 260000, "weight": 0.0170},
        {"route_id": 23, "origin_code": "BOM", "destination_code": "JAI", "origin_city": "Mumbai", "destination_city": "Jaipur", "dgca_monthly_pax": 240000, "weight": 0.0157},
        {"route_id": 24, "origin_code": "DEL", "destination_code": "COK", "origin_city": "New Delhi", "destination_city": "Kochi", "dgca_monthly_pax": 230000, "weight": 0.0150},
        {"route_id": 25, "origin_code": "BOM", "destination_code": "PNQ", "origin_city": "Mumbai", "destination_city": "Pune", "dgca_monthly_pax": 220000, "weight": 0.0144},
    ]
    
    store.routes = routes_data
    return routes_data


def generate_initial_data():
    """Generate 30 days of historical mock data on startup."""
    routes = store.routes
    base_date = date(2026, 8, 1)
    end_date = date.today()
    
    logger.info(f"Generating historical data from {base_date} to {end_date}...")
    
    all_obs = mock_generator.generate_historical(
        routes=routes,
        start_date=base_date,
        end_date=end_date,
    )
    
    obs_dicts = observations_to_dicts(all_obs)
    
    # Validate and store
    accepted, flagged, excluded = validator.validate_batch(obs_dicts)
    
    for obs in accepted + flagged:
        store.add_observation(obs)
    
    # Store anomalies
    for obs in flagged:
        store.add_anomaly({
            "route_id": obs.get("route_id"),
            "origin_code": obs.get("origin_code", ""),
            "destination_code": obs.get("destination_code", ""),
            "anomaly_type": "potential_anomaly",
            "severity": "low",
            "description": f"Flagged: {', '.join(obs.get('validation_flags', []))}",
            "fare_observed": obs.get("fare_total"),
            "action_taken": "flagged",
            "detected_at": datetime.now().isoformat(),
        })
    
    logger.info(
        f"Data loaded: {len(accepted)} accepted, "
        f"{len(flagged)} flagged, {len(excluded)} excluded"
    )
    
    # Compute indices for each day
    compute_all_indices(base_date, end_date)


def compute_all_indices(start_date: date, end_date: date):
    """Compute Jevons and national indices for all available dates."""
    routes = store.routes
    base_date = start_date
    
    # Build aggregator with route weights
    route_weights = [
        RouteWeight(
            route_id=r["route_id"],
            origin_code=r["origin_code"],
            destination_code=r["destination_code"],
            weight=r["weight"],
            monthly_pax=r["dgca_monthly_pax"],
        )
        for r in routes
    ]
    aggregator = NationalAggregator(route_weights)
    
    # Get base period prices (first week's geometric means per route)
    base_prices_by_route = {}
    for route in routes:
        route_fares = [
            obs["fare_total"]
            for obs in store.fare_observations
            if obs.get("route_id") == route["route_id"]
            and obs.get("scrape_timestamp", "")[:10] >= base_date.isoformat()
            and obs.get("scrape_timestamp", "")[:10] <= (base_date + timedelta(days=6)).isoformat()
            and obs.get("is_valid", True)
        ]
        if route_fares:
            base_prices_by_route[route["route_id"]] = float(
                np.exp(np.mean(np.log(np.array(route_fares))))
            )
    
    # Compute daily indices
    current = start_date + timedelta(days=7)  # Skip base period
    prev_national_cpi = None
    
    while current <= end_date:
        jevons_results = []
        
        for route in routes:
            # Get current day's prices for this route
            current_fares = [
                obs["fare_total"]
                for obs in store.fare_observations
                if obs.get("route_id") == route["route_id"]
                and obs.get("scrape_timestamp", "")[:10] == current.isoformat()
                and obs.get("is_valid", True)
            ]
            
            if not current_fares or route["route_id"] not in base_prices_by_route:
                continue
            
            result = jevons_calculator.compute_from_prices_only(
                current_prices=np.array(current_fares),
                base_geometric_mean=base_prices_by_route[route["route_id"]],
                route_id=route["route_id"],
                index_date=current,
                base_period_start=base_date,
                base_period_end=base_date + timedelta(days=6),
            )
            
            if result:
                jevons_results.append(result)
                store.route_indices.append({
                    "route_id": result.route_id,
                    "index_date": result.index_date.isoformat(),
                    "booking_horizon": result.booking_horizon,
                    "jevons_index": round(result.jevons_index, 4),
                    "observation_count": result.observation_count,
                    "geometric_mean_price": round(result.geometric_mean_price, 2),
                    "base_period": f"{result.base_period_start} to {result.base_period_end}",
                })
        
        # National aggregation
        if jevons_results:
            try:
                national = aggregator.compute_national_cpi(
                    jevons_results,
                    previous_cpi=prev_national_cpi,
                )
                store.national_indices.append({
                    "index_date": national.index_date.isoformat(),
                    "booking_horizon": national.booking_horizon,
                    "airfare_cpi": round(national.airfare_cpi, 2),
                    "mom_change_pct": round(national.mom_change_pct, 2) if national.mom_change_pct is not None else None,
                    "yoy_change_pct": round(national.yoy_change_pct, 2) if national.yoy_change_pct is not None else None,
                    "routes_included": national.routes_included,
                    "total_observations": national.total_observations,
                    "base_period": national.base_period,
                    "route_contributions": [
                        {
                            "route_id": rc.route_id,
                            "origin_code": rc.origin_code,
                            "destination_code": rc.destination_code,
                            "weight": round(rc.weight, 4),
                            "jevons_index": round(rc.jevons_index, 4),
                            "contribution_pct": round(rc.contribution_pct, 2),
                        }
                        for rc in national.route_contributions
                    ],
                })
                prev_national_cpi = national.airfare_cpi / 100  # Store as ratio for next iter
            except Exception as e:
                logger.error(f"National aggregation failed for {current}: {e}")
        
        current += timedelta(days=1)
    
    logger.info(f"Computed {len(store.national_indices)} national index values")


# ── App Lifecycle ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load routes + generate initial data."""
    logger.info("🛫 Starting Airfare CPI API...")
    load_routes()
    generate_initial_data()
    logger.info("✅ API ready with historical data")
    yield
    logger.info("🛬 Shutting down Airfare CPI API")


# ── FastAPI App ──

app = FastAPI(
    title="SIH26056 — Real-Time Airfare CPI",
    description=(
        "Real-Time Airfare Price Index for India — MoSPI CPI Augmentation. "
        "Collects domestic airfare data, computes route-level Jevons indices, "
        "and aggregates into a national Airfare CPI using DGCA passenger-volume weights."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# ROUTES ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/routes", response_model=RouteListResponse)
async def get_routes():
    """Get all monitored routes with DGCA weights."""
    routes = [
        RouteResponse(
            route_id=r["route_id"],
            origin_code=r["origin_code"],
            destination_code=r["destination_code"],
            origin_city=r["origin_city"],
            destination_city=r["destination_city"],
            dgca_monthly_pax=r["dgca_monthly_pax"],
            weight=r["weight"],
            is_active=True,
        )
        for r in store.routes
    ]
    return RouteListResponse(
        routes=routes,
        total_routes=len(routes),
        total_pax=sum(r.dgca_monthly_pax for r in routes),
    )


# ═══════════════════════════════════════════════════════════
# NATIONAL INDEX ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/index/national")
async def get_national_index():
    """Get the latest national Airfare CPI."""
    if not store.national_indices:
        raise HTTPException(status_code=404, detail="No index data available")
    
    latest = store.national_indices[-1]
    return latest


@app.get("/api/v1/index/national/history")
async def get_national_history(
    days: int = Query(default=30, ge=1, le=365),
):
    """Get historical national CPI series."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    history = [
        idx for idx in store.national_indices
        if idx["index_date"] >= cutoff
    ]
    return {"data": history, "count": len(history)}


# ═══════════════════════════════════════════════════════════
# ROUTE INDEX ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/index/routes")
async def get_route_indices():
    """Get the latest index for all routes."""
    # Get latest index per route
    latest_by_route = {}
    for idx in store.route_indices:
        rid = idx["route_id"]
        if rid not in latest_by_route or idx["index_date"] > latest_by_route[rid]["index_date"]:
            latest_by_route[rid] = idx
    
    # Enrich with route names
    route_map = {r["route_id"]: r for r in store.routes}
    result = []
    for rid, idx in latest_by_route.items():
        route = route_map.get(rid, {})
        result.append({
            **idx,
            "origin_code": route.get("origin_code", ""),
            "destination_code": route.get("destination_code", ""),
            "origin_city": route.get("origin_city", ""),
            "destination_city": route.get("destination_city", ""),
            "weight": route.get("weight", 0),
        })
    
    result.sort(key=lambda x: x.get("weight", 0), reverse=True)
    return {"routes": result, "count": len(result)}


@app.get("/api/v1/index/routes/{route_id}")
async def get_route_index_history(
    route_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get historical index for a specific route."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    history = [
        idx for idx in store.route_indices
        if idx["route_id"] == route_id and idx["index_date"] >= cutoff
    ]
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for route {route_id}")
    
    route = next((r for r in store.routes if r["route_id"] == route_id), None)
    
    return {
        "route": route,
        "history": sorted(history, key=lambda x: x["index_date"]),
        "count": len(history),
    }


# ═══════════════════════════════════════════════════════════
# FARE OBSERVATION ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/fares/latest")
async def get_latest_fares(
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get the most recent fare observations."""
    recent = store.fare_observations[-limit:]
    recent.reverse()
    return {"fares": recent, "total_count": len(store.fare_observations)}


@app.get("/api/v1/fares/route/{route_id}")
async def get_fares_by_route(
    route_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get fare observations for a specific route."""
    route_fares = [
        obs for obs in store.fare_observations
        if obs.get("route_id") == route_id
    ][-limit:]
    
    return {
        "fares": route_fares,
        "total_count": len(route_fares),
        "route_id": route_id,
    }


@app.get("/api/v1/fares/stats")
async def get_fare_stats():
    """Get aggregate fare statistics across all routes."""
    if not store.fare_observations:
        return {"stats": {}}
    
    fares = [obs["fare_total"] for obs in store.fare_observations if obs.get("is_valid")]
    
    return {
        "total_observations": len(store.fare_observations),
        "valid_observations": len(fares),
        "mean_fare": round(np.mean(fares), 2) if fares else 0,
        "median_fare": round(np.median(fares), 2) if fares else 0,
        "min_fare": round(min(fares), 2) if fares else 0,
        "max_fare": round(max(fares), 2) if fares else 0,
        "std_dev": round(np.std(fares), 2) if fares else 0,
        "routes_covered": len(set(obs["route_id"] for obs in store.fare_observations)),
        "airlines_covered": len(set(obs.get("airline_code", "") for obs in store.fare_observations)),
    }


# ═══════════════════════════════════════════════════════════
# PIPELINE TRIGGER (DEMO)
# ═══════════════════════════════════════════════════════════

@app.post("/api/v1/scraper/trigger", response_model=ScrapeResponse)
async def trigger_scrape(request: ScrapeRequest = None):
    """
    Trigger a scrape cycle manually (for live demo).
    Generates new mock observations and recomputes indices.
    """
    if request is None:
        request = ScrapeRequest()
    
    today = date.today()
    horizons = request.horizons or [0, 3, 7, 15, 30]
    target_routes = store.routes
    if request.routes:
        target_routes = [r for r in store.routes if r["route_id"] in request.routes]
    
    # Generate new observations
    new_obs = mock_generator.generate_day(
        routes=target_routes,
        target_date=today,
        booking_horizons=horizons,
        scrape_time=datetime.now(),
        base_date=date(2026, 8, 1),
    )
    
    obs_dicts = observations_to_dicts(new_obs)
    accepted, flagged, excluded = validator.validate_batch(obs_dicts)
    
    for obs in accepted + flagged:
        store.add_observation(obs)
    
    # Log scraper health
    store.scraper_health.append({
        "source_platform": "mock_generator",
        "scrape_timestamp": datetime.now().isoformat(),
        "status": "success",
        "fares_collected": len(accepted) + len(flagged),
        "response_time_ms": 150,
    })
    
    national_cpi = None
    
    if request.compute_index:
        # Recompute today's indices
        base_date = date(2026, 8, 1)
        base_prices = {}
        for route in store.routes:
            base_fares = [
                obs["fare_total"]
                for obs in store.fare_observations
                if obs.get("route_id") == route["route_id"]
                and obs.get("is_valid", True)
            ][:50]  # First 50 obs as base
            if base_fares:
                base_prices[route["route_id"]] = float(
                    np.exp(np.mean(np.log(np.array(base_fares[:20]))))
                )
        
        route_weights = [
            RouteWeight(
                route_id=r["route_id"],
                origin_code=r["origin_code"],
                destination_code=r["destination_code"],
                weight=r["weight"],
                monthly_pax=r["dgca_monthly_pax"],
            )
            for r in store.routes
        ]
        aggregator = NationalAggregator(route_weights)
        
        jevons_results = []
        for route in store.routes:
            today_fares = [
                obs["fare_total"]
                for obs in accepted + flagged
                if obs.get("route_id") == route["route_id"]
            ]
            
            if today_fares and route["route_id"] in base_prices:
                result = jevons_calculator.compute_from_prices_only(
                    current_prices=np.array(today_fares),
                    base_geometric_mean=base_prices[route["route_id"]],
                    route_id=route["route_id"],
                    index_date=today,
                    base_period_start=base_date,
                    base_period_end=base_date + timedelta(days=6),
                )
                if result:
                    jevons_results.append(result)
        
        if jevons_results:
            try:
                national = aggregator.compute_national_cpi(jevons_results)
                national_cpi = national.airfare_cpi
                
                store.national_indices.append({
                    "index_date": today.isoformat(),
                    "booking_horizon": None,
                    "airfare_cpi": national.airfare_cpi,
                    "mom_change_pct": national.mom_change_pct,
                    "yoy_change_pct": national.yoy_change_pct,
                    "routes_included": national.routes_included,
                    "total_observations": national.total_observations,
                    "base_period": national.base_period,
                    "route_contributions": [
                        {
                            "route_id": rc.route_id,
                            "origin_code": rc.origin_code,
                            "destination_code": rc.destination_code,
                            "weight": rc.weight,
                            "jevons_index": rc.jevons_index,
                            "contribution_pct": rc.contribution_pct,
                        }
                        for rc in national.route_contributions
                    ],
                })
            except Exception as e:
                logger.error(f"National CPI computation failed: {e}")
    
    return ScrapeResponse(
        status="success",
        observations_generated=len(new_obs),
        observations_valid=len(accepted),
        observations_flagged=len(flagged),
        observations_excluded=len(excluded),
        index_computed=national_cpi is not None,
        national_cpi=national_cpi,
        message=f"Scraped {len(target_routes)} routes × {len(horizons)} horizons",
    )


# ═══════════════════════════════════════════════════════════
# HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/health")
async def get_health():
    """System health overview."""
    return SystemHealthResponse(
        status="healthy",
        total_observations=len(store.fare_observations),
        total_routes=len(store.routes),
        active_scrapers=1,  # Mock scraper
        last_index_date=(
            date.fromisoformat(store.national_indices[-1]["index_date"])
            if store.national_indices else None
        ),
        scraper_health=[
            ScraperHealthResponse(
                source_platform=h["source_platform"],
                last_scrape=datetime.fromisoformat(h["scrape_timestamp"]),
                status=h["status"],
                fares_collected=h["fares_collected"],
                response_time_ms=h.get("response_time_ms"),
            )
            for h in store.scraper_health[-5:]
        ],
    )


# ═══════════════════════════════════════════════════════════
# ANOMALY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/anomalies")
async def get_anomalies(
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get flagged anomalies."""
    recent = store.anomalies[-limit:]
    recent.reverse()
    return {"anomalies": recent, "total_count": len(store.anomalies)}


# ═══════════════════════════════════════════════════════════
# REPORT ENDPOINT
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/reports/monthly")
async def get_monthly_report():
    """Generate a monthly report summary."""
    if not store.national_indices:
        raise HTTPException(status_code=404, detail="No data for report")
    
    latest = store.national_indices[-1]
    
    # Top inflating/deflating routes from latest contributions
    contributions = latest.get("route_contributions", [])
    sorted_by_index = sorted(contributions, key=lambda c: c.get("jevons_index", 1), reverse=True)
    
    return MonthlyReportResponse(
        report_month=latest["index_date"][:7],
        national_cpi=latest["airfare_cpi"],
        mom_change_pct=latest.get("mom_change_pct"),
        yoy_change_pct=latest.get("yoy_change_pct"),
        top_inflating_routes=sorted_by_index[:5],
        top_deflating_routes=sorted_by_index[-5:],
        data_quality={
            "total_observations": len(store.fare_observations),
            "valid_pct": round(
                len([o for o in store.fare_observations if o.get("is_valid")]) 
                / max(len(store.fare_observations), 1) * 100, 1
            ),
            "routes_covered": len(store.routes),
            "anomalies_detected": len(store.anomalies),
        },
        generated_at=datetime.now(),
    )


@app.get("/api/v1/reports/monthly/html", response_class=HTMLResponse)
async def get_monthly_report_html():
    """Generate and return the official MoSPI HTML publication bulletin."""
    if not store.national_indices:
        raise HTTPException(status_code=404, detail="No data for report")

    latest = store.national_indices[-1]
    contributions = latest.get("route_contributions", [])
    sorted_by_index = sorted(contributions, key=lambda c: c.get("jevons_index", 1), reverse=True)

    # Booking horizons summary
    horizons_summary = []
    for h in [0, 3, 7, 15, 30]:
        fares = [
            obs["fare_total"]
            for obs in store.fare_observations
            if obs.get("booking_horizon_days") == h and obs.get("is_valid", True)
        ]
        if fares:
            horizons_summary.append({
                "horizon_days": h,
                "avg_fare": float(np.mean(fares)),
                "median_fare": float(np.median(fares)),
                "observation_count": len(fares),
            })

    valid_pct = round(
        len([o for o in store.fare_observations if o.get("is_valid")]) 
        / max(len(store.fare_observations), 1) * 100, 1
    )

    bulletin = MonthlyBulletin(
        report_id=f"MoSPI-CPI-AIR-{latest['index_date'][:7]}",
        publication_date=datetime.now().strftime("%d %B %Y"),
        reference_month=datetime.strptime(latest["index_date"][:7], "%Y-%m").strftime("%B %Y"),
        headline_cpi=latest["airfare_cpi"],
        mom_rate_pct=latest.get("mom_change_pct", 0.0),
        routes_evaluated=len(store.routes),
        total_observations=len(store.fare_observations),
        top_accelerating_routes=sorted_by_index[:5],
        top_decelerating_routes=sorted_by_index[-5:],
        booking_horizon_summary=horizons_summary,
        data_quality_pct=valid_pct,
    )

    return MoSPIReportGenerator.generate_html_report(bulletin)



# ═══════════════════════════════════════════════════════════
# BOOKING HORIZON ANALYSIS
# ═══════════════════════════════════════════════════════════

@app.get("/api/v1/analysis/booking-horizons")
async def get_booking_horizon_analysis():
    """Analyze price differences across booking horizons."""
    horizons = [0, 3, 7, 15, 30]
    analysis = []
    
    for h in horizons:
        fares = [
            obs["fare_total"]
            for obs in store.fare_observations
            if obs.get("booking_horizon_days") == h
            and obs.get("is_valid", True)
        ]
        if fares:
            analysis.append({
                "horizon_days": h,
                "label": f"T+{h}",
                "avg_fare": round(np.mean(fares), 2),
                "median_fare": round(np.median(fares), 2),
                "min_fare": round(min(fares), 2),
                "max_fare": round(max(fares), 2),
                "observation_count": len(fares),
            })
    
    return {"horizons": analysis}


# ═══════════════════════════════════════════════════════════
# ROOT
# ═══════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """API root — project info."""
    return {
        "project": "SIH26056 — Real-Time Airfare CPI",
        "ministry": "MoSPI (Ministry of Statistics & Programme Implementation)",
        "version": "1.0.0",
        "endpoints": {
            "routes": "/api/v1/routes",
            "national_index": "/api/v1/index/national",
            "national_history": "/api/v1/index/national/history",
            "route_indices": "/api/v1/index/routes",
            "latest_fares": "/api/v1/fares/latest",
            "fare_stats": "/api/v1/fares/stats",
            "trigger_scrape": "/api/v1/scraper/trigger (POST)",
            "health": "/api/v1/health",
            "anomalies": "/api/v1/anomalies",
            "reports": "/api/v1/reports/monthly",
            "booking_horizons": "/api/v1/analysis/booking-horizons",
            "docs": "/docs",
        },
    }
