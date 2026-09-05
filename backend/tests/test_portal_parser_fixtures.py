"""
SIH26056 — Portal Parser Fixture Tests.

Validates parser against sanitized raw HTML fixtures:
1. normal_results.html: full extraction and 100% component reconciliation.
2. no_results.html: PageState.NO_RESULTS.
3. sold_out.html: PageState.NO_RESULTS.
4. layout_variation.html: tabular row extraction and reconciliation.
5. partial_price.html: headline fare extraction when components are missing.
6. source_error.html: PageState.ERROR.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from scraper.web.contracts import PageState
from scraper.web.portal_parser import PortalHtmlParser

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "portal_captures"


def test_parse_normal_results():
    html = (FIXTURES_DIR / "normal_results.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html, artifact_id="art-test-normal")

    assert result.state == PageState.SUCCESS
    assert result.artifact_id == "art-test-normal"
    assert len(result.quotes) == 3
    assert result.errors == []

    # Verify first quote (Air India)
    q1 = result.quotes[0]
    assert q1.airline_name == "Air India"
    assert q1.airline_code == "AI"
    assert q1.flight_number == "AI-805"
    assert q1.base_fare == 3800.0
    assert q1.taxes_and_fees == 1150.0
    assert q1.headline_fare == 4950.0
    assert q1.reconcile_price_components() is True
    assert q1.departure_time == "06:00"
    assert q1.arrival_time == "08:15"

    # Verify second quote (IndiGo)
    q2 = result.quotes[1]
    assert q2.airline_name == "IndiGo"
    assert q2.airline_code == "6E"
    assert q2.flight_number == "6E-2051"
    assert q2.base_fare == 3500.0
    assert q2.taxes_and_fees == 1120.0
    assert q2.headline_fare == 4620.0
    assert q2.reconcile_price_components() is True

    # Verify third quote (Air India Express)
    q3 = result.quotes[2]
    assert q3.flight_number == "IX-1144"
    assert q3.headline_fare == 4280.0
    assert q3.reconcile_price_components() is True


def test_parse_no_results():
    html = (FIXTURES_DIR / "no_results.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html)

    assert result.state == PageState.NO_RESULTS
    assert len(result.quotes) == 0


def test_parse_sold_out():
    html = (FIXTURES_DIR / "sold_out.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html)

    assert result.state == PageState.NO_RESULTS
    assert len(result.quotes) == 0


def test_parse_layout_variation():
    html = (FIXTURES_DIR / "layout_variation.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html)

    assert result.state == PageState.SUCCESS
    assert len(result.quotes) == 2
    assert result.errors == []

    q1 = result.quotes[0]
    assert q1.flight_number == "6E-501"
    assert q1.headline_fare == 5450.0
    assert q1.base_fare == 4200.0
    assert q1.taxes_and_fees == 1250.0
    assert q1.reconcile_price_components() is True

    q2 = result.quotes[1]
    assert q2.flight_number == "AI-506"
    assert q2.headline_fare == 5800.0
    assert q2.reconcile_price_components() is True


def test_parse_partial_price():
    html = (FIXTURES_DIR / "partial_price.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html)

    assert result.state == PageState.SUCCESS
    assert len(result.quotes) == 1
    q = result.quotes[0]
    assert q.flight_number == "6E-101"
    assert q.headline_fare == 4800.0
    assert q.base_fare is None
    assert q.taxes_and_fees is None


def test_parse_source_error():
    html = (FIXTURES_DIR / "source_error.html").read_text(encoding="utf-8")
    result = PortalHtmlParser.parse(html)

    assert result.state == PageState.ERROR
    assert len(result.quotes) == 0
    assert any("Source error" in e for e in result.errors)
