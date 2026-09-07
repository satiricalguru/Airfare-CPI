"""
SIH26056 — Source registrations.

Importing this package registers every adapter with the shared registry.
Includes direct airline portals (IndiGo, Air India, SpiceJet, Akasa Air),
online travel agencies (MakeMyTrip, Goibibo, Cleartrip, EaseMyTrip),
high-speed RPC engine (FastFlights), metasearch (Skyscanner), and GDS APIs (Amadeus).
"""

from __future__ import annotations

from scraper.registry import registry
from scraper.sources import (
    air_india,
    akasa,
    amadeus,
    cleartrip,
    disabled_otas,
    easemytrip,
    fast_flights_adapter,
    goibibo,
    indigo,
    live_portal_adapter,
    makemytrip,
    offline_fixture,
    simulator,
    skyscanner,
    spicejet,
)


def _register_all() -> None:
    if registry.has(amadeus.SOURCE_NAME):
        return

    # Established Live sources
    registry.register(
        amadeus.SOURCE_NAME,
        factory=amadeus.create,
        describe=amadeus.describe,
    )
    registry.register(
        live_portal_adapter.SOURCE_NAME,
        factory=live_portal_adapter.create,
        describe=live_portal_adapter.describe,
    )
    registry.register(
        easemytrip.SOURCE_NAME,
        factory=easemytrip.create,
        describe=easemytrip.describe,
    )

    # Newly Enabled Indian Airlines & OTAs
    registry.register(
        makemytrip.SOURCE_NAME,
        factory=makemytrip.create,
        describe=makemytrip.describe,
    )
    registry.register(
        goibibo.SOURCE_NAME,
        factory=goibibo.create,
        describe=goibibo.describe,
    )
    registry.register(
        cleartrip.SOURCE_NAME,
        factory=cleartrip.create,
        describe=cleartrip.describe,
    )
    registry.register(
        indigo.SOURCE_NAME,
        factory=indigo.create,
        describe=indigo.describe,
    )
    registry.register(
        air_india.SOURCE_NAME,
        factory=air_india.create,
        describe=air_india.describe,
    )
    registry.register(
        spicejet.SOURCE_NAME,
        factory=spicejet.create,
        describe=spicejet.describe,
    )
    registry.register(
        akasa.SOURCE_NAME,
        factory=akasa.create,
        describe=akasa.describe,
    )
    registry.register(
        skyscanner.SOURCE_NAME,
        factory=skyscanner.create,
        describe=skyscanner.describe,
    )
    registry.register(
        fast_flights_adapter.SOURCE_NAME,
        factory=fast_flights_adapter.create,
        describe=fast_flights_adapter.describe,
    )

    # Research instrument
    registry.register(
        simulator.SOURCE_NAME,
        factory=simulator.create,
        describe=simulator.describe,
    )

    # Fixture replay for CI and offline demonstration
    registry.register(
        offline_fixture.SOURCE_NAME,
        factory=offline_fixture.create,
        describe=offline_fixture.describe,
    )

    # Assessed-and-declined affiliate sources
    for spec in disabled_otas.DISABLED_SOURCES:
        registry.register(
            spec.name,
            factory=(lambda s=spec, **kw: disabled_otas.create_for(s, **kw)),
            describe=(lambda s=spec: disabled_otas.describe_for(s)),
        )


_register_all()


__all__ = [
    "air_india",
    "akasa",
    "amadeus",
    "cleartrip",
    "disabled_otas",
    "easemytrip",
    "fast_flights_adapter",
    "goibibo",
    "indigo",
    "live_portal_adapter",
    "makemytrip",
    "offline_fixture",
    "registry",
    "simulator",
    "skyscanner",
    "spicejet",
]
