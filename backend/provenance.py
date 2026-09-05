"""
SIH26056 — Data provenance primitives.

Provenance is a first-class, mandatory property of every fare observation in this
system. The rule it exists to enforce is simple and absolute:

    Synthetic data must never be presentable as collected data.

To make that structurally impossible rather than merely discouraged:

* Every observation carries a :class:`DataProvenance` record.
* :class:`SourceType` distinguishes ``live`` (retrieved from a real permitted
  source), ``simulated`` (generated locally by the calibrated simulator), and
  ``offline`` (replayed from a checked-in fixture).
* :class:`CollectionStatus` has no value that means "success" for anything other
  than a genuine live retrieval. Simulated collection reports ``SIMULATED``;
  offline replay reports ``OFFLINE``. A failed live attempt reports ``FAILED`` or
  ``UNAVAILABLE`` and yields **zero** observations — there is no code path that
  substitutes generated fares for a failed live fetch.

The display labels in :data:`PROVENANCE_LABELS` are the exact strings the UI and
reports are required to show, so the same vocabulary appears end to end.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# Bumped whenever the collection/normalization contract changes in a way that
# affects stored observations. Persisted per observation for reproducibility.
COLLECTOR_VERSION = "collector-2.0.0"

# Bumped whenever index computation changes in a way that would alter published
# figures. Persisted per index record so any published value can be traced to the
# exact calculation that produced it.
METHODOLOGY_VERSION = "methodology-2.1.0"


class AcquisitionMethod(str, Enum):
    """The technical acquisition method used to capture an observation."""

    WEB_SCRAPE = "WEB_SCRAPE"            # Fares read from a permitted airline/OTA web portal
    API = "API"                          # Fares returned by a documented external API (e.g. Amadeus)
    SIMULATED = "SIMULATED"              # Locally generated methodology/test data
    OFFLINE_FIXTURE = "OFFLINE_FIXTURE"  # Replayed test or static-preview data

    @property
    def display_label(self) -> str:
        return ACQUISITION_METHOD_LABELS[self]

    @property
    def counts_as_portal_scraping(self) -> bool:
        """Only genuine web scrape observations count toward portal-scraping targets."""
        return self is AcquisitionMethod.WEB_SCRAPE

    @property
    def is_empirical(self) -> bool:
        """Only real external captures (portal scrapes or API) are empirical."""
        return self in {AcquisitionMethod.WEB_SCRAPE, AcquisitionMethod.API}


class SourceType(str, Enum):
    """Where an observation actually came from."""

    LIVE = "live"            # Retrieved from a real, permitted external source
    SIMULATED = "simulated"  # Generated locally by the calibrated simulator
    OFFLINE = "offline"      # Replayed from a checked-in fixture

    @property
    def display_label(self) -> str:
        return PROVENANCE_LABELS[self]

    @property
    def is_real(self) -> bool:
        """True only for genuinely collected observations."""
        return self is SourceType.LIVE


class CollectionMode(str, Enum):
    """Operating mode of the collection pipeline."""

    LIVE = "LIVE"
    SIMULATED = "SIMULATED"
    OFFLINE = "OFFLINE"

    @property
    def source_type(self) -> SourceType:
        return {
            CollectionMode.LIVE: SourceType.LIVE,
            CollectionMode.SIMULATED: SourceType.SIMULATED,
            CollectionMode.OFFLINE: SourceType.OFFLINE,
        }[self]

    @classmethod
    def parse(cls, raw: str | None, default: "CollectionMode" = None) -> "CollectionMode":
        """
        Parse a mode string. Unknown values raise rather than silently defaulting
        to something more permissive.
        """
        if raw is None or not str(raw).strip():
            return default or cls.SIMULATED
        key = str(raw).strip().upper()
        try:
            return cls(key)
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(
                f"Unknown collection mode {raw!r}. Valid modes: {valid}."
            ) from exc


class CollectionStatus(str, Enum):
    """
    Outcome of a collection attempt.

    ``SUCCESS`` is reserved for live retrieval. Nothing else may use it — that is
    the invariant which stops synthetic output from looking like collected output
    to any downstream consumer.
    """

    SUCCESS = "success"          # LIVE only: real data retrieved
    SIMULATED = "simulated"      # Simulator produced data; no source contacted
    OFFLINE = "offline"          # Fixture replayed; no source contacted
    PARTIAL = "partial"          # LIVE: some routes retrieved, some failed
    FAILED = "failed"            # LIVE: attempt made and failed
    UNAVAILABLE = "unavailable"  # LIVE: source not configured / disabled / blocked
    SKIPPED = "skipped"          # Source deliberately not attempted

    @property
    def yielded_real_data(self) -> bool:
        return self in {CollectionStatus.SUCCESS, CollectionStatus.PARTIAL}

    @property
    def is_failure(self) -> bool:
        return self in {CollectionStatus.FAILED, CollectionStatus.UNAVAILABLE}


PROVENANCE_LABELS: dict[SourceType, str] = {
    SourceType.LIVE: "SCRAPED DATA",
    SourceType.SIMULATED: "SIMULATED DATA",
    SourceType.OFFLINE: "OFFLINE PREVIEW",
}

ACQUISITION_METHOD_LABELS: dict[AcquisitionMethod, str] = {
    AcquisitionMethod.WEB_SCRAPE: "PORTAL-SCRAPED DATA",
    AcquisitionMethod.API: "API-COLLECTED DATA",
    AcquisitionMethod.SIMULATED: "SIMULATED DATA",
    AcquisitionMethod.OFFLINE_FIXTURE: "OFFLINE PREVIEW",
}

# Shown when a live collection attempt produced nothing. Never replaced by data.
SOURCE_UNAVAILABLE_LABEL = "SOURCE UNAVAILABLE"

# Shown wherever a capability is not built. Used verbatim in API responses.
NOT_IMPLEMENTED_LABEL = "NOT IMPLEMENTED"


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp. Naive datetimes are not used anywhere."""
    return datetime.now(timezone.utc)


def new_request_id() -> str:
    """Correlation id for a single outbound request or generation call."""
    return uuid.uuid4().hex


def payload_hash(payload: Any) -> Optional[str]:
    """
    SHA-256 of a raw source payload, for audit without storing the payload itself.

    Returns None for empty input so an absent payload is distinguishable from a
    hash of the empty string.
    """
    if payload is None:
        return None
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    else:
        raw = str(payload).encode("utf-8")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class DataProvenance:
    """
    Mandatory origin record attached to every fare observation.

    Frozen because provenance must not be editable after collection: rewriting it
    is precisely the failure mode this class exists to prevent.
    """

    source_type: SourceType
    source_name: str
    collection_timestamp: datetime
    request_id: str
    acquisition_method: Optional[AcquisitionMethod] = None
    collector_version: str = COLLECTOR_VERSION
    source_url: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    # Free-form, source-specific audit detail (e.g. rate-limit headers, fixture
    # filename, simulator seed). Never used for control flow.
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_name:
            raise ValueError("DataProvenance.source_name is required")
        if not self.request_id:
            raise ValueError("DataProvenance.request_id is required")
        if self.collection_timestamp.tzinfo is None:
            raise ValueError(
                "DataProvenance.collection_timestamp must be timezone-aware"
            )
        if self.acquisition_method is None:
            if self.source_type is SourceType.SIMULATED:
                object.__setattr__(self, "acquisition_method", AcquisitionMethod.SIMULATED)
            elif self.source_type is SourceType.OFFLINE:
                object.__setattr__(self, "acquisition_method", AcquisitionMethod.OFFLINE_FIXTURE)
            elif self.source_type is SourceType.LIVE:
                object.__setattr__(self, "acquisition_method", AcquisitionMethod.WEB_SCRAPE)
        elif not isinstance(self.acquisition_method, AcquisitionMethod):
            object.__setattr__(
                self, "acquisition_method", AcquisitionMethod(self.acquisition_method)
            )

        # ── Invariant checks across source_type and acquisition_method ──
        if self.source_type is SourceType.SIMULATED and self.acquisition_method is not AcquisitionMethod.SIMULATED:
            raise ValueError(
                f"DataProvenance invariant violation: source_type=SIMULATED requires "
                f"acquisition_method=SIMULATED, got {self.acquisition_method.value}"
            )
        if self.source_type is SourceType.OFFLINE and self.acquisition_method is not AcquisitionMethod.OFFLINE_FIXTURE:
            raise ValueError(
                f"DataProvenance invariant violation: source_type=OFFLINE requires "
                f"acquisition_method=OFFLINE_FIXTURE, got {self.acquisition_method.value}"
            )
        if self.source_type is SourceType.LIVE and self.acquisition_method not in {
            AcquisitionMethod.WEB_SCRAPE,
            AcquisitionMethod.API,
        }:
            raise ValueError(
                f"DataProvenance invariant violation: source_type=LIVE requires "
                f"acquisition_method in (WEB_SCRAPE, API), got {self.acquisition_method.value}"
            )

    @property
    def display_label(self) -> str:
        return PROVENANCE_LABELS[self.source_type]

    @property
    def acquisition_label(self) -> str:
        return ACQUISITION_METHOD_LABELS[self.acquisition_method]

    @property
    def is_real(self) -> bool:
        return self.source_type.is_real

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        data["acquisition_method"] = self.acquisition_method.value
        data["collection_timestamp"] = self.collection_timestamp.isoformat()
        data["display_label"] = self.display_label
        data["acquisition_label"] = self.acquisition_label
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataProvenance":
        ts = data["collection_timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        st = SourceType(data["source_type"])
        acq_raw = data.get("acquisition_method")
        if acq_raw:
            acq = AcquisitionMethod(acq_raw)
        else:
            if st is SourceType.SIMULATED:
                acq = AcquisitionMethod.SIMULATED
            elif st is SourceType.OFFLINE:
                acq = AcquisitionMethod.OFFLINE_FIXTURE
            else:
                acq = AcquisitionMethod.WEB_SCRAPE

        return cls(
            source_type=st,
            acquisition_method=acq,
            source_name=data["source_name"],
            collection_timestamp=ts,
            request_id=data["request_id"],
            collector_version=data.get("collector_version", COLLECTOR_VERSION),
            source_url=data.get("source_url"),
            raw_payload_hash=data.get("raw_payload_hash"),
            notes=data.get("notes") or {},
        )

    @classmethod
    def for_simulator(
        cls,
        source_name: str,
        seed: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ) -> "DataProvenance":
        """Provenance for generated data. source_url is always None: nothing was fetched."""
        return cls(
            source_type=SourceType.SIMULATED,
            acquisition_method=AcquisitionMethod.SIMULATED,
            source_name=source_name,
            collection_timestamp=timestamp or utc_now(),
            request_id=new_request_id(),
            source_url=None,
            raw_payload_hash=None,
            notes={"seed": seed} if seed is not None else {},
        )

    @classmethod
    def for_fixture(
        cls,
        source_name: str,
        fixture_path: str,
        payload: Any = None,
        timestamp: Optional[datetime] = None,
    ) -> "DataProvenance":
        """Provenance for fixture replay."""
        return cls(
            source_type=SourceType.OFFLINE,
            acquisition_method=AcquisitionMethod.OFFLINE_FIXTURE,
            source_name=source_name,
            collection_timestamp=timestamp or utc_now(),
            request_id=new_request_id(),
            source_url=None,
            raw_payload_hash=payload_hash(payload),
            notes={"fixture": fixture_path},
        )

    @classmethod
    def for_api(
        cls,
        source_name: str,
        source_url: str,
        request_id: Optional[str] = None,
        raw_payload: Any = None,
        timestamp: Optional[datetime] = None,
        notes: Optional[dict[str, Any]] = None,
    ) -> "DataProvenance":
        """Provenance for external documented API collection."""
        return cls(
            source_type=SourceType.LIVE,
            acquisition_method=AcquisitionMethod.API,
            source_name=source_name,
            collection_timestamp=timestamp or utc_now(),
            request_id=request_id or new_request_id(),
            source_url=source_url,
            raw_payload_hash=payload_hash(raw_payload),
            notes=notes or {},
        )

    @classmethod
    def for_web_scrape(
        cls,
        source_name: str,
        source_url: str,
        request_id: Optional[str] = None,
        raw_payload: Any = None,
        timestamp: Optional[datetime] = None,
        notes: Optional[dict[str, Any]] = None,
    ) -> "DataProvenance":
        """Provenance for permitted web portal scraping."""
        return cls(
            source_type=SourceType.LIVE,
            acquisition_method=AcquisitionMethod.WEB_SCRAPE,
            source_name=source_name,
            collection_timestamp=timestamp or utc_now(),
            request_id=request_id or new_request_id(),
            source_url=source_url,
            raw_payload_hash=payload_hash(raw_payload),
            notes=notes or {},
        )


def resolve_display_label(
    source_type: SourceType | str | None,
    status: CollectionStatus | str | None = None,
    acquisition_method: AcquisitionMethod | str | None = None,
) -> str:
    """
    The single place that decides which honest label a consumer should render.

    A failed or unavailable live attempt reports SOURCE UNAVAILABLE rather than
    falling back to any data label, because there is no data to label.
    """
    # Accommodate callers passing acquisition_method as second positional parameter
    if isinstance(status, AcquisitionMethod) or (
        isinstance(status, str) and status in {m.value for m in AcquisitionMethod}
    ):
        acquisition_method = status
        status = None

    if status is not None:
        status = CollectionStatus(status) if isinstance(status, str) else status
        if status.is_failure:
            return SOURCE_UNAVAILABLE_LABEL

    if source_type is None:
        return SOURCE_UNAVAILABLE_LABEL

    source_type = SourceType(source_type) if isinstance(source_type, str) else source_type

    if acquisition_method is not None:
        acq = (
            AcquisitionMethod(acquisition_method)
            if isinstance(acquisition_method, str)
            else acquisition_method
        )
        return ACQUISITION_METHOD_LABELS[acq]

    return PROVENANCE_LABELS[source_type]
