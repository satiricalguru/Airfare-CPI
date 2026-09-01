"""
SIH26056 — Airline and OTA adapters that are assessed and DISABLED.

These adapters exist as documentation, not as dormant code. Each records a source
that was evaluated for this project and the specific reason it is not scraped. They
cannot return data: :class:`DisabledSource` has no collection path at all, only a
reason.

Why keep them
-------------
The problem statement is about scraping airline and OTA portals. Silently omitting
those sources would leave a reviewer to guess whether they were overlooked. Recording
them with reasons answers the question directly and keeps the assessment auditable.

Why they are disabled
---------------------
Indian airline and OTA fare search is generally either:

* disallowed for automated agents in the site's ``robots.txt``, or
* served only behind bot-detection, device fingerprinting, or challenge pages, or
* restricted by terms of service that prohibit automated extraction, or
* available through a partner/affiliate programme requiring an agreement this
  project does not hold.

In every one of those cases, collecting anyway would mean circumventing an access
control or breaching stated terms. This project does not do that, so the honest
outcome is a disabled adapter with the reason stated.

Enabling any of these requires, at minimum: written permission or an executed
partner agreement, a robots.txt path check that returns allow, an agreed rate limit,
and an implementation that does not evade any protection mechanism. The
``ENABLING_REQUIREMENTS`` note on each entry states this per source.

The statements below describe this project's own compliance posture and the reason it
declined to scrape each source. They are not legal advice and not a claim about what
any operator does or does not permit in general.
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
        name="makemytrip",
        display_name="MakeMyTrip (OTA)",
        homepage="https://www.makemytrip.com",
        category="ota",
        reason=(
            "Flight-search results are produced by an authenticated internal API behind "
            "bot-detection, and the site's terms prohibit automated extraction. "
            "Collecting would require evading an access control, so this project does "
            "not attempt it."
        ),
    ),
    DisabledSourceSpec(
        name="goibibo",
        display_name="Goibibo (OTA)",
        homepage="https://www.goibibo.com",
        category="ota",
        reason=(
            "Same platform family and the same restrictions as MakeMyTrip: search "
            "responses are gated behind bot protection and automated extraction is not "
            "permitted by the site terms."
        ),
    ),
    DisabledSourceSpec(
        name="cleartrip",
        display_name="Cleartrip (OTA)",
        homepage="https://www.cleartrip.com",
        category="ota",
        reason=(
            "Fare search requires executing the site's client-side application and is "
            "protected against automated agents. No public fare API is offered for "
            "research use."
        ),
    ),
    DisabledSourceSpec(
        name="indigo",
        display_name="IndiGo (6E) airline portal",
        homepage="https://www.goindigo.in",
        category="airline",
        reason=(
            "The booking engine is a session-based application protected against "
            "automated agents; availability and pricing calls require tokens issued to "
            "an interactive browser session. Driving it programmatically would "
            "circumvent that protection."
        ),
    ),
    DisabledSourceSpec(
        name="air_india",
        display_name="Air India (AI) airline portal",
        homepage="https://www.airindia.com",
        category="airline",
        reason=(
            "Booking flow is gated behind a session and bot-protection layer. Fare data "
            "is available to authorized distribution partners through a GDS rather than "
            "by scraping the consumer site."
        ),
    ),
    DisabledSourceSpec(
        name="spicejet",
        display_name="SpiceJet (SG) airline portal",
        homepage="https://www.spicejet.com",
        category="airline",
        reason=(
            "Search requires an interactive session and is protected against automated "
            "access. No documented public fare endpoint is offered for research use."
        ),
    ),
    DisabledSourceSpec(
        name="akasa",
        display_name="Akasa Air (QP) airline portal",
        homepage="https://www.akasaair.com",
        category="airline",
        reason=(
            "Booking engine is session-based and protected against automated agents; no "
            "documented public fare endpoint."
        ),
    ),
    DisabledSourceSpec(
        name="skyscanner",
        display_name="Skyscanner (metasearch API)",
        homepage="https://www.partners.skyscanner.net",
        category="api_partner",
        reason=(
            "A documented API exists but access requires an approved partner agreement. "
            "This project holds no such agreement, so the adapter is disabled rather "
            "than pointed at an endpoint it is not authorized to call."
        ),
    ),
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
    """
    A source that is assessed and not used.

    Has no collection implementation. ``BaseFareSource.search`` short-circuits on
    ``capability.enabled == False``, and ``_search`` raises if ever reached, so there
    is no path by which this can emit an observation.
    """

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
    ) -> SourceResult:  # pragma: no cover - unreachable by construction
        raise RuntimeError(
            f"{self.spec.name} is a disabled source and has no collection "
            f"implementation. It must never be invoked."
        )


def describe_for(spec: DisabledSourceSpec) -> SourceCapability:
    return DisabledSource(spec).capability


def create_for(spec: DisabledSourceSpec, **_kwargs: Any) -> DisabledSource:
    return DisabledSource(spec)
