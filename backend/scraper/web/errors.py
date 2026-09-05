"""
SIH26056 — Scraper Runtime Acquisition Errors.

Explicit exception hierarchy distinguishing specific failure causes:
- Policy block: source prohibited or unapproved.
- Robots block: target path disallowed by robots.txt.
- Auth wall: unexpected login or token required.
- CAPTCHA challenge: bot challenge detected (never bypassed).
- Selector drift: HTML changed such that selectors fail.
- No availability: genuine sold out / no flights found.
- Rate limit: 429 Too Many Requests.
- Timeout: navigation or response deadline exceeded.
- Parse error: invalid data, unparseable numbers.
- Network failure: connection dropped or DNS failure.
"""

from __future__ import annotations


class ScraperRuntimeError(Exception):
    """Base error for all web acquisition runtime issues."""
    pass


class PolicyBlockError(ScraperRuntimeError):
    """Raised when source governance blocks access (e.g. unapproved terms, expired review)."""
    pass


class RobotsBlockError(ScraperRuntimeError):
    """Raised when robots.txt disallows the target URL or user agent."""
    pass


class AuthWallError(ScraperRuntimeError):
    """Raised when an unexpected authentication screen, paywall, or login is encountered."""
    pass


class CaptchaChallengeError(ScraperRuntimeError):
    """
    Raised when a CAPTCHA or Cloudflare challenge is presented.
    In accordance with Section 10 rules, CAPTCHAs are NEVER solved or bypassed.
    """
    pass


class SelectorDriftError(ScraperRuntimeError):
    """Raised when the expected DOM structure has changed and selectors fail."""
    pass


class NoAvailabilityError(ScraperRuntimeError):
    """Raised when a search truthfully returns zero available seats or sold out."""
    pass


class RateLimitError(ScraperRuntimeError):
    """Raised when HTTP 429 or excessive request rejection occurs."""
    pass


class AcquisitionTimeoutError(ScraperRuntimeError):
    """Raised when navigation, response, or total cycle timeout is exceeded."""
    pass


class ParseError(ScraperRuntimeError):
    """Raised when fare or flight numbers fail reconciliation or validation."""
    pass


class NetworkFailureError(ScraperRuntimeError):
    """Raised when connection drops, TLS handshake fails, or host is unreachable."""
    pass
