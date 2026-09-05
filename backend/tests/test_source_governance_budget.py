"""
SIH26056 — Source Governance, 8-Gate Validation & Budget Enforcement Tests.

Tests:
1. Strict schema validation for source_access_registry.yaml.
2. 8-Gate enforcement:
   - Prohibited / unapproved sources cannot make network queries.
   - Unapproved paths are blocked.
   - Expired source reviews are blocked.
   - Terms and robots hash drift are detected and blocked.
3. Free budget enforcement:
   - 80% warning threshold.
   - 95% reduced-basket tracer mode.
   - 100% hard stop (QUOTA_EXHAUSTED).
4. Billing safety gate:
   - ALLOW_PAID_OVERAGE without secondary confirmation raises RuntimeError on startup.
5. API endpoints:
   - GET /api/v1/sources/{source_id}/governance
   - GET /api/v1/sources/budget
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
import httpx
import pytest

from api.main import app
from config import build_settings
from db.engine import get_database
from provenance import CollectionMode, CollectionStatus
from scraper.budget import (
    BudgetController,
    BudgetStatus,
    TRACER_BASKET_ROUTE_CODES,
)
from scraper.governance import (
    GovernanceValidator,
    check_source_permitted,
)
from scraper.pipeline import CollectionPipeline, CollectionRequest
from scraper.source_registry import (
    PermissionStatus,
    SourceAccessRecord,
    get_source_registry,
)


@pytest.fixture
def api_client():
    with TestClient(app) as client:
        yield client


# ═══════════════════════════════════════════════════════════
# 1. REGISTRY SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════

def test_source_registry_schema_validation():
    registry = get_source_registry()
    data = registry.to_dict()

    # The checked-in registry must have zero validation errors
    errors = GovernanceValidator.validate_registry_dict(data)
    assert errors == [], f"Checked-in registry has errors: {errors}"

    # An invalid entry must produce clear errors
    corrupted_data = {
        "registry_version": "1.0.0",
        "sources": [
            {
                "source_id": "corrupt_1",
                # missing display_name and operator
                "acquisition_method": "INVALID_METHOD",
                "permission_status": "UNKNOWN_STATUS",
                "maximum_requests_per_day": -5,
            },
            {
                "source_id": "corrupt_approved",
                "display_name": "Approved Without Contact",
                "operator": "Some Airline",
                "acquisition_method": "API",
                "permission_status": "APPROVED",
                "maximum_requests_per_day": 100,
                # missing contact
            },
        ],
    }
    corrupt_errors = GovernanceValidator.validate_registry_dict(corrupted_data)
    assert len(corrupt_errors) >= 5
    assert any("invalid acquisition_method" in e for e in corrupt_errors)
    assert any("invalid permission_status" in e for e in corrupt_errors)
    assert any("maximum_requests_per_day cannot be negative" in e for e in corrupt_errors)
    assert any("contact information is required" in e for e in corrupt_errors)


# ═══════════════════════════════════════════════════════════
# 2. 8-GATE GOVERNANCE ENFORCEMENT
# ═══════════════════════════════════════════════════════════

def test_prohibited_and_pending_sources_blocked():
    # Air India is PROHIBITED_WITHOUT_PERMISSION
    gate_ai = check_source_permitted("air_india")
    assert not gate_ai.is_permitted
    assert gate_ai.failed_gate == 1
    assert "Gate 1 failed" in gate_ai.reason

    # MakeMyTrip is PROHIBITED_WITHOUT_PERMISSION
    gate_mmt = check_source_permitted("makemytrip")
    assert not gate_mmt.is_permitted
    assert gate_mmt.failed_gate == 1

    # IndiGo is PENDING_FORMAL_REVIEW
    gate_igo = check_source_permitted("indigo")
    assert not gate_igo.is_permitted
    assert gate_igo.failed_gate == 1

    # Simulator is NON_EMPIRICAL: cannot make live network calls
    gate_sim = check_source_permitted("simulator")
    assert not gate_sim.is_permitted
    assert gate_sim.failed_gate == 1
    assert "NON_EMPIRICAL" in gate_sim.reason

    # Amadeus is AVAILABLE_AFTER_FREE_REGISTRATION
    gate_amadeus = check_source_permitted("amadeus")
    assert gate_amadeus.is_permitted
    assert gate_amadeus.failed_gate is None


def test_approved_path_restrictions():
    rec = SourceAccessRecord(
        source_id="test_api",
        display_name="Test API",
        operator="Test Org",
        source_kind="DIRECT_API",
        acquisition_method="API",
        homepage_url="https://api.test.org",
        search_url_pattern="https://api.test.org/v1/search",
        robots_url="",
        terms_url="",
        terms_reviewed_at=datetime.now(timezone.utc),
        terms_content_sha256="",
        robots_reviewed_at=datetime.now(timezone.utc),
        robots_content_sha256="",
        permission_status=PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION,
        permission_evidence_path="",
        approved_paths=("/v1/search", "/v1/health"),
        maximum_requests_per_minute=10,
        maximum_requests_per_day=500,
        contact="test@example.com",
        review_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        notes="",
    )

    # Approved path
    allowed = GovernanceValidator.evaluate_gates(rec, url_path="/v1/search")
    assert allowed.is_permitted

    # Unapproved path
    blocked = GovernanceValidator.evaluate_gates(rec, url_path="/v2/admin")
    assert not blocked.is_permitted
    assert blocked.failed_gate == 2
    assert "not within approved paths" in blocked.reason


def test_expired_source_review_blocked():
    rec = SourceAccessRecord(
        source_id="expired_source",
        display_name="Expired Source",
        operator="Expired Org",
        source_kind="DIRECT_API",
        acquisition_method="API",
        homepage_url="https://api.test.org",
        search_url_pattern="https://api.test.org/search",
        robots_url="",
        terms_url="",
        terms_reviewed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        terms_content_sha256="",
        robots_reviewed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        robots_content_sha256="",
        permission_status=PermissionStatus.APPROVED,
        permission_evidence_path="",
        approved_paths=("/search",),
        maximum_requests_per_minute=10,
        maximum_requests_per_day=500,
        contact="admin@example.com",
        review_expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),  # Past date
        notes="",
    )
    res = GovernanceValidator.evaluate_gates(rec, url_path="/search")
    assert not res.is_permitted
    assert res.failed_gate == 8
    assert "Review period for source 'expired_source' expired" in res.reason


def test_terms_and_robots_hash_drift_detection():
    rec = SourceAccessRecord(
        source_id="drift_test",
        display_name="Drift Test",
        operator="Drift Org",
        source_kind="DIRECT_API",
        acquisition_method="API",
        homepage_url="https://api.test.org",
        search_url_pattern="https://api.test.org/search",
        robots_url="https://api.test.org/robots.txt",
        terms_url="https://api.test.org/terms",
        terms_reviewed_at=datetime.now(timezone.utc),
        terms_content_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        robots_reviewed_at=datetime.now(timezone.utc),
        robots_content_sha256="1111111111111111111111111111111111111111111111111111111111111111",
        permission_status=PermissionStatus.APPROVED,
        permission_evidence_path="",
        approved_paths=("/search",),
        maximum_requests_per_minute=10,
        maximum_requests_per_day=500,
        contact="admin@example.com",
        review_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        notes="",
    )

    # Different terms content
    drift_terms = GovernanceValidator.evaluate_gates(
        rec, url_path="/search", current_terms_content="New Terms of Service 2026"
    )
    assert not drift_terms.is_permitted
    assert drift_terms.failed_gate == 8
    assert "Terms content hash drift" in drift_terms.reason

    # Different robots content
    drift_robots = GovernanceValidator.evaluate_gates(
        rec, url_path="/search", current_robots_content="User-agent: *\nDisallow: /search"
    )
    assert not drift_robots.is_permitted
    assert drift_robots.failed_gate == 8
    assert "Robots content hash drift" in drift_robots.reason


# ═══════════════════════════════════════════════════════════
# 3. FREE BUDGET ENFORCEMENT & QUOTA THRESHOLDS
# ═══════════════════════════════════════════════════════════

def test_budget_thresholds_evaluation():
    async def _test():
        db = get_database()
        await db.create_schema()
        session = db.session()

        source_id = "test_quota_src"
        daily_b, monthly_b = await BudgetController.get_or_create_budgets(session, source_id)
        daily_b.limit_count = 100
        monthly_b.limit_count = 1000
        await session.commit()

        # 1. Normal (0% used)
        e0 = await BudgetController.evaluate_budget(session, source_id, projected_count=10)
        assert e0.status == BudgetStatus.NORMAL
        assert e0.can_proceed
        assert not e0.is_reduced_basket

        # 2. Warning threshold (80% used)
        await BudgetController.record_usage(session, source_id, count=80, success=True)
        await session.commit()
        e80 = await BudgetController.evaluate_budget(session, source_id, projected_count=1)
        assert e80.status == BudgetStatus.WARNING
        assert e80.can_proceed
        assert not e80.is_reduced_basket

        # 3. Reduced basket threshold (95% used)
        await BudgetController.record_usage(session, source_id, count=15, success=True)  # total 95
        await session.commit()
        e95 = await BudgetController.evaluate_budget(session, source_id, projected_count=1)
        assert e95.status == BudgetStatus.REDUCED_BASKET
        assert e95.can_proceed
        assert e95.is_reduced_basket

        # 4. Hard Stop (100% used)
        await BudgetController.record_usage(session, source_id, count=5, success=True)  # total 100
        await session.commit()
        e100 = await BudgetController.evaluate_budget(session, source_id, projected_count=1)
        assert e100.status == BudgetStatus.QUOTA_EXHAUSTED
        assert not e100.can_proceed
        assert "Budget hard stop" in e100.reason

        await session.close()

    asyncio.run(_test())


# ═══════════════════════════════════════════════════════════
# 4. BILLING OVERAGE SAFETY GATE ON STARTUP
# ═══════════════════════════════════════════════════════════

def test_startup_rejects_paid_overage_without_confirmation(monkeypatch):
    monkeypatch.setenv("ALLOW_PAID_OVERAGE", "true")
    monkeypatch.delenv("ALLOW_PAID_OVERAGE_CONFIRMED", raising=False)

    with pytest.raises(RuntimeError, match="ALLOW_PAID_OVERAGE is enabled without explicit second control"):
        build_settings()

    # With second control confirmed, it succeeds
    monkeypatch.setenv("ALLOW_PAID_OVERAGE_CONFIRMED", "true")
    settings = build_settings()
    assert settings.amadeus.allow_paid_overage is True


# ═══════════════════════════════════════════════════════════
# 5. API GOVERNANCE & BUDGET ENDPOINTS
# ═══════════════════════════════════════════════════════════

def test_api_source_governance_and_budget_endpoints():
    async def _test():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                # Governance endpoint for prohibited source
                resp_ai = await client.get("/api/v1/sources/air_india/governance")
                assert resp_ai.status_code == 200
                data_ai = resp_ai.json()
                assert data_ai["source_id"] == "air_india"
                assert data_ai["is_permitted"] is False
                assert data_ai["gate_status"] == PermissionStatus.PROHIBITED_WITHOUT_PERMISSION
                assert data_ai["failed_gate"] == 1

                # Governance endpoint for permitted source
                resp_am = await client.get("/api/v1/sources/amadeus/governance")
                assert resp_am.status_code == 200
                data_am = resp_am.json()
                assert data_am["source_id"] == "amadeus"
                assert data_am["is_permitted"] is True
                assert data_am["gate_status"] == PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION

                # 404 for unknown source
                resp_404 = await client.get("/api/v1/sources/nonexistent_xyz/governance")
                assert resp_404.status_code == 404

                # Budget endpoint
                resp_budget = await client.get("/api/v1/sources/budget")
                assert resp_budget.status_code == 200
                data_budget = resp_budget.json()
                assert "budgets" in data_budget
                assert "policy" in data_budget
                assert data_budget["policy"]["warning_threshold_pct"] == 80.0
                assert data_budget["policy"]["reduced_basket_threshold_pct"] == 95.0
                assert data_budget["policy"]["hard_stop_pct"] == 100.0
                assert "DEL-BOM" in data_budget["policy"]["tracer_routes"]

    asyncio.run(_test())
