"""
SIH26056 — Response serialization.

One place builds the provenance envelope that every index response carries, so the
API contract cannot drift between endpoints and no endpoint can accidentally omit the
label that tells a consumer whether a number is measured or simulated.

Required envelope on every index response:

    value, base_period, data_provenance, sample_size, methodology_version

plus the honest display label and, where relevant, uncertainty and publishability.
"""

from __future__ import annotations

from typing import Any, Optional

from db.models import (
    Anomaly,
    CollectionRun,
    FareObservationRecord,
    HorizonIndex,
    IndexRevision,
    NationalIndex,
    RouteIndex,
    Source,
)
from db.repository import VALIDATION_RULES_VERSION
from provenance import (
    METHODOLOGY_VERSION,
    NOT_IMPLEMENTED_LABEL,
    PROVENANCE_LABELS,
    SOURCE_UNAVAILABLE_LABEL,
    AcquisitionMethod,
    SourceType,
    resolve_display_label,
)


def provenance_block(
    source_type: Optional[str],
    acquisition_method: Optional[str] = None,
    *,
    is_live_data: Optional[bool] = None,
) -> dict[str, Any]:
    """
    The provenance envelope fragment.

    ``display_label`` is the exact string a UI must render. There is no code path that
    yields a data label when there is no data.
    """
    if not source_type:
        return {
            "source_type": None,
            "acquisition_method": None,
            "display_label": SOURCE_UNAVAILABLE_LABEL,
            "is_live_data": False,
            "is_official_statistic": False,
        }

    st = SourceType(source_type)
    acq = AcquisitionMethod(acquisition_method) if acquisition_method else None
    display_label = resolve_display_label(st, acq)
    return {
        "source_type": st.value,
        "acquisition_method": acq.value if acq else None,
        "display_label": display_label,
        "is_live_data": st.is_real if is_live_data is None else bool(is_live_data),
        # Constant False. This project is not authorized to publish official
        # statistics, and the API says so on every response rather than leaving it to
        # a footnote a consumer may not read.
        "is_official_statistic": False,
    }


def uncertainty_block(row) -> dict[str, Any]:
    """
    Uncertainty fragment. All-null with a basis string when not estimable.

    Never synthesised: a confidence interval is a claim about a sampling
    distribution, and inventing one is worse than reporting none because it looks
    like rigour.
    """
    return {
        "standard_error": _round(row.standard_error, 6),
        "confidence_interval_low": _round(row.confidence_interval_low, 4),
        "confidence_interval_high": _round(row.confidence_interval_high, 4),
        "confidence_level": 0.95 if row.standard_error is not None else None,
        "is_estimable": row.standard_error is not None,
        "basis": row.uncertainty_basis,
    }


# ── national index ──

def national_index(row: NationalIndex) -> dict[str, Any]:
    """Serialize a national index row with the full envelope."""
    return {
        # ── required envelope ──
        "value": _round(row.index_value, 4),
        "base_period": row.base_period_label,
        "data_provenance": provenance_block(row.source_type, getattr(row, "acquisition_method", None)),
        "sample_size": row.total_observations,
        "methodology_version": row.methodology_version,
        # ── identity ──
        "index_date": row.index_date.isoformat(),
        "booking_horizon": row.booking_horizon,
        "is_headline": row.booking_horizon is None,
        # ── changes, with explicit statuses so null is never ambiguous ──
        "mom_change_pct": _round(row.mom_change_pct, 4),
        "mom_status": row.mom_status,
        "yoy_change_pct": _round(row.yoy_change_pct, 4),
        "yoy_status": row.yoy_status,
        # ── coverage and publishability ──
        "routes_included": row.routes_included,
        "routes_in_basket": row.routes_in_basket,
        "matched_products": row.total_matched_products,
        "coverage_weight": _round(row.coverage_weight, 6),
        "renormalization_applied": row.renormalization_applied,
        "is_publishable": row.is_publishable,
        "suppression_reason": row.suppression_reason,
        # ── methodology disclosure ──
        "uncertainty": uncertainty_block(row),
        "seasonal_adjustment": row.seasonal_adjustment,
        "series_type": "observed (not seasonally adjusted)",
        "base_period_start": row.base_period_start.isoformat(),
        "base_period_end": row.base_period_end.isoformat(),
        "weighting": {
            "basket_id": row.weight_basket_id,
            "basket_version": row.weight_basket_version,
            "method": row.weighting_method,
            "status": row.weighting_status,
            "is_official_cpi_expenditure_weight": False,
        },
        "validation_rules_version": row.validation_rules_version,
        "computed_at": _iso(row.computed_at),
        "missing_routes": list(row.missing_routes or []),
    }


def national_index_summary(row: NationalIndex) -> dict[str, Any]:
    """Compact form for history series."""
    return {
        "index_date": row.index_date.isoformat(),
        "value": _round(row.index_value, 4),
        "mom_change_pct": _round(row.mom_change_pct, 4),
        "mom_status": row.mom_status,
        "yoy_change_pct": _round(row.yoy_change_pct, 4),
        "yoy_status": row.yoy_status,
        "sample_size": row.total_observations,
        "coverage_weight": _round(row.coverage_weight, 6),
        "is_publishable": row.is_publishable,
        "standard_error": _round(row.standard_error, 6),
        "source_type": row.source_type,
        "acquisition_method": getattr(row, "acquisition_method", None),
    }


def national_index_with_contributions(row: NationalIndex) -> dict[str, Any]:
    payload = national_index(row)
    payload["route_contributions"] = list(row.route_contributions or [])
    return payload


# ── route and horizon indices ──

def route_index(row: RouteIndex, route: Optional[Any] = None) -> dict[str, Any]:
    payload = {
        "value": _round(row.index_100, 4),
        "index_ratio": _round(row.index_value, 6),
        "base_period": f"{row.base_period_start.isoformat()} to {row.base_period_end.isoformat()}",
        "data_provenance": provenance_block(row.source_type, getattr(row, "acquisition_method", None)),
        "sample_size": row.observation_count,
        "methodology_version": row.methodology_version,
        "route_id": row.route_id,
        "index_date": row.index_date.isoformat(),
        "matched_products": row.matched_products,
        "horizon_stratification": {
            "horizons_included": list(row.horizons_included or []),
            "horizons_missing": list(row.horizons_missing or []),
            "applied_weights": dict(row.applied_horizon_weights or {}),
            "weighting_method": row.horizon_weighting_method,
            "weighting_status": row.horizon_weighting_status,
            "policy_version": row.horizon_policy_version,
        },
        "uncertainty": uncertainty_block(row),
        "is_publishable": row.is_publishable,
        "suppression_reason": row.suppression_reason,
        "computed_at": _iso(row.computed_at),
    }
    if route is not None:
        payload.update({
            "origin_code": route.origin_code,
            "destination_code": route.destination_code,
            "route_code": route.route_code,
            "origin_city": route.origin_city,
            "destination_city": route.destination_city,
            "weight": _round(route.weight, 6),
            "monthly_pax": route.monthly_pax,
        })
    return payload


def horizon_index(row: HorizonIndex) -> dict[str, Any]:
    return {
        "value": _round(row.index_100, 4),
        "index_ratio": _round(row.index_value, 6),
        "base_period": f"{row.base_period_start.isoformat()} to {row.base_period_end.isoformat()}",
        "data_provenance": provenance_block(row.source_type, getattr(row, "acquisition_method", None)),
        "sample_size": row.observation_count,
        "methodology_version": row.methodology_version,
        "route_id": row.route_id,
        "booking_horizon": row.booking_horizon,
        "horizon_label": f"T+{row.booking_horizon}",
        "index_date": row.index_date.isoformat(),
        "matched_products": row.matched_products,
        "geometric_mean_price_inr": _round(float(row.geometric_mean_price), 2),
        "base_geometric_mean_price_inr": _round(float(row.base_geometric_mean_price), 2),
        "product_churn": {
            "base_products": row.base_products,
            "current_products": row.current_products,
            "new_products": row.new_products,
            "disappeared_products": row.disappeared_products,
            "reappeared_products": row.reappeared_products,
            "match_rate": _round(row.match_rate, 4),
        },
        "uncertainty": uncertainty_block(row),
        "computed_at": _iso(row.computed_at),
    }


# ── observations ──

def fare_observation(row: FareObservationRecord) -> dict[str, Any]:
    """
    Serialize a stored observation.

    Provenance is included on every record, so a consumer inspecting raw data can see
    per-row whether it was collected, simulated, or replayed.
    """
    return {
        "observation_id": row.id,
        "route_id": row.route_id,
        "origin_code": row.origin_code,
        "destination_code": row.destination_code,
        "route_code": f"{row.origin_code}-{row.destination_code}",
        "departure_date": row.departure_date.isoformat(),
        "collection_datetime": _iso(row.collection_timestamp),
        "collection_date": row.collection_date.isoformat(),
        "booking_horizon_days": row.booking_horizon_days,
        "airline_code": row.airline_code,
        "airline_name": row.airline_name,
        "flight_number": row.flight_number,
        "cabin_class": row.cabin_class,
        "fare_family": row.fare_family,
        "fare_total": _round(float(row.fare_total), 2),
        "fare_base": _round(float(row.fare_base), 2) if row.fare_base is not None else None,
        "fare_taxes": _round(float(row.fare_taxes), 2) if row.fare_taxes is not None else None,
        "fare_udf": _round(float(row.fare_udf), 2) if getattr(row, "fare_udf", None) is not None else None,
        "fare_convenience": _round(float(row.fare_convenience), 2) if getattr(row, "fare_convenience", None) is not None else None,
        "dep_time": getattr(row, "dep_time", None),
        "dep_time_band": getattr(row, "dep_time_band", None),
        "currency": row.currency,
        "stops": row.stops,
        "is_direct": row.stops == 0,
        "is_refundable": row.is_refundable,
        "baggage_kg": row.baggage_kg,
        "seats_available": row.seats_available,
        "product_key": row.product_key,
        "data_provenance": {
            **provenance_block(row.source_type, getattr(row, "acquisition_method", None)),
            "source_name": row.source_name,
            "request_id": row.request_id,
            "collector_version": row.collector_version,
            "source_url": row.source_url,
            "raw_payload_hash": row.raw_payload_hash,
            "source_currency": row.source_currency,
            "source_fare_total": (
                _round(float(row.source_fare_total), 2)
                if row.source_fare_total is not None
                else None
            ),
        },
        "validation": {
            "is_valid": row.is_valid,
            "action": row.validation_action,
            "flags": list(row.validation_flags or []),
        },
    }


# ── collection runs ──

def collection_run(row: CollectionRun, include_attempts: bool = False) -> dict[str, Any]:
    payload = {
        "run_id": row.run_id,
        "mode": row.mode,
        "status": row.status,
        "display_label": row.display_label,
        "data_provenance": provenance_block(
            row.source_type,
            getattr(row, "acquisition_method", None),
            is_live_data=row.source_type == SourceType.LIVE.value,
        ),
        "data_available": row.observations_collected > 0,
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
        "duration_ms": row.duration_ms,
        "collection_day": row.collection_day.isoformat(),
        "routes_requested": row.routes_requested,
        "routes_with_data": row.routes_with_data,
        "horizons_requested": list(row.horizons_requested or []),
        "observations": {
            "collected": row.observations_collected,
            "accepted": row.observations_accepted,
            "flagged": row.observations_flagged,
            "excluded": row.observations_excluded,
            "duplicates_removed": row.duplicates_removed,
        },
        "error_message": row.error_message,
        "collector_version": row.collector_version,
        "skipped_sources": list(row.skipped_sources or []),
        "triggered_by": row.triggered_by,
    }
    if include_attempts:
        payload["attempts"] = list(row.attempts or [])
        payload["dedupe"] = dict(row.dedupe_summary or {})
    return payload


# ── sources ──

def source(row: Source) -> dict[str, Any]:
    """
    Serialize a source, including disabled ones with their reasons.

    Exposing the disabled set is deliberate: it answers "why aren't you scraping
    MakeMyTrip?" in the API rather than leaving a reviewer to infer an oversight.
    """
    from scraper.source_registry import get_source_registry

    gov = get_source_registry().get(row.name)
    return {
        "name": row.name,
        "display_name": row.display_name,
        "source_type": row.source_type,
        "provenance_label": PROVENANCE_LABELS[SourceType(row.source_type)],
        "enabled": row.is_enabled,
        "disabled_reason": row.disabled_reason,
        "requires_credentials": row.requires_credentials,
        "homepage": row.homepage,
        "terms_url": row.terms_url,
        "robots_url": row.robots_url,
        "compliance_note": row.compliance_note,
        "native_currency": row.native_currency,
        "last_updated_at": _iso(row.last_updated_at),
        "governance": gov.to_dict() if gov else None,
    }


# ── anomalies ──

def anomaly(row: Anomaly) -> dict[str, Any]:
    return {
        "id": row.id,
        "observation_id": row.observation_id,
        "route_id": row.route_id,
        "route_code": row.route_code,
        "booking_horizon": row.booking_horizon,
        "detected_at": _iso(row.detected_at),
        "rule": row.rule,
        "severity": row.severity,
        "description": row.description,
        "fare_observed": (
            _round(float(row.fare_observed), 2) if row.fare_observed is not None else None
        ),
        "fare_expected_low": (
            _round(float(row.fare_expected_low), 2)
            if row.fare_expected_low is not None
            else None
        ),
        "fare_expected_high": (
            _round(float(row.fare_expected_high), 2)
            if row.fare_expected_high is not None
            else None
        ),
        "detail": dict(row.detail or {}),
        "status": row.status,
        # NULL means unreviewed, which is a distinct state from "reviewed and not
        # genuine". The triage workflow writes it.
        "is_genuine": row.is_genuine,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": _iso(row.reviewed_at),
        "notes": row.notes,
        "data_provenance": provenance_block(row.source_type),
    }


# ── revisions ──

def revision(row: IndexRevision) -> dict[str, Any]:
    return {
        "id": row.id,
        "target_table": row.target_table,
        "target_index_date": row.target_index_date.isoformat(),
        "target_route_id": row.target_route_id,
        "target_booking_horizon": row.target_booking_horizon,
        "previous_value": _round(row.previous_value, 4),
        "new_value": _round(row.new_value, 4),
        "revision_type": row.revision_type,
        "reason": row.reason,
        "previous_methodology_version": row.previous_methodology_version,
        "new_methodology_version": row.new_methodology_version,
        "triggered_by": row.triggered_by,
        "created_at": _iso(row.created_at),
    }


# ── not-implemented responses ──

def not_implemented(capability: str, explanation: str) -> dict[str, Any]:
    """
    The response for a capability that does not exist.

    Returns the literal string ``NOT IMPLEMENTED`` rather than an empty success
    payload, so a missing feature cannot read as a feature that returned nothing.
    """
    return {
        "status": NOT_IMPLEMENTED_LABEL,
        "capability": capability,
        "value": None,
        "explanation": explanation,
        "methodology_version": METHODOLOGY_VERSION,
    }


def unavailable(reason: str, capability: Optional[str] = None) -> dict[str, Any]:
    """The response when data would be expected but none exists."""
    return {
        "status": SOURCE_UNAVAILABLE_LABEL,
        "capability": capability,
        "value": None,
        "reason": reason,
        "data_provenance": provenance_block(None),
        "methodology_version": METHODOLOGY_VERSION,
        "validation_rules_version": VALIDATION_RULES_VERSION,
    }


# ── helpers ──

def _round(value: Optional[float], places: int) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), places)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value is not None else None
