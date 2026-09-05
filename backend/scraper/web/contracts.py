"""
SIH26056 — Web Acquisition Contracts.

Defines the core data contracts between collectors, parsers, and pipeline:
- WebSearchQuery: structured flight search criteria
- PageState: observed page state classification
- PriceQuote: single extracted flight offer with components
- ParseResult: bundle of extracted offers, classification, and artifact reference
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional


class PageState(str, Enum):
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    CAPTCHA_CHALLENGE = "CAPTCHA_CHALLENGE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    BLOCKED = "BLOCKED"
    SELECTOR_DRIFT = "SELECTOR_DRIFT"
    ERROR = "ERROR"


@dataclass(frozen=True)
class WebSearchQuery:
    origin_code: str
    destination_code: str
    departure_date: date
    booking_horizon_days: int
    passengers: int = 1
    cabin: str = "ECONOMY"
    currency: str = "INR"

    @property
    def route_code(self) -> str:
        return f"{self.origin_code}-{self.destination_code}"


@dataclass(frozen=True)
class PriceQuote:
    """Individual flight quotation extracted from a portal result page."""
    airline_code: str
    airline_name: str
    flight_number: str
    headline_fare: float
    base_fare: Optional[float] = None
    taxes_and_fees: Optional[float] = None
    currency: str = "INR"
    cabin_class: str = "ECONOMY"
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    stops: int = 0
    is_refundable: Optional[bool] = None
    baggage_kg: Optional[int] = None
    raw_details: dict[str, Any] = field(default_factory=dict)

    def reconcile_price_components(self, tolerance: float = 2.0) -> bool:
        """
        Verify that base + taxes reconcile with headline fare within tolerance.
        Returns True if components are absent (cannot check) or match headline.
        """
        if self.base_fare is not None and self.taxes_and_fees is not None:
            sum_comp = self.base_fare + self.taxes_and_fees
            return abs(sum_comp - self.headline_fare) <= tolerance
        return True


@dataclass
class ParseResult:
    """Comprehensive parse outcome from an acquired web artifact."""
    state: PageState
    quotes: list[PriceQuote] = field(default_factory=list)
    artifact_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)
