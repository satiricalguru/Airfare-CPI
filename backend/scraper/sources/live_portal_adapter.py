"""
SIH26056 — Multi-Source Live Portal Web Scraper Adapter.

Coordinates automated, ethical web scraping across Indian scheduled passenger flight portals
using headless Playwright (Chromium):
- Compliant with source governance and robots.txt (/travel/flights search is allowed).
- Extracts live real-time flight quotes for IndiGo (6E), Air India (AI), Akasa Air (QP),
  SpiceJet (SG), and Air India Express (IX).
- Captures departure & arrival times, departure time bands (4 standard strata), stops,
  and decomposes statutory Indian civil aviation fees (base fare, GST, UDF, convenience fee).
- Attaches mandatory DataProvenance with AcquisitionMethod.WEB_SCRAPE.
- Provides robust error handling (timeouts, CAPTCHAs, bot gates) with non-evasion circuit breaking.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime, timezone
from typing import Any, Optional
import urllib.parse

from loguru import logger

from provenance import (
    COLLECTOR_VERSION,
    AcquisitionMethod,
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
    payload_hash,
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

SOURCE_NAME = "live_portal"

AIRLINE_IATA_MAP: dict[str, tuple[str, str]] = {
    "INDIGO": ("6E", "IndiGo"),
    "AIR INDIA EXPRESS": ("IX", "Air India Express"),
    "AIR INDIA": ("AI", "Air India"),
    "AKASA AIR": ("QP", "Akasa Air"),
    "AKASA": ("QP", "Akasa Air"),
    "SPICEJET": ("SG", "SpiceJet"),
    "VISTARA": ("AI", "Air India"),
}

CAPTCHA_HINTS = ("captcha", "recaptcha", "hcaptcha", "challenge", "unusual traffic")


def detect_block(title: str, html: str, status: Optional[int]) -> bool:
    """Detect bot walls, dynamic challenges, or HTTP 403/429 denials."""
    if status in (403, 429):
        return True
    blob = f"{title} {html[:4000]}".lower()
    return any(h in blob for h in CAPTCHA_HINTS)


def describe() -> SourceCapability:
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="Multi-Source Airline & OTA Web Scraper (Playwright/HTTP)",
        source_type=SourceType.LIVE,
        enabled=True,
        disabled_reason=None,
        requires_credentials=False,
        homepage="https://www.google.com/travel/flights",
        terms_url="https://policies.google.com/terms",
        robots_url="https://www.google.com/robots.txt",
        compliance_note=(
            "Extracts live public flight quotes using polite rates and ethical scraping safeguards. "
            "Attaches DataProvenance with AcquisitionMethod.WEB_SCRAPE."
        ),
        supports_cabin=(CABIN_ECONOMY,),
        native_currency="INR",
    )


class LivePortalFareSource(BaseFareSource):
    """
    Live web scraper adapter capable of automated scheduled extraction
    from domestic flight portals via Playwright and BrowserCollector.
    """

    def __init__(
        self,
        capability: Optional[SourceCapability] = None,
        timeout_seconds: float = 35.0,
        user_agent: str = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        collector: Optional[BrowserCollector] = None,
    ):
        super().__init__(capability or describe())
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.collector = collector or BrowserCollector(
            timeout_seconds=timeout_seconds,
            browser_user_agent=user_agent,
        )

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
        origin_code = origin
        destination_code = destination
        started_at = time.time()
        req_id = new_request_id()

        # Public search URL conforming to registered pattern
        search_url = (
            f"https://www.google.com/travel/flights?q=Flights%20to%20{destination_code}"
            f"%20from%20{origin_code}%20on%20{departure_date.isoformat()}%20oneway"
        )
        logger.info(
            f"Playwright live scraping {origin_code}->{destination_code} on {departure_date} "
            f"(horizon T+{booking_horizon_days})"
        )

        try:
            acq_res, raw_text_rows = await self.collector.fetch_page_and_cards(
                source_id=SOURCE_NAME,
                url=search_url,
                card_selectors=("div.yR1fYc", "li.pIavfa"),
                wait_selector="div.yR1fYc, li.pIavfa",
                settle_ms=3500,
            )

            # Fallback parsing from sanitized HTML if card text locator was empty
            if not raw_text_rows and acq_res.html_content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(acq_res.html_content, "html.parser")
                cards = soup.select("div.yR1fYc, li.pIavfa")
                for c in cards:
                    txt = c.get_text(separator="\n", strip=True)
                    if txt and "₹" in txt:
                        raw_text_rows.append(txt)

            observations = self._parse_and_build_observations(
                raw_text_rows=raw_text_rows,
                route_id=route_id,
                origin_code=origin_code,
                destination_code=destination_code,
                departure_date=departure_date,
                booking_horizon_days=booking_horizon_days,
                search_url=search_url,
                request_id=req_id,
                cabin=cabin,
                artifact_id=acq_res.stored_artifact.artifact_id,
                artifact_sha256=acq_res.stored_artifact.sha256,
            )

            latency_ms = int((time.time() - started_at) * 1000)
            logger.info(
                f"Playwright extracted {len(observations)} live flight observations for "
                f"{origin_code}->{destination_code} in {latency_ms}ms"
            )

            return SourceResult(
                source_name=SOURCE_NAME,
                status=CollectionStatus.SUCCESS if observations else CollectionStatus.FAILED,
                observations=tuple(observations),
                error_message=None if observations else "No valid flight cards parsed from portal response.",
                error_type=None if observations else "empty_portal_response",
                attempts=1,
                response_time_ms=latency_ms,
            )

        except CaptchaChallengeError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"Live scraper challenged on {search_url}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Bot challenge rendered on {SOURCE_NAME}: {exc}",
                error_type="captcha_challenge",
                response_time_ms=latency_ms,
            )
        except PolicyBlockError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"Governance policy blocked {search_url}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Governance policy blocked: {exc}",
                error_type="policy_block",
                response_time_ms=latency_ms,
            )
        except AcquisitionTimeoutError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"Live scraper timeout for {origin_code}->{destination_code}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Portal navigation timed out: {exc}",
                error_type="timeout",
                response_time_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.error(
                f"Playwright scraper error for {origin_code}->{destination_code}: {type(exc).__name__}: {exc}"
            )
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Scraper error: {type(exc).__name__}: {exc}",
                error_type="adapter_exception",
                response_time_ms=latency_ms,
            )

    def _parse_and_build_observations(
        self,
        raw_text_rows: list[str],
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

        for txt in raw_text_rows:
            # 1. Identify carrier
            txt_upper = txt.upper()
            carrier_code, carrier_name = "UNKNOWN", "Unknown Airline"
            for name, (code, cname) in AIRLINE_IATA_MAP.items():
                if name in txt_upper:
                    carrier_code, carrier_name = code, cname
                    break

            if carrier_code == "UNKNOWN":
                continue

            # 2. Extract total price (INR)
            price_match = re.search(r"₹\s*([\d,]+)", txt)
            if not price_match:
                continue
            try:
                total_fare = float(price_match.group(1).replace(",", ""))
            except ValueError:
                continue

            if total_fare < 500 or total_fare > 80000:
                continue

            # 3. Extract departure & arrival times
            times = re.findall(r"(\d{1,2}:\d{2}\s*[AP]M)", txt)
            dep_time = times[0].replace("\u202f", " ") if len(times) >= 1 else None
            arr_time = times[1].replace("\u202f", " ") if len(times) >= 2 else None
            dep_time_band = classify_time_band(dep_time)

            # 4. Stops
            stops = 0 if any(k in txt.lower() for k in ("nonstop", "non-stop", "0 stop")) else 1

            # 5. Deterministic surrogate flight identifier: carrier + sector + dep-slug
            dep_slug = re.sub(r"[^\w]", "", dep_time or "0000")
            flight_no = f"{carrier_code}-{origin_code}{destination_code}-{dep_slug}"
            dedupe_key = f"{carrier_code}_{flight_no}_{departure_date}_{dep_time}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            # 6. Decompose statutory civil aviation fees using AERA Tariff Orders
            decomp = unbundle_statutory_tariff(
                total_fare=total_fare,
                origin_code=origin_code,
                convenience_fee=300.0,
            )

            raw_rep = f"{flight_no}|{carrier_code}|{total_fare}|{dep_time}|{stops}"
            prov = DataProvenance.for_web_scrape(
                source_name=SOURCE_NAME,
                source_url=search_url,
                request_id=request_id,
                raw_payload=raw_rep,
                timestamp=utc_now(),
                notes={
                    "collector": "PlaywrightPortalCollector",
                    "horizon": booking_horizon_days,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "time_band": dep_time_band,
                    "artifact_id": artifact_id,
                    "artifact_sha256": artifact_sha256,
                    "decomposition_method": decomp["decomposition_method"],
                    "is_estimated": decomp["is_estimated"],
                    "udf_airport": decomp["udf_airport"],
                    "is_surrogate": True,
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
                baggage_kg=None,  # Summary cards do not expose check-in allowance
                fare_base=decomp["base_fare"],
                fare_taxes=decomp["taxes"],
                fare_udf=decomp["udf"],
                fare_convenience=decomp["convenience"],
                fare_total=total_fare,
                currency="INR",
                source_currency="INR",
                source_fare_total=total_fare,
                seats_available=None,  # Summary cards do not expose seat count
                dep_time=dep_time,
                dep_time_band=dep_time_band,
                provenance=prov,
            )
            observations.append(obs)

        return observations


def create(**kwargs: Any) -> LivePortalFareSource:
    return LivePortalFareSource(**kwargs)
