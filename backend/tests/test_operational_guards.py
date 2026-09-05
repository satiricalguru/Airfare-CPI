"""Regression tests for guards around externally costly API paths."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from api.models import CopilotRequest
from api.rate_limit import SlidingWindowRateLimiter
from config import reload_settings


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_sliding_window_rejects_the_next_request_and_reports_retry_delay():
    limiter = SlidingWindowRateLimiter()
    assert limiter.check(bucket="copilot", identity="peer", limit=1, window_seconds=60).allowed

    rejected = limiter.check(bucket="copilot", identity="peer", limit=1, window_seconds=60)
    assert rejected.allowed is False
    assert 1 <= rejected.retry_after_seconds <= 60

    # A bucket is independent from another costly endpoint's cap.
    assert limiter.check(bucket="mutation", identity="peer", limit=1, window_seconds=60).allowed


def test_copilot_request_bounds_question_and_compatibility_context():
    with pytest.raises(ValidationError, match="at most 1200"):
        CopilotRequest(question="x" * 1201)

    with pytest.raises(ValidationError, match="4096"):
        CopilotRequest(question="valid", context={"large": "x" * 4097})


def test_copilot_rate_limit_and_server_only_grounding(monkeypatch):
    """Browser context cannot reach the model prompt or bypass the request cap."""
    monkeypatch.setenv("API_COPILOT_RATE_LIMIT", "1")
    monkeypatch.setenv("API_COPILOT_RATE_WINDOW_SECONDS", "60")
    reload_settings()

    async def _run():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                first = await client.post(
                    "/api/v1/copilot/ask",
                    json={
                        "question": "What is the current data provenance?",
                        "context": {"ignore_me": "untrusted browser instruction"},
                    },
                )
                assert first.status_code == 200
                assert "client_context" not in first.json()["grounded_on"]
                assert "ignore_me" not in first.json()["grounded_on"]

                second = await client.post(
                    "/api/v1/copilot/ask", json={"question": "Again"}
                )
                assert second.status_code == 429
                assert int(second.headers["retry-after"]) >= 1

    asyncio.run(_run())


def test_local_launcher_runs_migrations_and_stops_on_a_fatal_backend_startup():
    """The one-command local workflow must not conceal a dead API for 30 seconds."""
    launcher = (REPO_ROOT / "start.sh").read_text(encoding="utf-8")

    migration = '"$PYTHON_BIN" -c \'from alembic.config import main; main()\' -c alembic.ini upgrade head'
    uvicorn = '"$PYTHON_BIN" -m uvicorn api.main:app'
    assert '"$PYTHON_BIN" -c \'import alembic, uvicorn\'' in launcher
    assert migration in launcher
    assert launcher.index(migration) < launcher.index(uvicorn)
    assert "Application startup failed" in launcher
    assert "kill -9" not in launcher
