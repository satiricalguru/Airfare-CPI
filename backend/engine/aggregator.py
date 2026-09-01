"""
SIH26056 — National Airfare index aggregation.

Combines route-level indices into a national figure with a Young-type weighted mean:

    Index(t) = sum_r ( w_r * I_r(t) ) * 100

with ``w_r`` the provisional passenger-volume weights derived in
``engine/weights.py``.

Missing routes
--------------
The previous implementation divided the weighted sum by the sum of weights actually
present. That is arithmetically a renormalization, but statistically it is an
imputation: an absent route is assigned the weighted-average movement of the routes
that were collected. It happened silently, on every cycle.

The operation is retained — with no route-level data there is no better estimator —
but it is now:

* **explicit**: ``renormalization_applied`` and ``coverage_weight`` are on every
  result and in every API response;
* **bounded**: below ``min_coverage_weight`` the aggregate is marked
  ``is_publishable=False`` rather than published from a fragment of the basket;
* **attributed**: each missing route carries a :class:`MissingDataReason`.

Weighting honesty
-----------------
Passenger volume is a proxy for expenditure. A CPI component needs expenditure
shares (passengers x fare). The proxy is labelled PROVISIONAL wherever weights are
exposed, and ``expenditure_weight_status`` is carried on every aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import numpy as np
from loguru import logger

from engine.weights import RouteBasket
from provenance import METHODOLOGY_VERSION
from scraper.validator import MissingDataReason


# Minimum share of basket weight that must be present before a national figure is
# published. 0.70 is a judgement call, stated rather than buried: below roughly
# two-thirds coverage the renormalized figure describes the collected subset more than
# it describes the basket.
DEFAULT_MIN_COVERAGE_WEIGHT = 0.70


@dataclass
class RouteIndexInput:
    """A route's index for one period, as fed to national aggregation."""

    route_id: int
    index_value: float          # ratio form, 1.0 == base
    matched_products: int
    observation_count: int
    standard_error: Optional[float] = None
    horizons_included: list[int] = field(default_factory=list)
    horizons_missing: list[int] = field(default_factory=list)


@dataclass
class RouteContribution:
    """One route's contribution to the national figure."""

    route_id: int
    origin_code: str
    destination_code: str
    weight: float
    index_value: float
    weighted_contribution: float
    contribution_pct: float
    matched_products: int
    observation_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "origin_code": self.origin_code,
            "destination_code": self.destination_code,
            "route_code": f"{self.origin_code}-{self.destination_code}",
            "weight": round(self.weight, 6),
            "index_value": round(self.index_value, 6),
            "index_100": round(self.index_value * 100, 4),
            "weighted_contribution": round(self.weighted_contribution, 6),
            "contribution_pct": round(self.contribution_pct, 4),
            "matched_products": self.matched_products,
            "observation_count": self.observation_count,
        }


@dataclass
class MissingRoute:
    """A basket route with no index for the period, and why."""

    route_id: int
    route_code: str
    weight: float
    reason: MissingDataReason

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "route_code": self.route_code,
            "weight": round(self.weight, 6),
            "reason": self.reason.value,
            "policy": self.reason.description,
            "imputed_value": None,
        }


@dataclass
class NationalIndexResult:
    """The national aggregate for one period."""

    index_date: date
    index_value: float                  # base=100 scale
    booking_horizon: Optional[int]
    routes_included: int
    routes_in_basket: int
    total_observations: int
    total_matched_products: int
    base_period_label: str
    coverage_weight: float
    renormalization_applied: bool
    is_publishable: bool
    methodology_version: str = METHODOLOGY_VERSION
    route_contributions: list[RouteContribution] = field(default_factory=list)
    missing_routes: list[MissingRoute] = field(default_factory=list)
    suppression_reason: Optional[str] = None
    # Weighting provenance, carried so a consumer cannot read these as official
    # CPI expenditure weights.
    weighting_method: str = "passenger_volume"
    weighting_status: str = "PROVISIONAL"
    expenditure_weight_status: str = (
        "NOT expenditure-weighted. Passenger volume is used as a documented proxy."
    )

    mom_change_pct: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    yoy_status: str = "insufficient_history"
    mom_status: str = "insufficient_history"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_date": self.index_date.isoformat(),
            "value": round(self.index_value, 4),
            "booking_horizon": self.booking_horizon,
            "base_period": self.base_period_label,
            "routes_included": self.routes_included,
            "routes_in_basket": self.routes_in_basket,
            "sample_size": self.total_observations,
            "matched_products": self.total_matched_products,
            "coverage_weight": round(self.coverage_weight, 6),
            "renormalization_applied": self.renormalization_applied,
            "is_publishable": self.is_publishable,
            "suppression_reason": self.suppression_reason,
            "methodology_version": self.methodology_version,
            "weighting": {
                "method": self.weighting_method,
                "status": self.weighting_status,
                "expenditure_weight_status": self.expenditure_weight_status,
            },
            "mom_change_pct": (
                round(self.mom_change_pct, 4) if self.mom_change_pct is not None else None
            ),
            "mom_status": self.mom_status,
            "yoy_change_pct": (
                round(self.yoy_change_pct, 4) if self.yoy_change_pct is not None else None
            ),
            "yoy_status": self.yoy_status,
            "missing_routes": [m.to_dict() for m in self.missing_routes],
        }


class NationalAggregator:
    """Aggregates route indices into the national figure."""

    def __init__(
        self,
        basket: RouteBasket,
        min_coverage_weight: float = DEFAULT_MIN_COVERAGE_WEIGHT,
    ):
        self.basket = basket
        self.min_coverage_weight = min_coverage_weight
        logger.debug(
            f"Aggregator: {len(basket.routes)} routes, weights sum "
            f"{basket.weight_sum:.12f}, min coverage {min_coverage_weight:.2f}"
        )

    def aggregate(
        self,
        route_indices: list[RouteIndexInput],
        index_date: date,
        base_period_label: str,
        booking_horizon: Optional[int] = None,
        missing_reasons: Optional[dict[int, MissingDataReason]] = None,
        previous_index: Optional[float] = None,
        previous_year_index: Optional[float] = None,
    ) -> NationalIndexResult:
        """
        Compute the national index.

        ``previous_index`` and ``previous_year_index`` are on the same base=100 scale.
        Either being None yields a null change with an explicit status string rather
        than a fabricated percentage.
        """
        weight_map = self.basket.weight_map()
        missing_reasons = missing_reasons or {}

        contributions: list[RouteContribution] = []
        weighted_sum = 0.0
        coverage_weight = 0.0
        total_obs = 0
        total_matched = 0

        for ri in route_indices:
            route = self.basket.by_id(ri.route_id)
            if route is None:
                logger.warning(
                    f"Route {ri.route_id} has an index but is not in the basket; "
                    f"excluded from aggregation"
                )
                continue
            if ri.index_value <= 0:
                logger.warning(
                    f"Route {ri.route_id} index is {ri.index_value}; excluded"
                )
                continue

            weight = weight_map[ri.route_id]
            weighted = weight * ri.index_value

            weighted_sum += weighted
            coverage_weight += weight
            total_obs += ri.observation_count
            total_matched += ri.matched_products

            contributions.append(
                RouteContribution(
                    route_id=ri.route_id,
                    origin_code=route.origin_code,
                    destination_code=route.destination_code,
                    weight=weight,
                    index_value=ri.index_value,
                    weighted_contribution=weighted,
                    contribution_pct=0.0,  # set once the total is known
                    matched_products=ri.matched_products,
                    observation_count=ri.observation_count,
                )
            )

        present_ids = {c.route_id for c in contributions}
        missing_routes = [
            MissingRoute(
                route_id=route.route_id,
                route_code=route.route_code,
                weight=weight_map[route.route_id],
                reason=missing_reasons.get(
                    route.route_id, MissingDataReason.ROUTE_NOT_COLLECTED
                ),
            )
            for route in self.basket.routes
            if route.route_id not in present_ids
        ]

        if not contributions:
            return NationalIndexResult(
                index_date=index_date,
                index_value=0.0,
                booking_horizon=booking_horizon,
                routes_included=0,
                routes_in_basket=len(self.basket.routes),
                total_observations=0,
                total_matched_products=0,
                base_period_label=base_period_label,
                coverage_weight=0.0,
                renormalization_applied=False,
                is_publishable=False,
                missing_routes=missing_routes,
                suppression_reason=(
                    "No route index was computable for this period, so no national "
                    "figure exists. No value has been imputed."
                ),
                weighting_method=self.basket.methodology.method,
                weighting_status=self.basket.methodology.status,
                mom_status="not_computable",
                yoy_status="not_computable",
            )

        # Renormalize over present weight. Explicit, recorded, and bounded below.
        renormalization_applied = abs(coverage_weight - 1.0) > 1e-9
        index_ratio = weighted_sum / coverage_weight
        index_value = index_ratio * 100.0

        for c in contributions:
            c.contribution_pct = (
                c.weighted_contribution / weighted_sum * 100 if weighted_sum > 0 else 0.0
            )
        contributions.sort(key=lambda c: c.weighted_contribution, reverse=True)

        is_publishable = coverage_weight >= self.min_coverage_weight
        suppression_reason = None
        if not is_publishable:
            suppression_reason = (
                f"Basket coverage is {coverage_weight:.1%}, below the "
                f"{self.min_coverage_weight:.0%} minimum. Renormalizing from this "
                f"fraction of the basket would attribute the collected routes' movement "
                f"to the {len(missing_routes)} uncollected route(s), so the figure is "
                f"computed but marked not publishable."
            )
            logger.warning(suppression_reason)
        elif renormalization_applied:
            logger.info(
                f"National index {index_date}: coverage {coverage_weight:.1%} "
                f"({len(missing_routes)} route(s) missing); renormalization applied and "
                f"recorded"
            )

        mom_change, mom_status = _period_change(index_value, previous_index, "previous period")
        yoy_change, yoy_status = _period_change(
            index_value, previous_year_index, "same period one year earlier"
        )

        result = NationalIndexResult(
            index_date=index_date,
            index_value=index_value,
            booking_horizon=booking_horizon,
            routes_included=len(contributions),
            routes_in_basket=len(self.basket.routes),
            total_observations=total_obs,
            total_matched_products=total_matched,
            base_period_label=base_period_label,
            coverage_weight=coverage_weight,
            renormalization_applied=renormalization_applied,
            is_publishable=is_publishable,
            route_contributions=contributions,
            missing_routes=missing_routes,
            suppression_reason=suppression_reason,
            weighting_method=self.basket.methodology.method,
            weighting_status=self.basket.methodology.status,
            mom_change_pct=mom_change,
            mom_status=mom_status,
            yoy_change_pct=yoy_change,
            yoy_status=yoy_status,
        )

        logger.info(
            f"National index {index_date} H={booking_horizon}: {index_value:.2f} "
            f"({len(contributions)}/{len(self.basket.routes)} routes, "
            f"{total_obs} obs, publishable={is_publishable})"
        )
        return result

    def decompose_change(
        self,
        current: NationalIndexResult,
        previous: NationalIndexResult,
    ) -> list[dict[str, Any]]:
        """
        Attribute the change in the national figure to route movements.

        Only routes present in BOTH periods are decomposed: a route that entered or
        left the sample has no comparable prior contribution, and pretending otherwise
        would attribute a composition change to a price movement.
        """
        previous_map = {c.route_id: c for c in previous.route_contributions}
        total_change = current.index_value - previous.index_value

        rows: list[dict[str, Any]] = []
        for curr in current.route_contributions:
            prior = previous_map.get(curr.route_id)
            if prior is None:
                continue

            route_change = curr.index_value - prior.index_value
            points = curr.weight * route_change * 100

            rows.append({
                "route_id": curr.route_id,
                "route_code": f"{curr.origin_code}-{curr.destination_code}",
                "weight": round(curr.weight, 6),
                "index_current": round(curr.index_value * 100, 4),
                "index_previous": round(prior.index_value * 100, 4),
                "route_change_pct": (
                    round(route_change / prior.index_value * 100, 4)
                    if prior.index_value > 0
                    else None
                ),
                "contribution_to_change_points": round(points, 4),
                "share_of_total_change_pct": (
                    round(points / total_change * 100, 2) if total_change else None
                ),
            })

        rows.sort(key=lambda r: abs(r["contribution_to_change_points"]), reverse=True)

        excluded = len(current.route_contributions) - len(rows)
        if excluded:
            logger.debug(
                f"Change decomposition excluded {excluded} route(s) absent from the "
                f"comparison period"
            )
        return rows


def _period_change(
    current: float, previous: Optional[float], description: str
) -> tuple[Optional[float], str]:
    """
    Percentage change against a prior level, or a stated reason for its absence.

    Returns ``(None, "insufficient_history")`` when the comparison level does not
    exist. That string is what the API publishes; no placeholder percentage is ever
    substituted to make a dashboard look complete.
    """
    if previous is None:
        return None, "insufficient_history"
    if previous <= 0:
        return None, "invalid_comparison_base"
    return ((current - previous) / previous) * 100.0, "available"


def geometric_mean(values: list[float]) -> Optional[float]:
    """Geometric mean helper, used by callers that need a level summary."""
    positive = [v for v in values if v > 0]
    if not positive:
        return None
    return float(np.exp(np.mean(np.log(np.array(positive, dtype=float)))))
