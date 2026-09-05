"""
SIH26056 — Shared Browser Acquisition Collector (Playwright).

Controls headless Chromium for authorized JavaScript-rendered portal flows:
- Enforces isolated browser context per run; discards cookies afterward.
- Blocks images, media, and fonts to minimize host load.
- Prohibits stealth plugins, CAPTCHA bypass, and credential injection.
- Redacts secrets and archives DOM snapshots to the immutable artifact store.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from scraper.web.artifact_store import ArtifactStore, StoredArtifact
from scraper.web.errors import (
    AcquisitionTimeoutError,
    AuthWallError,
    CaptchaChallengeError,
    PolicyBlockError,
    ScraperRuntimeError,
)
from scraper.web.source_policy import SourcePolicyEnforcer

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class BrowserAcquisitionResult:
    source_id: str
    url: str
    html_content: str
    stored_artifact: StoredArtifact


class BrowserCollector:
    """Acquires JavaScript-rendered portal flows using headless Chromium."""

    def __init__(
        self,
        artifact_store: Optional[ArtifactStore] = None,
        timeout_seconds: float = 30.0,
        user_agent: str = "AirfareCPI-Research/2.0 (SIH26056 academic prototype; contact: repository maintainer)",
    ):
        self.artifact_store = artifact_store or ArtifactStore()
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    async def fetch_page(
        self,
        source_id: str,
        url: str,
        wait_selector: Optional[str] = None,
    ) -> BrowserAcquisitionResult:
        """
        Navigate to url, wait for content readiness, inspect for bot challenges,
        and archive sanitized DOM capture.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ScraperRuntimeError("Playwright is not installed or available in this Python environment.")

        # 1. Enforce Source Policy Gate before launch
        SourcePolicyEnforcer.check_can_fetch(
            source_id=source_id,
            target_url=url,
            user_agent=self.user_agent,
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            # Isolated context per run: no cookie retention across collection tasks
            context = await browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
            )
            page = await context.new_page()

            # Block heavy non-analytical resources (images, fonts, stylesheets, media)
            async def _route_filter(route):
                if route.request.resource_type in {"image", "media", "font"}:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", _route_filter)

            try:
                logger.debug(f"[{source_id}] Navigating browser to {url}")
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=int(self.timeout_seconds * 1000),
                )

                if wait_selector:
                    await page.wait_for_selector(
                        wait_selector,
                        timeout=int(self.timeout_seconds * 1000),
                    )

                html = await page.content()
            except Exception as exc:
                if "Timeout" in str(type(exc)):
                    raise AcquisitionTimeoutError(f"Browser navigation timed out for {url}: {exc}")
                raise ScraperRuntimeError(f"Browser navigation failed: {exc}")
            finally:
                await context.close()
                await browser.close()

        # 2. Check for challenges / auth walls in rendered DOM
        lower_html = html.lower()
        if (
            "cf-challenge" in lower_html
            or "g-recaptcha" in lower_html
            or "hcaptcha" in lower_html
            or "please verify you are a human" in lower_html
            or "robot check" in lower_html
        ):
            raise CaptchaChallengeError(
                f"Bot challenge rendered on {source_id}. Bypassing is prohibited."
            )

        if "login to your account" in lower_html and "enter password" in lower_html:
            raise AuthWallError(f"Login required to view fare offers on {source_id}.")

        # 3. Store sanitized immutable artifact
        stored = self.artifact_store.store_capture(
            source_id=source_id,
            url=url,
            content=html,
            mime_type="text/html",
        )

        return BrowserAcquisitionResult(
            source_id=source_id,
            url=url,
            html_content=html,
            stored_artifact=stored,
        )
