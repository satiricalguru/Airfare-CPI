"""
SIH26056 — Pydantic Response Models

Type-safe API response models for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ── Route Models ──

class RouteResponse(BaseModel):
    route_id: int
    origin_code: str
    destination_code: str
    origin_city: str
    destination_city: str
    dgca_monthly_pax: int
    weight: float
    is_active: bool


class RouteListResponse(BaseModel):
    routes: list[RouteResponse]
    total_routes: int
    total_pax: int


# ── Fare Observation Models ──

class FareObservationResponse(BaseModel):
    observation_id: int
    scrape_timestamp: datetime
    route_id: int
    origin_code: Optional[str] = None
    destination_code: Optional[str] = None
    airline_code: str
    airline_name: Optional[str] = None
    flight_number: Optional[str] = None
    departure_date: date
    booking_horizon_days: int
    cabin_class: str
    fare_base: Optional[float] = None
    fare_taxes: Optional[float] = None
    fare_total: float
    is_direct: bool
    source_platform: str
    is_valid: bool
    validation_flags: Optional[list] = None


class FareListResponse(BaseModel):
    fares: list[FareObservationResponse]
    total_count: int
    route_id: Optional[int] = None


# ── Index Models ──

class RouteIndexResponse(BaseModel):
    route_id: int
    origin_code: Optional[str] = None
    destination_code: Optional[str] = None
    index_date: date
    booking_horizon: Optional[int] = None
    jevons_index: float
    observation_count: int
    geometric_mean_price: Optional[float] = None
    base_period: Optional[str] = None


class NationalIndexResponse(BaseModel):
    index_date: date
    booking_horizon: Optional[int] = None
    airfare_cpi: float
    mom_change_pct: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    routes_included: int
    total_observations: int
    base_period: str


class NationalIndexHistoryResponse(BaseModel):
    data: list[NationalIndexResponse]
    count: int


class RouteContributionResponse(BaseModel):
    route_id: int
    origin_code: str
    destination_code: str
    weight: float
    jevons_index: float
    contribution_pct: float


class NationalIndexDetailResponse(NationalIndexResponse):
    route_contributions: list[RouteContributionResponse] = []


# ── Health Models ──

class ScraperHealthResponse(BaseModel):
    source_platform: str
    last_scrape: Optional[datetime] = None
    status: str
    fares_collected: int
    error_type: Optional[str] = None
    response_time_ms: Optional[int] = None


class SystemHealthResponse(BaseModel):
    status: str
    total_observations: int
    total_routes: int
    active_scrapers: int
    last_index_date: Optional[date] = None
    scraper_health: list[ScraperHealthResponse] = []


# ── Anomaly Models ──

class AnomalyResponse(BaseModel):
    id: int
    route_id: int
    origin_code: Optional[str] = None
    destination_code: Optional[str] = None
    anomaly_type: str
    severity: str
    description: Optional[str] = None
    fare_observed: Optional[float] = None
    fare_expected_low: Optional[float] = None
    fare_expected_high: Optional[float] = None
    action_taken: str
    detected_at: datetime


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyResponse]
    total_count: int


# ── Pipeline Trigger Models ──

class ScrapeRequest(BaseModel):
    routes: Optional[list[int]] = None  # None = all routes
    horizons: Optional[list[int]] = None  # None = all horizons
    compute_index: bool = True


class ScrapeResponse(BaseModel):
    status: str
    observations_generated: int
    observations_valid: int
    observations_flagged: int
    observations_excluded: int
    index_computed: bool
    national_cpi: Optional[float] = None
    message: str


# ── Report Models ──

class MonthlyReportResponse(BaseModel):
    report_month: str
    national_cpi: float
    mom_change_pct: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    top_inflating_routes: list[dict] = []
    top_deflating_routes: list[dict] = []
    data_quality: dict = {}
    generated_at: datetime
