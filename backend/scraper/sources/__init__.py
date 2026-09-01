"""
SIH26056 — Source registrations.

Importing this package registers every adapter with the shared registry. Adding a
source means adding it here; nothing in the index engine changes.

The registry intentionally contains disabled entries. ``GET /api/v1/sources`` exposes
all of them with their reasons, so the answer to "why aren't you scraping MakeMyTrip?"
is in the API rather than left to inference.
"""

from __future__ import annotations

from scraper.registry import registry
from scraper.sources import amadeus, disabled_otas, offline_fixture, simulator


def _register_all() -> None:
    # Guard against double registration when the module is re-imported (e.g. by
    # tests that reload configuration).
    if registry.has(amadeus.SOURCE_NAME):
        return

    # The one genuine live source.
    registry.register(
        amadeus.SOURCE_NAME,
        factory=amadeus.create,
        describe=amadeus.describe,
    )

    # Research instrument.
    registry.register(
        simulator.SOURCE_NAME,
        factory=simulator.create,
        describe=simulator.describe,
    )

    # Fixture replay for CI and offline demonstration.
    registry.register(
        offline_fixture.SOURCE_NAME,
        factory=offline_fixture.create,
        describe=offline_fixture.describe,
    )

    # Assessed-and-declined sources, registered so their reasons are discoverable.
    for spec in disabled_otas.DISABLED_SOURCES:
        registry.register(
            spec.name,
            factory=(lambda s=spec, **kw: disabled_otas.create_for(s, **kw)),
            describe=(lambda s=spec: disabled_otas.describe_for(s)),
        )


_register_all()


__all__ = ["amadeus", "simulator", "offline_fixture", "disabled_otas", "registry"]
