"""
SIH26056 — Shared HTTP / Browser Acquisition Runtime Tests.

Verifies:
1. Artifact store secret redaction (URLs, headers, tokens) and SHA-256 verification.
2. HttpCollector with local mock portal server:
   - Normal results retrieval and capture archiving.
   - Policy block on unauthorized source.
   - robots.txt disallow block.
   - CAPTCHA challenge detection (raises CaptchaChallengeError, never bypassed).
   - Authentication wall detection (raises AuthWallError).
   - Rate limit 429 detection (raises RateLimitError).
3. PriceQuote component reconciliation (base + taxes = headline).
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
import tempfile

import httpx
import pytest

from scraper.web.artifact_store import (
    ArtifactStore,
    redact_headers,
    redact_payload_text,
    redact_url,
)
from scraper.web.contracts import PageState, PriceQuote, WebSearchQuery
from scraper.web.errors import (
    AuthWallError,
    CaptchaChallengeError,
    PolicyBlockError,
    RateLimitError,
    RobotsBlockError,
)
from scraper.web.http_collector import HttpCollector


# ═══════════════════════════════════════════════════════════
# 1. SECRET REDACTION & ARTIFACT STORAGE
# ═══════════════════════════════════════════════════════════

def test_secret_redaction_in_urls_and_headers():
    # URL query parameter redaction
    raw_url = "https://portal.example.com/search?origin=DEL&destination=BOM&token=secret_jwt_xyz999&auth=123"
    clean_url = redact_url(raw_url)
    assert "secret_jwt_xyz999" not in clean_url
    assert "token=%5BREDACTED%5D" in clean_url
    assert "auth=%5BREDACTED%5D" in clean_url
    assert "origin=DEL" in clean_url

    # Header redaction
    raw_headers = {
        "User-Agent": "AirfareCPI/2.0",
        "Authorization": "Bearer sensitive_token_abc",
        "Cookie": "session_id=987654321; secure",
        "Accept": "text/html",
    }
    clean_headers = redact_headers(raw_headers)
    assert clean_headers["Authorization"] == "[REDACTED]"
    assert clean_headers["Cookie"] == "[REDACTED]"
    assert clean_headers["User-Agent"] == "AirfareCPI/2.0"

    # Payload Bearer token redaction
    payload = '{"status": "ok", "access_token": "secret_abc123", "header": "Bearer tok_xyz"}'
    clean_payload = redact_payload_text(payload)
    assert "secret_abc123" not in clean_payload
    assert "tok_xyz" not in clean_payload
    assert "Bearer [REDACTED]" in clean_payload


def test_immutable_artifact_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(base_dir=Path(tmpdir))
        content = "<html><body><h1>Flight Results DEL-BOM</h1><p>Fare: INR 4500</p></body></html>"

        stored = store.store_capture(
            source_id="amadeus",
            url="https://test.api.amadeus.com/v2/flight-offers?origin=DEL&token=secret123",
            content=content,
            mime_type="text/html",
        )

        assert stored.artifact_id.startswith("art-")
        assert len(stored.sha256) == 64
        assert "secret123" not in stored.sanitized_url
        assert Path(tmpdir, stored.relative_path).exists()


# ═══════════════════════════════════════════════════════════
# 2. PRICE COMPONENT RECONCILIATION
# ═══════════════════════════════════════════════════════════

def test_price_quote_reconciliation():
    # Valid reconciliation: 3500 base + 1000 taxes = 4500 headline
    quote_valid = PriceQuote(
        airline_code="6E",
        airline_name="IndiGo",
        flight_number="6E-201",
        headline_fare=4500.0,
        base_fare=3500.0,
        taxes_and_fees=1000.0,
    )
    assert quote_valid.reconcile_price_components(tolerance=1.0) is True

    # Invalid reconciliation: 3500 base + 500 taxes != 4500 headline
    quote_mismatch = PriceQuote(
        airline_code="6E",
        airline_name="IndiGo",
        flight_number="6E-201",
        headline_fare=4500.0,
        base_fare=3500.0,
        taxes_and_fees=500.0,
    )
    assert quote_mismatch.reconcile_price_components(tolerance=1.0) is False

    # No components provided (e.g. headline only displayed) reconciles by definition
    quote_headline_only = PriceQuote(
        airline_code="6E",
        airline_name="IndiGo",
        flight_number="6E-201",
        headline_fare=4500.0,
    )
    assert quote_headline_only.reconcile_price_components() is True


# ═══════════════════════════════════════════════════════════
# 3. HTTP COLLECTOR & FAKE PORTAL SERVER
# ═══════════════════════════════════════════════════════════

def create_fake_portal_handler():
    """Mock ASGI handler representing an airline quotation portal."""
    async def app(scope, receive, send):
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode("utf-8")

        if path == "/v2/shopping/flight-offers":
            if "scenario=captcha" in query:
                body = b"<html><body><div id='cf-challenge'>Please verify you are a human</div></body></html>"
                headers = [(b"content-type", b"text/html; charset=utf-8")]
                status = 200
            elif "scenario=auth" in query:
                body = b"<html><body><h1>Access Denied: Login Required</h1></body></html>"
                headers = [(b"content-type", b"text/html; charset=utf-8")]
                status = 403
            elif "scenario=rate-limit" in query:
                body = b"Too Many Requests"
                headers = [(b"content-type", b"text/plain")]
                status = 429
            else:
                body = (
                    b"<html><body>"
                    b"<div class='flight-row' data-flight='AI-101' data-fare='5200'>"
                    b"  <span class='airline'>Air India</span>"
                    b"  <span class='price'>INR 5200</span>"
                    b"</div>"
                    b"</body></html>"
                )
                headers = [(b"content-type", b"text/html; charset=utf-8")]
                status = 200
        else:
            body = b"Not Found"
            headers = [(b"content-type", b"text/plain")]
            status = 404

        await send({
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    return app


def test_http_collector_with_fake_portal():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(base_dir=Path(tmpdir))
            collector = HttpCollector(artifact_store=store, timeout_seconds=5.0)

            fake_app = create_fake_portal_handler()
            transport = httpx.ASGITransport(app=fake_app)

            async with httpx.AsyncClient(transport=transport, base_url="https://test.api.amadeus.com") as client:
                # 1. Normal successful fetch
                res = await collector.fetch(
                    source_id="amadeus",
                    url="https://test.api.amadeus.com/v2/shopping/flight-offers?origin=DEL&destination=BOM",
                    client=client,
                )
                assert res.status_code == 200
                assert "AI-101" in res.content_text
                assert res.stored_artifact.sha256 is not None

                # 2. CAPTCHA Challenge detection: must raise CaptchaChallengeError
                with pytest.raises(CaptchaChallengeError, match="Bot challenge or CAPTCHA encountered"):
                    await collector.fetch(
                        source_id="amadeus",
                        url="https://test.api.amadeus.com/v2/shopping/flight-offers?scenario=captcha",
                        client=client,
                    )

                # 3. Auth wall detection: must raise AuthWallError
                with pytest.raises(AuthWallError, match="Authentication or authorization required"):
                    await collector.fetch(
                        source_id="amadeus",
                        url="https://test.api.amadeus.com/v2/shopping/flight-offers?scenario=auth",
                        client=client,
                    )

                # 4. Rate limit 429 detection: must raise RateLimitError
                with pytest.raises(RateLimitError, match="Rate limited"):
                    await collector.fetch(
                        source_id="amadeus",
                        url="https://test.api.amadeus.com/v2/shopping/flight-offers?scenario=rate-limit",
                        client=client,
                    )

                # 5. Policy block on prohibited source
                with pytest.raises(PolicyBlockError, match="Gate 1 failed"):
                    await collector.fetch(
                        source_id="air_india",
                        url="https://test.api.amadeus.com/v2/shopping/flight-offers",
                        client=client,
                    )

                # 6. robots.txt disallow check
                robots_txt = "User-agent: *\nDisallow: /v2/shopping/flight-offers\n"
                with pytest.raises(RobotsBlockError, match="robots.txt disallows"):
                    await collector.fetch(
                        source_id="amadeus",
                        url="https://test.api.amadeus.com/v2/shopping/flight-offers",
                        robots_txt_content=robots_txt,
                        client=client,
                    )

    asyncio.run(_test())
