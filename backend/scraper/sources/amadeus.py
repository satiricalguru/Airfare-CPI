"""
SIH26056 — Amadeus Self-Service adapter. The genuine live fare source.

Why this source
---------------
The problem statement asks for automated collection from airline and OTA portals.
Most Indian OTA and airline booking flows either disallow automated access to their
search paths in robots.txt or gate them behind anti-bot controls. Defeating those is
circumvention of an access control, so those adapters are registered as disabled
with their reasons recorded (see ``disabled_otas.py``) rather than implemented.

Amadeus for Developers is a documented, publicly available REST API with published
rate limits and terms of use, and its Flight Offers Search endpoint returns real
priced flight offers, including Indian domestic city pairs, in INR. It is a genuine
external fare source that can be used as intended rather than against its own rules,
which is why it is the one live adapter implemented end to end.

Endpoints (both official and documented):
  POST {host}/v1/security/oauth2/token          OAuth2 client_credentials
  GET  {host}/v2/shopping/flight-offers         Flight Offers Search

  host = https://test.api.amadeus.com   (test tier, free monthly quota)
       = https://api.amadeus.com        (production)

Honesty properties
------------------
* No credentials are committed and there is no fallback key. Without
  ``AMADEUS_CLIENT_ID`` / ``AMADEUS_CLIENT_SECRET`` the adapter reports
  ``UNAVAILABLE`` and returns zero observations.
* Every failure path returns a failure result. There is no branch that produces
  synthetic data when a request fails.
* Rate limiting is enforced client-side against the documented test-tier ceiling of
  one request per 100 ms, with a more conservative default.
* Retries are bounded and only for transient statuses.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx
from loguru import logger

from config import AmadeusSettings, ScraperSettings, get_settings
from provenance import (
    COLLECTOR_VERSION,
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
    payload_hash,
)
from scraper.base import (
    BaseFareSource,
    CABIN_ECONOMY,
    FareObservation,
    SourceCapability,
    SourceResult,
)
from scraper.normalizer import (
    CurrencyNotSupported,
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
from scraper.politeness import HostRateLimiter, RetryPolicy, honest_headers


SOURCE_NAME = "amadeus"


def describe(settings: Optional[AmadeusSettings] = None) -> SourceCapability:
    """
    Capability, including whether credentials are present.

    Reported as disabled with a plain reason when unconfigured, so a deployment
    running without credentials says SOURCE UNAVAILABLE rather than appearing to
    have a working live source.
    """
    settings = settings or get_settings().amadeus
    configured = settings.is_configured
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="Amadeus Self-Service (Flight Offers Search)",
        source_type=SourceType.LIVE,
        enabled=configured,
        disabled_reason=(
            None
            if configured
            else (
                "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are not set. Register a free "
                "self-service application at developers.amadeus.com and supply the "
                "credentials as server-side environment variables. No key is bundled "
                "with this repository."
            )
        ),
        requires_credentials=True,
        homepage="https://developers.amadeus.com/self-service",
        terms_url="https://developers.amadeus.com/self-service/apis-docs/policies",
        robots_url=None,  # Documented REST API, not a crawled web path.
        compliance_note=(
            "Accessed as a documented public REST API under its published terms of use, "
            "using issued credentials. Client-side rate limiting is applied to stay "
            "within the documented request ceiling. No access control is circumvented."
        ),
        supports_cabin=("ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"),
        native_currency="INR",
    )


class AmadeusTokenError(RuntimeError):
    """Token acquisition failed."""


class AmadeusFareSource(BaseFareSource):
    """Live fare source backed by the Amadeus Flight Offers Search API."""

    def __init__(
        self,
        amadeus: Optional[AmadeusSettings] = None,
        scraper: Optional[ScraperSettings] = None,
        client: Optional[httpx.AsyncClient] = None,
        rate_limiter: Optional[HostRateLimiter] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        settings = get_settings()
        self.amadeus = amadeus or settings.amadeus
        self.scraper = scraper or settings.scraper

        super().__init__(describe(self.amadeus))

        self._client = client
        self._owns_client = client is None
        self._rate_limiter = rate_limiter or HostRateLimiter(
            min_interval_seconds=self.amadeus.min_request_interval_seconds,
            jitter_seconds=0.05,
        )
        self._retry = retry_policy or RetryPolicy(
            max_attempts=max(1, self.scraper.max_retries + 1),
            base_seconds=self.scraper.retry_backoff_base_seconds,
            max_seconds=self.scraper.retry_backoff_max_seconds,
        )

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ── HTTP plumbing ──

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.amadeus.timeout_seconds,
                headers=honest_headers(self.scraper.user_agent),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def _ensure_token(self) -> str:
        """
        Fetch or reuse an OAuth2 access token.

        Refreshed 60 s early so a token cannot expire mid-request.
        """
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        client = await self._http()
        await self._rate_limiter.acquire(self.amadeus.token_url)

        try:
            resp = await client.post(
                self.amadeus.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus.client_id,
                    "client_secret": self.amadeus.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as exc:
            raise AmadeusTokenError(
                f"could not reach the Amadeus token endpoint: {type(exc).__name__}: {exc}"
            ) from exc

        if resp.status_code != 200:
            # Deliberately does not echo the response body: it can contain the
            # submitted client_id.
            raise AmadeusTokenError(
                f"token request rejected with HTTP {resp.status_code}. Verify "
                f"AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET and that the credentials "
                f"match AMADEUS_ENVIRONMENT={self.amadeus.environment!r}."
            )

        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise AmadeusTokenError("token response contained no access_token")

        expires_in = float(payload.get("expires_in", 1799))
        self._access_token = token
        self._token_expires_at = time.monotonic() + max(30.0, expires_in - 60.0)
        logger.debug(f"Amadeus token acquired, valid for ~{int(expires_in)}s")
        return token

    # ── collection ──

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
        request_id = new_request_id()
        started = time.monotonic()

        try:
            token = await self._ensure_token()
        except AmadeusTokenError as exc:
            return SourceResult.unavailable(
                SOURCE_NAME,
                f"Amadeus authentication failed: {exc}",
                error_type="authentication_failed",
            )

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date.isoformat(),
            "adults": max(1, int(passengers)),
            "travelClass": normalize_cabin(cabin, CABIN_ECONOMY),
            # Request INR directly so no exchange rate is ever needed.
            "currencyCode": "INR",
            "nonStop": "false",
            "max": self.amadeus.max_offers_per_search,
        }

        client = await self._http()
        last_error: Optional[str] = None
        last_status: Optional[int] = None
        attempts = 0

        for attempt in range(1, self._retry.max_attempts + 1):
            attempts = attempt
            await self._retry.sleep_before(attempt)
            await self._rate_limiter.acquire(self.amadeus.flight_offers_url)

            try:
                resp = await client.get(
                    self.amadeus.flight_offers_url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                last_status = None
                logger.warning(
                    f"Amadeus {origin}-{destination} attempt {attempt}: {last_error}"
                )
                continue

            last_status = resp.status_code

            if resp.status_code == 200:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                return self._build_result(
                    payload_text=resp.text,
                    payload=resp.json(),
                    route_id=route_id,
                    origin=origin,
                    destination=destination,
                    booking_horizon_days=booking_horizon_days,
                    request_id=request_id,
                    response_time_ms=elapsed_ms,
                    attempts=attempts,
                    source_url=str(resp.url),
                )

            if resp.status_code == 401:
                # Token may have been revoked; drop it and retry once with a new one.
                self._access_token = None
                self._token_expires_at = 0.0
                try:
                    token = await self._ensure_token()
                    last_error = "authorization rejected; token refreshed"
                    continue
                except AmadeusTokenError as exc:
                    return SourceResult.unavailable(
                        SOURCE_NAME,
                        f"Amadeus authorization rejected and re-authentication failed: {exc}",
                        error_type="authentication_failed",
                    )

            if self._retry.should_retry_status(resp.status_code):
                last_error = f"HTTP {resp.status_code} (retryable)"
                logger.warning(
                    f"Amadeus {origin}-{destination} attempt {attempt}: {last_error}"
                )
                continue

            # Non-retryable: report and stop. Repeating a rejected request is not
            # politeness, and it will not change the answer.
            return SourceResult.failed(
                SOURCE_NAME,
                f"Amadeus rejected the request for {origin}-{destination} on "
                f"{departure_date.isoformat()} with HTTP {resp.status_code}: "
                f"{_safe_error_detail(resp)}",
                error_type="http_error",
                http_status=resp.status_code,
                attempts=attempts,
                response_time_ms=int((time.monotonic() - started) * 1000),
            )

        return SourceResult.failed(
            SOURCE_NAME,
            f"Amadeus collection for {origin}-{destination} on "
            f"{departure_date.isoformat()} failed after {attempts} attempt(s): "
            f"{last_error or 'unknown error'}",
            error_type="retries_exhausted",
            http_status=last_status,
            attempts=attempts,
            response_time_ms=int((time.monotonic() - started) * 1000),
        )

    # ── payload -> observations ──

    def _build_result(
        self,
        payload_text: str,
        payload: dict[str, Any],
        route_id: int,
        origin: str,
        destination: str,
        booking_horizon_days: int,
        request_id: str,
        response_time_ms: int,
        attempts: int,
        source_url: str,
    ) -> SourceResult:
        offers = payload.get("data") or []
        carriers = ((payload.get("dictionaries") or {}).get("carriers") or {})

        if not offers:
            # A well-formed empty result is not an error, but it is also not data.
            # Reported as FAILED so the run records that this route/horizon produced
            # nothing, rather than the index silently treating it as a gap.
            return SourceResult.failed(
                SOURCE_NAME,
                f"Amadeus returned no flight offers for {origin}-{destination} "
                f"(horizon T+{booking_horizon_days}).",
                error_type="no_offers_returned",
                http_status=200,
                attempts=attempts,
                response_time_ms=response_time_ms,
            )

        provenance = DataProvenance(
            source_type=SourceType.LIVE,
            source_name=SOURCE_NAME,
            collection_timestamp=datetime.now(timezone.utc),
            request_id=request_id,
            collector_version=COLLECTOR_VERSION,
            source_url=_strip_credentials(source_url),
            raw_payload_hash=payload_hash(payload_text),
            notes={
                "amadeus_environment": self.amadeus.environment,
                "offers_returned": len(offers),
            },
        )

        builders = []
        for offer in offers:
            context = {
                "source": SOURCE_NAME,
                "route_id": route_id,
                "offer_id": offer.get("id"),
                "origin": origin,
                "destination": destination,
            }
            builders.append(
                (
                    context,
                    lambda offer=offer: self._normalize_offer(
                        offer=offer,
                        carriers=carriers,
                        route_id=route_id,
                        origin=origin,
                        destination=destination,
                        booking_horizon_days=booking_horizon_days,
                        provenance=provenance,
                    ),
                )
            )

        outcome = collect_normalized(builders)

        if not outcome.observations:
            return SourceResult.failed(
                SOURCE_NAME,
                f"Amadeus returned {len(offers)} offer(s) for {origin}-{destination} "
                f"but none could be normalized: {outcome.summary()['drop_reasons']}",
                error_type="normalization_failed",
                http_status=200,
                attempts=attempts,
                response_time_ms=response_time_ms,
            )

        logger.info(
            f"Amadeus {origin}-{destination} T+{booking_horizon_days}: "
            f"{len(outcome.observations)} observation(s) from {len(offers)} offer(s)"
            + (f", {outcome.dropped_count} dropped" if outcome.dropped_count else "")
        )

        return SourceResult(
            source_name=SOURCE_NAME,
            status=CollectionStatus.SUCCESS,
            observations=tuple(outcome.observations),
            response_time_ms=response_time_ms,
            request_id=request_id,
            source_url=_strip_credentials(source_url),
            attempts=attempts,
        )

    def _normalize_offer(
        self,
        offer: dict[str, Any],
        carriers: dict[str, str],
        route_id: int,
        origin: str,
        destination: str,
        booking_horizon_days: int,
        provenance: DataProvenance,
    ) -> Optional[FareObservation]:
        """Map one Amadeus flight offer onto a canonical FareObservation."""
        itineraries = offer.get("itineraries") or []
        if not itineraries:
            raise NormalizationError("offer has no itineraries")

        segments = itineraries[0].get("segments") or []
        if not segments:
            raise NormalizationError("offer itinerary has no segments")

        first, last = segments[0], segments[-1]

        # Reject offers that do not actually serve the requested city pair. The
        # index compares like with like; an alternate-airport offer is a different
        # product and would corrupt the matched-model comparison.
        actual_origin = str((first.get("departure") or {}).get("iataCode", "")).upper()
        actual_destination = str((last.get("arrival") or {}).get("iataCode", "")).upper()
        if actual_origin != origin.upper() or actual_destination != destination.upper():
            raise NormalizationError(
                f"offer routes {actual_origin}-{actual_destination}, "
                f"requested {origin}-{destination}"
            )

        price = offer.get("price") or {}
        currency = str(price.get("currency") or "INR").upper()
        raw_total = price.get("grandTotal") or price.get("total")
        if raw_total is None:
            raise NormalizationError("offer has no total price")

        try:
            total_source = float(raw_total)
        except (TypeError, ValueError) as exc:
            raise NormalizationError(f"unparseable total price {raw_total!r}") from exc

        total_inr, fx_rate = to_inr(total_source, currency)

        base_source = price.get("base")
        base_inr: Optional[float] = None
        if base_source is not None:
            try:
                base_inr = to_inr(float(base_source), currency)[0]
            except (TypeError, ValueError, CurrencyNotSupported):
                base_inr = None

        taxes_inr = (
            round(total_inr - base_inr, 2)
            if base_inr is not None and total_inr >= base_inr
            else None
        )

        airline_code = normalize_airline_code(
            first.get("carrierCode")
            or (offer.get("validatingAirlineCodes") or [None])[0]
        )

        traveler = (offer.get("travelerPricings") or [{}])[0]
        fare_details = (traveler.get("fareDetailsBySegment") or [{}])[0]

        cabin = normalize_cabin(fare_details.get("cabin"), CABIN_ECONOMY)

        # Prefer the carrier's branded fare name; fall back to Amadeus's fareOption
        # then the fare basis code. Fare family is a matched-model dimension, so a
        # stable identifier matters more than a pretty one.
        fare_family = (
            fare_details.get("brandedFare")
            or fare_details.get("brandedFareLabel")
            or traveler.get("fareOption")
            or fare_details.get("fareBasis")
        )
        if fare_family:
            fare_family = str(fare_family).strip().upper()

        stops = normalize_stops(
            first.get("numberOfStops") if len(segments) == 1 else None,
            segments=len(segments),
        )

        bags = fare_details.get("includedCheckedBags") or {}
        baggage_kg = None
        if str(bags.get("weightUnit", "")).upper() == "KG":
            baggage_kg = normalize_baggage_kg(bags.get("weight"))
        elif bags.get("weight") is not None:
            baggage_kg = normalize_baggage_kg(bags.get("weight"))
        # A piece-based allowance stays None: converting pieces to kg would require
        # assuming a per-piece weight the API did not state.

        refundable = normalize_bool(
            (offer.get("pricingOptions") or {}).get("refundableFare")
        )

        seats = offer.get("numberOfBookableSeats")
        try:
            seats_available = int(seats) if seats is not None else None
        except (TypeError, ValueError):
            seats_available = None

        obs_provenance = provenance
        if fx_rate is not None:
            obs_provenance = DataProvenance(
                source_type=provenance.source_type,
                source_name=provenance.source_name,
                collection_timestamp=provenance.collection_timestamp,
                request_id=provenance.request_id,
                collector_version=provenance.collector_version,
                source_url=provenance.source_url,
                raw_payload_hash=provenance.raw_payload_hash,
                notes={
                    **provenance.notes,
                    "fx_source_currency": currency,
                    "fx_rate_to_inr": fx_rate,
                },
            )

        return FareObservation(
            route_id=route_id,
            origin_code=actual_origin,
            destination_code=actual_destination,
            departure_date=parse_iso_date((first.get("departure") or {}).get("at")),
            booking_horizon_days=booking_horizon_days,
            airline_code=airline_code,
            airline_name=airline_name_for(
                airline_code, _titleize(carriers.get(airline_code))
            ),
            flight_number=normalize_flight_number(airline_code, first.get("number")),
            cabin_class=cabin,
            fare_family=fare_family,
            fare_total=round(total_inr, 2),
            fare_base=round(base_inr, 2) if base_inr is not None else None,
            fare_taxes=taxes_inr,
            currency="INR",
            stops=stops,
            is_refundable=refundable,
            baggage_kg=baggage_kg,
            seats_available=seats_available,
            source_currency=currency,
            source_fare_total=total_source,
            source_offer_id=str(offer.get("id")) if offer.get("id") is not None else None,
            provenance=obs_provenance,
        )


# ── helpers ──

def _titleize(name: Optional[str]) -> Optional[str]:
    """Amadeus returns carrier names uppercased ("INDIGO")."""
    if not name:
        return None
    return " ".join(part.capitalize() for part in str(name).split())


def _strip_credentials(url: str) -> str:
    """Record the request path without any query string, which can echo parameters."""
    return url.split("?", 1)[0]


def _safe_error_detail(resp: httpx.Response) -> str:
    """
    Extract a short error description without echoing an entire payload.

    Amadeus error bodies are structured; only title/detail are surfaced.
    """
    try:
        body = resp.json()
    except Exception:
        return "(no parseable error body)"

    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        title = first.get("title") or ""
        detail = first.get("detail") or ""
        return f"{title}: {detail}".strip(": ") or "(unspecified error)"
    return "(unspecified error)"


def create(**kwargs: Any) -> AmadeusFareSource:
    """Registry factory."""
    return AmadeusFareSource(**kwargs)
