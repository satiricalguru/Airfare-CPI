"""
SIH26056 — Lead-Time Elasticity Econometric Model.

Estimates the empirical relationship between advance booking lead-time (horizon)
and domestic airfares in India using polynomial log-linear regression:

    ln(Fare_i) = beta_0 + beta_1 * lead_i + beta_2 * lead_i^2 + epsilon_i

Where:
    - lead_i is advance purchase horizon in days (e.g. 1, 7, 15, 30, 45).
    - Marginal elasticity: eta(d) = d ln(P) / d(lead) = beta_1 + 2 * beta_2 * d
      measures the % price change per additional advance booking day.
    - Optimal booking horizon (minimum-fare sweet spot): d* = -beta_1 / (2 * beta_2)
    - Goodness-of-fit R^2 evaluates dynamic yield management predictability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Optional, Sequence

import numpy as np
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from db import repository as repo


@dataclass(frozen=True)
class CurvePoint:
    days: int
    predicted_fare: float
    marginal_elasticity_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "days": self.days,
            "predicted_fare": self.predicted_fare,
            "marginal_elasticity_pct": self.marginal_elasticity_pct,
        }


@dataclass(frozen=True)
class ElasticityModelResult:
    formula: str
    beta_0: float
    beta_1: float
    beta_2: float
    r_squared: float
    sample_size: int
    optimal_horizon_days: Optional[float]
    marginal_elasticities: dict[str, float]
    predicted_curve: list[dict[str, Any]]
    by_carrier: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula": self.formula,
            "coefficients": {
                "beta_0_intercept": self.beta_0,
                "beta_1_linear": self.beta_1,
                "beta_2_quadratic": self.beta_2,
            },
            "r_squared": self.r_squared,
            "sample_size": self.sample_size,
            "optimal_horizon_days": self.optimal_horizon_days,
            "marginal_elasticities_pct_per_day": self.marginal_elasticities,
            "predicted_curve": self.predicted_curve,
            "by_carrier": self.by_carrier,
            "notes": self.notes,
        }


def fit_polynomial_elasticity(
    days: Sequence[int | float],
    fares: Sequence[int | float],
    grid_points: tuple[int, ...] = (1, 3, 7, 14, 21, 30, 45, 60),
) -> Optional[ElasticityModelResult]:
    """
    Fits ln(fare) = beta_0 + beta_1 * days + beta_2 * days^2 using OLS.
    """
    clean_days: list[float] = []
    clean_fares: list[float] = []

    for d, f in zip(days, fares):
        try:
            d_val = float(d)
            f_val = float(f)
            if d_val >= 0 and f_val > 0 and not math.isnan(f_val) and not math.isinf(f_val):
                clean_days.append(d_val)
                clean_fares.append(f_val)
        except (TypeError, ValueError):
            continue

    n = len(clean_days)
    if n < 3:
        return None

    x = np.array(clean_days, dtype=np.float64)
    y = np.log(np.array(clean_fares, dtype=np.float64))

    # Variance check
    if np.var(x) < 1e-6 or np.var(y) < 1e-6:
        return None

    # Design matrix [1, x, x^2]
    X = np.column_stack([np.ones(n), x, x**2])

    try:
        # Least squares fit
        coeffs, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
        beta_0, beta_1, beta_2 = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

        y_pred = X @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-9 else 0.0
        r_squared = max(0.0, min(1.0, r_squared))
    except Exception as exc:
        logger.warning(f"Elasticity regression failed: {exc}")
        return None

    # Optimal booking horizon: d* = -beta_1 / (2 * beta_2)
    # If beta_2 > 0 (U-shaped), minimum is reached at d*
    optimal_horizon: Optional[float] = None
    if beta_2 > 1e-8:
        crit = -beta_1 / (2.0 * beta_2)
        if 1.0 <= crit <= 90.0:
            optimal_horizon = round(float(crit), 1)

    # Marginal elasticities at canonical horizons T+1, T+7, T+15, T+30, T+45
    canonical = [1, 7, 15, 30, 45]
    marginal_el: dict[str, float] = {}
    for h in canonical:
        # eta(h) = d ln(P)/dh = beta_1 + 2*beta_2*h (in percent)
        eta = (beta_1 + 2.0 * beta_2 * float(h)) * 100.0
        marginal_el[f"T+{h}"] = round(float(eta), 3)

    # Predicted curve on evaluation grid
    curve: list[dict[str, Any]] = []
    for g in grid_points:
        g_val = float(g)
        ln_p = beta_0 + beta_1 * g_val + beta_2 * (g_val**2)
        pred_fare = float(np.exp(ln_p))
        eta_g = (beta_1 + 2.0 * beta_2 * g_val) * 100.0
        curve.append({
            "days": g,
            "predicted_fare_inr": round(pred_fare, 2),
            "marginal_elasticity_pct": round(eta_g, 3),
        })

    notes = [
        "ln(Fare) = beta_0 + beta_1*lead + beta_2*lead^2",
        "Marginal elasticity reflects estimated % price shift per extra advance day.",
        "Convex pricing curve indicates standard airline dynamic yield management.",
    ]

    return ElasticityModelResult(
        formula="ln(Fare) = beta_0 + beta_1*lead + beta_2*lead^2",
        beta_0=round(beta_0, 4),
        beta_1=round(beta_1, 5),
        beta_2=round(beta_2, 6),
        r_squared=round(r_squared, 4),
        sample_size=n,
        optimal_horizon_days=optimal_horizon,
        marginal_elasticities=marginal_el,
        predicted_curve=curve,
        notes=notes,
    )


async def compute_lead_time_elasticity(
    session: AsyncSession,
    source_type: Optional[str] = None,
    route_id: Optional[int] = None,
    carrier: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Loads latest valid observations and computes the empirical lead-time elasticity.
    """
    rows = await repo.load_observations(
        session,
        route_ids=[route_id] if route_id is not None else None,
        source_type=source_type,
        valid_only=True,
    )

    if carrier:
        rows = [r for r in rows if r.airline_code == carrier]

    if not rows or len(rows) < 10:
        return None

    days = [r.booking_horizon_days for r in rows]
    fares = [float(r.fare_total) for r in rows]

    overall_result = fit_polynomial_elasticity(days, fares)
    if not overall_result:
        return None

    # Carrier breakdowns for major carriers (6E, AI, QP, SG, etc.)
    by_carrier: dict[str, dict[str, Any]] = {}
    carrier_groups: dict[str, tuple[list[int], list[float]]] = {}
    for r in rows:
        c = r.airline_code or "UNKNOWN"
        if c not in carrier_groups:
            carrier_groups[c] = ([], [])
        carrier_groups[c][0].append(r.booking_horizon_days)
        carrier_groups[c][1].append(float(r.fare_total))

    for c, (c_days, c_fares) in carrier_groups.items():
        if len(c_days) >= 10:
            c_fit = fit_polynomial_elasticity(c_days, c_fares)
            if c_fit:
                by_carrier[c] = {
                    "sample_size": c_fit.sample_size,
                    "r_squared": c_fit.r_squared,
                    "optimal_horizon_days": c_fit.optimal_horizon_days,
                    "marginal_elasticities_pct": c_fit.marginal_elasticities,
                }

    res_dict = overall_result.to_dict()
    res_dict["by_carrier"] = by_carrier
    return res_dict
