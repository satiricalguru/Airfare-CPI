"""
SIH26056 — Assessed and Disabled Affiliate Sources.

These adapters exist as documentation for sources evaluated and not collected.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from provenance import SourceType
from scraper.base import (
    BaseFareSource,
    CABIN_ECONOMY,
    SourceCapability,
    SourceResult,
)

ENABLING_REQUIREMENTS = (
    "To enable: obtain written authorization or an executed partner/affiliate "
    "agreement from the operator; confirm the target path is allowed by robots.txt "
    "for this project's user agent; agree a request rate with the operator; and "
    "implement collection without evading any bot-detection, CAPTCHA, or "
    "authentication mechanism. Until all four hold, this adapter stays disabled."
)


@dataclass(frozen=True)
class DisabledSourceSpec:
    name: str
    display_name: str
    homepage: str
    reason: str
    category: str


# Assessment record. `reason` is this project's stated basis for not collecting.
DISABLED_SOURCES: tuple[DisabledSourceSpec, ...] = (
    DisabledSourceSpec(
        name="kiwi",
        display_name="Kiwi.com Tequila (affiliate API)",
        homepage="https://tequila.kiwi.com",
        category="api_partner",
        reason=(
            "Documented API gated behind affiliate approval. No agreement is in place "
            "for this project, so it is not called."
        ),
    ),
)


class DisabledSource(BaseFareSource):
    """A source that is assessed and not used."""

    def __init__(self, spec: DisabledSourceSpec):
        self.spec = spec
        super().__init__(
            SourceCapability(
                name=spec.name,
                display_name=spec.display_name,
                source_type=SourceType.LIVE,
                enabled=False,
                disabled_reason=f"{spec.reason} {ENABLING_REQUIREMENTS}",
                requires_credentials=False,
                homepage=spec.homepage,
                terms_url=f"{spec.homepage.rstrip('/')}/",
                robots_url=f"{spec.homepage.rstrip('/')}/robots.txt",
                compliance_note=(
                    f"Assessed and NOT collected ({spec.category}). {spec.reason}"
                ),
                supports_cabin=(CABIN_ECONOMY,),
                native_currency="INR",
            )
        )

    async def _search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: str,
        route_id: int,
        booking_horizon_days: int,
    ) -> SourceResult:  # pragma: no cover
        raise RuntimeError(
            f"{self.spec.name} is a disabled source and has no collection "
            f"implementation. It must never be invoked."
        )


def describe_for(spec: DisabledSourceSpec) -> SourceCapability:
    return DisabledSource(spec).capability


def create_for(spec: DisabledSourceSpec, **_kwargs: Any) -> DisabledSource:
    return DisabledSource(spec)
