"""
SIH26056 — Index computation service.

Walks the full pipeline from stored observations to a published national figure:

    normalized_fares
      -> matched-model Jevons per (route, horizon)   -> horizon_indices
      -> horizon weighting per route                 -> route_indices
      -> passenger-volume weighting across routes    -> national_indices

Every step reads from the database and writes back to it, so a published value is
reproducible: recomputing from the same stored observations yields the same number.
Nothing is regenerated from a simulator at read time.

Two properties worth stating explicitly, because both were defects in the audit:

* **MoM and YoY come from stored index history**, looked up in the database. When the
  comparison period does not exist, the change is ``None`` with a status string. No
  placeholder percentage is ever produced.
* **A period with no computable index is recorded as such.** Routes absent from a
  period carry a :class:`MissingDataReason`; they are never imputed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from db import repository as repo
from engine.aggregator import NationalAggregator, RouteIndexInput
from engine.horizon import (
    CombinedRouteIndex,
    HorizonIndexInput,
    HorizonPolicy,
    combine_horizon_indices,
    get_horizon_policy,
)
from engine.matched_jevons import MatchedJevonsCalculator, MatchedJevonsResult
from engine.rebase import BasePeriod, BasePriceSet, compute_base_prices
from engine.seasonality import SEASONAL_ADJUSTMENT_STATUS
from engine.uncertainty import (
    UncertaintyEstimate,
    aggregate_uncertainty,
    estimate_elementary_uncertainty,
)
from engine.weights import RouteBasket, get_route_basket
from provenance import (
    METHODOLOGY_VERSION,
    PROVENANCE_LABELS,
    SourceType,
    utc_now,
)
from scraper.base import FareObservation
from scraper.validator import MissingDataReason


@dataclass
class IndexComputationResult:
    """Summary of one computation pass."""

    dates_computed: list[date] = field(default_factory=list)
    horizon_indices_written: int = 0
    route_indices_written: int = 0
    national_indices_written: int = 0
    base_period: Optional[BasePeriod] = None
    source_type: Optional[SourceType] = None
    skipped_dates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dates_computed": [d.isoformat() for d in self.dates_computed],
            "horizon_indices_written": self.horizon_indices_written,
            "route_indices_written": self.route_indices_written,
            "national_indices_written": self.national_indices_written,
            "base_period": self.base_period.to_dict() if self.base_period else None,
            "source_type": self.source_type.value if self.source_type else None,
            "provenance_label": (
                PROVENANCE_LABELS[self.source_type] if self.source_type else None
            ),
            "methodology_version": METHODOLOGY_VERSION,
            "skipped_dates": self.skipped_dates,
        }


class IndexService:
    """Computes and persists indices from stored observations."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        basket: Optional[RouteBasket] = None,
        policy: Optional[HorizonPolicy] = None,
    ):
        self.settings = settings or get_settings()
        self.basket = basket or get_route_basket(self.settings.route_basket_path)
        self.policy = policy or get_horizon_policy(self.settings.horizon_policy_path)
        self.base_period = BasePeriod.from_settings(self.settings.index)
        self.calculator = MatchedJevonsCalculator(self.settings.index)
        self.aggregator = NationalAggregator(self.basket)

    # ── entry point ──

    async def recompute(
        self,
        session: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        reason: str = "scheduled recomputation",
    ) -> IndexComputationResult:
        """
        Recompute indices for every date with observations after the base period.

        Idempotent: running it twice over unchanged observations produces identical
        stored values, and each write appends an ``index_revisions`` row so the second
        run is visible as a recomputation rather than silently overwriting.
        """
        result = IndexComputationResult(base_period=self.base_period)

        records = await repo.load_observations(session, valid_only=True)
        if not records:
            logger.info("No stored observations; nothing to compute")
            return result

        observations = [repo.record_to_observation(r) for r in records]
        source_types = {o.source_type for o in observations}

        # A mixed-provenance index would be uninterpretable: part measurement, part
        # simulation, with no way to label the result honestly.
        if len(source_types) > 1:
            logger.warning(
                f"Stored observations span multiple provenance types "
                f"{sorted(t.value for t in source_types)}. Computing per provenance "
                f"type is not supported; the dominant type is used and the mixture is "
                f"reported. Clear the database when switching modes."
            )
        dominant = max(source_types, key=lambda t: sum(1 for o in observations if o.source_type is t))
        observations = [o for o in observations if o.source_type is dominant]
        result.source_type = dominant

        base_sets = compute_base_prices(observations, self.base_period)
        if not base_sets:
            logger.warning(
                f"No observations fall inside the base period "
                f"{self.base_period.label}; no index can be computed. Base prices are "
                f"selected strictly by collection date, never by insertion order."
            )
            result.skipped_dates.append({
                "date": None,
                "reason": MissingDataReason.NO_BASE_PERIOD_DATA.value,
                "detail": MissingDataReason.NO_BASE_PERIOD_DATA.description,
            })
            return result

        # Candidate index dates: every collection day after the base period ends.
        by_day: dict[date, list[FareObservation]] = {}
        for obs in observations:
            by_day.setdefault(obs.collection_date, []).append(obs)

        candidate_dates = sorted(d for d in by_day if d > self.base_period.end)
        if start_date:
            candidate_dates = [d for d in candidate_dates if d >= start_date]
        if end_date:
            candidate_dates = [d for d in candidate_dates if d <= end_date]

        if not candidate_dates:
            logger.info(
                f"No collection days after the base period end "
                f"({self.base_period.end}); no index dates to compute"
            )
            return result

        # Tracks product keys seen in any earlier period, so a product returning after
        # an absence is reported as reappeared rather than new.
        seen_keys: set[str] = set()
        for key, base_set in base_sets.items():
            seen_keys.update(base_set.product_prices)

        for index_date in candidate_dates:
            day_observations = by_day[index_date]
            written = await self._compute_for_date(
                session=session,
                index_date=index_date,
                observations=day_observations,
                base_sets=base_sets,
                source_type=dominant,
                seen_keys=seen_keys,
                reason=reason,
            )

            if written is None:
                result.skipped_dates.append({
                    "date": index_date.isoformat(),
                    "reason": MissingDataReason.INSUFFICIENT_MATCHED_OBSERVATIONS.value,
                    "detail": (
                        MissingDataReason.INSUFFICIENT_MATCHED_OBSERVATIONS.description
                    ),
                })
                continue

            horizon_count, route_count, national_written = written
            result.dates_computed.append(index_date)
            result.horizon_indices_written += horizon_count
            result.route_indices_written += route_count
            result.national_indices_written += national_written

            for obs in day_observations:
                seen_keys.add(obs.product_key())

        logger.info(
            f"Index computation complete: {len(result.dates_computed)} date(s), "
            f"{result.horizon_indices_written} horizon, "
            f"{result.route_indices_written} route, "
            f"{result.national_indices_written} national value(s)"
        )
        return result

    # ── per-date computation ──

    async def _compute_for_date(
        self,
        session: AsyncSession,
        index_date: date,
        observations: list[FareObservation],
        base_sets: dict[tuple[int, int], BasePriceSet],
        source_type: SourceType,
        seen_keys: set[str],
        reason: str,
    ) -> Optional[tuple[int, int, int]]:
        """
        Compute horizon, route and national indices for one date.

        Returns ``(horizon_rows, route_rows, national_rows)``, or None when no route
        index was computable for the date.
        """
        now = utc_now()

        # ── group by (route, horizon) ──
        grouped: dict[tuple[int, int], list[FareObservation]] = {}
        for obs in observations:
            grouped.setdefault((obs.route_id, obs.booking_horizon_days), []).append(obs)

        horizon_rows: list[dict[str, Any]] = []
        horizon_results: dict[int, list[HorizonIndexInput]] = {}
        # (route_id, horizon) -> uncertainty, reused when combining
        horizon_uncertainty: dict[tuple[int, int], UncertaintyEstimate] = {}

        for (route_id, horizon), group in sorted(grouped.items()):
            base_set = base_sets.get((route_id, horizon))
            if base_set is None:
                logger.debug(
                    f"Route {route_id} T+{horizon} on {index_date}: no base-period "
                    f"prices; horizon index not computed"
                )
                continue

            jevons = self.calculator.compute(
                current_observations=group,
                base_prices=base_set.product_prices,
                route_id=route_id,
                index_date=index_date,
                base_period_start=self.base_period.start,
                base_period_end=self.base_period.end,
                booking_horizon=horizon,
                previously_seen_keys=seen_keys,
            )

            if jevons is None:
                continue

            uncertainty = estimate_elementary_uncertainty(
                log_relatives=jevons.log_relatives,
                index_value=jevons.index_value,
            )
            horizon_uncertainty[(route_id, horizon)] = uncertainty

            horizon_rows.append(
                self._horizon_row(jevons, uncertainty, source_type, now)
            )
            horizon_results.setdefault(route_id, []).append(
                HorizonIndexInput(
                    booking_horizon=horizon,
                    index_value=jevons.index_value,
                    matched_products=jevons.matched_products,
                    observation_count=jevons.observation_count,
                )
            )

        if not horizon_rows:
            logger.info(
                f"{index_date}: no horizon index was computable; no route or national "
                f"figure is published for this date"
            )
            return None

        written_horizons = await repo.save_horizon_indices(session, horizon_rows)

        # ── combine horizons into route indices ──
        route_rows: list[dict[str, Any]] = []
        route_inputs: list[RouteIndexInput] = []
        missing_reasons: dict[int, MissingDataReason] = {}

        for route_id, inputs in sorted(horizon_results.items()):
            combined = combine_horizon_indices(route_id, inputs, self.policy)

            route_uncertainty = self._combine_route_uncertainty(
                route_id=route_id,
                combined=combined,
                horizon_uncertainty=horizon_uncertainty,
            )

            route_rows.append(
                self._route_row(
                    combined, index_date, route_uncertainty, source_type, now
                )
            )

            if not combined.is_publishable:
                missing_reasons[route_id] = MissingDataReason.INSUFFICIENT_HORIZONS
                continue

            route_inputs.append(
                RouteIndexInput(
                    route_id=route_id,
                    index_value=combined.index_value,
                    matched_products=combined.total_matched_products,
                    observation_count=combined.total_observations,
                    standard_error=route_uncertainty.standard_error,
                    horizons_included=combined.horizons_included,
                    horizons_missing=combined.horizons_missing,
                )
            )

        written_routes = await repo.save_route_indices(session, route_rows)

        # Routes in the basket with no observations at all on this date.
        computed_ids = set(horizon_results)
        for route in self.basket.routes:
            if route.route_id not in computed_ids and route.route_id not in missing_reasons:
                missing_reasons[route.route_id] = MissingDataReason.ROUTE_NOT_COLLECTED

        if not route_inputs:
            logger.info(
                f"{index_date}: horizon indices exist but no route index is "
                f"publishable; no national figure published"
            )
            return written_horizons, written_routes, 0

        # ── national aggregate ──
        previous = await repo.get_national_index_nearest_before(session, index_date)
        previous_year = await self._find_previous_year_index(session, index_date)

        national = self.aggregator.aggregate(
            route_indices=route_inputs,
            index_date=index_date,
            base_period_label=self.base_period.label,
            booking_horizon=None,
            missing_reasons=missing_reasons,
            previous_index=previous.index_value if previous else None,
            previous_year_index=previous_year.index_value if previous_year else None,
        )

        national_uncertainty = aggregate_uncertainty(
            component_values=[c.index_value for c in national.route_contributions],
            component_weights=[c.weight for c in national.route_contributions],
            component_standard_errors=[
                next(
                    (ri.standard_error for ri in route_inputs if ri.route_id == c.route_id),
                    None,
                )
                for c in national.route_contributions
            ],
            aggregate_value=national.index_value,
        )

        await repo.save_national_index(
            session,
            self._national_row(national, national_uncertainty, source_type, now),
            revision_reason=reason,
        )

        # ── horizon-specific national indices ──
        # Published alongside the headline so a reader can see how much of a movement
        # is concentrated in short-notice versus advance-purchase travel.
        horizon_national = 0
        for horizon in self.policy.horizon_days:
            per_horizon_inputs = [
                RouteIndexInput(
                    route_id=route_id,
                    index_value=hi.index_value,
                    matched_products=hi.matched_products,
                    observation_count=hi.observation_count,
                    standard_error=horizon_uncertainty.get(
                        (route_id, horizon), UncertaintyEstimate.not_estimable("n/a")
                    ).standard_error,
                )
                for route_id, inputs in horizon_results.items()
                for hi in inputs
                if hi.booking_horizon == horizon
            ]
            if not per_horizon_inputs:
                continue

            previous_h = await repo.get_national_index_nearest_before(
                session, index_date, booking_horizon=horizon
            )
            previous_year_h = await self._find_previous_year_index(
                session, index_date, booking_horizon=horizon
            )

            national_h = self.aggregator.aggregate(
                route_indices=per_horizon_inputs,
                index_date=index_date,
                base_period_label=self.base_period.label,
                booking_horizon=horizon,
                missing_reasons=missing_reasons,
                previous_index=previous_h.index_value if previous_h else None,
                previous_year_index=previous_year_h.index_value if previous_year_h else None,
            )

            uncertainty_h = aggregate_uncertainty(
                component_values=[c.index_value for c in national_h.route_contributions],
                component_weights=[c.weight for c in national_h.route_contributions],
                component_standard_errors=[
                    next(
                        (ri.standard_error for ri in per_horizon_inputs
                         if ri.route_id == c.route_id),
                        None,
                    )
                    for c in national_h.route_contributions
                ],
                aggregate_value=national_h.index_value,
            )

            await repo.save_national_index(
                session,
                self._national_row(national_h, uncertainty_h, source_type, now),
                revision_reason=f"{reason} (horizon T+{horizon})",
            )
            horizon_national += 1

        return written_horizons, written_routes, 1 + horizon_national

    # ── uncertainty combination ──

    def _combine_route_uncertainty(
        self,
        route_id: int,
        combined: CombinedRouteIndex,
        horizon_uncertainty: dict[tuple[int, int], UncertaintyEstimate],
    ) -> UncertaintyEstimate:
        """
        Propagate horizon uncertainty into the route index.

        The route index is a fixed-weight sum of horizon indices, so the same
        weighted-variance formula applies, with the horizon weights actually used.
        """
        if not combined.is_publishable:
            return UncertaintyEstimate.not_estimable(
                f"route index is not publishable: {combined.suppression_reason}"
            )

        values, weights, errors = [], [], []
        for horizon, weight in combined.applied_weights.items():
            estimate = horizon_uncertainty.get((route_id, horizon))
            values.append(1.0)  # placeholder: only weights and errors affect variance
            weights.append(weight)
            errors.append(estimate.standard_error if estimate else None)

        return aggregate_uncertainty(
            component_values=values,
            component_weights=weights,
            component_standard_errors=errors,
            aggregate_value=combined.index_value,
        )

    # ── row builders ──

    def _horizon_row(
        self,
        jevons: MatchedJevonsResult,
        uncertainty: UncertaintyEstimate,
        source_type: SourceType,
        now,
    ) -> dict[str, Any]:
        return {
            "route_id": jevons.route_id,
            "booking_horizon": jevons.booking_horizon,
            "index_date": jevons.index_date,
            "index_value": jevons.index_value,
            "index_100": jevons.index_100,
            "matched_products": jevons.matched_products,
            "observation_count": jevons.observation_count,
            "geometric_mean_price": jevons.geometric_mean_price,
            "base_geometric_mean_price": jevons.base_geometric_mean_price,
            "base_period_start": jevons.base_period_start,
            "base_period_end": jevons.base_period_end,
            "new_products": jevons.new_products,
            "disappeared_products": jevons.disappeared_products,
            "reappeared_products": jevons.reappeared_products,
            "base_products": jevons.base_products,
            "current_products": jevons.current_products,
            "match_rate": jevons.match_rate,
            "standard_error": uncertainty.standard_error,
            "confidence_interval_low": uncertainty.confidence_interval_low,
            "confidence_interval_high": uncertainty.confidence_interval_high,
            "uncertainty_basis": uncertainty.basis,
            "source_type": source_type.value,
            "methodology_version": METHODOLOGY_VERSION,
            "computed_at": now,
            "matched_product_keys": list(jevons.matched_keys),
        }

    def _route_row(
        self,
        combined: CombinedRouteIndex,
        index_date: date,
        uncertainty: UncertaintyEstimate,
        source_type: SourceType,
        now,
    ) -> dict[str, Any]:
        return {
            "route_id": combined.route_id,
            "index_date": index_date,
            "index_value": combined.index_value,
            "index_100": combined.index_value * 100.0,
            "horizons_included": list(combined.horizons_included),
            "horizons_missing": list(combined.horizons_missing),
            "applied_horizon_weights": {
                str(k): v for k, v in combined.applied_weights.items()
            },
            "horizon_weighting_method": combined.weighting_method,
            "horizon_weighting_status": combined.weighting_status,
            "horizon_policy_version": combined.policy_version,
            "matched_products": combined.total_matched_products,
            "observation_count": combined.total_observations,
            "standard_error": uncertainty.standard_error,
            "confidence_interval_low": uncertainty.confidence_interval_low,
            "confidence_interval_high": uncertainty.confidence_interval_high,
            "uncertainty_basis": uncertainty.basis,
            "base_period_start": self.base_period.start,
            "base_period_end": self.base_period.end,
            "is_publishable": combined.is_publishable,
            "suppression_reason": combined.suppression_reason,
            "source_type": source_type.value,
            "methodology_version": METHODOLOGY_VERSION,
            "computed_at": now,
        }

    def _national_row(
        self,
        national,
        uncertainty: UncertaintyEstimate,
        source_type: SourceType,
        now,
    ) -> dict[str, Any]:
        return {
            "index_date": national.index_date,
            "booking_horizon": national.booking_horizon,
            "index_value": national.index_value,
            "routes_included": national.routes_included,
            "routes_in_basket": national.routes_in_basket,
            "total_observations": national.total_observations,
            "total_matched_products": national.total_matched_products,
            "coverage_weight": national.coverage_weight,
            "renormalization_applied": national.renormalization_applied,
            "is_publishable": national.is_publishable,
            "suppression_reason": national.suppression_reason,
            "mom_change_pct": national.mom_change_pct,
            "mom_status": national.mom_status,
            "yoy_change_pct": national.yoy_change_pct,
            "yoy_status": national.yoy_status,
            "standard_error": uncertainty.standard_error,
            "confidence_interval_low": uncertainty.confidence_interval_low,
            "confidence_interval_high": uncertainty.confidence_interval_high,
            "uncertainty_basis": uncertainty.basis,
            "seasonal_adjustment": SEASONAL_ADJUSTMENT_STATUS,
            "base_period_start": self.base_period.start,
            "base_period_end": self.base_period.end,
            "base_period_label": self.base_period.label,
            "weight_basket_id": self.basket.basket_id,
            "weight_basket_version": self.basket.basket_version,
            "weighting_method": national.weighting_method,
            "weighting_status": national.weighting_status,
            "source_type": source_type.value,
            "provenance_label": PROVENANCE_LABELS[source_type],
            "methodology_version": METHODOLOGY_VERSION,
            "validation_rules_version": repo.VALIDATION_RULES_VERSION,
            "computed_at": now,
            "contributing_run_ids": [],
            "route_contributions": [c.to_dict() for c in national.route_contributions],
            "missing_routes": [m.to_dict() for m in national.missing_routes],
        }

    # ── year-on-year lookup ──

    async def _find_previous_year_index(
        self,
        session: AsyncSession,
        index_date: date,
        booking_horizon: Optional[int] = None,
    ):
        """
        Locate the stored index 12 months before ``index_date``.

        Returns None when the series does not reach back that far, which is the honest
        answer for a young series. Callers surface ``yoy_status="insufficient_history"``
        rather than a fabricated percentage.
        """
        try:
            anchor = index_date.replace(year=index_date.year - 1)
        except ValueError:  # 29 February
            anchor = index_date.replace(year=index_date.year - 1, day=28)

        exact = await repo.get_national_index_on(
            session, anchor, booking_horizon=booking_horizon
        )
        if exact is not None:
            return exact

        # Allow a small tolerance so a one-day collection gap does not silently drop
        # YoY, but never widen it enough to compare against a different month.
        for offset in range(1, 8):
            for candidate in (anchor - timedelta(days=offset), anchor + timedelta(days=offset)):
                if candidate.month != anchor.month:
                    continue
                found = await repo.get_national_index_on(
                    session, candidate, booking_horizon=booking_horizon
                )
                if found is not None:
                    return found
        return None
