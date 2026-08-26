"""
SIH26056 — Fare Observation Validator

Validates incoming fare observations before they enter the index pipeline.
Classification: scraping error → exclude | genuine anomaly → flag + preserve.
"""

import numpy as np
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from loguru import logger


@dataclass
class ValidationResult:
    """Result of validating a fare observation."""
    is_valid: bool
    flags: list[str] = field(default_factory=list)
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    action: str = "accepted"  # accepted / flagged / excluded


class FareValidator:
    """
    Validates fare observations for data quality.
    
    Rules:
    1. EXCLUDE: Clearly bad data (zero fares, impossible values, scrape errors)
    2. FLAG: Unusual but potentially genuine (spikes, deep discounts)
    3. ACCEPT: Normal observations that pass all checks
    
    Philosophy: Never automatically remove genuine market volatility.
    Airfares ARE volatile — the index should reflect this.
    """
    
    def __init__(
        self,
        min_fare: float = 500.0,        # ₹500 minimum for domestic economy
        max_fare: float = 80000.0,       # ₹80,000 cap for domestic economy
        max_daily_change_pct: float = 300.0,  # Flag if >300% change from prior day
        iqr_multiplier: float = 3.0,     # IQR fence multiplier
    ):
        self.min_fare = min_fare
        self.max_fare = max_fare
        self.max_daily_change_pct = max_daily_change_pct
        self.iqr_multiplier = iqr_multiplier
        
        # Rolling statistics per route (populated as data flows through)
        self._route_stats: dict[int, dict] = {}
    
    def validate(
        self,
        fare_total: float,
        fare_base: Optional[float],
        fare_taxes: Optional[float],
        route_id: int,
        airline_code: str,
        booking_horizon: int,
        departure_date: date,
        cabin_class: str = "Economy",
    ) -> ValidationResult:
        """
        Validate a single fare observation.
        
        Returns ValidationResult with is_valid, flags, and action.
        """
        flags = []
        
        # ── HARD EXCLUSIONS (data errors) ──
        
        # Zero or negative fare
        if fare_total <= 0:
            return ValidationResult(
                is_valid=False,
                flags=["zero_or_negative_fare"],
                anomaly_type="scrape_error",
                severity="critical",
                action="excluded",
            )
        
        # Below absolute minimum
        if fare_total < self.min_fare:
            return ValidationResult(
                is_valid=False,
                flags=[f"below_minimum_fare_{self.min_fare}"],
                anomaly_type="scrape_error",
                severity="high",
                action="excluded",
            )
        
        # Above absolute maximum
        if fare_total > self.max_fare:
            return ValidationResult(
                is_valid=False,
                flags=[f"above_maximum_fare_{self.max_fare}"],
                anomaly_type="scrape_error",
                severity="high",
                action="excluded",
            )
        
        # Tax/base consistency check
        if fare_base is not None and fare_taxes is not None:
            expected_total = fare_base + fare_taxes
            if abs(fare_total - expected_total) > 1.0:  # Allow ₹1 rounding
                flags.append("fare_total_mismatch")
        
        # Taxes > 50% of total (suspicious)
        if fare_taxes is not None and fare_total > 0:
            tax_pct = fare_taxes / fare_total
            if tax_pct > 0.50:
                flags.append("high_tax_ratio")
            if tax_pct < 0.05:
                flags.append("suspiciously_low_tax")
        
        # ── SOFT FLAGS (genuine but unusual) ──
        
        # Statistical outlier check against route history
        route_stat = self._route_stats.get(route_id)
        if route_stat and route_stat.get("count", 0) >= 10:
            median = route_stat["median"]
            q1 = route_stat["q1"]
            q3 = route_stat["q3"]
            iqr = q3 - q1
            
            lower_fence = q1 - self.iqr_multiplier * iqr
            upper_fence = q3 + self.iqr_multiplier * iqr
            
            if fare_total < lower_fence:
                flags.append(f"statistical_low_outlier_iqr{self.iqr_multiplier}")
            elif fare_total > upper_fence:
                flags.append(f"statistical_high_outlier_iqr{self.iqr_multiplier}")
        
        # Booking horizon sanity
        if booking_horizon == 30 and fare_total > 25000:
            flags.append("high_fare_for_30day_advance")
        if booking_horizon == 0 and fare_total < 1500:
            flags.append("suspiciously_low_sameday_fare")
        
        # ── UPDATE ROUTE STATS ──
        self._update_route_stats(route_id, fare_total)
        
        # ── DETERMINE RESULT ──
        if flags:
            severity = "low" if len(flags) == 1 else "medium"
            return ValidationResult(
                is_valid=True,  # Flagged but not excluded
                flags=flags,
                anomaly_type="potential_anomaly",
                severity=severity,
                action="flagged",
            )
        
        return ValidationResult(
            is_valid=True,
            flags=[],
            action="accepted",
        )
    
    def validate_batch(
        self,
        observations: list[dict],
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """
        Validate a batch of observations.
        
        Returns:
            (accepted, flagged, excluded) — three lists
        """
        accepted = []
        flagged = []
        excluded = []
        
        for obs in observations:
            result = self.validate(
                fare_total=obs.get("fare_total", 0),
                fare_base=obs.get("fare_base"),
                fare_taxes=obs.get("fare_taxes"),
                route_id=obs.get("route_id", 0),
                airline_code=obs.get("airline_code", ""),
                booking_horizon=obs.get("booking_horizon_days", 0),
                departure_date=date.fromisoformat(obs.get("departure_date", "2026-01-01")),
                cabin_class=obs.get("cabin_class", "Economy"),
            )
            
            obs["is_valid"] = result.is_valid
            obs["validation_flags"] = result.flags
            
            if result.action == "excluded":
                excluded.append(obs)
            elif result.action == "flagged":
                flagged.append(obs)
            else:
                accepted.append(obs)
        
        logger.info(
            f"Validation: {len(accepted)} accepted, "
            f"{len(flagged)} flagged, {len(excluded)} excluded "
            f"(of {len(observations)} total)"
        )
        
        return accepted, flagged, excluded
    
    def _update_route_stats(self, route_id: int, fare: float):
        """Update rolling statistics for a route."""
        if route_id not in self._route_stats:
            self._route_stats[route_id] = {
                "prices": [],
                "count": 0,
                "median": 0,
                "q1": 0,
                "q3": 0,
            }
        
        stats = self._route_stats[route_id]
        stats["prices"].append(fare)
        
        # Keep only last 500 observations per route
        if len(stats["prices"]) > 500:
            stats["prices"] = stats["prices"][-500:]
        
        prices = np.array(stats["prices"])
        stats["count"] = len(prices)
        stats["median"] = float(np.median(prices))
        stats["q1"] = float(np.percentile(prices, 25))
        stats["q3"] = float(np.percentile(prices, 75))
