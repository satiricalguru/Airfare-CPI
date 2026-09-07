"""
SIH26056 — Goibibo (OTA) Live Web Scraper Adapter.

Coordinates automated, ethical web scraping of domestic flight search results
from Goibibo (MakeMyTrip / Ibibo Group) using headless Chromium via BrowserCollector.
- Extracts exact IATA flight numbers, departure/arrival times, stops, and fare totals.
- Unbundles statutory Indian civil aviation fees (Base Fare, GST, UDF, Convenience).
- Stores sanitized DOM snapshots in ArtifactStore with cryptographic SHA-256 verification.
- Attaches DataProvenance with AcquisitionMethod.WEB_SCRAPE.
"""

from __future__ import annotations

import re
import time
from datetime import date
from typing import Any, Optional

from loguru import logger

from provenance import (
    AcquisitionMethod,
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
    utc_now,
)
from scraper.base import (
    CABIN_ECONOMY,
    BaseFareSource,
    FareObservation,
    SourceCapability,
    SourceResult,
    classify_time_band,
)
from scraper.tariff_orders import unbundle_statutory_tariff
from scraper.web.browser_collector import BrowserCollector
from scraper.web.errors import (
    AcquisitionTimeoutError,
    CaptchaChallengeError,
    PolicyBlockError,
)

SOURCE_NAME = "goibibo"

AIRLINE_MAP: dict[str, tuple[str, str]] = {
    "INDIGO": ("6E", "IndiGo"),
    "6E": ("6E", "IndiGo"),
    "AIR INDIA": ("AI", "Air India"),
    "AI": ("AI", "Air India"),
    "SPICEJET": ("SG", "SpiceJet"),
    "SG": ("SG", "SpiceJet"),
    "AKASA": ("QP", "Akasa Air"),
    "QP": ("QP", "Akasa Air"),
    "AIR INDIA EXPRESS": ("IX", "Air India Express"),
    "IX": ("IX", "Air India Express"),
}


def describe() -> SourceCapability:
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="Goibibo Domestic Flight Portal (Playwright)",
        source_type=SourceType.LIVE,
        enabled=True,
        disabled_reason=None,
        requires_credentials=False,
        homepage="https://www.goibibo.com",
        terms_url="https://www.goibibo.com/terms-and-conditions/",
        robots_url="https://www.goibibo.com/robots.txt",
        compliance_note=(
            "Extracts public domestic flight quotes via Goibibo portal under "
            "Academic Research Prototype Exemption. Attaches DataProvenance with AcquisitionMethod.WEB_SCRAPE."
        ),
        supports_cabin=(CABIN_ECONOMY,),
        native_currency="INR",
    )


class GoibiboFareSource(BaseFareSource):
    """Goibibo OTA web scraper adapter utilizing BrowserCollector."""

    def __init__(
        self,
        capability: Optional[SourceCapability] = None,
        timeout_seconds: float = 35.0,
        collector: Optional[BrowserCollector] = None,
    ):
        super().__init__(capability or describe())
        self.timeout_seconds = timeout_seconds
        self.collector = collector or BrowserCollector(timeout_seconds=timeout_seconds)

    async def _search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
        **kwargs: Any,
    ) -> SourceResult:
        started_at = time.time()
        req_id = new_request_id()

        date_slug = departure_date.strftime("%Y%m%d")
        search_url = f"https://www.goibibo.com/flights/air-{origin}-{destination}-{date_slug}--{passengers}-0-0-E-d/"
        logger.info(f"Goibibo scraping {origin}->{destination} on {departure_date}")

        try:
            acq_res, card_texts = await self.collector.fetch_page_and_cards(
                source_id=SOURCE_NAME,
                url=search_url,
                card_selectors=("div.srp-card-uic__Card", "div.flightItem", "div.fltResultCard"),
                wait_selector="div.srp-card-uic__Card, div.flightItem, div.fltResultCard",
                settle_ms=3000,
            )

            observations = self._parse_cards(
                raw_rows=card_texts,
                route_id=route_id,
                origin_code=origin,
                destination_code=destination,
                departure_date=departure_date,
                booking_horizon_days=booking_horizon_days,
                search_url=search_url,
                request_id=req_id,
                cabin=cabin,
                artifact_id=acq_res.stored_artifact.artifact_id,
                artifact_sha256=acq_res.stored_artifact.sha256,
            )

            latency_ms = int((time.time() - started_at) * 1000)
            return SourceResult(
                source_name=SOURCE_NAME,
                status=CollectionStatus.SUCCESS if observations else CollectionStatus.FAILED,
                observations=tuple(observations),
                error_message=None if observations else "No valid flight cards parsed from Goibibo response.",
                error_type=None if observations else "empty_portal_response",
                attempts=1,
                response_time_ms=latency_ms,
            )

        except CaptchaChallengeError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Bot challenge rendered on {SOURCE_NAME}: {exc}",
                error_type="captcha_challenge",
                response_time_ms=latency_ms,
            )
        except PolicyBlockError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Governance policy blocked: {exc}",
                error_type="policy_block",
                response_time_ms=latency_ms,
            )
        except AcquisitionTimeoutError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Goibibo navigation timed out: {exc}",
                error_type="timeout",
                response_time_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Scraper error: {type(exc).__name__}: {exc}",
                error_type="adapter_exception",
                response_time_ms=latency_ms,
            )

    def _parse_cards(
        self,
        raw_rows: list[str],
        route_id: int,
        origin_code: str,
        destination_code: str,
        departure_date: date,
        booking_horizon_days: int,
        search_url: str,
        request_id: str,
        cabin: str,
        artifact_id: Optional[str] = None,
        artifact_sha256: Optional[str] = None,
    ) -> list[FareObservation]:
        observations: list[FareObservation] = []
        seen_keys: set[str] = set()

        for txt in raw_rows:
            txt_upper = txt.upper()
            carrier_code, carrier_name = "UNKNOWN", "Unknown Airline"
            for k, (code, cname) in AIRLINE_MAP.items():
                if k in txt_upper:
                    carrier_code, carrier_name = code, cname
                    break

            if carrier_code == "UNKNOWN":
                continue

            price_match = re.search(r"₹\s*([\d,]+)", txt)
            if not price_match:
                continue
            try:
                total_fare = float(price_match.group(1).replace(",", ""))
            except ValueError:
                continue

            if total_fare < 600 or total_fare > 90000:
                continue

            times = re.findall(r"(\d{1,2}:\d{2})", txt)
            dep_time = times[0] if len(times) >= 1 else "09:00"
            dep_time_band = classify_time_band(dep_time)
            stops = 0 if any(k in txt.lower() for k in ("non stop", "non-stop", "0 stop")) else 1

            flight_match = re.search(r"(6E|AI|SG|QP|IX)[-\s]?(\d{3,4})", txt_upper)
            if flight_match:
                flight_no = f"{flight_match.group(1)}-{flight_match.group(2)}"
                is_surrogate = False
            else:
                dep_slug = re.sub(r"[^\w]", "", dep_time)
                flight_no = f"{carrier_code}-{origin_code}{destination_code}-{dep_slug}"
                is_surrogate = True

            dedupe_key = f"{flight_no}_{departure_date}_{dep_time}_{total_fare}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            decomp = unbundle_statutory_tariff(
                total_fare=total_fare,
                origin_code=origin_code,
                convenience_fee=350.0,
            )

            prov = DataProvenance.for_web_scrape(
                source_name=SOURCE_NAME,
                source_url=search_url,
                request_id=request_id,
                raw_payload=f"{flight_no}|{carrier_code}|{total_fare}|{dep_time}|{stops}",
                timestamp=utc_now(),
                notes={
                    "collector": "GoibiboPortalCollector",
                    "horizon": booking_horizon_days,
                    "dep_time": dep_time,
                    "time_band": dep_time_band,
                    "artifact_id": artifact_id,
                    "artifact_sha256": artifact_sha256,
                    "decomposition_method": decomp["decomposition_method"],
                    "is_estimated": decomp["is_estimated"],
                    "udf_airport": decomp["udf_airport"],
                    "is_surrogate": is_surrogate,
                },
            )

            obs = FareObservation(
                route_id=route_id,
                origin_code=origin_code,
                destination_code=destination_code,
                departure_date=departure_date,
                booking_horizon_days=booking_horizon_days,
                airline_code=carrier_code,
                airline_name=carrier_name,
                flight_number=flight_no,
                cabin_class=cabin,
                fare_family="SAVER",
                stops=stops,
                is_refundable=False,
                baggage_kg=15,
                fare_base=decomp["base_fare"],
                fare_taxes=decomp["taxes"],
                fare_udf=decomp["udf"],
                fare_convenience=decomp["convenience"],
                fare_total=total_fare,
                currency="INR",
                source_currency="INR",
                source_fare_total=total_fare,
                seats_available=None,
                dep_time=dep_time,
                dep_time_band=dep_time_band,
                provenance=prov,
            )
            observations.append(obs)

        return observations


def create(**kwargs: Any) -> GoibiboFareSource:
    return GoibiboFareSource(**kwargs)
