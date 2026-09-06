"""
SIH26056 — Fare source contract.

Defines the canonical :class:`FareObservation`, the :class:`FareSource` adapter
protocol every source implements, and :class:`SourceResult`, the only value a
source may return.

Design intent
-------------
The index engine must not know or care which website or API a fare came from. A
source's entire job is: given a route/date/horizon request, return zero or more
normalized :class:`FareObservation` values, each carrying honest provenance, plus
a :class:`CollectionStatus` describing what actually happened.

Two invariants are enforced structurally rather than by convention:

1. ``SourceResult`` rejects ``status=SUCCESS`` unless every observation carries
   ``SourceType.LIVE`` provenance. Generated data therefore cannot report success.
2. A result whose status is a failure must carry zero observations. There is no
   representable state meaning "the live fetch failed, so here is synthetic data".
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any, Optional, Protocol, runtime_checkable

from provenance import (
    AcquisitionMethod,
    CollectionStatus,
    DataProvenance,
    SourceType,
    resolve_display_label,
)


# Cabin classes recognised across sources, normalized to these labels.
CABIN_ECONOMY = "ECONOMY"
CABIN_PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
CABIN_BUSINESS = "BUSINESS"
CABIN_FIRST = "FIRST"

VALID_CABINS = {CABIN_ECONOMY, CABIN_PREMIUM_ECONOMY, CABIN_BUSINESS, CABIN_FIRST}


def classify_time_band(time_str: Optional[str]) -> str:
    """
    Classifies a departure time string (e.g. '08:15 AM', '14:30', '19:45') into one of
    the four canonical SIH26056 / Implementation Plan departure time bands:
      - 00:00-05:59: Early Morning / Red-eye
      - 06:00-11:59: Morning
      - 12:00-17:59: Afternoon
      - 18:00-23:59: Evening / Night
    """
    if not time_str:
        return "UNSPECIFIED"
    import re
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)?", str(time_str).upper())
    if not m:
        return "UNSPECIFIED"
    try:
        hour = int(m.group(1))
        ampm = m.group(3)
        if ampm == "PM" and hour < 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0
        
        if 0 <= hour <= 5:
            return "00:00-05:59"
        elif 6 <= hour <= 11:
            return "06:00-11:59"
        elif 12 <= hour <= 17:
            return "12:00-17:59"
        else:
            return "18:00-23:59"
    except Exception:
        return "UNSPECIFIED"


@dataclass(frozen=True)
class FareObservation:
    """
    One fare quote for one product, at one collection moment.

    The atomic unit of the whole system. Fields are the union of what the index
    needs for matched-model comparison and what an auditor needs to trace a
    published figure back to its source.

    ``fare_total`` is always INR (see ``normalizer.py``); ``source_currency`` and
    ``source_fare_total`` retain the original values so a conversion can be checked.
    """

    # ── identity / routing ──
    route_id: int
    origin_code: str
    destination_code: str
    departure_date: date
    booking_horizon_days: int

    # ── product description (the matched-model dimensions) ──
    airline_code: str
    cabin_class: str
    fare_total: float                      # INR, tax-inclusive
    currency: str = "INR"

    airline_name: Optional[str] = None
    flight_number: Optional[str] = None
    fare_family: Optional[str] = None
    stops: int = 0
    is_refundable: Optional[bool] = None
    baggage_kg: Optional[int] = None
    fare_base: Optional[float] = None
    fare_taxes: Optional[float] = None
    fare_udf: Optional[float] = None
    fare_convenience: Optional[float] = None
    dep_time: Optional[str] = None
    dep_time_band: Optional[str] = None

    # ── availability, where the source discloses it ──
    seats_available: Optional[int] = None

    # ── original source values, retained for audit ──
    source_currency: Optional[str] = None
    source_fare_total: Optional[float] = None
    source_offer_id: Optional[str] = None

    # ── provenance (mandatory) ──
    provenance: Optional[DataProvenance] = None

    # ── validation outcome, populated downstream ──
    is_valid: bool = True
    validation_flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.provenance is None:
            raise ValueError(
                "FareObservation.provenance is mandatory. An observation without "
                "provenance cannot be distinguished from synthetic data."
            )
        if getattr(self.provenance, "acquisition_method", None) is None:
            raise ValueError(
                "FareObservation.provenance.acquisition_method is mandatory."
            )
        if self.fare_total is None or self.fare_total <= 0:
            raise ValueError(
                f"FareObservation.fare_total must be positive, got {self.fare_total!r}"
            )
        if self.currency != "INR":
            raise ValueError(
                f"FareObservation.fare_total must be normalized to INR before "
                f"construction; got currency={self.currency!r}. Use normalizer.to_inr()."
            )
        if self.cabin_class not in VALID_CABINS:
            raise ValueError(
                f"Unrecognised cabin_class {self.cabin_class!r}; "
                f"expected one of {sorted(VALID_CABINS)}"
            )
        if self.stops < 0:
            raise ValueError(f"stops must be >= 0, got {self.stops}")
        if self.dep_time and not self.dep_time_band:
            object.__setattr__(self, "dep_time_band", classify_time_band(self.dep_time))

    # ── derived identity ──

    @property
    def route_code(self) -> str:
        return f"{self.origin_code}-{self.destination_code}"

    @property
    def source_type(self) -> SourceType:
        return self.provenance.source_type

    @property
    def acquisition_method(self) -> AcquisitionMethod:
        return self.provenance.acquisition_method

    @property
    def collection_datetime(self) -> datetime:
        return self.provenance.collection_timestamp

    @property
    def collection_date(self) -> date:
        return self.provenance.collection_timestamp.date()

    def product_key(self) -> str:
        """
        Matched-model product identity.

        Two observations share a product key when they describe the same purchasable
        product, so that a price change between them is a genuine price change rather
        than a difference in what is being bought. Deliberately includes quality
        dimensions (cabin, fare family, stops, refundability, baggage, and departure
        time band) — omitting them is exactly how a product-quality change gets misread
        as inflation.

        Flight number is included to avoid collapsing different scheduled services
        from the same carrier into one product. Departure date is deliberately not
        included: at a fixed horizon each collection day targets a different travel
        date, so including it would make every inter-period match impossible. The
        resulting product is a repeatable service specification, not one physical
        seat; that limitation is reported in the methodology.
        """
        parts = (
            self.origin_code,
            self.destination_code,
            self.airline_code,
            self.flight_number or "FLIGHTUNKNOWN",
            self.cabin_class,
            self.fare_family or "UNSPECIFIED",
            str(self.stops),
            "REF" if self.is_refundable else "NONREF" if self.is_refundable is False else "REFUNKNOWN",
            f"BAG{self.baggage_kg}" if self.baggage_kg is not None else "BAGUNKNOWN",
            f"H{self.booking_horizon_days}",
            f"BAND_{self.dep_time_band}" if self.dep_time_band else "BAND_UNSPECIFIED",
        )
        return "|".join(parts)

    def product_key_hash(self) -> str:
        return hashlib.sha256(self.product_key().encode("utf-8")).hexdigest()[:32]

    def dedupe_fingerprint(self) -> str:
        """
        Cross-source duplicate identity.

        The same physical seat offered through several sources should be counted
        once. Fingerprint therefore spans the flight and product but NOT the source,
        and NOT the price: two sources quoting slightly different prices for the same
        product are still the same product, and keeping both would double-count it.
        """
        parts = (
            self.origin_code,
            self.destination_code,
            self.departure_date.isoformat(),
            self.airline_code,
            self.flight_number or "NOFLIGHT",
            self.cabin_class,
            self.fare_family or "UNSPECIFIED",
            str(self.stops),
            f"H{self.booking_horizon_days}",
            self.collection_date.isoformat(),
        )
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]

    def with_validation(
        self, is_valid: bool, flags: tuple[str, ...]
    ) -> "FareObservation":
        return replace(self, is_valid=is_valid, validation_flags=tuple(flags))

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "route_code": self.route_code,
            "origin_code": self.origin_code,
            "destination_code": self.destination_code,
            "departure_date": self.departure_date.isoformat(),
            "collection_datetime": self.collection_datetime.isoformat(),
            "booking_horizon_days": self.booking_horizon_days,
            "airline_code": self.airline_code,
            "airline_name": self.airline_name,
            "flight_number": self.flight_number,
            "cabin_class": self.cabin_class,
            "fare_family": self.fare_family,
            "fare_total": self.fare_total,
            "fare_base": self.fare_base,
            "fare_taxes": self.fare_taxes,
            "fare_udf": self.fare_udf,
            "fare_convenience": self.fare_convenience,
            "dep_time": self.dep_time,
            "dep_time_band": self.dep_time_band,
            "currency": self.currency,
            "stops": self.stops,
            "is_direct": self.stops == 0,
            "is_refundable": self.is_refundable,
            "baggage_kg": self.baggage_kg,
            "seats_available": self.seats_available,
            "source_currency": self.source_currency,
            "source_fare_total": self.source_fare_total,
            "source_offer_id": self.source_offer_id,
            "product_key": self.product_key(),
            "product_key_hash": self.product_key_hash(),
            "dedupe_fingerprint": self.dedupe_fingerprint(),
            "is_valid": self.is_valid,
            "validation_flags": list(self.validation_flags),
            "data_provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True)
class SourceCapability:
    """
    What a source can do and whether it may legally and technically be used.

    ``enabled=False`` with a populated ``disabled_reason`` is a first-class,
    documented state. Several OTA adapters exist in this repository purely to record
    that they are NOT permitted, rather than pretending they were never considered.
    """

    name: str
    display_name: str
    source_type: SourceType
    enabled: bool
    # Present whenever enabled is False. Stated plainly, e.g. "robots.txt disallows
    # the flight-search path" or "no credentials configured".
    disabled_reason: Optional[str] = None
    requires_credentials: bool = False
    homepage: Optional[str] = None
    terms_url: Optional[str] = None
    robots_url: Optional[str] = None
    # Free-text note on the legal / ToS position for this source.
    compliance_note: str = ""
    supports_cabin: tuple[str, ...] = (CABIN_ECONOMY,)
    native_currency: str = "INR"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "source_type": self.source_type.value,
            "provenance_label": self.source_type.display_label,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
            "requires_credentials": self.requires_credentials,
            "homepage": self.homepage,
            "terms_url": self.terms_url,
            "robots_url": self.robots_url,
            "compliance_note": self.compliance_note,
            "supports_cabin": list(self.supports_cabin),
            "native_currency": self.native_currency,
        }


@dataclass(frozen=True)
class SourceResult:
    """
    The only value a :class:`FareSource` may return.

    Validation in ``__post_init__`` is the mechanism that makes it impossible for
    synthetic data to masquerade as live data, so it raises rather than warns.
    """

    source_name: str
    status: CollectionStatus
    observations: tuple[FareObservation, ...] = field(default_factory=tuple)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    request_id: Optional[str] = None
    source_url: Optional[str] = None
    attempts: int = 1

    def __post_init__(self):
        # Invariant 1: SUCCESS means live, and only live.
        if self.status is CollectionStatus.SUCCESS:
            offenders = {
                o.source_type.value
                for o in self.observations
                if o.source_type is not SourceType.LIVE
            }
            if offenders:
                raise ValueError(
                    f"{self.source_name}: status=success requires every observation to "
                    f"carry live provenance, but found {sorted(offenders)}. Generated or "
                    f"replayed data must report status='simulated' or 'offline'."
                )
            if not self.observations:
                raise ValueError(
                    f"{self.source_name}: status=success with zero observations is "
                    f"contradictory. Use status='failed' or 'unavailable'."
                )

        # Invariant 2: a failure carries no data. Closes the silent-substitution path.
        if self.status.is_failure and self.observations:
            raise ValueError(
                f"{self.source_name}: status={self.status.value} must carry zero "
                f"observations, got {len(self.observations)}. Never substitute data "
                f"for a failed collection."
            )

        if self.status.is_failure and not self.error_message:
            raise ValueError(
                f"{self.source_name}: status={self.status.value} requires an "
                f"error_message explaining why no data was collected."
            )

        # Simulated/offline results must be uniformly labelled as such.
        if self.status is CollectionStatus.SIMULATED:
            bad = [o for o in self.observations if o.source_type is not SourceType.SIMULATED]
            if bad:
                raise ValueError(
                    f"{self.source_name}: status=simulated requires simulated provenance "
                    f"on every observation"
                )
        if self.status is CollectionStatus.OFFLINE:
            bad = [o for o in self.observations if o.source_type is not SourceType.OFFLINE]
            if bad:
                raise ValueError(
                    f"{self.source_name}: status=offline requires offline provenance "
                    f"on every observation"
                )

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def source_type(self) -> Optional[SourceType]:
        return self.observations[0].source_type if self.observations else None

    @property
    def display_label(self) -> str:
        return resolve_display_label(self.source_type, self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "status": self.status.value,
            "display_label": self.display_label,
            "observation_count": self.observation_count,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "http_status": self.http_status,
            "response_time_ms": self.response_time_ms,
            "request_id": self.request_id,
            "source_url": self.source_url,
            "attempts": self.attempts,
        }

    # ── constructors, so callers cannot accidentally build an invalid result ──

    @classmethod
    def unavailable(
        cls,
        source_name: str,
        reason: str,
        error_type: str = "source_unavailable",
    ) -> "SourceResult":
        """
        The honest answer when a source cannot be used: no credentials, adapter
        disabled, robots.txt disallows the path, or the endpoint is unreachable.
        """
        return cls(
            source_name=source_name,
            status=CollectionStatus.UNAVAILABLE,
            observations=(),
            error_message=reason,
            error_type=error_type,
        )

    @classmethod
    def failed(
        cls,
        source_name: str,
        reason: str,
        error_type: str = "collection_failed",
        http_status: Optional[int] = None,
        attempts: int = 1,
        response_time_ms: Optional[int] = None,
    ) -> "SourceResult":
        return cls(
            source_name=source_name,
            status=CollectionStatus.FAILED,
            observations=(),
            error_message=reason,
            error_type=error_type,
            http_status=http_status,
            attempts=attempts,
            response_time_ms=response_time_ms,
        )


@runtime_checkable
class FareSource(Protocol):
    """
    Adapter interface. Any object satisfying this can feed the index.

    Keeping the index engine coupled only to this protocol is what allows sources to
    be added, disabled, or swapped without touching index computation.
    """

    @property
    def capability(self) -> SourceCapability:
        """Static description of the source, including whether it may be used."""
        ...

    async def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
    ) -> SourceResult:
        """
        Retrieve fares for one route / date / cabin request.

        Must never raise for an expected failure (network error, rate limit, missing
        credentials) — return ``SourceResult.failed`` or ``SourceResult.unavailable``
        instead, so the pipeline records the failure rather than aborting.
        """
        ...

    async def aclose(self) -> None:
        """Release any held network resources."""
        ...


class BaseFareSource(abc.ABC):
    """
    Convenience base class implementing the boilerplate of :class:`FareSource`.

    Subclasses implement :meth:`_search` and get capability gating for free: a
    disabled source short-circuits to ``UNAVAILABLE`` and never issues a request.
    """

    def __init__(self, capability: SourceCapability):
        self._capability = capability

    @property
    def capability(self) -> SourceCapability:
        return self._capability

    @property
    def name(self) -> str:
        return self._capability.name

    async def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
    ) -> SourceResult:
        if not self._capability.enabled:
            return SourceResult.unavailable(
                self.name,
                self._capability.disabled_reason or "Source is disabled.",
                error_type="source_disabled",
            )
        return await self._search(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
            cabin=cabin,
            route_id=route_id,
            booking_horizon_days=booking_horizon_days,
        )

    @abc.abstractmethod
    async def _search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
    ) -> SourceResult:
        ...

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        return None
