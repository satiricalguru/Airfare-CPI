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
from urllib.parse import urlparse

from loguru import logger

from scraper.politeness import HostRateLimiter, extract_domain_root
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


DEFAULT_POLICY_UA = "AirfareCPI-Research/2.0 (SIH26056 academic prototype; contact: repository maintainer)"
DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


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
        timeout_seconds: float = 35.0,
        user_agent: str = DEFAULT_POLICY_UA,
        browser_user_agent: str = DEFAULT_BROWSER_UA,
        rate_limiter: Optional[HostRateLimiter] = None,
        max_host_concurrency: int = 2,
    ):
        self.artifact_store = artifact_store or ArtifactStore()
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.browser_user_agent = browser_user_agent
        self.rate_limiter = rate_limiter or HostRateLimiter(
            min_interval_seconds=1.5,
            jitter_seconds=0.25,
            host_intervals={
                "easemytrip.com": 3.0,
                "flight.easemytrip.com": 3.0,
                "google.com": 1.5,
                "travel.google.com": 1.5,
            },
        )
        self.max_host_concurrency = max(1, max_host_concurrency)
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_host_semaphore(self, host: str) -> asyncio.Semaphore:
        root = extract_domain_root(host)
        if root not in self._host_semaphores:
            self._host_semaphores[root] = asyncio.Semaphore(self.max_host_concurrency)
        return self._host_semaphores[root]

    async def fetch_page(
        self,
        source_id: str,
        url: str,
        wait_selector: Optional[str] = None,
        settle_ms: int = 2500,
    ) -> BrowserAcquisitionResult:
        """
        Navigate to url, wait for content readiness, inspect for bot challenges,
        and archive sanitized DOM capture.
        """
        res, _ = await self.fetch_page_and_cards(
            source_id=source_id,
            url=url,
            wait_selector=wait_selector,
            card_selectors=(),
            settle_ms=settle_ms,
        )
        return res

    async def fetch_page_and_cards(
        self,
        source_id: str,
        url: str,
        card_selectors: tuple[str, ...] = ("div.yR1fYc", "li.pIavfa"),
        wait_selector: Optional[str] = None,
        settle_ms: int = 2500,
    ) -> tuple[BrowserAcquisitionResult, list[str]]:
        """
        Navigate to url, wait for content readiness, inspect for challenges,
        extract text from matching card locators, and archive sanitized DOM capture.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ScraperRuntimeError("Playwright is not installed or available in this Python environment.")

        # 1. Enforce Source Policy Gate before launch
        SourcePolicyEnforcer.check_can_fetch(
            source_id=source_id,
            target_url=url,
            user_agent=self.user_agent,
        )

        host = urlparse(url).netloc or url
        sem = self._get_host_semaphore(host)

        async with sem:
            # Enforce politeness delay for this host
            waited = await self.rate_limiter.acquire(url)
            if waited > 0:
                logger.debug(f"[{source_id}] Waited {waited:.2f}s for host rate limit ({host})")

            card_texts: list[str] = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    user_agent=self.browser_user_agent,
                    viewport={"width": 1280, "height": 800},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    extra_http_headers={
                        "X-Research-Identity": self.user_agent,
                    },
                )
                page = await context.new_page()

                # Block heavy non-analytical media
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
                        try:
                            await page.wait_for_selector(
                                wait_selector,
                                timeout=int(min(self.timeout_seconds, 12.0) * 1000),
                            )
                        except Exception:
                            pass

                    if settle_ms > 0:
                        await page.wait_for_timeout(settle_ms)

                    # Extract live card texts if selectors supplied
                    if card_selectors:
                        selector_str = ", ".join(card_selectors)
                        locators = await page.locator(selector_str).all()
                        for loc in locators:
                            try:
                                txt = (await loc.inner_text()).strip()
                                if txt:
                                    card_texts.append(txt)
                            except Exception:
                                pass

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

        acq_result = BrowserAcquisitionResult(
            source_id=source_id,
            url=url,
            html_content=html,
            stored_artifact=stored,
        )
        return acq_result, card_texts

