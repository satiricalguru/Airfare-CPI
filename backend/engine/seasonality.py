"""
SIH26056 — Seasonal adjustment: NOT IMPLEMENTED.

This module exists to state that clearly and to hold the structure a real
implementation would slot into. It does not adjust anything, and it does not pretend
to.

Why it is not implemented
-------------------------
Seasonal adjustment requires estimating a seasonal factor for each period of the
seasonal cycle. For monthly data that means several years of history: X-13ARIMA-SEATS
and STL both need multiple complete cycles before their seasonal estimates mean
anything, and standard practice is at least three years, preferably five.

This project's index series is days old. Fitting a seasonal model to it would produce
factors driven entirely by whatever happened to be in the window — and, because the
simulator injects known festival multipliers, fitting to simulated data would recover
the generator's own configuration and present it as a discovered seasonal pattern.

Airfares are among the most strongly seasonal items in a consumer basket, so this is
a genuine and material limitation, not a technicality. It is reported everywhere the
index is published:

* :data:`SEASONAL_ADJUSTMENT_STATUS` is surfaced by the methodology endpoint.
* Index responses carry ``seasonal_adjustment: "NOT IMPLEMENTED"``.
* The bulletin states that festival and holiday effects pass into the headline figure.

What the index therefore is
---------------------------
An OBSERVED (not seasonally adjusted, "NSA") index. A Diwali or holiday surge appears
in it as a price increase, because that is what was observed. It must not be read as
underlying inflation.

Shape of a future implementation
--------------------------------
:func:`assess_readiness` computes whether a series is long enough to support
adjustment, so the decision is data-driven rather than a claim. When a series does
qualify, :func:`adjust` is the intended entry point and must:

1. Publish observed and adjusted series SEPARATELY, never overwrite the observed one.
2. Record the method, its parameters, and the estimation window on every adjusted
   value.
3. Version the adjustment so revisions are traceable through ``index_revisions``.
4. Keep the adjusted series clearly labelled as derived and subject to revision as
   more history accrues.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Optional, Sequence

from provenance import NOT_IMPLEMENTED_LABEL


# Surfaced verbatim by the API. Deliberately blunt.
SEASONAL_ADJUSTMENT_STATUS = NOT_IMPLEMENTED_LABEL

SEASONAL_ADJUSTMENT_NOTE = (
    "Seasonal adjustment is NOT IMPLEMENTED. The published index is an OBSERVED "
    "(not seasonally adjusted) series. Festival, holiday and school-vacation effects "
    "pass directly into the headline figure and must not be interpreted as underlying "
    "inflation. Adjustment requires several complete seasonal cycles of collected "
    "history, which this series does not yet have."
)

# Minimum history before any seasonal method is defensible. Three complete annual
# cycles is the conventional floor; five is preferred for a stable estimate.
MIN_MONTHS_FOR_ADJUSTMENT = 36
PREFERRED_MONTHS_FOR_ADJUSTMENT = 60


class SeasonalMethod(str, Enum):
    """Methods a future implementation could use. None is currently available."""

    NONE = "none"
    X13_ARIMA_SEATS = "x13_arima_seats"
    STL = "stl"
    SEATS = "seats"

    @property
    def is_available(self) -> bool:
        """No method is implemented, so this is False for every member."""
        return False


@dataclass(frozen=True)
class SeasonalityReadiness:
    """Whether a series could support seasonal adjustment."""

    is_ready: bool
    months_available: int
    months_required: int
    months_preferred: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "months_available": self.months_available,
            "months_required": self.months_required,
            "months_preferred": self.months_preferred,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SeasonalAdjustmentResult:
    """
    Container for an adjusted series.

    Always returned with ``status=NOT IMPLEMENTED`` and ``adjusted_values=None``. The
    observed series is passed through untouched so a caller cannot accidentally
    display an "adjusted" figure that is really the observed one relabelled.
    """

    status: str
    method: SeasonalMethod
    note: str
    observed_values: tuple[float, ...]
    adjusted_values: Optional[tuple[float, ...]] = None
    readiness: Optional[SeasonalityReadiness] = None

    @property
    def is_adjusted(self) -> bool:
        return self.adjusted_values is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "seasonal_adjustment": self.status,
            "method": self.method.value,
            "note": self.note,
            "is_adjusted": self.is_adjusted,
            "observed_series_length": len(self.observed_values),
            "adjusted_series": None,
            "readiness": self.readiness.to_dict() if self.readiness else None,
        }


def assess_readiness(index_dates: Sequence[date]) -> SeasonalityReadiness:
    """
    Report whether a series is long enough for seasonal adjustment.

    Counts distinct calendar months present, which is the unit a monthly seasonal
    model works in. A daily series spanning three weeks contains one month, not
    twenty-one observations' worth of seasonal information.
    """
    months = {(d.year, d.month) for d in index_dates}
    available = len(months)
    ready = available >= MIN_MONTHS_FOR_ADJUSTMENT

    if ready:
        reason = (
            f"{available} distinct months of history available, meeting the "
            f"{MIN_MONTHS_FOR_ADJUSTMENT}-month minimum. Adjustment is still NOT "
            f"IMPLEMENTED in this codebase; readiness alone does not produce an "
            f"adjusted series."
        )
    else:
        reason = (
            f"only {available} distinct month(s) of history available; at least "
            f"{MIN_MONTHS_FOR_ADJUSTMENT} ({PREFERRED_MONTHS_FOR_ADJUSTMENT} preferred) "
            f"are needed before a seasonal factor can be estimated. Any adjustment "
            f"fitted to this series would describe the window, not a seasonal pattern."
        )

    return SeasonalityReadiness(
        is_ready=ready,
        months_available=available,
        months_required=MIN_MONTHS_FOR_ADJUSTMENT,
        months_preferred=PREFERRED_MONTHS_FOR_ADJUSTMENT,
        reason=reason,
    )


def adjust(
    index_dates: Sequence[date],
    index_values: Sequence[float],
    method: SeasonalMethod = SeasonalMethod.NONE,
) -> SeasonalAdjustmentResult:
    """
    Intended entry point for seasonal adjustment. Currently adjusts nothing.

    Returns the observed series with ``adjusted_values=None`` and a NOT IMPLEMENTED
    status. It does not raise, so callers can request adjustment metadata uniformly
    and render the honest answer.
    """
    return SeasonalAdjustmentResult(
        status=SEASONAL_ADJUSTMENT_STATUS,
        method=SeasonalMethod.NONE,
        note=(
            SEASONAL_ADJUSTMENT_NOTE
            + (
                f" (Requested method {method.value!r} is not available.)"
                if method is not SeasonalMethod.NONE
                else ""
            )
        ),
        observed_values=tuple(float(v) for v in index_values),
        adjusted_values=None,
        readiness=assess_readiness(index_dates),
    )


def methodology_metadata(index_dates: Optional[Sequence[date]] = None) -> dict[str, Any]:
    """Seasonality block for the methodology endpoint."""
    readiness = assess_readiness(index_dates or [])
    return {
        "status": SEASONAL_ADJUSTMENT_STATUS,
        "note": SEASONAL_ADJUSTMENT_NOTE,
        "published_series_type": "observed (not seasonally adjusted)",
        "available_methods": [],
        "candidate_methods": [m.value for m in SeasonalMethod if m is not SeasonalMethod.NONE],
        "readiness": readiness.to_dict(),
        "requirements_for_implementation": [
            "Publish observed and seasonally adjusted series separately; never "
            "overwrite the observed series.",
            "Record method, parameters and estimation window on every adjusted value.",
            "Version the adjustment and record revisions in index_revisions.",
            "Label the adjusted series as derived and subject to revision.",
        ],
    }
