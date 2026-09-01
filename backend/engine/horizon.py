"""
SIH26056 — Booking-horizon stratification.

The most consequential methodological property of this index. Advance-purchase
horizons are modelled SEPARATELY and then combined with fixed, documented weights:

    route
      +-- T+0   -> I_r,0(t)
      +-- T+3   -> I_r,3(t)
      +-- T+7   -> I_r,7(t)
      +-- T+15  -> I_r,15(t)
      +-- T+30  -> I_r,30(t)

    I_r(t) = sum_h ( alpha_h * I_r,h(t) )      with sum_h alpha_h = 1

Why this matters
----------------
A same-day fare sits at a structurally higher LEVEL than a 30-day-advance fare.
If observations from all horizons are pooled into one elementary aggregate (the
previous behaviour), the resulting index moves whenever the horizon MIX of the
sample changes, even with every underlying price held constant. That is a
composition artefact being reported as inflation.

Stratifying fixes it: each horizon is indexed against its own base level, so the
level difference between horizons cancels, and the combining weights alpha_h are
fixed by policy rather than by how many observations each horizon contributed.
``test_horizons.py`` pins this property directly.

The weights come from ``data/booking_horizons.json`` and are NOT the simulator's
price multipliers — those are generator calibration parameters and using them as
weights would make the index recover the generator's own configuration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class HorizonPolicyError(RuntimeError):
    """Raised when the horizon policy file is missing or inconsistent."""


@dataclass(frozen=True)
class HorizonDefinition:
    days: int
    label: str
    name: str
    description: str
    advance_purchase_category: str
    statistical_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "days": self.days,
            "label": self.label,
            "name": self.name,
            "description": self.description,
            "advance_purchase_category": self.advance_purchase_category,
            "statistical_rationale": self.statistical_rationale,
        }


@dataclass(frozen=True)
class HorizonWeighting:
    method: str
    status: str
    formula: str
    weights: dict[int, float]
    is_official_cpi_weight: bool
    why: list[str] = field(default_factory=list)
    renormalization_policy: str = ""
    upgrade_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "status": self.status,
            "formula": self.formula,
            "weights": {f"T+{k}": v for k, v in sorted(self.weights.items())},
            "is_official_cpi_weight": self.is_official_cpi_weight,
            "why": list(self.why),
            "renormalization_policy": self.renormalization_policy,
            "upgrade_path": self.upgrade_path,
        }


@dataclass(frozen=True)
class HorizonPolicy:
    policy_id: str
    policy_version: str
    horizons: tuple[HorizonDefinition, ...]
    weighting: HorizonWeighting
    min_horizons_for_route_index: int
    min_matched_products_per_horizon: int

    @property
    def horizon_days(self) -> list[int]:
        return [h.days for h in self.horizons]

    def definition(self, days: int) -> Optional[HorizonDefinition]:
        return next((h for h in self.horizons if h.days == days), None)

    def label(self, days: int) -> str:
        d = self.definition(days)
        return d.label if d else f"T+{days}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "horizons": [h.to_dict() for h in self.horizons],
            "weighting": self.weighting.to_dict(),
            "requirements": {
                "min_horizons_for_route_index": self.min_horizons_for_route_index,
                "min_matched_products_per_horizon": self.min_matched_products_per_horizon,
            },
        }


def load_horizon_policy(path: Path) -> HorizonPolicy:
    if not path.exists():
        raise HorizonPolicyError(
            f"Horizon policy file not found: {path}. Horizon weights have no built-in "
            f"fallback: an undocumented weighting is not acceptable in an index."
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HorizonPolicyError(f"{path} is not valid JSON: {exc}") from exc

    entries = raw.get("horizons") or []
    if not entries:
        raise HorizonPolicyError(f"{path} defines no horizons")

    horizons = tuple(
        HorizonDefinition(
            days=int(e["days"]),
            label=e.get("label", f"T+{e['days']}"),
            name=e.get("name", ""),
            description=e.get("description", ""),
            advance_purchase_category=e.get("advance_purchase_category", ""),
            statistical_rationale=e.get("statistical_rationale", ""),
        )
        for e in sorted(entries, key=lambda e: int(e["days"]))
    )

    w = raw.get("weighting") or {}
    declared = {int(k): float(v) for k, v in (w.get("weights") or {}).items()}

    if not declared:
        # Equal weighting is the documented default, but it is materialised
        # explicitly rather than left implicit.
        declared = {h.days: 1.0 / len(horizons) for h in horizons}
        logger.warning(
            f"{path} declares no explicit horizon weights; materialising equal weights"
        )

    missing = set(h.days for h in horizons) - set(declared)
    if missing:
        raise HorizonPolicyError(
            f"{path}: horizons {sorted(missing)} have no declared weight. Every "
            f"collected horizon must have an explicit weight."
        )

    total = sum(declared.values())
    if abs(total - 1.0) > 1e-9:
        raise HorizonPolicyError(
            f"{path}: horizon weights sum to {total}, expected 1.0"
        )

    weighting = HorizonWeighting(
        method=w.get("method", "equal"),
        status=w.get("status", "PROVISIONAL"),
        formula=w.get("formula", "alpha_h = 1 / H"),
        weights=declared,
        is_official_cpi_weight=bool(w.get("is_official_cpi_weight", False)),
        why=list(w.get("why_equal") or w.get("why") or []),
        renormalization_policy=w.get("renormalization_policy", ""),
        upgrade_path=w.get("upgrade_path", ""),
    )

    reqs = raw.get("requirements") or {}
    policy = HorizonPolicy(
        policy_id=raw.get("policy_id", "unknown"),
        policy_version=raw.get("policy_version", "0.0.0"),
        horizons=horizons,
        weighting=weighting,
        min_horizons_for_route_index=int(reqs.get("min_horizons_for_route_index", 2)),
        min_matched_products_per_horizon=int(
            reqs.get("min_matched_products_per_horizon", 3)
        ),
    )

    logger.info(
        f"Horizon policy {policy.policy_id} v{policy.policy_version}: "
        f"{[h.label for h in horizons]} with {weighting.method} weighting "
        f"({weighting.status})"
    )
    return policy


@lru_cache(maxsize=4)
def get_horizon_policy(path: Optional[Path] = None) -> HorizonPolicy:
    if path is None:
        from config import get_settings

        path = get_settings().horizon_policy_path
    return load_horizon_policy(Path(path))


def clear_policy_cache() -> None:
    get_horizon_policy.cache_clear()


# ── combination ──

@dataclass
class HorizonIndexInput:
    """One horizon's computed index for a single route and period."""

    booking_horizon: int
    index_value: float          # ratio form, 1.0 == base
    matched_products: int
    observation_count: int


@dataclass
class CombinedRouteIndex:
    """
    Route index built from horizon-specific indices.

    ``applied_weights`` records the weights actually used after renormalization, so
    a published figure can be reproduced exactly even if a horizon was missing.
    """

    route_id: int
    index_value: float
    horizons_included: list[int]
    horizons_missing: list[int]
    applied_weights: dict[int, float]
    total_matched_products: int
    total_observations: int
    weighting_method: str
    weighting_status: str
    policy_version: str
    is_publishable: bool
    suppression_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "index_value": self.index_value,
            "horizons_included": list(self.horizons_included),
            "horizons_missing": list(self.horizons_missing),
            "applied_weights": {f"T+{k}": v for k, v in sorted(self.applied_weights.items())},
            "total_matched_products": self.total_matched_products,
            "total_observations": self.total_observations,
            "weighting_method": self.weighting_method,
            "weighting_status": self.weighting_status,
            "horizon_policy_version": self.policy_version,
            "is_publishable": self.is_publishable,
            "suppression_reason": self.suppression_reason,
        }


def combine_horizon_indices(
    route_id: int,
    horizon_indices: list[HorizonIndexInput],
    policy: HorizonPolicy,
) -> CombinedRouteIndex:
    """
    Combine horizon indices into a route index using the policy weights.

    Composition stability is the point: ``applied_weights`` depends only on WHICH
    horizons are present, never on how many observations each contributed. Two
    samples with identical matched prices but wildly different horizon observation
    counts therefore produce the identical route index.

    A horizon with too few matched products is treated as missing rather than being
    silently included with a noisy index.
    """
    all_days = set(policy.horizon_days)

    usable = [
        h for h in horizon_indices
        if h.booking_horizon in all_days
        and h.matched_products >= policy.min_matched_products_per_horizon
        and h.index_value > 0
    ]

    included = sorted(h.booking_horizon for h in usable)
    missing = sorted(all_days - set(included))

    if len(included) < policy.min_horizons_for_route_index:
        return CombinedRouteIndex(
            route_id=route_id,
            index_value=0.0,
            horizons_included=included,
            horizons_missing=missing,
            applied_weights={},
            total_matched_products=sum(h.matched_products for h in usable),
            total_observations=sum(h.observation_count for h in usable),
            weighting_method=policy.weighting.method,
            weighting_status=policy.weighting.status,
            policy_version=policy.policy_version,
            is_publishable=False,
            suppression_reason=(
                f"insufficient_horizons: {len(included)} of "
                f"{policy.min_horizons_for_route_index} required"
            ),
        )

    # Renormalize the declared weights across present horizons only.
    declared = policy.weighting.weights
    present_total = sum(declared[d] for d in included)
    if present_total <= 0:
        raise HorizonPolicyError(
            f"Route {route_id}: present horizons {included} carry zero total weight"
        )
    applied = {d: declared[d] / present_total for d in included}

    index_value = sum(
        applied[h.booking_horizon] * h.index_value for h in usable
    )

    return CombinedRouteIndex(
        route_id=route_id,
        index_value=float(index_value),
        horizons_included=included,
        horizons_missing=missing,
        applied_weights=applied,
        total_matched_products=sum(h.matched_products for h in usable),
        total_observations=sum(h.observation_count for h in usable),
        weighting_method=policy.weighting.method,
        weighting_status=policy.weighting.status,
        policy_version=policy.policy_version,
        is_publishable=True,
        suppression_reason=None,
    )
