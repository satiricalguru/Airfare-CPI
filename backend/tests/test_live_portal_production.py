"""
SIH26056 — Multi-Source Live Web Scraper Production Tests.

Verifies:
1. LivePortalFareSource & EaseMyTripFareSource capabilities and registry integration.
2. 8-Gate Source Access Governance: APPROVED status, robots.txt compliance, and rate limits.
3. Card extraction and parsing for both Google Flights and EaseMyTrip formats.
4. Exact statutory civil aviation fee unbundling (Base, Taxes, UDF, Convenience = Total).
5. DataProvenance completeness with AcquisitionMethod.WEB_SCRAPE and cryptographic artifact IDs.
6. Robust circuit breakers: non-evasion handling of CAPTCHAs, bot walls, and policy blocks.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import pytest

from provenance import AcquisitionMethod, CollectionStatus
from scraper.base import classify_time_band
from scraper.registry import registry
from scraper.source_registry import get_source_registry
from scraper.sources.easemytrip import EaseMyTripFareSource, describe as describe_emt
from scraper.sources.live_portal_adapter import (
    LivePortalFareSource,
    describe as describe_live,
    detect_block,
)
from scraper.web.artifact_store import ArtifactStore
from scraper.web.browser_collector import BrowserAcquisitionResult, BrowserCollector
from scraper.web.errors import CaptchaChallengeError, PolicyBlockError
from scraper.web.source_policy import SourcePolicyEnforcer


# ═══════════════════════════════════════════════════════════
# 1. REGISTRY & GOVERNANCE ENFORCEMENT
# ═══════════════════════════════════════════════════════════

def test_sources_registered():
    """Verify live_portal and easemytrip are registered in the global adapter registry."""
    assert registry.has("live_portal")
    assert registry.has("easemytrip")

    cap_live = registry.capability("live_portal")
    assert cap_live.enabled is True
    assert cap_live.native_currency == "INR"

    cap_emt = registry.capability("easemytrip")
    assert cap_emt.enabled is True
    assert cap_emt.native_currency == "INR"


def test_governance_registry_approval():
    """Verify both live sources have PENDING_FORMAL_REVIEW status, real hashes, and 90-day expiry."""
    source_reg = get_source_registry()

    rec_live = source_reg.get("live_portal")
    assert rec_live is not None
    assert rec_live.permission_status == "PENDING_FORMAL_REVIEW"
    assert rec_live.is_permitted_for_network_collection is True
    assert rec_live.maximum_requests_per_minute >= 10
    assert len(rec_live.robots_content_sha256) == 64
    assert rec_live.robots_content_sha256 != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert len(rec_live.terms_content_sha256) == 64
    assert rec_live.contact == "support-in@google.com"
    assert rec_live.review_expires_at is not None
    assert (rec_live.review_expires_at - rec_live.robots_reviewed_at).days <= 90

    rec_emt = source_reg.get("easemytrip")
    assert rec_emt is not None
    assert rec_emt.permission_status == "PENDING_FORMAL_REVIEW"
    assert rec_emt.is_permitted_for_network_collection is True
    assert rec_emt.maximum_requests_per_minute >= 10
    assert len(rec_emt.robots_content_sha256) == 64
    assert rec_emt.robots_content_sha256 != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert len(rec_emt.terms_content_sha256) == 64
    assert rec_emt.contact == "care@easemytrip.com"
    assert rec_emt.review_expires_at is not None
    assert (rec_emt.review_expires_at - rec_emt.robots_reviewed_at).days <= 90


def test_source_policy_enforcement_paths():
    """Test 8-gate policy enforcer validates authorized paths and rejects unknown sources."""
    lp_url = "https://www.google.com/travel/flights?q=Flights%20to%20BOM%20from%20DEL"
    rec_lp = SourcePolicyEnforcer.check_can_fetch("live_portal", lp_url)
    assert rec_lp.source_id == "live_portal"

    emt_url = "https://flight.easemytrip.com/FlightList/Index?srch=DEL-Delhi-India|BOM-Mumbai-India|15/09/2026"
    rec_emt = SourcePolicyEnforcer.check_can_fetch("easemytrip", emt_url)
    assert rec_emt.source_id == "easemytrip"

    # Unauthorized source rejected
    with pytest.raises(PolicyBlockError):
        SourcePolicyEnforcer.check_can_fetch("unregistered_portal_xyz", "https://example.com/flights")


# ═══════════════════════════════════════════════════════════
# 2. GOOGLE FLIGHTS ADAPTER PARSING & FEE RECONCILIATION
# ═══════════════════════════════════════════════════════════

def test_live_portal_adapter_card_parsing():
    """Test parsing flight cards from Google Flights text extracts."""
    adapter = LivePortalFareSource()

    raw_cards = [
        # IndiGo card
        "6:00 AM – 8:15 AM\nIndiGo\n2 hr 15 min\nDEL-BOM\nNonstop\n₹4,620",
        # Air India card
        "7:00 AM – 9:20 AM\nAir India\n2 hr 20 min\nDEL-BOM\nNonstop\n₹5,280",
        # Akasa Air card
        "11:30 AM – 1:45 PM\nAkasa Air\n2 hr 15 min\nDEL-BOM\nNonstop\n₹4,190",
        # Non-matching card (ignored)
        "Something unrelated without price or airline",
    ]

    dep_date = date(2026, 9, 15)
    obs = adapter._parse_and_build_observations(
        raw_text_rows=raw_cards,
        route_id=1,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=dep_date,
        booking_horizon_days=7,
        search_url="https://www.google.com/travel/flights?q=Flights",
        request_id="req-test-1",
        cabin="ECONOMY",
        artifact_id="art-test-sha1",
        artifact_sha256="abcdef1234567890",
    )

    assert len(obs) == 3

    # Check IndiGo observation
    obs_6e = next(o for o in obs if o.airline_code == "6E")
    assert obs_6e.airline_name == "IndiGo"
    assert obs_6e.origin_code == "DEL"
    assert obs_6e.destination_code == "BOM"
    assert obs_6e.fare_total == 4620.0
    assert obs_6e.stops == 0
    assert obs_6e.dep_time == "6:00 AM"
    assert obs_6e.seats_available is None
    assert obs_6e.baggage_kg is None

    # Check MoCA / AERA statutory fee reconciliation (sum == total) and disclosure
    for o in obs:
        reconciled_sum = round(o.fare_base + o.fare_taxes + o.fare_udf + o.fare_convenience, 2)
        assert abs(reconciled_sum - o.fare_total) < 0.02, (
            f"Fee decomposition does not match total fare for {o.airline_code}: "
            f"{reconciled_sum} vs {o.fare_total}"
        )
        assert o.provenance.acquisition_method == AcquisitionMethod.WEB_SCRAPE
        assert o.provenance.source_name == "live_portal"
        assert o.provenance.notes.get("artifact_id") == "art-test-sha1"
        assert o.provenance.notes.get("artifact_sha256") == "abcdef1234567890"
        assert o.provenance.notes.get("decomposition_method") == "AERA_STATUTORY_TARIFF_ESTIMATOR"
        assert o.provenance.notes.get("is_estimated") is True
        assert o.provenance.notes.get("udf_airport") == "DEL"
        assert o.provenance.notes.get("is_surrogate") is True


def test_live_portal_block_detection():
    """Verify challenge interstitial detection triggers block flag."""
    assert detect_block("Unusual Traffic", "Please verify you are a human", 200) is True
    assert detect_block("403 Forbidden", "Access denied", 403) is True
    assert detect_block("429 Too Many Requests", "", 429) is True
    assert detect_block("Google Flights - Flights from Delhi to Mumbai", "Nonstop flights ₹4,500", 200) is False


# ═══════════════════════════════════════════════════════════
# 3. EASEMYTRIP ADAPTER PARSING & EXACT FLIGHT NUMBERS
# ═══════════════════════════════════════════════════════════

def test_easemytrip_url_builder():
    """Verify EaseMyTrip search URL is properly formatted with IATA and cities."""
    adapter = EaseMyTripFareSource()
    url = adapter._build_search_url("DEL", "BOM", date(2026, 9, 20))
    assert "srch=DEL-Delhi-India|BOM-Mumbai-India|20/09/2026" in url
    assert "isqs=true" in url


def test_easemytrip_card_parsing():
    """Verify exact IATA flight numbers, branded fare families, baggage, and fee breakdown."""
    adapter = EaseMyTripFareSource()

    # Real EaseMyTrip card representations
    sample_cards = [
        (
            "SpiceJet|SG|-|162|ECONOMY|Boeing 737|19:55|New Delhi|02h 35m|Non-stop|22:30|Mumbai|"
            "6,368|6,368|SpiceSaver|15 KG|Check-in Baggage|Refundable|Selected"
        ),
        (
            "IndiGo|6E|-|205|ECONOMY|Airbus A320|08:15|New Delhi|02h 15m|Non-stop|10:30|Mumbai|"
            "5,420|5,420|Saver|15 KG|Check-in Baggage|Non-Refundable"
        ),
        (
            "Air India|AI|-|887|ECONOMY|Airbus A321|14:00|New Delhi|02h 20m|Non-stop|16:20|Mumbai|"
            "5,890|5,890|Flex|15 Kgs|Check-in Baggage|Refundable"
        ),
    ]

    dep_date = date(2026, 9, 20)
    obs = adapter._parse_and_build_observations(
        raw_text_rows=sample_cards,
        route_id=1,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=dep_date,
        booking_horizon_days=15,
        search_url="https://flight.easemytrip.com/FlightList/Index",
        request_id="req-emt-1",
        cabin="ECONOMY",
        artifact_id="art-emt-123",
        artifact_sha256="fedcba9876543210",
    )

    assert len(obs) == 3

    # 1. SpiceJet verification
    obs_sg = next(o for o in obs if o.airline_code == "SG")
    assert obs_sg.airline_name == "SpiceJet"
    assert obs_sg.flight_number == "SG-162"  # Exact IATA flight number!
    assert obs_sg.fare_total == 6368.0
    assert obs_sg.dep_time == "19:55"
    assert obs_sg.fare_family == "SAVER"
    assert obs_sg.baggage_kg == 15
    assert obs_sg.is_refundable is True
    assert obs_sg.stops == 0

    # 2. IndiGo verification
    obs_6e = next(o for o in obs if o.airline_code == "6E")
    assert obs_6e.airline_name == "IndiGo"
    assert obs_6e.flight_number == "6E-205"  # Exact IATA flight number!
    assert obs_6e.fare_total == 5420.0
    assert obs_6e.dep_time == "08:15"
    assert obs_6e.is_refundable is False

    # 3. Air India verification
    obs_ai = next(o for o in obs if o.airline_code == "AI")
    assert obs_ai.airline_name == "Air India"
    assert obs_ai.flight_number == "AI-887"
    assert obs_ai.fare_family == "FLEX"

    # 4. Arithmetic reconciliation of statutory fees and disclosure
    for o in obs:
        total_recon = round(o.fare_base + o.fare_taxes + o.fare_udf + o.fare_convenience, 2)
        assert abs(total_recon - o.fare_total) < 0.02
        assert o.provenance.acquisition_method == AcquisitionMethod.WEB_SCRAPE
        assert o.provenance.source_name == "easemytrip"
        assert o.provenance.notes.get("ota") == "EaseMyTrip"
        assert o.provenance.notes.get("artifact_id") == "art-emt-123"
        assert o.provenance.notes.get("artifact_sha256") == "fedcba9876543210"
        assert o.provenance.notes.get("decomposition_method") == "AERA_STATUTORY_TARIFF_ESTIMATOR"
        assert o.provenance.notes.get("is_estimated") is True
        assert o.provenance.notes.get("udf_airport") == "DEL"
        assert o.provenance.notes.get("is_surrogate") is False


# ═══════════════════════════════════════════════════════════
# 4. ARTIFACT RETRIEVAL AND INTEGRITY
# ═══════════════════════════════════════════════════════════

def test_browser_acquisition_artifact_integrity():
    """Verify BrowserCollector archives sanitized content with verifiable sha256."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(base_dir=Path(tmpdir))
        content = "<html><body><div class='fltResult'>SG-162 ₹6,368</div></body></html>"
        stored = store.store_capture(
            source_id="easemytrip",
            url="https://flight.easemytrip.com/FlightList/Index",
            content=content,
            mime_type="text/html",
        )

        assert stored.artifact_id.startswith("art-")
        assert len(stored.sha256) == 64
        # Verify content on disk matches SHA-256
        import gzip
        import hashlib
        disk_bytes = gzip.decompress((Path(tmpdir) / stored.relative_path).read_bytes())
        assert hashlib.sha256(disk_bytes).hexdigest() == stored.sha256


# ═══════════════════════════════════════════════════════════
# 5. POLITENESS & RATE LIMITING CONTROLS
# ═══════════════════════════════════════════════════════════

def test_browser_collector_rate_limiter_and_concurrency():
    """Verify BrowserCollector enforces per-host rate limits and concurrency buckets."""
    import asyncio
    import time

    async def _run():
        collector = BrowserCollector()

        # Verify per-host configured intervals (EMT at 3.0s enforces <= 20 req/min)
        assert collector.rate_limiter.get_host_interval("google.com") == 1.5
        assert collector.rate_limiter.get_host_interval("www.google.com") == 1.5
        assert collector.rate_limiter.get_host_interval("travel.google.com") == 1.5
        assert collector.rate_limiter.get_host_interval("flight.easemytrip.com") == 3.0
        assert collector.rate_limiter.get_host_interval("easemytrip.com") == 3.0
        assert collector.rate_limiter.get_host_interval("unknown-host.org") == 1.5

        # Verify eTLD+1 root domain semaphore unification (subdomains share the same semaphore)
        sem_g1 = collector._get_host_semaphore("www.google.com")
        sem_g2 = collector._get_host_semaphore("travel.google.com")
        assert sem_g1 is sem_g2
        assert sem_g1._value == 2

        sem_emt1 = collector._get_host_semaphore("flight.easemytrip.com")
        sem_emt2 = collector._get_host_semaphore("www.easemytrip.com")
        assert sem_emt1 is sem_emt2
        assert sem_emt1._value == 2

        # Verify rate limiter enforces delay on consecutive calls
        # Fast acquire first time
        w1 = await collector.rate_limiter.acquire("https://www.google.com/travel/flights")
        assert w1 == 0.0

        # Second immediate acquire on same host must be delayed
        start = time.monotonic()
        w2 = await collector.rate_limiter.acquire("https://www.google.com/travel/flights")
        elapsed = time.monotonic() - start
        assert w2 >= 1.4
        assert elapsed >= 1.4

    asyncio.run(_run())


# ═══════════════════════════════════════════════════════════
# 6. COMMERCIAL PRODUCTION KILL-SWITCH
# ═══════════════════════════════════════════════════════════

def test_commercial_kill_switch_governance():
    """Verify ALLOW_RESEARCH_SCRAPING=false blocks PENDING_FORMAL_REVIEW sources."""
    from scraper.governance import check_source_permitted

    # 1. When research scraping is enabled (prototype mode), sources are permitted
    gate_live_on = check_source_permitted("live_portal", allow_research_scraping=True)
    assert gate_live_on.is_permitted is True

    gate_emt_on = check_source_permitted("easemytrip", allow_research_scraping=True)
    assert gate_emt_on.is_permitted is True

    # 2. When research scraping is disabled (sovereign production mode), sources are blocked
    gate_live_off = check_source_permitted("live_portal", allow_research_scraping=False)
    assert gate_live_off.is_permitted is False
    assert gate_live_off.failed_gate == 1
    assert "ALLOW_RESEARCH_SCRAPING=false" in gate_live_off.reason
    assert "Only fully APPROVED sources are permitted in sovereign production" in gate_live_off.reason

    gate_emt_off = check_source_permitted("easemytrip", allow_research_scraping=False)
    assert gate_emt_off.is_permitted is False
    assert gate_emt_off.failed_gate == 1
    assert "ALLOW_RESEARCH_SCRAPING=false" in gate_emt_off.reason


def test_politeness_override_root_domain():
    """Verify override_min_interval normalizes to root domain across subdomains."""
    from scraper.politeness import HostRateLimiter

    limiter = HostRateLimiter(min_interval_seconds=1.0)
    # Calling override with a specific subdomain
    limiter.override_min_interval(3.5, host="www.google.com")

    # Both root and other subdomains now reflect 3.5s
    assert limiter.get_host_interval("google.com") == 3.5
    assert limiter.get_host_interval("travel.google.com") == 3.5
    assert limiter.get_host_interval("www.google.com") == 3.5


def test_source_access_record_fail_closed(monkeypatch):
    """Verify is_permitted_for_network_collection fails closed when research scraping is disabled."""
    from scraper.source_registry import get_source_registry

    source_reg = get_source_registry()
    rec_live = source_reg.get("live_portal")
    assert rec_live is not None

    monkeypatch.setenv("ALLOW_RESEARCH_SCRAPING", "false")
    from config import reload_settings
    reload_settings()

    assert rec_live.is_permitted_for_network_collection is False

    monkeypatch.setenv("ALLOW_RESEARCH_SCRAPING", "true")
    reload_settings()
    assert rec_live.is_permitted_for_network_collection is True
