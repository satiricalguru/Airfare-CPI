"""
SIH26056 — Uncertainty estimation.

A published index figure without a stated precision invites over-interpretation of
small movements. This module estimates sampling uncertainty where it is defensible
and returns ``None`` with a stated reason where it is not.

It never invents an interval. That is the whole point: a confidence interval is a
claim about the sampling distribution, and asserting one without a basis is worse
than reporting nothing, because it looks like rigour.

What IS estimated
-----------------
Sampling variability of the elementary (route x horizon) Jevons index, from the
observed dispersion of its log price relatives. The Jevons index is
``exp(mean(ln r_p))``, so ``mean(ln r_p)`` is a sample mean and its standard error is
``s / sqrt(n)`` where ``s`` is the sample standard deviation of the log relatives.
The interval is formed in log space and exponentiated back, which keeps it strictly
positive and asymmetric in level terms — correct for a geometric mean.

What is NOT estimated, and why
------------------------------
* **Route selection uncertainty.** The 25-route basket is a purposive selection, not
  a probability sample of city pairs. There is no sampling frame and no inclusion
  probabilities, so no design-based variance can be computed for the national
  aggregate's coverage of the market.
* **Weight uncertainty.** Passenger-volume weights are treated as fixed known
  constants. Their own error is not published and cannot be estimated here.
* **Non-sampling error.** Collection gaps, product-matching failures and source
  coverage bias are reported as counts and diagnostics, not folded into a variance.

Consequently the national index reports an aggregated sampling standard error over
its route components and explicitly states that this excludes basket-selection and
weight uncertainty. It is a lower bound on total uncertainty, and says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np


# Two-sided normal critical value at 95%. The t distribution is used instead when the
# sample is small, since a normal interval would be too narrow there.
_Z_95 = 1.959964


@dataclass(frozen=True)
class UncertaintyEstimate:
    """
    Sampling uncertainty for one index value, or a stated reason for its absence.

    All fields are ``None`` when ``is_estimable`` is False. ``basis`` always explains
    what was or was not done.
    """

    is_estimable: bool
    basis: str
    sample_size: Optional[int] = None
    standard_error: Optional[float] = None
    confidence_level: Optional[float] = None
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    # Coefficient of variation of the log relatives: a scale-free dispersion measure.
    relative_standard_error_pct: Optional[float] = None
    excludes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_estimable": self.is_estimable,
            "basis": self.basis,
            "sample_size": self.sample_size,
            "standard_error": (
                round(self.standard_error, 6) if self.standard_error is not None else None
            ),
            "confidence_level": self.confidence_level,
            "confidence_interval_low": (
                round(self.confidence_interval_low, 4)
                if self.confidence_interval_low is not None
                else None
            ),
            "confidence_interval_high": (
                round(self.confidence_interval_high, 4)
                if self.confidence_interval_high is not None
                else None
            ),
            "relative_standard_error_pct": (
                round(self.relative_standard_error_pct, 3)
                if self.relative_standard_error_pct is not None
                else None
            ),
            "excludes": list(self.excludes),
        }

    @classmethod
    def not_estimable(cls, reason: str, sample_size: Optional[int] = None) -> "UncertaintyEstimate":
        return cls(is_estimable=False, basis=reason, sample_size=sample_size)


# Standard caveat list attached to every estimate produced here.
_STANDARD_EXCLUSIONS = (
    "route basket selection (purposive, not a probability sample — no design-based "
    "variance is computable)",
    "route weight error (passenger volumes treated as fixed known constants)",
    "non-sampling error (collection gaps, product-matching failure, source coverage)",
)


def _t_critical_95(df: int) -> float:
    """
    Two-sided 95% t critical value.

    A small lookup avoids adding SciPy as a dependency for a handful of constants.
    Values above the table converge on the normal quantile.
    """
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        25: 2.060, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980,
    }
    if df in table:
        return table[df]
    if df < 1:
        return float("nan")
    candidates = [k for k in sorted(table) if k <= df]
    if not candidates:
        return table[1]
    if df > 120:
        return _Z_95
    return table[candidates[-1]]


def estimate_elementary_uncertainty(
    log_relatives: Sequence[float],
    index_value: float,
    confidence_level: float = 0.95,
) -> UncertaintyEstimate:
    """
    Sampling uncertainty of a matched-model Jevons index.

    The index is ``exp(mean(ln r))``, so uncertainty is estimated on ``mean(ln r)``
    and transformed back:

        se_log = s_log / sqrt(n)
        CI     = exp( mean_log +/- t * se_log )

    Requires at least three matched relatives; with fewer, the dispersion estimate is
    not meaningful and ``None`` is returned with that stated.
    """
    values = np.asarray([v for v in log_relatives if math.isfinite(v)], dtype=float)
    n = int(values.size)

    if n < 3:
        return UncertaintyEstimate.not_estimable(
            reason=(
                f"only {n} matched price relative(s); at least 3 are required before a "
                f"dispersion estimate is meaningful. No interval is reported."
            ),
            sample_size=n,
        )

    mean_log = float(np.mean(values))
    # ddof=1: sample standard deviation, since the mean is estimated from the data.
    std_log = float(np.std(values, ddof=1))

    if std_log == 0.0:
        # Every matched product moved by exactly the same factor. Zero sampling
        # dispersion is a real result, not an error, so it is reported as such.
        return UncertaintyEstimate(
            is_estimable=True,
            basis=(
                "All matched price relatives are identical, so the sampling standard "
                "error of the log mean is zero. This reflects zero dispersion within "
                "the matched sample only."
            ),
            sample_size=n,
            standard_error=0.0,
            confidence_level=confidence_level,
            confidence_interval_low=index_value,
            confidence_interval_high=index_value,
            relative_standard_error_pct=0.0,
            excludes=_STANDARD_EXCLUSIONS,
        )

    se_log = std_log / math.sqrt(n)
    critical = _t_critical_95(n - 1) if confidence_level == 0.95 else _Z_95

    low = math.exp(mean_log - critical * se_log)
    high = math.exp(mean_log + critical * se_log)

    # Standard error in index-level terms, via the delta method: d/dx exp(x) = exp(x).
    se_level = index_value * se_log

    return UncertaintyEstimate(
        is_estimable=True,
        basis=(
            f"Sampling standard error of the geometric mean of {n} matched log price "
            f"relatives (se_log = s/sqrt(n)), transformed to index level. Interval uses "
            f"a t critical value with {n - 1} degrees of freedom."
        ),
        sample_size=n,
        standard_error=se_level,
        confidence_level=confidence_level,
        confidence_interval_low=low,
        confidence_interval_high=high,
        relative_standard_error_pct=(se_level / index_value * 100) if index_value else None,
        excludes=_STANDARD_EXCLUSIONS,
    )


def aggregate_uncertainty(
    component_values: Sequence[float],
    component_weights: Sequence[float],
    component_standard_errors: Sequence[Optional[float]],
    aggregate_value: float,
    confidence_level: float = 0.95,
) -> UncertaintyEstimate:
    """
    Sampling uncertainty of a weighted aggregate of independent components.

    For ``A = sum_i w_i * I_i`` with components treated as independent:

        var(A) = sum_i w_i^2 * var(I_i)

    Independence across routes is an assumption, and a strong one: fuel prices and
    macro demand move many routes together, so positive covariance is likely and the
    true variance is probably larger than this. Stated in ``basis`` rather than
    quietly assumed, and it means the reported interval should be read as a lower
    bound on sampling uncertainty.

    Returns not-estimable when any component lacks a standard error, because dropping
    those components would understate the aggregate's uncertainty.
    """
    if not component_values:
        return UncertaintyEstimate.not_estimable(
            "no components were aggregated", sample_size=0
        )

    if len(component_values) != len(component_weights) or len(component_values) != len(
        component_standard_errors
    ):
        raise ValueError("component values, weights and standard errors must align")

    missing = sum(1 for se in component_standard_errors if se is None)
    if missing:
        return UncertaintyEstimate.not_estimable(
            reason=(
                f"{missing} of {len(component_values)} components have no estimable "
                f"standard error, so an aggregate interval would understate uncertainty "
                f"by ignoring them. No interval is reported."
            ),
            sample_size=len(component_values),
        )

    weights = np.asarray(component_weights, dtype=float)
    errors = np.asarray([float(se) for se in component_standard_errors], dtype=float)

    variance = float(np.sum((weights ** 2) * (errors ** 2)))
    se = math.sqrt(variance)

    critical = _Z_95
    return UncertaintyEstimate(
        is_estimable=True,
        basis=(
            f"Weighted-sum sampling variance over {len(component_values)} route "
            f"components: var = sum(w_i^2 * se_i^2). Components are assumed "
            f"independent; airfares are plausibly positively correlated across routes "
            f"through fuel and demand, so this is a LOWER BOUND on sampling "
            f"uncertainty. Normal critical value used."
        ),
        sample_size=len(component_values),
        standard_error=se,
        confidence_level=confidence_level,
        confidence_interval_low=aggregate_value - critical * se,
        confidence_interval_high=aggregate_value + critical * se,
        relative_standard_error_pct=(se / aggregate_value * 100) if aggregate_value else None,
        excludes=_STANDARD_EXCLUSIONS
        + ("cross-route covariance (components assumed independent)",),
    )
