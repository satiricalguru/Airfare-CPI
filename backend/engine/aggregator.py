"""
SIH26056 — National Airfare CPI Aggregator

Aggregates route-level Jevons indices into a national Airfare CPI
using a Laspeyres/Young-type weighted sum with DGCA passenger volumes.

Formula:
    CPI(t) = Σᵣ [wᵣ × I(r,t)]

Where:
    - wᵣ = DGCA_paxᵣ / Σ DGCA_pax  (normalized passenger-volume weight)
    - I(r,t) = Jevons index for route r at time t

Methodological Notes:
    - Pure passenger volume is a proxy for expenditure weight
    - True CPI expenditure = volume × average_price
    - For prototype: volume-only weights (justified by data availability)
    - Production: multiply by average observed fare to get expenditure weights
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from loguru import logger

from .jevons import JevonsResult


@dataclass
class RouteWeight:
    """A route with its normalized DGCA passenger-volume weight."""
    route_id: int
    origin_code: str
    destination_code: str
    weight: float
    monthly_pax: int


@dataclass
class RouteContribution:
    """Contribution of a single route to the national index."""
    route_id: int
    origin_code: str
    destination_code: str
    weight: float
    jevons_index: float
    weighted_contribution: float  # weight × jevons_index
    contribution_pct: float       # What % of national CPI this route explains


@dataclass
class NationalCPIResult:
    """Result of the national Airfare CPI aggregation."""
    index_date: date
    booking_horizon: Optional[int]
    airfare_cpi: float
    routes_included: int
    total_observations: int
    base_period: str
    route_contributions: list[RouteContribution] = field(default_factory=list)
    mom_change_pct: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    missing_routes: list[int] = field(default_factory=list)


class NationalAggregator:
    """
    Aggregates route-level Jevons indices into a national Airfare CPI.
    
    Uses a Laspeyres/Young-type formula:
        CPI(t) = Σ wᵣ × Iᵣ(t)
    
    Weights are derived from DGCA city-pair passenger volumes,
    normalized to sum to 1.0.
    """
    
    def __init__(self, route_weights: list[RouteWeight]):
        """
        Args:
            route_weights: List of routes with their normalized weights.
                          Weights should sum to 1.0 (will be re-normalized if not).
        """
        self.route_weights = {rw.route_id: rw for rw in route_weights}
        
        # Re-normalize weights to ensure they sum to exactly 1.0
        total_weight = sum(rw.weight for rw in route_weights)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                f"Route weights sum to {total_weight:.4f}, re-normalizing to 1.0"
            )
            for rw in route_weights:
                rw.weight = rw.weight / total_weight
                self.route_weights[rw.route_id] = rw
        
        logger.info(
            f"Aggregator initialized with {len(route_weights)} routes, "
            f"total weight = {sum(rw.weight for rw in route_weights):.6f}"
        )
    
    def compute_national_cpi(
        self,
        route_indices: list[JevonsResult],
        previous_cpi: Optional[float] = None,
        previous_year_cpi: Optional[float] = None,
    ) -> NationalCPIResult:
        """
        Compute the national Airfare CPI as a weighted sum of route indices.
        
        Args:
            route_indices: List of Jevons results for each route
            previous_cpi: Previous month's CPI (for MoM calculation)
            previous_year_cpi: Same month last year's CPI (for YoY)
            
        Returns:
            NationalCPIResult with the aggregated index
        """
        if not route_indices:
            logger.error("No route indices provided for national aggregation")
            raise ValueError("No route indices to aggregate")
        
        # Get common metadata from first result
        index_date = route_indices[0].index_date
        booking_horizon = route_indices[0].booking_horizon
        base_period = (
            f"{route_indices[0].base_period_start.isoformat()} to "
            f"{route_indices[0].base_period_end.isoformat()}"
        )
        
        # Match route indices to weights
        contributions = []
        weighted_sum = 0.0
        active_weight_sum = 0.0
        total_obs = 0
        available_route_ids = {ri.route_id for ri in route_indices}
        missing_routes = []
        
        for ri in route_indices:
            rw = self.route_weights.get(ri.route_id)
            if rw is None:
                logger.warning(f"Route {ri.route_id} has no weight — skipping")
                continue
            
            weighted_contribution = rw.weight * ri.jevons_index
            weighted_sum += weighted_contribution
            active_weight_sum += rw.weight
            total_obs += ri.observation_count
            
            contributions.append(RouteContribution(
                route_id=ri.route_id,
                origin_code=rw.origin_code,
                destination_code=rw.destination_code,
                weight=rw.weight,
                jevons_index=ri.jevons_index,
                weighted_contribution=weighted_contribution,
                contribution_pct=0.0,  # Will be set after total is known
            ))
        
        # Check for missing routes
        for route_id in self.route_weights:
            if route_id not in available_route_ids:
                missing_routes.append(route_id)
        
        if missing_routes:
            logger.warning(
                f"Missing {len(missing_routes)} routes in national aggregation: "
                f"{missing_routes}"
            )
        
        if active_weight_sum == 0:
            logger.error("No valid routes with weights for national CPI")
            raise ValueError("No valid routes for aggregation")
        
        # Re-normalize by active weight sum (handles missing routes)
        # This ensures the CPI reflects only the routes we have data for,
        # scaled so that if all routes were present, the index would be correct
        airfare_cpi = weighted_sum / active_weight_sum
        
        # Set contribution percentages
        for c in contributions:
            c.contribution_pct = (
                (c.weighted_contribution / weighted_sum * 100) 
                if weighted_sum > 0 else 0.0
            )
        
        # Sort by contribution (largest first)
        contributions.sort(key=lambda c: c.weighted_contribution, reverse=True)
        
        # MoM and YoY changes
        mom_change = None
        yoy_change = None
        if previous_cpi is not None and previous_cpi > 0:
            mom_change = ((airfare_cpi - previous_cpi) / previous_cpi) * 100
        if previous_year_cpi is not None and previous_year_cpi > 0:
            yoy_change = ((airfare_cpi - previous_year_cpi) / previous_year_cpi) * 100
        
        # Scale to base 100
        airfare_cpi_scaled = airfare_cpi * 100
        
        logger.info(
            f"National CPI | Date={index_date} | Horizon={booking_horizon} | "
            f"CPI={airfare_cpi_scaled:.2f} | Routes={len(contributions)}/{len(self.route_weights)} | "
            f"Obs={total_obs}"
        )
        if mom_change is not None:
            logger.info(f"  MoM: {mom_change:+.2f}%")
        if yoy_change is not None:
            logger.info(f"  YoY: {yoy_change:+.2f}%")
        
        return NationalCPIResult(
            index_date=index_date,
            booking_horizon=booking_horizon,
            airfare_cpi=airfare_cpi_scaled,
            routes_included=len(contributions),
            total_observations=total_obs,
            base_period=base_period,
            route_contributions=contributions,
            mom_change_pct=mom_change,
            yoy_change_pct=yoy_change,
            missing_routes=missing_routes,
        )
    
    def decompose_change(
        self,
        current_result: NationalCPIResult,
        previous_result: NationalCPIResult,
    ) -> list[dict]:
        """
        Decompose the change in national CPI into route-level contributions.
        
        For each route, shows how much of the total CPI change is attributable
        to that route's price movement (weighted by DGCA passenger volume).
        
        Useful for the dashboard and MoSPI report.
        """
        prev_map = {
            c.route_id: c for c in previous_result.route_contributions
        }
        
        total_change = current_result.airfare_cpi - previous_result.airfare_cpi
        decomposition = []
        
        for curr in current_result.route_contributions:
            prev = prev_map.get(curr.route_id)
            if prev is None:
                continue
            
            route_change = curr.jevons_index - prev.jevons_index
            weighted_change = curr.weight * route_change * 100  # In CPI points
            
            decomposition.append({
                "route_id": curr.route_id,
                "origin": curr.origin_code,
                "destination": curr.destination_code,
                "weight": curr.weight,
                "jevons_current": curr.jevons_index,
                "jevons_previous": prev.jevons_index,
                "route_change_pct": (
                    (route_change / prev.jevons_index * 100)
                    if prev.jevons_index > 0 else 0
                ),
                "contribution_to_national_change": weighted_change,
                "share_of_total_change": (
                    (weighted_change / total_change * 100)
                    if total_change != 0 else 0
                ),
            })
        
        decomposition.sort(
            key=lambda d: abs(d["contribution_to_national_change"]),
            reverse=True
        )
        
        return decomposition
