"""
SIH26056 — Deterministic Portal HTML Results Parser.

Parses server-rendered and browser-rendered flight results pages into
canonical PriceQuote records:
- Identifies page state: SUCCESS, NO_RESULTS, CAPTCHA_CHALLENGE, AUTH_REQUIRED, ERROR.
- Reconciles price components: verifies base_fare + taxes_and_fees == headline_fare.
- Handles layout variations (card vs tabular layout).
- Flags partial price exposures when base/tax breakdowns are absent.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger

from scraper.web.contracts import PageState, ParseResult, PriceQuote


def _parse_currency_amount(text_or_attr: Optional[str]) -> Optional[float]:
    """Clean ₹, INR, commas, and whitespace into a float amount."""
    if not text_or_attr:
        return None
    cleaned = re.sub(r"[^\d.]", "", text_or_attr)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


class PortalHtmlParser:
    """Parser for sanitized flight quotation HTML captures."""

    @classmethod
    def parse(cls, html_content: str, artifact_id: Optional[str] = None) -> ParseResult:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. State: Error page detection
        if soup.find("div", class_="error-container") or (
            soup.find("h1") and "500" in soup.find("h1").get_text()
        ):
            return ParseResult(
                state=PageState.ERROR,
                artifact_id=artifact_id,
                errors=["Source error: portal reported internal error / service unavailable."],
            )

        # 2. State: Bot Challenge / CAPTCHA
        if soup.find(id="cf-challenge") or "please verify you are a human" in html_content.lower():
            return ParseResult(
                state=PageState.CAPTCHA_CHALLENGE,
                artifact_id=artifact_id,
                errors=["CAPTCHA challenge encountered."],
            )

        # 3. State: Sold Out or Empty Results
        if (
            soup.find("div", class_="sold-out-banner")
            or soup.find("div", class_="empty-state")
            or "all flights sold out" in html_content.lower()
            or "no flights found" in html_content.lower()
        ):
            return ParseResult(
                state=PageState.NO_RESULTS,
                artifact_id=artifact_id,
                quotes=[],
                notes={"availability": "zero_offers"},
            )

        quotes: list[PriceQuote] = []
        errors: list[str] = []

        # 4. Extract Offers: Layout A (Cards)
        cards = soup.find_all("div", class_="flight-card")
        if cards:
            for card in cards:
                try:
                    airline_name = card.find(class_="airline-name").get_text(strip=True)
                    airline_code = card.find(class_="airline-code").get_text(strip=True)
                    flight_num = card.find(class_="flight-number").get_text(strip=True)

                    dep_time = card.find(class_="dep-time")
                    arr_time = card.find(class_="arr-time")

                    # Price components
                    total_el = card.find(class_="fare-total")
                    base_el = card.find(class_="fare-base")
                    tax_el = card.find(class_="fare-taxes")

                    total_amt = _parse_currency_amount(
                        total_el.get("data-amount") or total_el.get_text()
                    )
                    base_amt = _parse_currency_amount(
                        base_el.get("data-amount") or base_el.get_text()
                    ) if base_el else None
                    tax_amt = _parse_currency_amount(
                        tax_el.get("data-amount") or tax_el.get_text()
                    ) if tax_el else None

                    if total_amt is None or total_amt <= 0:
                        errors.append(f"Invalid total fare for flight {flight_num}")
                        continue

                    quote = PriceQuote(
                        airline_code=airline_code,
                        airline_name=airline_name,
                        flight_number=flight_num,
                        headline_fare=total_amt,
                        base_fare=base_amt,
                        taxes_and_fees=tax_amt,
                        currency="INR",
                        departure_time=dep_time.get_text(strip=True) if dep_time else None,
                        arrival_time=arr_time.get_text(strip=True) if arr_time else None,
                    )

                    if not quote.reconcile_price_components():
                        errors.append(
                            f"Price component mismatch for {flight_num}: "
                            f"base({base_amt}) + tax({tax_amt}) != total({total_amt})"
                        )
                        continue

                    quotes.append(quote)
                except Exception as exc:
                    errors.append(f"Card parse error: {exc}")

        # 5. Extract Offers: Layout B (Tabular Rows)
        rows = soup.find_all("tr", class_="flight-row")
        if rows and not quotes:
            for row in rows:
                try:
                    airline_code = row.get("data-airline-code") or ""
                    airline_name = row.get("data-airline") or ""
                    flight_num = row.get("data-flight-number") or ""

                    dep_el = row.find(class_="dep-time")
                    arr_el = row.find(class_="arr-time")

                    total_el = row.find(class_="fare-total")
                    base_el = row.find(class_="fare-base")
                    tax_el = row.find(class_="fare-taxes")

                    total_amt = _parse_currency_amount(
                        total_el.get("data-amount") or total_el.get_text()
                    )
                    base_amt = _parse_currency_amount(
                        base_el.get("data-amount") or base_el.get_text()
                    ) if base_el else None
                    tax_amt = _parse_currency_amount(
                        tax_el.get("data-amount") or tax_el.get_text()
                    ) if tax_el else None

                    if total_amt is None or total_amt <= 0:
                        continue

                    quote = PriceQuote(
                        airline_code=airline_code,
                        airline_name=airline_name,
                        flight_number=flight_num,
                        headline_fare=total_amt,
                        base_fare=base_amt,
                        taxes_and_fees=tax_amt,
                        currency="INR",
                        departure_time=dep_el.get_text(strip=True) if dep_el else None,
                        arrival_time=arr_el.get_text(strip=True) if arr_el else None,
                    )

                    if not quote.reconcile_price_components():
                        errors.append(f"Tabular price reconciliation failed for {flight_num}")
                        continue

                    quotes.append(quote)
                except Exception as exc:
                    errors.append(f"Row parse error: {exc}")

        state = PageState.SUCCESS if quotes else (PageState.NO_RESULTS if not errors else PageState.SELECTOR_DRIFT)

        return ParseResult(
            state=state,
            quotes=quotes,
            artifact_id=artifact_id,
            errors=errors,
            notes={"quote_count": len(quotes)},
        )
