"""
SIH26056 — Central configuration.

Single source of truth for every environment variable the backend reads. Nothing
else calls ``os.getenv`` for a tunable, so ``.env.example`` and the code cannot
drift apart: if a variable is not listed here it has no effect anywhere.

Access via :func:`get_settings` (cached) or :func:`reload_settings` in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

from provenance import CollectionMode

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data"
FIXTURE_DIR = BACKEND_DIR / "fixtures"
# Keep the historical, unversioned `airfare_cpi.db` read-only.  Fresh local runs
# use an explicitly versioned store created by Alembic, just like deployments.
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{BACKEND_DIR / 'airfare_cpi_managed.db'}"
SUPPORTED_BOOKING_HORIZONS = (1, 7, 15, 30, 45)

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


# ── env parsing helpers ──

def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning(f"{name}={raw!r} is not an integer; using default {default}")
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        logger.warning(f"{name}={raw!r} is not a number; using default {default}")
        return default


def _env_str_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _env_int_list(name: str, default: str) -> list[int]:
    out: list[int] = []
    for part in _env_str_list(name, default):
        try:
            out.append(int(part))
        except ValueError:
            logger.warning(f"{name}: ignoring non-integer entry {part!r}")
    return out


def _env_date(name: str, default: str) -> date:
    raw = _env_str(name, default) or default
    try:
        return date.fromisoformat(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r} is not an ISO date; using default {default}")
        return date.fromisoformat(default)


# ── settings groups ──

@dataclass(frozen=True)
class AmadeusSettings:
    """
    Credentials and endpoints for the Amadeus Self-Service API — the one genuine
    live fare source implemented in this project.

    Credentials are read from the server environment only. There is deliberately
    no default and no committed fallback: without a key the adapter reports
    SOURCE UNAVAILABLE rather than producing anything.
    """

    client_id: str = ""
    client_secret: str = ""
    # 'test' → test.api.amadeus.com (free monthly quota, subset of real data)
    # 'production' → api.amadeus.com
    environment: str = "test"
    timeout_seconds: float = 20.0
    # Amadeus documents a test-environment ceiling of one request per 100 ms.
    # A conservative default leaves headroom.
    min_request_interval_seconds: float = 0.25
    max_offers_per_search: int = 40
    # For paid-capable APIs, default ALLOW_PAID_OVERAGE=false; startup must reject a
    # configuration that can bill without an explicit second control.
    allow_paid_overage: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def host(self) -> str:
        return (
            "https://api.amadeus.com"
            if self.environment == "production"
            else "https://test.api.amadeus.com"
        )

    @property
    def token_url(self) -> str:
        return f"{self.host}/v1/security/oauth2/token"

    @property
    def flight_offers_url(self) -> str:
        return f"{self.host}/v2/shopping/flight-offers"


@dataclass(frozen=True)
class ScraperSettings:
    """Collection behaviour, including politeness and retry limits."""

    # Which sources may be attempted, in priority order. A name listed here that is
    # not registered, or is registered as disabled, is skipped with a logged reason.
    enabled_sources: list[str] = field(default_factory=lambda: ["amadeus"])
    booking_horizons: list[int] = field(default_factory=lambda: [1, 7, 15, 30, 45])
    passengers: int = 1
    cabin: str = "ECONOMY"

    # Politeness / robustness. Retries are bounded; there is no infinite retry loop.
    max_retries: int = 2
    retry_backoff_base_seconds: float = 2.0
    retry_backoff_max_seconds: float = 30.0
    request_timeout_seconds: float = 20.0
    per_host_min_interval_seconds: float = 1.0
    max_concurrent_requests: int = 4

    # robots.txt is honoured for any source fetched over plain HTTP(S) from a web
    # host. Disabling this is not offered as a switch.
    respect_robots_txt: bool = True
    user_agent: str = (
        "AirfareCPI-Research/2.0 (SIH26056 academic price-index prototype; "
        "contact: repository maintainer)"
    )


@dataclass(frozen=True)
class SchedulerSettings:
    """Automated collection windows."""

    enabled: bool = False
    # Local-clock hours at which a collection run starts, e.g. [10, 18].
    collection_hours: list[int] = field(default_factory=lambda: [10, 18])
    timezone_name: str = "Asia/Kolkata"
    # Guard so a long-running cycle cannot overlap the next window.
    max_cycle_seconds: int = 3600
    # How often the scheduler wakes to check whether a window has opened.
    tick_seconds: int = 60


@dataclass(frozen=True)
class IndexSettings:
    """Index computation parameters."""

    base_period_start: date = date(2026, 9, 3)
    base_period_days: int = 7
    min_matched_products: int = 3
    # Safety bounds on a single price relative, applied before aggregation.
    min_price_relative: float = 0.1
    max_price_relative: float = 10.0
    winsorize_lower_pct: float = 1.0
    winsorize_upper_pct: float = 99.0

    @property
    def base_period_end(self) -> date:
        return self.base_period_start + timedelta(days=self.base_period_days - 1)

    @property
    def base_period_label(self) -> str:
        return f"{self.base_period_start.isoformat()} to {self.base_period_end.isoformat()}"


@dataclass(frozen=True)
class ValidationSettings:
    """Data-quality thresholds. Every one of these is enforced in code."""

    min_fare_inr: float = 500.0
    max_fare_inr: float = 80000.0
    max_daily_change_pct: float = 300.0
    iqr_multiplier: float = 3.0
    min_observations_for_iqr: int = 10
    # Reference-distribution window per route, in observations.
    route_history_window: int = 500


@dataclass(frozen=True)
class DatabaseSettings:
    """
    Persistence. PostgreSQL is the target store and is what docker-compose wires
    up; SQLite is supported so the project runs without a database server.

    There is no in-memory mode: published figures must survive a restart.
    """

    url: str = DEFAULT_DB_URL
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    # Metadata-driven schema creation is allowed only for isolated tests/local
    # throwaway work. Shared deployments must run Alembic before the API starts.
    auto_create_schema: bool = False

    @property
    def is_postgres(self) -> bool:
        return self.url.startswith("postgresql")


@dataclass(frozen=True)
class ApiSettings:
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"]
    )
    admin_token: str = ""
    # Server-side key for the Copilot LLM proxy. Never exposed to the client.
    copilot_api_key: str = ""
    # An explicit provider model is required; there is intentionally no invented
    # default model name which could make the UI claim a model was used when it was
    # not available from the provider.
    copilot_model: str = ""
    copilot_enabled: bool = False
    # Per-process caps for operations with external cost or collection side effects.
    # Production deployments with multiple workers also need equivalent gateway caps.
    copilot_rate_limit: int = 20
    copilot_rate_window_seconds: int = 600
    mutation_rate_limit: int = 6
    mutation_rate_window_seconds: int = 60


@dataclass(frozen=True)
class Settings:
    """Root settings object."""

    mode: CollectionMode
    amadeus: AmadeusSettings
    scraper: ScraperSettings
    scheduler: SchedulerSettings
    index: IndexSettings
    validation: ValidationSettings
    database: DatabaseSettings
    api: ApiSettings

    route_basket_path: Path
    horizon_policy_path: Path
    fixture_path: Path
    simulator_seed: int

    @property
    def is_live(self) -> bool:
        return self.mode is CollectionMode.LIVE

    def describe(self) -> dict:
        """Non-secret summary, safe to log and to expose on a status endpoint."""
        return {
            "mode": self.mode.value,
            "source_type": self.mode.source_type.value,
            "provenance_label": self.mode.source_type.display_label,
            "enabled_sources": list(self.scraper.enabled_sources),
            "booking_horizons": list(self.scraper.booking_horizons),
            "base_period": self.index.base_period_label,
            "database_backend": "postgresql" if self.database.is_postgres else "sqlite",
            "scheduler_enabled": self.scheduler.enabled,
            "amadeus_configured": self.amadeus.is_configured,
            "copilot_proxy_enabled": self.api.copilot_enabled,
            "respect_robots_txt": self.scraper.respect_robots_txt,
        }


def build_settings() -> Settings:
    """Read the environment once and construct an immutable Settings object."""
    # Production-facing default is honest failure: without live credentials the
    # collector reports SOURCE UNAVAILABLE. Simulation must always be opted into.
    mode = CollectionMode.parse(_env_str("COLLECTION_MODE"), CollectionMode.LIVE)

    allow_paid_overage = _env_bool("ALLOW_PAID_OVERAGE", False)
    allow_paid_overage_confirmed = _env_bool("ALLOW_PAID_OVERAGE_CONFIRMED", False)
    if allow_paid_overage and not allow_paid_overage_confirmed:
        raise RuntimeError(
            "ALLOW_PAID_OVERAGE is enabled without explicit second control. "
            "Set ALLOW_PAID_OVERAGE_CONFIRMED=true to acknowledge billing risk."
        )

    amadeus = AmadeusSettings(
        client_id=_env_str("AMADEUS_CLIENT_ID"),
        client_secret=_env_str("AMADEUS_CLIENT_SECRET"),
        environment=_env_str("AMADEUS_ENVIRONMENT", "test").lower(),
        timeout_seconds=_env_float("AMADEUS_TIMEOUT_SECONDS", 20.0),
        min_request_interval_seconds=_env_float("AMADEUS_MIN_REQUEST_INTERVAL", 0.25),
        max_offers_per_search=_env_int("AMADEUS_MAX_OFFERS", 40),
        allow_paid_overage=allow_paid_overage,
    )

    scraper = ScraperSettings(
        enabled_sources=_env_str_list("ENABLED_SOURCES", "amadeus"),
        booking_horizons=_env_int_list("BOOKING_HORIZONS", "1,7,15,30,45"),
        passengers=_env_int("COLLECTION_PASSENGERS", 1),
        cabin=_env_str("COLLECTION_CABIN", "ECONOMY").upper(),
        max_retries=_env_int("SCRAPER_MAX_RETRIES", 2),
        retry_backoff_base_seconds=_env_float("SCRAPER_RETRY_BACKOFF_BASE", 2.0),
        retry_backoff_max_seconds=_env_float("SCRAPER_RETRY_BACKOFF_MAX", 30.0),
        request_timeout_seconds=_env_float("SCRAPER_TIMEOUT_SECONDS", 20.0),
        per_host_min_interval_seconds=_env_float("SCRAPER_MIN_REQUEST_INTERVAL", 1.0),
        max_concurrent_requests=_env_int("SCRAPER_MAX_CONCURRENCY", 4),
        user_agent=_env_str(
            "SCRAPER_USER_AGENT",
            "AirfareCPI-Research/2.0 (SIH26056 academic price-index prototype; "
            "contact: repository maintainer)",
        ),
    )
    invalid_horizons = sorted(
        set(scraper.booking_horizons) - set(SUPPORTED_BOOKING_HORIZONS)
    )
    if invalid_horizons:
        raise ValueError(
            "BOOKING_HORIZONS contains values outside the SIH26056 policy "
            f"{list(SUPPORTED_BOOKING_HORIZONS)}: {invalid_horizons}"
        )
    if not scraper.booking_horizons:
        raise ValueError("BOOKING_HORIZONS must contain at least one policy horizon")

    scheduler = SchedulerSettings(
        enabled=_env_bool("SCHEDULER_ENABLED", False),
        collection_hours=_env_int_list("SCHEDULER_COLLECTION_HOURS", "10,18"),
        timezone_name=_env_str("SCHEDULER_TIMEZONE", "Asia/Kolkata"),
        max_cycle_seconds=_env_int("SCHEDULER_MAX_CYCLE_SECONDS", 3600),
        tick_seconds=_env_int("SCHEDULER_TICK_SECONDS", 60),
    )

    index = IndexSettings(
        base_period_start=_env_date("INDEX_BASE_PERIOD_START", "2026-09-03"),
        base_period_days=max(1, _env_int("INDEX_BASE_PERIOD_DAYS", 7)),
        min_matched_products=_env_int("INDEX_MIN_MATCHED_PRODUCTS", 3),
    )

    validation = ValidationSettings(
        min_fare_inr=_env_float("VALIDATION_MIN_FARE", 500.0),
        max_fare_inr=_env_float("VALIDATION_MAX_FARE", 80000.0),
        max_daily_change_pct=_env_float("VALIDATION_MAX_DAILY_CHANGE_PCT", 300.0),
        iqr_multiplier=_env_float("VALIDATION_IQR_MULTIPLIER", 3.0),
    )

    database = DatabaseSettings(
        url=_env_str("DATABASE_URL", DEFAULT_DB_URL),
        pool_size=_env_int("DB_POOL_SIZE", 10),
        max_overflow=_env_int("DB_MAX_OVERFLOW", 20),
        echo=_env_bool("DB_ECHO", False),
        auto_create_schema=_env_bool("DB_AUTO_CREATE_SCHEMA", False),
    )

    copilot_key = _env_str("COPILOT_API_KEY")
    api = ApiSettings(
        cors_origins=_env_str_list(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
        ),
        admin_token=_env_str("ADMIN_API_TOKEN"),
        copilot_api_key=copilot_key,
        copilot_model=_env_str("COPILOT_MODEL"),
        copilot_enabled=bool(copilot_key and _env_str("COPILOT_MODEL")),
        copilot_rate_limit=_env_int("API_COPILOT_RATE_LIMIT", 20),
        copilot_rate_window_seconds=_env_int(
            "API_COPILOT_RATE_WINDOW_SECONDS", 600
        ),
        mutation_rate_limit=_env_int("API_MUTATION_RATE_LIMIT", 6),
        mutation_rate_window_seconds=_env_int(
            "API_MUTATION_RATE_WINDOW_SECONDS", 60
        ),
    )

    settings = Settings(
        mode=mode,
        amadeus=amadeus,
        scraper=scraper,
        scheduler=scheduler,
        index=index,
        validation=validation,
        database=database,
        api=api,
        route_basket_path=Path(
            _env_str("ROUTE_BASKET_PATH", str(DATA_DIR / "route_basket.json"))
        ),
        horizon_policy_path=Path(
            _env_str("HORIZON_POLICY_PATH", str(DATA_DIR / "booking_horizons.json"))
        ),
        fixture_path=Path(
            _env_str("OFFLINE_FIXTURE_PATH", str(FIXTURE_DIR / "offline_fares.json"))
        ),
        simulator_seed=_env_int("SIMULATOR_SEED", 42),
    )

    _warn_on_risky_configuration(settings)
    return settings


def _warn_on_risky_configuration(settings: Settings) -> None:
    """Surface configuration that would be unsafe or misleading in a deployment."""
    if settings.is_live and not settings.amadeus.is_configured:
        logger.warning(
            "COLLECTION_MODE=LIVE but no Amadeus credentials are configured. Live "
            "collection will report SOURCE UNAVAILABLE and produce zero observations. "
            "It will NOT fall back to simulated data."
        )
    if "*" in settings.api.cors_origins:
        logger.warning(
            "CORS_ORIGINS contains '*'. Credentials are disabled so this is not "
            "exploitable for session theft, but an explicit origin list is preferred."
        )
    if not settings.api.admin_token:
        logger.warning(
            "ADMIN_API_TOKEN is unset: state-mutating endpoints are disabled until "
            "a token is configured."
        )
    if not settings.api.copilot_enabled and settings.api.copilot_api_key:
        logger.warning(
            "COPILOT_API_KEY is set but COPILOT_MODEL is empty. The Copilot will use "
            "its labelled local fallback until an explicit provider model is set."
        )
    if settings.amadeus.allow_paid_overage:
        logger.warning(
            "ALLOW_PAID_OVERAGE is active: requests exceeding free quotas may bill the account."
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return build_settings()


def reload_settings() -> Settings:
    """Re-read the environment. Used by tests that monkeypatch env vars."""
    get_settings.cache_clear()
    return get_settings()
