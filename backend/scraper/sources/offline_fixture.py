"""
SIH26056 — Offline fixture source.

Replays fare observations from a checked-in JSON file. Two uses:

* CI: exercise the full collection -> validation -> index path with no network
  dependency, so the test suite does not depend on a live source being reachable.
* Demonstration on a machine with no credentials and no connectivity.

Everything it emits carries ``SourceType.OFFLINE`` and displays as OFFLINE PREVIEW.
It is not a fallback: nothing automatically switches to it when live collection
fails. Reaching it requires ``COLLECTION_MODE=OFFLINE`` explicitly.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from config import get_settings
from provenance import (
    CollectionStatus,
    DataProvenance,
    SourceType,
    payload_hash,
    new_request_id,
)
from scraper.base import (
    BaseFareSource,
    CABIN_ECONOMY,
    FareObservation,
    SourceCapability,
    SourceResult,
)
from scraper.normalizer import (
    NormalizationError,
    airline_name_for,
    collect_normalized,
    normalize_airline_code,
    normalize_baggage_kg,
    normalize_bool,
    normalize_cabin,
    normalize_flight_number,
    normalize_stops,
    parse_iso_date,
    to_inr,
)


SOURCE_NAME = "offline_fixture"


def describe(fixture_path: Optional[Path] = None) -> SourceCapability:
    path = fixture_path or get_settings().fixture_path
    exists = Path(path).exists()
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="Offline fixture replay",
        source_type=SourceType.OFFLINE,
        enabled=exists,
        disabled_reason=(
            None if exists else f"Fixture file not found: {path}"
        ),
        requires_credentials=False,
        homepage=None,
        terms_url=None,
        robots_url=None,
        compliance_note=(
            "Replays a checked-in fixture. No external system is contacted. Output is "
            "labelled OFFLINE PREVIEW and is never presented as collected data."
        ),
        supports_cabin=(CABIN_ECONOMY,),
        native_currency="INR",
    )


class OfflineFixtureSource(BaseFareSource):
    """Replays observations matching the requested route / date / horizon."""

    def __init__(self, fixture_path: Optional[Path] = None):
        self.fixture_path = Path(fixture_path or get_settings().fixture_path)
        super().__init__(describe(self.fixture_path))
        self._payload: Optional[dict[str, Any]] = None
        self._raw_text: Optional[str] = None

    def _load(self) -> dict[str, Any]:
        if self._payload is not None:
            return self._payload
        self._raw_text = self.fixture_path.read_text(encoding="utf-8")
        self._payload = json.loads(self._raw_text)
        logger.info(
            f"Loaded offline fixture {self.fixture_path.name} "
            f"({len(self._payload.get('observations', []))} record(s))"
        )
        return self._payload

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
        try:
            payload = self._load()
        except (OSError, json.JSONDecodeError) as exc:
            return SourceResult.unavailable(
                SOURCE_NAME,
                f"Offline fixture {self.fixture_path} could not be read: {exc}",
                error_type="fixture_unreadable",
            )

        records = [
            r for r in payload.get("observations", [])
            if str(r.get("origin_code", "")).upper() == origin.upper()
            and str(r.get("destination_code", "")).upper() == destination.upper()
            and int(r.get("booking_horizon_days", -1)) == booking_horizon_days
        ]

        if not records:
            return SourceResult.failed(
                SOURCE_NAME,
                f"Offline fixture holds no records for {origin}-{destination} "
                f"T+{booking_horizon_days}.",
                error_type="no_fixture_records",
            )

        provenance = DataProvenance.for_fixture(
            source_name=SOURCE_NAME,
            fixture_path=str(self.fixture_path.name),
            payload=self._raw_text,
            # Fixture records carry their own collection date; the replay timestamp
            # records when the replay happened.
            timestamp=datetime.now(timezone.utc),
        )

        builders = [
            (
                {"source": SOURCE_NAME, "route_id": route_id, "record_index": i},
                lambda record=record: self._to_observation(
                    record=record,
                    route_id=route_id,
                    booking_horizon_days=booking_horizon_days,
                    departure_date=departure_date,
                    provenance=provenance,
                ),
            )
            for i, record in enumerate(records)
        ]

        outcome = collect_normalized(builders)

        if not outcome.observations:
            return SourceResult.failed(
                SOURCE_NAME,
                f"Offline fixture records for {origin}-{destination} could not be "
                f"normalized: {outcome.summary()['drop_reasons']}",
                error_type="normalization_failed",
            )

        return SourceResult(
            source_name=SOURCE_NAME,
            status=CollectionStatus.OFFLINE,
            observations=tuple(outcome.observations),
            request_id=provenance.request_id,
            response_time_ms=None,
        )

    def _to_observation(
        self,
        record: dict[str, Any],
        route_id: int,
        booking_horizon_days: int,
        departure_date: date,
        provenance: DataProvenance,
    ) -> FareObservation:
        currency = str(record.get("currency", "INR")).upper()
        raw_total = record.get("fare_total")
        if raw_total is None:
            raise NormalizationError("fixture record has no fare_total")
        total_inr, _ = to_inr(float(raw_total), currency)

        airline_code = normalize_airline_code(record.get("airline_code"))

        # Each fixture record carries its own collection timestamp so a replayed
        # series has real dates; the replay moment goes into notes.
        collected_raw = record.get("collection_datetime")
        if collected_raw:
            collected = datetime.fromisoformat(str(collected_raw))
            if collected.tzinfo is None:
                collected = collected.replace(tzinfo=timezone.utc)
            record_provenance = DataProvenance(
                source_type=SourceType.OFFLINE,
                source_name=SOURCE_NAME,
                collection_timestamp=collected,
                request_id=new_request_id(),
                source_url=None,
                raw_payload_hash=payload_hash(json.dumps(record, sort_keys=True)),
                notes={
                    **provenance.notes,
                    "replayed_at": provenance.collection_timestamp.isoformat(),
                },
            )
        else:
            record_provenance = provenance

        return FareObservation(
            route_id=route_id,
            origin_code=str(record["origin_code"]).upper(),
            destination_code=str(record["destination_code"]).upper(),
            departure_date=parse_iso_date(record.get("departure_date") or departure_date),
            booking_horizon_days=booking_horizon_days,
            airline_code=airline_code,
            airline_name=airline_name_for(airline_code, record.get("airline_name")),
            flight_number=normalize_flight_number(airline_code, record.get("flight_number")),
            cabin_class=normalize_cabin(record.get("cabin_class"), CABIN_ECONOMY),
            fare_family=(str(record["fare_family"]).upper() if record.get("fare_family") else None),
            fare_total=round(total_inr, 2),
            fare_base=(float(record["fare_base"]) if record.get("fare_base") is not None else None),
            fare_taxes=(float(record["fare_taxes"]) if record.get("fare_taxes") is not None else None),
            currency="INR",
            stops=normalize_stops(record.get("stops")),
            is_refundable=normalize_bool(record.get("is_refundable")),
            baggage_kg=normalize_baggage_kg(record.get("baggage_kg")),
            seats_available=record.get("seats_available"),
            source_currency=currency,
            source_fare_total=float(raw_total),
            source_offer_id=record.get("source_offer_id"),
            provenance=record_provenance,
        )


def create(**kwargs: Any) -> OfflineFixtureSource:
    """Registry factory."""
    return OfflineFixtureSource(**kwargs)
