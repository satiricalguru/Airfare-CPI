"""
SIH26056 — Shared HTTP Acquisition Collector.

Performs polite, single-concurrency HTTP retrieval with:
- Source policy gate verification before dispatch.
- Project user-agent identification.
- Bounded response timeouts.
- CAPTCHA / Cloudflare / Auth wall detection (never bypassed).
- Immutable raw artifact persistence with secret redaction.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional
import urllib.parse

import httpx
from loguru import logger

from scraper.web.artifact_store import ArtifactStore, StoredArtifact
from scraper.web.errors import (
    AcquisitionTimeoutError,
    AuthWallError,
    CaptchaChallengeError,
    NetworkFailureError,
    PolicyBlockError,
    RateLimitError,
    RobotsBlockError,
)
from scraper.web.source_policy import SourcePolicyEnforcer

DEFAULT_USER_AGENT = (
    "AirfareCPI-Research/2.0 (SIH26056 academic price-index prototype; "
    "contact: repository maintainer)"
)

# Host-level lock to ensure concurrency of one per host as per Phase 3 requirements
_HOST_LOCKS: dict[str, asyncio.Lock] = {}


def _get_host_lock(url: str) -> asyncio.Lock:
    netloc = urllib.parse.urlparse(url).netloc
    if netloc not in _HOST_LOCKS:
        _HOST_LOCKS[netloc] = asyncio.Lock()
    return _HOST_LOCKS[netloc]


@dataclass
class HttpAcquisitionResult:
    source_id: str
    url: str
    status_code: int
    content_text: str
    stored_artifact: StoredArtifact
    headers: dict[str, str]


class HttpCollector:
    """Polite HTTP collector for server-rendered airline and travel portal pages."""

    def __init__(
        self,
        artifact_store: Optional[ArtifactStore] = None,
        timeout_seconds: float = 20.0,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.artifact_store = artifact_store or ArtifactStore()
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    async def fetch(
        self,
        source_id: str,
        url: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        robots_txt_content: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> HttpAcquisitionResult:
        """
        Fetch an authorized target URL with strict policy checks, single concurrency,
        and automatic raw capture archiving.
        """
        # 1. Check Source Access Policy
        SourcePolicyEnforcer.check_can_fetch(
            source_id=source_id,
            target_url=url,
            user_agent=self.user_agent,
            robots_txt_content=robots_txt_content,
        )

        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        host_lock = _get_host_lock(url)
        async with host_lock:
            owns_client = client is None
            http_client = client or httpx.AsyncClient(timeout=self.timeout_seconds)

            try:
                logger.debug(f"[{source_id}] Fetching {url}")
                response = await http_client.get(url, headers=req_headers, params=params)
            except httpx.TimeoutException as exc:
                raise AcquisitionTimeoutError(f"HTTP request timed out after {self.timeout_seconds}s: {exc}")
            except httpx.RequestError as exc:
                raise NetworkFailureError(f"Network failure connecting to {url}: {exc}")
            finally:
                if owns_client:
                    await http_client.aclose()

        # 2. Status & Challenge Inspections
        content = response.text

        # Detect Rate Limiting
        if response.status_code == 429:
            raise RateLimitError(f"Rate limited (HTTP 429) by {source_id} for {url}")

        # Detect Authentication Wall
        if response.status_code in {401, 403}:
            if "captcha" not in content.lower() and "challenge" not in content.lower():
                raise AuthWallError(
                    f"Authentication or authorization required (HTTP {response.status_code}) by {source_id}"
                )

        # Detect CAPTCHA or Bot Challenge (never solve or bypass)
        lower_content = content.lower()
        if (
            "cf-challenge" in lower_content
            or "g-recaptcha" in lower_content
            or "hcaptcha" in lower_content
            or "datadome" in lower_content
            or "perimeterx" in lower_content
            or "please verify you are a human" in lower_content
        ):
            raise CaptchaChallengeError(
                f"Bot challenge or CAPTCHA encountered from {source_id}. Bypassing is prohibited."
            )

        # 3. Store sanitized immutable artifact
        stored = self.artifact_store.store_capture(
            source_id=source_id,
            url=str(response.url),
            content=content,
            mime_type=response.headers.get("content-type", "text/html"),
        )

        return HttpAcquisitionResult(
            source_id=source_id,
            url=str(response.url),
            status_code=response.status_code,
            content_text=content,
            stored_artifact=stored,
            headers=dict(response.headers),
        )
