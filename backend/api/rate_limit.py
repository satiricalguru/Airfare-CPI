"""Small, explicit per-process request limiter for expensive API operations.

This protects the collection controller and optional Copilot provider from accidental
repeated clicks and simple abuse.  It deliberately does not trust forwarding headers:
the application has no trusted-proxy configuration, so ``request.client.host`` is the
only identity used here.

The limiter is in-memory and therefore scoped to one API worker.  A multi-worker or
multi-replica deployment must also enforce equivalent limits at its ingress/gateway.
Keeping that limitation in this module makes it visible rather than implying that a
single process dictionary is a distributed security control.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class RateLimitDecision:
    """Result of attempting to consume one slot in a rolling time window."""

    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Thread-safe rolling-window counter with bounded retained state."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, *, bucket: str, identity: str, limit: int, window_seconds: int) -> RateLimitDecision:
        """Consume a slot, or report how long until the oldest slot expires."""
        if limit <= 0 or window_seconds <= 0:
            # A bad deployment value should not silently turn this endpoint into an
            # unbounded external-cost sink.  Treat it as disabled until corrected.
            return RateLimitDecision(allowed=False, retry_after_seconds=60)

        now = monotonic()
        key = f"{bucket}:{identity}"
        with self._lock:
            events = self._events[key]
            cutoff = now - window_seconds
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(1, ceil(events[0] + window_seconds - now))
                return RateLimitDecision(False, retry_after)

            events.append(now)
            return RateLimitDecision(True)

    def reset(self) -> None:
        """Clear retained counters (used by isolated automated tests)."""
        with self._lock:
            self._events.clear()


rate_limiter = SlidingWindowRateLimiter()


def client_identity(request: Request) -> str:
    """Return the directly connected peer; do not accept spoofable forwarded headers."""
    return request.client.host if request.client and request.client.host else "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise a standard HTTP 429 response once a bucket is exhausted."""
    decision = rate_limiter.check(
        bucket=bucket,
        identity=client_identity(request),
        limit=limit,
        window_seconds=window_seconds,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many requests for this expensive operation. Try again after "
                f"{decision.retry_after_seconds} seconds."
            ),
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
