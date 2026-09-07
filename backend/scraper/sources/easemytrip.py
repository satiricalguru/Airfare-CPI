"""
SIH26056 — EaseMyTrip (OTA) Live Web Scraper Adapter.

Coordinates automated, ethical web scraping of live domestic flight search results
from EaseMyTrip (Easy Trip Planners Ltd.) using headless Chromium via BrowserCollector:
- Extracts exact IATA flight numbers (e.g. 6E-205, SG-162, AI-887), scheduled departure/arrival
  times, duration, direct/stops, fare families (Saver/Flex), and check-in baggage allowances.
- Applies standard AERA/MoCA statutory civil aviation fee unbundling (Base Fare, GST, UDF, Convenience).
- Stores full sanitized HTML DOM snapshots in ArtifactStore with cryptographic SHA-256 verification.
- Attaches DataProvenance with AcquisitionMethod.WEB_SCRAPE.
- Complies with ethical scraping standards: polite request rate, non-evasion circuit breakers.
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

SOURCE_NAME = "easemytrip"

CARRIER_NAME_MAP: dict[str, str] = {
    "6E": "IndiGo",
    "AI": "Air India",
    "SG": "SpiceJet",
    "QP": "Akasa Air",
    "IX": "Air India Express",
    "I5": "Air India Express",
    "UK": "Air India",
}

AIRLINE_KEYWORD_MAP: dict[str, tuple[str, str]] = {
    "INDIGO": ("6E", "IndiGo"),
    "AIR INDIA EXPRESS": ("IX", "Air India Express"),
    "AIR INDIA": ("AI", "Air India"),
    "AKASA AIR": ("QP", "Akasa Air"),
    "AKASA": ("QP", "Akasa Air"),
    "SPICEJET": ("SG", "SpiceJet"),
    "VISTARA": ("AI", "Air India"),
}

# Major airport IATA -> EaseMyTrip city name mapping
CITY_MAP: dict[str, str] = {
    "DEL": "Delhi",
    "BOM": "Mumbai",
    "BLR": "Bangalore",
    "MAA": "Chennai",
    "CCU": "Kolkata",
    "HYD": "Hyderabad",
    "AMD": "Ahmedabad",
    "PNQ": "Pune",
    "GOI": "Goa",
    "GOX": "Goa",
    "JAI": "Jaipur",
    "LKO": "Lucknow",
    "COK": "Kochi",
    "TRV": "Thiruvananthapuram",
    "IXC": "Chandigarh",
    "PAT": "Patna",
    "BBI": "Bhubaneswar",
    "GAU": "Guwahati",
    "SXR": "Srinagar",
    "ATQ": "Amritsar",
    "VTZ": "Visakhapatnam",
    "IXB": "Bagdogra",
    "IDR": "Indore",
    "VNS": "Varanasi",
    "BDQ": "Vadodara",
    "RPR": "Raipur",
    "NAG": "Nagpur",
    "IXE": "Mangalore",
    "CJB": "Coimbatore",
    "IXM": "Madurai",
    "TRZ": "Tiruchirappalli",
    "UDR": "Udaipur",
    "JDH": "Jodhpur",
    "IXR": "Ranchi",
    "DED": "Dehradun",
    "IXA": "Agartala",
    "IMF": "Imphal",
}


def describe() -> SourceCapability:
    return SourceCapability(
        name=SOURCE_NAME,
        display_name="EaseMyTrip Domestic Flight Portal (Playwright)",
        source_type=SourceType.LIVE,
        enabled=True,
        disabled_reason=None,
        requires_credentials=False,
        homepage="https://www.easemytrip.com",
        terms_url="https://www.easemytrip.com/terms.html",
        robots_url="https://www.easemytrip.com/robots.txt",
        compliance_note=(
            "Extracts public domestic flight quotes via BrowserCollector. "
            "Attaches DataProvenance with AcquisitionMethod.WEB_SCRAPE."
        ),
        supports_cabin=(CABIN_ECONOMY,),
        native_currency="INR",
    )


class EaseMyTripFareSource(BaseFareSource):
    """
    Live OTA scraper adapter extracting flight quotes directly from EaseMyTrip search listings.
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

    def _build_search_url(self, origin: str, destination: str, departure_date: date) -> str:
        orig_city = CITY_MAP.get(origin, origin)
        dest_city = CITY_MAP.get(destination, destination)
        date_str = departure_date.strftime("%d/%m/%Y")
        return (
            f"https://flight.easemytrip.com/FlightList/Index?"
            f"srch={origin}-{orig_city}-India|{destination}-{dest_city}-India|{date_str}"
            f"&px=1-0-0&cbn=0&ar=undefined&isqs=true"
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
        started_at = time.time()
        req_id = new_request_id()
        search_url = self._build_search_url(origin, destination, departure_date)

        logger.info(
            f"EaseMyTrip live scraping {origin}->{destination} on {departure_date} "
            f"(horizon T+{booking_horizon_days})"
        )

        try:
            acq_res, raw_text_rows = await self.collector.fetch_page_and_cards(
                source_id=SOURCE_NAME,
                url=search_url,
                card_selectors=("div.fltResult", "div[id^='fltRow_']"),
                wait_selector="div.fltResult",
                settle_ms=4000,
            )

            # Fallback BeautifulSoup parsing if card text rows were empty
            if not raw_text_rows and acq_res.html_content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(acq_res.html_content, "html.parser")
                cards = soup.select("div.fltResult, div[id^='fltRow_']")
                for c in cards:
                    txt = c.get_text(separator="|", strip=True)
                    if txt and ("₹" in txt or any(code in txt for code in ("6E", "AI", "SG", "QP", "IX"))):
                        raw_text_rows.append(txt)

            observations = self._parse_and_build_observations(
                raw_text_rows=raw_text_rows,
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
            logger.info(
                f"EaseMyTrip extracted {len(observations)} live flight observations for "
                f"{origin}->{destination} in {latency_ms}ms"
            )

            return SourceResult(
                source_name=SOURCE_NAME,
                status=CollectionStatus.SUCCESS if observations else CollectionStatus.FAILED,
                observations=tuple(observations),
                error_message=None if observations else "No valid flight cards parsed from EaseMyTrip response.",
                error_type=None if observations else "empty_portal_response",
                attempts=1,
                response_time_ms=latency_ms,
            )

        except CaptchaChallengeError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"EaseMyTrip challenged on {search_url}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Bot challenge rendered on {SOURCE_NAME}: {exc}",
                error_type="captcha_challenge",
                response_time_ms=latency_ms,
            )
        except PolicyBlockError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"EaseMyTrip governance policy blocked {search_url}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Governance policy blocked: {exc}",
                error_type="policy_block",
                response_time_ms=latency_ms,
            )
        except AcquisitionTimeoutError as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.warning(f"EaseMyTrip timeout for {origin}->{destination}: {exc}")
            return SourceResult.failed(
                source_name=SOURCE_NAME,
                reason=f"Portal navigation timed out: {exc}",
                error_type="timeout",
                response_time_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.time() - started_at) * 1000)
            logger.error(
                f"EaseMyTrip scraper error for {origin}->{destination}: {type(exc).__name__}: {exc}"
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
            # 1. Identify carrier code and flight number
            carrier_code: Optional[str] = None
            flight_num_digits: Optional[str] = None

            fn_match = re.search(r"\b(6E|AI|QP|SG|IX|I5|UK)[|\s-]+(\d{3,4})\b", txt, re.IGNORECASE)
            if fn_match:
                carrier_code = fn_match.group(1).upper()
                if carrier_code == "UK":
                    carrier_code = "AI"  # Vistara merged into Air India
                elif carrier_code == "I5":
                    carrier_code = "IX"  # AirAsia India merged into AIX Connect
                flight_num_digits = fn_match.group(2)
            else:
                # Fallback: scan for airline name keywords
                txt_upper = txt.upper()
                for name, (code, _) in AIRLINE_KEYWORD_MAP.items():
                    if name in txt_upper:
                        carrier_code = code
                        break

            if not carrier_code:
                continue

            carrier_name = CARRIER_NAME_MAP.get(carrier_code, f"Airline {carrier_code}")

            # 2. Extract times (departure and arrival)
            times = re.findall(r"\b(\d{1,2}:\d{2})\b", txt)
            dep_time = times[0] if len(times) >= 1 else None
            arr_time = times[1] if len(times) >= 2 else None
            dep_time_band = classify_time_band(dep_time)

            # 3. Construct canonical flight number and surrogate indicator
            is_surrogate = False
            if flight_num_digits:
                flight_no = f"{carrier_code}-{flight_num_digits}"
            else:
                is_surrogate = True
                dep_slug = re.sub(r"[^\w]", "", dep_time or "0000")
                flight_no = f"{carrier_code}-{origin_code}{destination_code}-{dep_slug}"

            # 4. Extract total fare (INR)
            total_fare: Optional[float] = None

            # Primary: Match headline fare immediately preceding Book Now or + More Fare
            headline_match = re.search(
                r"([\d,]{4,6})\s*(?:\|\s*[\d,]{4,6})?\s*\|\s*(?:\+\s*More Fare|Book Now)",
                txt,
                re.IGNORECASE,
            )
            if headline_match:
                try:
                    total_fare = float(headline_match.group(1).replace(",", ""))
                except ValueError:
                    pass

            # Secondary: Grand Total explicitly stated in card
            if not total_fare:
                gt_match = re.search(r"Grand Total\s*\|\s*([\d,]{4,6})", txt, re.IGNORECASE)
                if gt_match:
                    try:
                        total_fare = float(gt_match.group(1).replace(",", ""))
                    except ValueError:
                        pass

            # Tertiary: Formatted currency tokens with comma separator (e.g. 6,368) >= 1500
            if not total_fare:
                price_candidates: list[float] = []
                for p in re.findall(r"\b(\d{1,2},\d{3})\b", txt):
                    try:
                        price_candidates.append(float(p.replace(",", "")))
                    except ValueError:
                        pass
                valid_prices = [p for p in price_candidates if 1500 <= p <= 80000]
                if valid_prices:
                    total_fare = min(valid_prices)

            if not total_fare or total_fare < 500 or total_fare > 80000:
                continue

            # Deduplication
            dedupe_key = f"{carrier_code}_{flight_no}_{departure_date}_{dep_time}_{int(total_fare)}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            # 5. Stops
            stops = 0 if any(k in txt.lower() for k in ("non-stop", "nonstop", "0 stop")) else 1

            # 6. Fare family
            txt_lower = txt.lower()
            if "flex" in txt_lower:
                fare_family = "FLEX"
            elif "max" in txt_lower:
                fare_family = "MAX"
            else:
                fare_family = "SAVER"

            # 7. Baggage allowance (kg) — only set if explicitly observed on card
            bag_match = re.search(r"(\d+)\s*(?:KG|Kgs)\s*(?:\||\s)*(?:Check-in|Baggage)", txt, re.IGNORECASE)
            baggage_kg = int(bag_match.group(1)) if bag_match else None

            # 8. Available seat inventory — only set if explicitly observed on card
            seat_match = re.search(r"(\d+)\s*Seats?\s*Left", txt, re.IGNORECASE)
            seats_available = int(seat_match.group(1)) if seat_match else None

            # 9. Refundable status
            is_refundable = "REFUNDABLE" in txt.upper() and "NON-REFUNDABLE" not in txt.upper()

            # 10. Statutory fee unbundling using AERA Tariff Orders
            decomp = unbundle_statutory_tariff(
                total_fare=total_fare,
                origin_code=origin_code,
                convenience_fee=300.0,
            )

            raw_rep = f"{flight_no}|{carrier_code}|{total_fare}|{dep_time}|{stops}|{fare_family}"
            prov = DataProvenance.for_web_scrape(
                source_name=SOURCE_NAME,
                source_url=search_url,
                request_id=request_id,
                raw_payload=raw_rep,
                timestamp=utc_now(),
                notes={
                    "collector": "PlaywrightPortalCollector",
                    "ota": "EaseMyTrip",
                    "horizon": booking_horizon_days,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
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
                fare_family=fare_family,
                stops=stops,
                is_refundable=is_refundable,
                baggage_kg=baggage_kg,
                fare_base=decomp["base_fare"],
                fare_taxes=decomp["taxes"],
                fare_udf=decomp["udf"],
                fare_convenience=decomp["convenience"],
                fare_total=total_fare,
                currency="INR",
                source_currency="INR",
                source_fare_total=total_fare,
                seats_available=seats_available,
                dep_time=dep_time,
                dep_time_band=dep_time_band,
                provenance=prov,
            )
            observations.append(obs)

        return observations


def create(**kwargs: Any) -> EaseMyTripFareSource:
    return EaseMyTripFareSource(**kwargs)
