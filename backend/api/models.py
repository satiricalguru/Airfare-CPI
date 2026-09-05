"""
SIH26056 — API request/response models.

Response bodies are assembled as dicts in ``api/serializers.py`` because every index
response carries a common provenance envelope that is more legible built in one place
than spread across a dozen response classes. The Pydantic models here cover REQUEST
validation, where rejecting bad input early genuinely matters.
"""

from __future__ import annotations

from datetime import date
import json
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from config import SUPPORTED_BOOKING_HORIZONS


def _validated_horizons(value: Optional[list[int]]) -> Optional[list[int]]:
    if value is None:
        return None
    if not value:
        raise ValueError("booking horizons cannot be empty")
    invalid = sorted(set(value) - set(SUPPORTED_BOOKING_HORIZONS))
    if invalid:
        raise ValueError(
            f"booking horizons must be selected from "
            f"{list(SUPPORTED_BOOKING_HORIZONS)}; got unsupported {invalid}"
        )
    return list(dict.fromkeys(value))


class CollectionTriggerRequest(BaseModel):
    """Body for POST /api/v1/collection/trigger."""

    # Omitted = the configured COLLECTION_MODE. Supplying a mode explicitly is allowed
    # so an operator can run a simulated cycle on a live deployment for comparison —
    # the result is still labelled SIMULATED DATA.
    mode: Optional[str] = Field(
        default=None, description="LIVE | SIMULATED | OFFLINE. Defaults to COLLECTION_MODE."
    )
    routes: Optional[list[int]] = Field(
        default=None, description="Route ids to collect. Omitted = the whole basket."
    )
    horizons: Optional[list[int]] = Field(
        default=None, description="Booking horizons in days. Omitted = configured horizons."
    )
    collection_day: Optional[date] = Field(
        default=None,
        description=(
            "Reference collection day. Departure dates are computed as "
            "collection_day + horizon."
        ),
    )
    acquisition_method: Optional[str] = Field(
        default=None,
        description="WEB_SCRAPE | API | SIMULATED | OFFLINE_FIXTURE. Defaults according to mode/source.",
    )
    compute_index: bool = Field(
        default=True, description="Recompute indices from stored data after collection."
    )

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        upper = value.strip().upper()
        if upper not in {"LIVE", "SIMULATED", "OFFLINE"}:
            raise ValueError(
                f"mode must be LIVE, SIMULATED or OFFLINE; got {value!r}"
            )
        return upper

    @field_validator("acquisition_method")
    @classmethod
    def _validate_acquisition_method(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        upper = value.strip().upper()
        if upper not in {"WEB_SCRAPE", "API", "SIMULATED", "OFFLINE_FIXTURE"}:
            raise ValueError(
                f"acquisition_method must be WEB_SCRAPE, API, SIMULATED, or OFFLINE_FIXTURE; got {value!r}"
            )
        return upper

    @field_validator("horizons")
    @classmethod
    def _validate_horizons(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return _validated_horizons(value)


class AnomalyReviewRequest(BaseModel):
    """
    Body for POST /api/v1/anomalies/{id}/review.

    ``is_genuine`` is the decision the old schema declared and never recorded:
    True means genuine market volatility (the observation stays in the index),
    False means a collection error (the observation is excluded and a revision is
    logged, because a published figure that used it will change).
    """

    is_genuine: bool = Field(
        description=(
            "True = genuine market movement, kept in the index. "
            "False = collection error, excluded and a revision recorded."
        )
    )
    reviewed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Reviewer identity. Recorded on the anomaly for audit.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)


class CopilotRequest(BaseModel):
    """
    Body for POST /api/v1/copilot/ask.

    Exists so the provider API key stays server-side. The frontend never holds a key.
    """

    question: str = Field(min_length=1, max_length=1200)
    # Retained temporarily for client compatibility. The API deliberately ignores
    # this untrusted browser-supplied material and grounds answers only on server-side
    # persisted figures; validation merely prevents oversized requests in transit.
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Deprecated compatibility field. Server-side data is the sole grounding "
            "source; client context is ignored."
        ),
        deprecated=True,
    )

    @field_validator("context")
    @classmethod
    def _bound_context_size(
        cls, value: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        if value is None:
            return None
        try:
            encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("context must be JSON-serializable") from exc
        if len(encoded) > 4096:
            raise ValueError("context is limited to 4096 UTF-8 bytes")
        return value


class BackfillRequest(BaseModel):
    """
    Body for POST /api/v1/collection/backfill-simulated.

    Seeds a SIMULATED series so the methodology can be demonstrated over a span of
    dates. Always labelled SIMULATED DATA; never a substitute for live collection.
    """

    start_date: date
    end_date: date
    routes: Optional[list[int]] = None
    horizons: Optional[list[int]] = None

    @field_validator("horizons")
    @classmethod
    def _validate_horizons(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return _validated_horizons(value)

    @field_validator("end_date")
    @classmethod
    def _validate_range(cls, value: date, info) -> date:
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("end_date must be on or after start_date")
        if start and (value - start).days > 400:
            raise ValueError("backfill range is limited to 400 days")
        return value


class RouteScrapeRequest(BaseModel):
    """
    Body for POST /api/v1/routes/scrape.
    
    Trigger live or simulated fare scraping for any specific Indian route/city-pair.
    """

    origin: str = Field(min_length=3, max_length=3, description="3-letter IATA code, e.g. PAT")
    destination: str = Field(min_length=3, max_length=3, description="3-letter IATA code, e.g. BLR")
    origin_city: Optional[str] = Field(default=None, description="Origin city name")
    destination_city: Optional[str] = Field(default=None, description="Destination city name")
    mode: Optional[str] = Field(default=None, description="LIVE | SIMULATED | OFFLINE")
    horizons: Optional[list[int]] = Field(default=None, description="Booking horizons in days")
    collection_day: Optional[date] = Field(default=None, description="Collection reference date")
    compute_index: bool = Field(default=True, description="Compute index for the route after scraping")

    @field_validator("origin", "destination")
    @classmethod
    def _validate_iata(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError(f"IATA airport code must be 3 letters, got {value!r}")
        return code

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        upper = value.strip().upper()
        if upper not in {"LIVE", "SIMULATED", "OFFLINE"}:
            raise ValueError(f"mode must be LIVE, SIMULATED or OFFLINE; got {value!r}")
        return upper

    @field_validator("horizons")
    @classmethod
    def _validate_horizons(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        return _validated_horizons(value)
