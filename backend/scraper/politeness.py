"""
SIH26056 — Politeness controls: robots.txt, rate limiting, bounded retry.

Previously the base scraper's docstring advertised robots.txt compliance, backoff
and rate limiting; none of it existed. This module implements them for real, and is
the only place outbound HTTP politeness is decided.

Scope of what is deliberately NOT here
--------------------------------------
No CAPTCHA solving, no authentication bypass, no proxy rotation, no browser
fingerprint spoofing, no header forgery designed to look like a human. Those are
mechanisms for defeating access controls, and a source that requires them is
treated as not permitted — the adapter stays disabled and says so. The user agent
identifies the project honestly.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger


# ── robots.txt ──

@dataclass
class RobotsDecision:
    """Outcome of a robots.txt check."""

    allowed: bool
    reason: str
    robots_url: Optional[str] = None
    crawl_delay: Optional[float] = None
    checked: bool = True


class RobotsPolicy:
    """
    Fetches and caches robots.txt per host, and answers fetch permission.

    Fail-closed: if robots.txt cannot be retrieved or parsed, the path is treated
    as disallowed. An unreadable policy is not consent, and guessing in the
    permissive direction is exactly the mistake this class exists to avoid.

    ``RFC 9309`` treats a 404 as "no restrictions", so a definitive 404 is honoured
    as allow. A 5xx or a network error is not definitive and is refused.
    """

    def __init__(
        self,
        user_agent: str,
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: float = 3600.0,
    ):
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        # host -> (parser or None, fetched_at, note)
        self._cache: dict[str, tuple[Optional[RobotFileParser], float, str]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def robots_url_for(url: str) -> str:
        parsed = urlparse(url)
        return urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

    def _lock(self, host: str) -> asyncio.Lock:
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def _load(self, url: str) -> tuple[Optional[RobotFileParser], str]:
        parsed = urlparse(url)
        host = parsed.netloc
        robots_url = self.robots_url_for(url)

        cached = self._cache.get(host)
        if cached and (time.monotonic() - cached[1]) < self.cache_ttl_seconds:
            return cached[0], cached[2]

        async with self._lock(host):
            # Re-check: another coroutine may have populated the cache while waiting.
            cached = self._cache.get(host)
            if cached and (time.monotonic() - cached[1]) < self.cache_ttl_seconds:
                return cached[0], cached[2]

            parser: Optional[RobotFileParser] = None
            note = ""
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": self.user_agent},
                ) as client:
                    resp = await client.get(robots_url)

                if resp.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(resp.text.splitlines())
                    note = "robots.txt retrieved"
                elif resp.status_code in (401, 403):
                    # Access to the policy itself is restricted: treat as disallow.
                    note = (
                        f"robots.txt returned HTTP {resp.status_code}; treating the "
                        f"site as disallowed"
                    )
                elif resp.status_code == 404:
                    parser = RobotFileParser()
                    parser.parse([])  # Empty policy: no restrictions.
                    note = "no robots.txt published (HTTP 404); no restrictions declared"
                else:
                    note = (
                        f"robots.txt returned HTTP {resp.status_code}; policy "
                        f"indeterminate, treating as disallowed"
                    )
            except Exception as exc:
                note = (
                    f"robots.txt could not be retrieved ({type(exc).__name__}: {exc}); "
                    f"treating as disallowed"
                )

            self._cache[host] = (parser, time.monotonic(), note)
            return parser, note

    async def check(self, url: str) -> RobotsDecision:
        """Decide whether ``url`` may be fetched under the declared robots policy."""
        robots_url = self.robots_url_for(url)
        parser, note = await self._load(url)

        if parser is None:
            return RobotsDecision(
                allowed=False,
                reason=f"robots.txt policy unavailable: {note}",
                robots_url=robots_url,
            )

        allowed = parser.can_fetch(self.user_agent, url)
        delay = parser.crawl_delay(self.user_agent)

        return RobotsDecision(
            allowed=bool(allowed),
            reason=(
                f"allowed by robots.txt ({note})"
                if allowed
                else f"disallowed by robots.txt for user-agent {self.user_agent!r} ({note})"
            ),
            robots_url=robots_url,
            crawl_delay=float(delay) if delay is not None else None,
        )

    def clear_cache(self) -> None:
        self._cache.clear()


# ── rate limiting ──

class HostRateLimiter:
    """
    Per-host minimum interval between requests.

    Serialises requests to a host so a configured interval is genuinely respected
    even under concurrency, with a small random jitter so many workers do not align
    into a burst at each interval boundary.
    """

    def __init__(self, min_interval_seconds: float, jitter_seconds: float = 0.25):
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self.jitter_seconds = max(0.0, jitter_seconds)
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, host: str) -> asyncio.Lock:
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def acquire(self, url_or_host: str) -> float:
        """Wait until the host may be contacted. Returns seconds actually waited."""
        host = urlparse(url_or_host).netloc or url_or_host
        waited = 0.0
        async with self._lock(host):
            last = self._last_request.get(host)
            now = time.monotonic()
            if last is not None:
                target = last + self.min_interval_seconds
                if self.jitter_seconds:
                    target += random.uniform(0, self.jitter_seconds)
                delay = target - now
                if delay > 0:
                    waited = delay
                    await asyncio.sleep(delay)
            self._last_request[host] = time.monotonic()
        return waited

    def override_min_interval(self, seconds: float) -> None:
        """
        Raise the interval, e.g. to honour a robots.txt Crawl-delay.

        Only ever increases it — a site's declared delay cannot be shortened by
        local configuration.
        """
        if seconds > self.min_interval_seconds:
            logger.info(
                f"Rate limit raised from {self.min_interval_seconds}s to {seconds}s "
                f"to honour a declared crawl delay"
            )
            self.min_interval_seconds = seconds


# ── bounded retry ──

class RetryExhausted(RuntimeError):
    """Raised internally when the retry budget is spent. Callers convert to a result."""

    def __init__(self, message: str, attempts: int, last_error: Optional[BaseException]):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


@dataclass
class RetryPolicy:
    """
    Exponential backoff with a hard attempt ceiling and a per-sleep cap.

    Bounded on purpose. An unbounded retry loop against a source that is rejecting
    requests is indistinguishable from hammering it.
    """

    max_attempts: int = 3
    base_seconds: float = 2.0
    max_seconds: float = 30.0
    jitter: bool = True

    # HTTP statuses worth retrying: transient server-side and rate-limit responses.
    # 4xx other than 429 are the source telling us the request is wrong; repeating
    # it will not help.
    retryable_statuses: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})

    def delay_for(self, attempt: int) -> float:
        """Backoff before ``attempt`` (1-indexed: attempt 1 has no preceding delay)."""
        if attempt <= 1:
            return 0.0
        raw = self.base_seconds * (2 ** (attempt - 2))
        capped = min(raw, self.max_seconds)
        if self.jitter:
            capped *= random.uniform(0.7, 1.0)
        return capped

    def should_retry_status(self, status_code: int) -> bool:
        return status_code in self.retryable_statuses

    async def sleep_before(self, attempt: int) -> None:
        delay = self.delay_for(attempt)
        if delay > 0:
            await asyncio.sleep(delay)


def honest_headers(user_agent: str, accept: str = "application/json") -> dict[str, str]:
    """
    Request headers that identify the client truthfully.

    Deliberately not a spoofed browser fingerprint. Rotating fake user agents to
    evade bot detection is circumvention of an access control, which this project
    does not do; if a source only serves browsers, the correct outcome is a disabled
    adapter with a documented reason.
    """
    return {
        "User-Agent": user_agent,
        "Accept": accept,
        "Accept-Language": "en-IN,en;q=0.9",
    }
