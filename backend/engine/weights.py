"""
SIH26056 — Route basket and weight derivation.

The ONE authoritative route-weight calculation. Weights are always derived from
``data/route_basket.json``:

    w_r = pax_r / sum_k(pax_k)

so they sum to exactly 1.0 by construction and cannot disagree with a second copy
kept in SQL, Python constants, frontend mock data, or the README. Those copies have
been removed; ``backend/database/seed_routes.sql`` is generated from this file (see
``scripts/generate_seed_sql.py``) and the README table is generated too.

Honesty note carried through to the API: passenger-volume weighting is a
**provisional** methodology, not an official CPI expenditure share. Every response
that exposes weights also exposes ``status`` and ``label`` from the basket file so a
consumer cannot mistake it for one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from loguru import logger


@dataclass(frozen=True)
class Route:
    """A city-pair in the basket, with its derived weight."""

    route_id: int
    origin_code: str
    destination_code: str
    origin_city: str
    destination_city: str
    monthly_pax: int
    weight: float
    is_active: bool = True

    @property
    def route_code(self) -> str:
        return f"{self.origin_code}-{self.destination_code}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "origin_code": self.origin_code,
            "destination_code": self.destination_code,
            "origin_city": self.origin_city,
            "destination_city": self.destination_city,
            "route_code": self.route_code,
            "monthly_pax": self.monthly_pax,
            "weight": self.weight,
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class WeightingMethodology:
    """Documented provenance of the weighting scheme itself."""

    method: str
    status: str
    formula: str
    label: str
    is_official_cpi_expenditure_weight: bool
    rationale: list[str] = field(default_factory=list)
    upgrade_path: str = ""
    source_note: str = ""
    review_policy: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "status": self.status,
            "formula": self.formula,
            "label": self.label,
            "is_official_cpi_expenditure_weight": self.is_official_cpi_expenditure_weight,
            "rationale": list(self.rationale),
            "upgrade_path": self.upgrade_path,
            "source_note": self.source_note,
            "review_policy": self.review_policy,
        }


@dataclass(frozen=True)
class RouteBasket:
    """The complete basket: routes with derived weights plus methodology metadata."""

    basket_id: str
    basket_version: str
    effective_from: str
    currency: str
    routes: tuple[Route, ...]
    methodology: WeightingMethodology

    @property
    def total_pax(self) -> int:
        return sum(r.monthly_pax for r in self.routes)

    @property
    def weight_sum(self) -> float:
        return sum(r.weight for r in self.routes)

    def by_id(self, route_id: int) -> Optional[Route]:
        return next((r for r in self.routes if r.route_id == route_id), None)

    def by_code(self, route_code: str) -> Optional[Route]:
        wanted = route_code.replace("_", "-").upper()
        return next((r for r in self.routes if r.route_code == wanted), None)

    def get_or_dynamic(
        self,
        route_id: Optional[int] = None,
        origin_code: Optional[str] = None,
        destination_code: Optional[str] = None,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
    ) -> Route:
        """Find a route in the basket, or construct a dynamic Route definition."""
        if route_id is not None:
            found = self.by_id(route_id)
            if found:
                return found
        if origin_code and destination_code:
            code = f"{origin_code.upper()}-{destination_code.upper()}"
            found = self.by_code(code)
            if found:
                return found
            r_id = route_id or dynamic_route_id(origin_code, destination_code)
            return Route(
                route_id=r_id,
                origin_code=origin_code.upper(),
                destination_code=destination_code.upper(),
                origin_city=origin_city or origin_code.upper(),
                destination_city=destination_city or destination_code.upper(),
                monthly_pax=100000,
                weight=0.0,
                is_active=True,
            )
        raise ValueError("Either route_id or (origin_code, destination_code) required")

    def weight_map(self) -> dict[int, float]:
        return {r.route_id: r.weight for r in self.routes}

    def to_dict(self) -> dict[str, Any]:
        return {
            "basket_id": self.basket_id,
            "basket_version": self.basket_version,
            "effective_from": self.effective_from,
            "currency": self.currency,
            "total_routes": len(self.routes),
            "total_monthly_pax": self.total_pax,
            "weight_sum": self.weight_sum,
            "weighting_methodology": self.methodology.to_dict(),
            "routes": [r.to_dict() for r in self.routes],
        }


def dynamic_route_id(origin_code: str, destination_code: str) -> int:
    """Deterministic route_id for arbitrary city pairs (outside 1..25 basket)."""
    import zlib
    key = f"{origin_code.strip().upper()}-{destination_code.strip().upper()}"
    return 1000 + (zlib.crc32(key.encode("utf-8")) % 900000)



class RouteBasketError(RuntimeError):
    """Raised when the basket file is missing or internally inconsistent."""


def derive_weights(pax_by_route: dict[int, int]) -> dict[int, float]:
    """
    The weight formula, isolated so it can be tested directly.

    Raises rather than returning degenerate weights when total volume is zero: a
    silently-uniform basket would be a fabricated weighting scheme.
    """
    total = sum(pax_by_route.values())
    if total <= 0:
        raise RouteBasketError(
            "Cannot derive route weights: total passenger volume is zero. "
            "Weights must come from real volumes, not a uniform fallback."
        )
    return {route_id: pax / total for route_id, pax in pax_by_route.items()}


def load_route_basket(path: Path) -> RouteBasket:
    """Load and validate the basket, deriving weights from passenger volumes."""
    if not path.exists():
        raise RouteBasketError(
            f"Route basket file not found: {path}. This file is the single source of "
            f"truth for route weights and has no built-in fallback."
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RouteBasketError(f"Route basket file {path} is not valid JSON: {exc}") from exc

    entries = raw.get("routes") or []
    if not entries:
        raise RouteBasketError(f"Route basket file {path} defines no routes")

    route_ids = [e["route_id"] for e in entries]
    if len(set(route_ids)) != len(route_ids):
        raise RouteBasketError(f"Route basket file {path} contains duplicate route_ids")

    pax_by_route = {int(e["route_id"]): int(e["monthly_pax"]) for e in entries}
    weights = derive_weights(pax_by_route)

    routes = tuple(
        Route(
            route_id=int(e["route_id"]),
            origin_code=str(e["origin_code"]).upper(),
            destination_code=str(e["destination_code"]).upper(),
            origin_city=str(e.get("origin_city", "")),
            destination_city=str(e.get("destination_city", "")),
            monthly_pax=int(e["monthly_pax"]),
            weight=weights[int(e["route_id"])],
            is_active=bool(e.get("is_active", True)),
        )
        for e in sorted(entries, key=lambda e: int(e["route_id"]))
    )

    w = raw.get("weighting") or {}
    methodology = WeightingMethodology(
        method=w.get("method", "passenger_volume"),
        status=w.get("status", "PROVISIONAL"),
        formula=w.get("formula", "w_r = pax_r / sum_k(pax_k)"),
        label=w.get("label", "Provisional passenger-volume weights"),
        is_official_cpi_expenditure_weight=bool(
            w.get("is_official_cpi_expenditure_weight", False)
        ),
        rationale=list(w.get("rationale") or []),
        upgrade_path=w.get("upgrade_path", ""),
        source_note=w.get("source_note", ""),
        review_policy=w.get("review_policy", ""),
    )

    basket = RouteBasket(
        basket_id=raw.get("basket_id", "unknown"),
        basket_version=raw.get("basket_version", "0.0.0"),
        effective_from=raw.get("effective_from", ""),
        currency=raw.get("currency", "INR"),
        routes=routes,
        methodology=methodology,
    )

    # Hard invariant: weights sum to 1. A violation is a bug, not a warning.
    if abs(basket.weight_sum - 1.0) > 1e-9:
        raise RouteBasketError(
            f"Derived route weights sum to {basket.weight_sum!r}, expected 1.0. "
            f"This indicates a defect in weight derivation."
        )

    logger.info(
        f"Route basket {basket.basket_id} v{basket.basket_version}: "
        f"{len(routes)} routes, {basket.total_pax:,} monthly pax, "
        f"weights sum to {basket.weight_sum:.12f} "
        f"({methodology.status} {methodology.method} weighting)"
    )
    return basket


@lru_cache(maxsize=4)
def get_route_basket(path: Optional[Path] = None) -> RouteBasket:
    """Cached basket accessor. Pass an explicit path in tests."""
    if path is None:
        from config import get_settings

        path = get_settings().route_basket_path
    return load_route_basket(Path(path))


def clear_basket_cache() -> None:
    get_route_basket.cache_clear()
