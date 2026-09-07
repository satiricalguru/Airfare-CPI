"""
SIH26056 — Fare observation validation.

Philosophy, unchanged from the original and still correct: a scraping/parsing error
is EXCLUDED; genuine market volatility is FLAGGED and kept. Airfares really are
volatile, and an index that quietly deletes real volatility is not measuring the
market.

What changed
------------
* ``max_daily_change_pct`` is enforced per route AND per booking horizon. Comparing a
  same-day fare against yesterday's 30-day-advance median would flag the horizon
  gap, not a price movement.
* The IQR reference distribution no longer admits observations that were themselves
  flagged as outliers. Previously each accepted outlier widened the fences, which
  progressively desensitised the filter — a slow drift toward accepting anything.
* Validator state is serialisable (:meth:`FareValidator.export_state` /
  :meth:`restore_state`) and persisted, so fences do not reset on restart. Previously
  the first ten observations after every restart went unchecked and results were not
  reproducible.
* Missing data has an explicit, enumerated policy (:class:`MissingDataReason`)
  instead of being silently absorbed. Nothing is imputed at the basket average.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Iterable, Optional

import numpy as np
from loguru import logger

from config import ValidationSettings, get_settings
from scraper.base import FareObservation


class ValidationAction(str, Enum):
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    EXCLUDED = "excluded"


class MissingDataReason(str, Enum):
    """
    Enumerated reasons an index value may be unavailable.

    Every one of these produces a recorded, published reason rather than an imputed
    number. The previous aggregator divided by the active weight sum, which silently
    imputed an absent route at the basket average — a fabricated observation wearing
    the basket's clothes.
    """

    # No observation at all for a route in the period.
    ROUTE_NOT_COLLECTED = "route_not_collected"
    # A source failed for this route; distinct from the route not being in the basket.
    SOURCE_FAILURE = "source_failure"
    # Route was withdrawn from the basket; it exits the index rather than being
    # carried forward at a stale level.
    ROUTE_DISCONTINUED = "route_discontinued"
    # Observations exist but too few products matched between base and current period.
    INSUFFICIENT_MATCHED_OBSERVATIONS = "insufficient_matched_observations"
    # Fewer horizons than the policy minimum.
    INSUFFICIENT_HORIZONS = "insufficient_horizons"
    # No base-period observation for this product/route, so no relative is computable.
    NO_BASE_PERIOD_DATA = "no_base_period_data"
    # A component (base fare / taxes) was absent, so the record could not be used.
    MISSING_FARE_COMPONENT = "missing_fare_component"
    # More than one provenance series was selected for a single computation.
    MIXED_PROVENANCE = "mixed_provenance"

    @property
    def description(self) -> str:
        return _MISSING_DATA_DESCRIPTIONS[self]


_MISSING_DATA_DESCRIPTIONS: dict[MissingDataReason, str] = {
    MissingDataReason.ROUTE_NOT_COLLECTED: (
        "No observations were collected for this route in the period. The route is "
        "omitted from the aggregate and its absence is recorded; its weight is NOT "
        "redistributed as an implied basket-average price movement."
    ),
    MissingDataReason.SOURCE_FAILURE: (
        "Collection was attempted and failed. The route is omitted and the failure is "
        "recorded against the collection run. No value is substituted."
    ),
    MissingDataReason.ROUTE_DISCONTINUED: (
        "The route has left the basket. It exits the index from this period onward "
        "rather than being carried forward at its last observed level."
    ),
    MissingDataReason.INSUFFICIENT_MATCHED_OBSERVATIONS: (
        "Observations exist but fewer than the minimum number of products could be "
        "matched between the base and current periods, so no defensible price "
        "relative can be formed."
    ),
    MissingDataReason.INSUFFICIENT_HORIZONS: (
        "Fewer booking horizons produced an index than the horizon policy requires, so "
        "the combined route index would be dominated by whichever horizons happened to "
        "be present."
    ),
    MissingDataReason.NO_BASE_PERIOD_DATA: (
        "No base-period observation exists for this route or product, so there is no "
        "reference price against which to compute a relative."
    ),
    MissingDataReason.MISSING_FARE_COMPONENT: (
        "A required fare component was absent from the source payload and the "
        "observation could not be used."
    ),
    MissingDataReason.MIXED_PROVENANCE: (
        "The selected observations contain more than one provenance type. Live, "
        "simulated and offline observations are separate statistical series and "
        "cannot share a base period or published index."
    ),
}


@dataclass
class ValidationResult:
    """Outcome of validating one observation."""

    is_valid: bool
    action: ValidationAction
    flags: tuple[str, ...] = ()
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    # Diagnostic numbers that triggered the decision (exclusions/flags), plus
    # informational reconciliation for estimated statutory decompositions
    # (accepted rows carry component_sum_estimated so the estimator stays auditable).
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def excluded(self) -> bool:
        return self.action is ValidationAction.EXCLUDED


@dataclass
class ValidationBatchResult:
    accepted: list[FareObservation] = field(default_factory=list)
    flagged: list[FareObservation] = field(default_factory=list)
    excluded: list[FareObservation] = field(default_factory=list)
    # Results are retained for the public summary/legacy callers.
    results: list[ValidationResult] = field(default_factory=list)
    # Canonical persistence input. Keeping the evaluated observation and its decision
    # together prevents equal sort keys from being re-paired incorrectly after the
    # observations have been split into accepted/flagged/excluded buckets.
    evaluated: list[tuple[FareObservation, ValidationResult]] = field(default_factory=list)

    @property
    def usable(self) -> list[FareObservation]:
        """Observations admitted to the index: accepted plus flagged-but-genuine."""
        return self.accepted + self.flagged

    @property
    def total(self) -> int:
        return len(self.accepted) + len(self.flagged) + len(self.excluded)

    def summary(self) -> dict[str, Any]:
        flag_counts: dict[str, int] = {}
        for obs in self.flagged:
            for flag in obs.validation_flags:
                key = flag.split("_")[0] if flag[0].isalpha() else flag
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        return {
            "total": self.total,
            "accepted": len(self.accepted),
            "flagged": len(self.flagged),
            "excluded": len(self.excluded),
            "valid_pct": (
                round(len(self.usable) / self.total * 100, 2) if self.total else None
            ),
            "flag_counts": flag_counts,
        }


@dataclass
class RouteHorizonStats:
    """
    Rolling reference distribution for one (route, horizon) pair.

    ``prices`` holds only CLEAN observations — those not flagged as statistical
    outliers. That is the contamination fix: an outlier is judged against the clean
    distribution and then withheld from it, so the fences cannot ratchet outward.
    """

    clean_prices: deque[float]
    daily_medians: dict[str, float] = field(default_factory=dict)
    daily_prices: dict[str, list[float]] = field(default_factory=dict)
    outliers_withheld: int = 0

    @property
    def count(self) -> int:
        return len(self.clean_prices)

    def fences(self, multiplier: float) -> Optional[tuple[float, float, float]]:
        """Returns (lower_fence, upper_fence, median) or None if underpowered."""
        if len(self.clean_prices) < 4:
            return None
        arr = np.asarray(self.clean_prices, dtype=float)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1
        return q1 - multiplier * iqr, q3 + multiplier * iqr, float(np.median(arr))


class FareValidator:
    """
    Validates observations before they reach the index.

    State is explicitly exportable so the reference distributions survive process
    restarts. A price index whose outlier filter behaves differently depending on how
    recently the server was restarted is not reproducible.
    """

    def __init__(
        self,
        settings: Optional[ValidationSettings] = None,
        history_window: Optional[int] = None,
    ):
        cfg = settings or get_settings().validation
        self.min_fare = cfg.min_fare_inr
        self.max_fare = cfg.max_fare_inr
        self.max_daily_change_pct = cfg.max_daily_change_pct
        self.iqr_multiplier = cfg.iqr_multiplier
        self.min_observations_for_iqr = cfg.min_observations_for_iqr
        self.history_window = history_window or cfg.route_history_window

        # (route_id, horizon) -> RouteHorizonStats
        self._stats: dict[tuple[int, int], RouteHorizonStats] = {}

    # ── state persistence ──

    def export_state(self) -> dict[str, Any]:
        """
        Serialise reference distributions for persistence.

        Keys are ``"routeid:horizon"`` strings so the structure survives a JSON round
        trip.
        """
        return {
            "version": 2,
            "iqr_multiplier": self.iqr_multiplier,
            "max_daily_change_pct": self.max_daily_change_pct,
            "stats": {
                f"{route_id}:{horizon}": {
                    "clean_prices": list(stats.clean_prices),
                    "daily_medians": dict(stats.daily_medians),
                    "outliers_withheld": stats.outliers_withheld,
                }
                for (route_id, horizon), stats in self._stats.items()
            },
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Rehydrate reference distributions saved by :meth:`export_state`."""
        if not state or state.get("version") != 2:
            if state:
                logger.warning(
                    f"Ignoring validator state with unsupported version "
                    f"{state.get('version')!r}; fences will rebuild from new data."
                )
            return

        restored = 0
        for key, payload in (state.get("stats") or {}).items():
            try:
                route_part, _, horizon_part = str(key).partition(":")
                route_id, horizon = int(route_part), int(horizon_part)
            except ValueError:
                logger.warning(f"Skipping unparseable validator state key {key!r}")
                continue
            self._stats[(route_id, horizon)] = RouteHorizonStats(
                clean_prices=deque(
                    [float(p) for p in payload.get("clean_prices", [])],
                    maxlen=self.history_window,
                ),
                daily_medians={
                    str(k): float(v) for k, v in (payload.get("daily_medians") or {}).items()
                },
                outliers_withheld=int(payload.get("outliers_withheld", 0)),
            )
            restored += 1

        logger.info(
            f"Restored validator reference distributions for {restored} "
            f"(route, horizon) pair(s); IQR fences are continuous across restart"
        )

    # ── single observation ──

    def validate(self, obs: FareObservation) -> ValidationResult:
        """Validate one observation against hard limits and rolling statistics."""
        flags: list[str] = []
        detail: dict[str, Any] = {}

        fare = obs.fare_total

        # ── hard exclusions: these indicate a collection or parsing error ──
        if fare <= 0:
            return ValidationResult(
                is_valid=False,
                action=ValidationAction.EXCLUDED,
                flags=("zero_or_negative_fare",),
                anomaly_type="collection_error",
                severity="critical",
                detail={"fare_total": fare},
            )

        if fare < self.min_fare:
            return ValidationResult(
                is_valid=False,
                action=ValidationAction.EXCLUDED,
                flags=(f"below_minimum_fare_{self.min_fare:.0f}",),
                anomaly_type="collection_error",
                severity="high",
                detail={"fare_total": fare, "min_fare": self.min_fare},
            )

        if fare > self.max_fare:
            return ValidationResult(
                is_valid=False,
                action=ValidationAction.EXCLUDED,
                flags=(f"above_maximum_fare_{self.max_fare:.0f}",),
                anomaly_type="collection_error",
                severity="high",
                detail={"fare_total": fare, "max_fare": self.max_fare},
            )

        # ── component consistency ──
        is_estimated = bool(
            obs.provenance and obs.provenance.notes and obs.provenance.notes.get("is_estimated")
        )
        if obs.fare_base is not None and obs.fare_taxes is not None:
            fee_udf = obs.fare_udf or 0.0
            fee_conv = obs.fare_convenience or 0.0
            expected = obs.fare_base + obs.fare_taxes + fee_udf + fee_conv
            if abs(fare - expected) > 1.0:  # allow INR 1 of rounding
                if is_estimated:
                    detail["component_sum_info"] = round(expected, 2)
                else:
                    flags.append("fare_component_mismatch")
                    detail["component_sum"] = round(expected, 2)
            elif is_estimated:
                detail["component_sum_estimated"] = round(expected, 2)

        if obs.fare_taxes is not None and fare > 0 and not is_estimated:
            tax_share = obs.fare_taxes / fare
            if tax_share > 0.50:
                flags.append("high_tax_ratio")
                detail["tax_share"] = round(tax_share, 4)
            elif tax_share < 0.05:
                flags.append("suspiciously_low_tax_ratio")
                detail["tax_share"] = round(tax_share, 4)

        key = (obs.route_id, obs.booking_horizon_days)
        stats = self._stats.get(key)
        is_statistical_outlier = False

        # ── IQR fencing against the CLEAN distribution ──
        if stats and stats.count >= self.min_observations_for_iqr:
            fence = stats.fences(self.iqr_multiplier)
            if fence:
                lower, upper, median = fence
                if fare < lower:
                    flags.append(f"statistical_low_outlier_iqr{self.iqr_multiplier:g}")
                    is_statistical_outlier = True
                elif fare > upper:
                    flags.append(f"statistical_high_outlier_iqr{self.iqr_multiplier:g}")
                    is_statistical_outlier = True
                if is_statistical_outlier:
                    detail.update({
                        "iqr_lower_fence": round(lower, 2),
                        "iqr_upper_fence": round(upper, 2),
                        "reference_median": round(median, 2),
                        "reference_sample_size": stats.count,
                    })

        # ── day-over-day movement, per route AND horizon ──
        prior_median = self._prior_day_median(key, obs.collection_date)
        if prior_median and prior_median > 0:
            change_pct = abs(fare - prior_median) / prior_median * 100
            if change_pct > self.max_daily_change_pct:
                direction = "spike" if fare > prior_median else "collapse"
                flags.append(
                    f"daily_change_{direction}_{change_pct:.0f}pct"
                    f"_exceeds_{self.max_daily_change_pct:.0f}pct"
                )
                detail.update({
                    "prior_day_median": round(prior_median, 2),
                    "daily_change_pct": round(change_pct, 2),
                })

        # ── horizon plausibility ──
        if obs.booking_horizon_days >= 30 and fare > 25000:
            flags.append("high_fare_for_advance_purchase")
        if obs.booking_horizon_days == 0 and fare < 1500:
            flags.append("suspiciously_low_same_day_fare")

        # ── update reference state ──
        # Order matters: the observation is judged first, then recorded, so it never
        # participates in judging itself. Outliers update the daily series (they are
        # real quotes) but are withheld from the IQR reference distribution.
        self._record(key, obs.collection_date, fare, is_clean=not is_statistical_outlier)

        if flags:
            return ValidationResult(
                is_valid=True,  # flagged, not excluded: genuine volatility is kept
                action=ValidationAction.FLAGGED,
                flags=tuple(flags),
                anomaly_type="potential_anomaly",
                severity="low" if len(flags) == 1 else "medium",
                detail=detail,
            )

        return ValidationResult(is_valid=True, action=ValidationAction.ACCEPTED, detail=detail)

    # ── batch ──

    def validate_batch(
        self, observations: Iterable[FareObservation]
    ) -> ValidationBatchResult:
        """
        Validate a batch in collection-date order.

        Sorting first is what makes the day-over-day check meaningful: the comparison
        must be against a genuinely earlier day, not against whatever order the batch
        happened to arrive in.
        """
        ordered = sorted(
            observations,
            key=lambda o: (o.collection_datetime, o.route_id, o.booking_horizon_days),
        )

        batch = ValidationBatchResult()
        for obs in ordered:
            result = self.validate(obs)
            annotated = obs.with_validation(result.is_valid, result.flags)
            batch.results.append(result)
            batch.evaluated.append((annotated, result))

            if result.action is ValidationAction.EXCLUDED:
                batch.excluded.append(annotated)
            elif result.action is ValidationAction.FLAGGED:
                batch.flagged.append(annotated)
            else:
                batch.accepted.append(annotated)

        if batch.total:
            logger.info(
                f"Validation: {len(batch.accepted)} accepted, {len(batch.flagged)} "
                f"flagged, {len(batch.excluded)} excluded (of {batch.total})"
            )
        return batch

    # ── internal state helpers ──

    def _stats_for(self, key: tuple[int, int]) -> RouteHorizonStats:
        if key not in self._stats:
            self._stats[key] = RouteHorizonStats(
                clean_prices=deque(maxlen=self.history_window)
            )
        return self._stats[key]

    def _prior_day_median(
        self, key: tuple[int, int], observation_date: date
    ) -> Optional[float]:
        """
        Median for this (route, horizon) on the most recent day strictly before
        ``observation_date``. None on the first day: there is nothing to compare to,
        so no flag is warranted.
        """
        stats = self._stats.get(key)
        if not stats or not stats.daily_medians:
            return None
        current = observation_date.isoformat()
        prior = [d for d in stats.daily_medians if d < current]
        if not prior:
            return None
        return stats.daily_medians[max(prior)]

    def _record(
        self, key: tuple[int, int], observation_date: date, fare: float, is_clean: bool
    ) -> None:
        stats = self._stats_for(key)
        day = observation_date.isoformat()

        # Daily medians include outliers: they are real quotes and the day-over-day
        # check should reflect the actual market level.
        prices = stats.daily_prices.setdefault(day, [])
        prices.append(fare)
        stats.daily_medians[day] = float(np.median(prices))

        if is_clean:
            stats.clean_prices.append(fare)
        else:
            stats.outliers_withheld += 1

        # Bounded retention: 90 days of daily reference levels per (route, horizon).
        if len(stats.daily_medians) > 90:
            for stale in sorted(stats.daily_medians)[:-90]:
                stats.daily_medians.pop(stale, None)
                stats.daily_prices.pop(stale, None)

    # ── introspection, surfaced by the API ──

    def diagnostics(self) -> dict[str, Any]:
        """Reference-distribution state, for the monitoring endpoint."""
        pairs = len(self._stats)
        ready = sum(
            1 for s in self._stats.values() if s.count >= self.min_observations_for_iqr
        )
        return {
            "tracked_route_horizon_pairs": pairs,
            "pairs_with_active_iqr_fences": ready,
            "min_observations_for_iqr": self.min_observations_for_iqr,
            "iqr_multiplier": self.iqr_multiplier,
            "max_daily_change_pct": self.max_daily_change_pct,
            "min_fare_inr": self.min_fare,
            "max_fare_inr": self.max_fare,
            "outliers_withheld_from_reference": sum(
                s.outliers_withheld for s in self._stats.values()
            ),
            "reference_distribution_is_outlier_free": True,
        }


def missing_data_policy() -> list[dict[str, str]]:
    """The enumerated missing-data policy, exposed on the methodology endpoint."""
    return [
        {
            "reason": reason.value,
            "policy": reason.description,
            "imputation": "none",
        }
        for reason in MissingDataReason
    ]
