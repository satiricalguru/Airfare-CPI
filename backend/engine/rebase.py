"""
SIH26056 — Base period and re-referencing.

One coherent, configurable base period for the whole system, defined by
``INDEX_BASE_PERIOD_START`` and ``INDEX_BASE_PERIOD_DAYS`` and computed from the
observations that actually fall inside that window.

What this replaces
------------------
The previous implementation had three separate defects, all fixed here:

1. Two code paths disagreed on what the base period was. Startup used a 7-day date
   window; the manual trigger used "the first 20 observations regardless of date". The
   same route could therefore carry two different base prices.
2. ``apply_base_year`` rewrote a key (``national_cpi``) that stored records did not
   use (``airfare_cpi``), so changing the base year changed the label and left the
   number untouched.
3. The four base-year factors were invented constants with no derivation.

Approach now
------------
Base prices are per PRODUCT, not per route: matched-model comparison needs a base
price for each product key, and a route-level geometric mean cannot supply that.

Re-referencing is a genuine recomputation. :func:`rebase_series` divides a series by
the mean level of the series over the requested reference window — the standard
re-referencing operation ``I_new(t) = I_old(t) / I_old(ref) * 100``. It therefore
actually moves the numbers, and it only works for reference windows the collected
series covers. A window outside the data returns a refusal with a reason, instead of
an invented link factor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Optional, Sequence

import numpy as np
from loguru import logger

from config import IndexSettings, get_settings
from engine.matched_jevons import ProductPrice, aggregate_product_prices
from scraper.base import FareObservation


@dataclass(frozen=True)
class BasePeriod:
    """The index reference base, from configuration."""

    start: date
    days: int

    @property
    def end(self) -> date:
        return self.start + timedelta(days=self.days - 1)

    @property
    def label(self) -> str:
        return f"{self.start.isoformat()} to {self.end.isoformat()}"

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "days": self.days,
            "label": self.label,
            "index_reference_value": 100.0,
        }

    @classmethod
    def from_settings(cls, settings: Optional[IndexSettings] = None) -> "BasePeriod":
        cfg = settings or get_settings().index
        return cls(start=cfg.base_period_start, days=cfg.base_period_days)


@dataclass
class BasePriceSet:
    """
    Base-period product prices for one route and horizon.

    Keyed by product key so matched-model comparison can pair like with like.
    """

    route_id: int
    booking_horizon: int
    base_period: BasePeriod
    product_prices: dict[str, ProductPrice]
    observation_count: int

    @property
    def product_count(self) -> int:
        return len(self.product_prices)

    @property
    def geometric_mean_price(self) -> Optional[float]:
        if not self.product_prices:
            return None
        arr = np.array([p.price for p in self.product_prices.values()], dtype=float)
        return float(np.exp(np.mean(np.log(arr))))


def compute_base_prices(
    observations: Iterable[FareObservation],
    base_period: Optional[BasePeriod] = None,
) -> dict[tuple[int, int], BasePriceSet]:
    """
    Build base-period product prices from observations, keyed by (route, horizon).

    Only observations whose COLLECTION date falls inside the configured window are
    used, and only those that passed validation. Selection is purely by date, never by
    insertion order, so the base is a property of the data rather than of the order it
    happened to be loaded in.
    """
    period = base_period or BasePeriod.from_settings()

    grouped: dict[tuple[int, int], list[FareObservation]] = {}
    for obs in observations:
        if not obs.is_valid:
            continue
        if not period.contains(obs.collection_date):
            continue
        grouped.setdefault((obs.route_id, obs.booking_horizon_days), []).append(obs)

    base_sets: dict[tuple[int, int], BasePriceSet] = {}
    for key, group in grouped.items():
        route_id, horizon = key
        base_sets[key] = BasePriceSet(
            route_id=route_id,
            booking_horizon=horizon,
            base_period=period,
            product_prices=aggregate_product_prices(group),
            observation_count=len(group),
        )

    logger.info(
        f"Base period {period.label}: built base prices for {len(base_sets)} "
        f"(route, horizon) pair(s) from "
        f"{sum(b.observation_count for b in base_sets.values())} observations"
    )
    return base_sets


# ── re-referencing ──

@dataclass(frozen=True)
class RebaseResult:
    """
    Outcome of re-referencing a series to a different reference window.

    ``is_applied=False`` with a ``reason`` is the honest answer when the requested
    window is not covered by collected data. No factor is fabricated to fill the gap.
    """

    is_applied: bool
    reference_label: str
    reference_start: Optional[date]
    reference_end: Optional[date]
    divisor: Optional[float]
    observations_in_reference: int
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_applied": self.is_applied,
            "reference_label": self.reference_label,
            "reference_start": self.reference_start.isoformat() if self.reference_start else None,
            "reference_end": self.reference_end.isoformat() if self.reference_end else None,
            "divisor": round(self.divisor, 6) if self.divisor is not None else None,
            "index_points_in_reference_window": self.observations_in_reference,
            "reason": self.reason,
            "method": (
                "I_new(t) = I_old(t) / mean(I_old over reference window) * 100"
            ),
        }


def rebase_series(
    series: Sequence[tuple[date, float]],
    reference_start: date,
    reference_end: date,
    reference_label: Optional[str] = None,
) -> tuple[list[tuple[date, float]], RebaseResult]:
    """
    Re-reference a series so the mean over ``[reference_start, reference_end]`` is 100.

    This is a real recomputation from the series itself, which is why the numbers move
    when the window moves. Requires the window to contain at least one index point;
    otherwise the original series is returned unchanged with a stated reason.
    """
    label = reference_label or f"{reference_start.isoformat()} to {reference_end.isoformat()}"

    in_window = [
        value for day, value in series if reference_start <= day <= reference_end and value > 0
    ]

    if not in_window:
        return (
            list(series),
            RebaseResult(
                is_applied=False,
                reference_label=label,
                reference_start=reference_start,
                reference_end=reference_end,
                divisor=None,
                observations_in_reference=0,
                reason=(
                    f"The collected series contains no index points between "
                    f"{reference_start.isoformat()} and {reference_end.isoformat()}, so a "
                    f"re-referencing divisor cannot be computed from data. The series is "
                    f"returned on its original base; no link factor has been invented."
                ),
            ),
        )

    # Geometric mean, consistent with the multiplicative nature of an index level.
    divisor = float(np.exp(np.mean(np.log(np.array(in_window, dtype=float)))))
    if divisor <= 0:
        return (
            list(series),
            RebaseResult(
                is_applied=False,
                reference_label=label,
                reference_start=reference_start,
                reference_end=reference_end,
                divisor=None,
                observations_in_reference=len(in_window),
                reason="reference-window mean is not positive; re-referencing skipped",
            ),
        )

    rebased = [(day, value / divisor * 100.0) for day, value in series]

    logger.info(
        f"Re-referenced series to {label}: divisor={divisor:.4f} from "
        f"{len(in_window)} index point(s)"
    )

    return (
        rebased,
        RebaseResult(
            is_applied=True,
            reference_label=label,
            reference_start=reference_start,
            reference_end=reference_end,
            divisor=divisor,
            observations_in_reference=len(in_window),
        ),
    )


def available_reference_windows(
    series_dates: Sequence[date],
) -> list[dict[str, Any]]:
    """
    Calendar years the collected series can actually be re-referenced to.

    Only years the data covers are offered. The previous UI exposed 2023–2026 with
    invented link factors for years the series does not reach; a selector that only
    offers achievable windows cannot mislead.
    """
    if not series_dates:
        return []

    years = sorted({d.year for d in series_dates})
    windows: list[dict[str, Any]] = []

    for year in years:
        in_year = [d for d in series_dates if d.year == year]
        windows.append({
            "reference": str(year),
            "label": f"{year} = 100",
            "start": date(year, 1, 1).isoformat(),
            "end": date(year, 12, 31).isoformat(),
            "index_points_available": len(in_year),
            "coverage_start": min(in_year).isoformat(),
            "coverage_end": max(in_year).isoformat(),
            "is_complete_year": len({d.month for d in in_year}) == 12,
        })

    return windows
