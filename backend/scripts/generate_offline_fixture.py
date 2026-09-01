#!/usr/bin/env python3
"""
Generate the offline fixture used by CI and by OFFLINE mode.

    python3 scripts/generate_offline_fixture.py

Provenance of the fixture itself, stated in the file it writes: these records are
produced by the calibrated simulator, not captured from a live source. They exist so
the pipeline can be exercised deterministically with no network access.

Fixture records are replayed as ``SourceType.OFFLINE`` and display as OFFLINE
PREVIEW. They are never labelled LIVE DATA. If you replace this fixture with a real
captured sample, update ``derivation`` in the output so the record stays accurate.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from engine.weights import get_route_basket  # noqa: E402
from scraper.sources.simulator import SimulatorFareSource  # noqa: E402


# Representative subset kept deliberately small: the fixture is checked into git, so
# it is sized for the pipeline's minimum requirements (a full base period plus several
# current periods, across enough horizons to exercise stratification) rather than for
# breadth. One trunk route, one mid-density, one thinner route.
FIXTURE_ROUTE_IDS = [1, 4, 17]
FIXTURE_HORIZONS = [0, 3, 7, 15, 30]
FIXTURE_START = date(2026, 8, 1)
FIXTURE_DAYS = 10


def main() -> int:
    basket = get_route_basket(BACKEND_DIR.parent / "data" / "route_basket.json")
    routes = [basket.by_id(rid) for rid in FIXTURE_ROUTE_IDS]
    missing = [rid for rid, r in zip(FIXTURE_ROUTE_IDS, routes) if r is None]
    if missing:
        print(f"error: route ids not in basket: {missing}", file=sys.stderr)
        return 1

    simulator = SimulatorFareSource(seed=20260801, drift_origin=FIXTURE_START)

    observations = simulator.generate_history(
        routes=[
            {
                "route_id": r.route_id,
                "origin_code": r.origin_code,
                "destination_code": r.destination_code,
            }
            for r in routes
        ],
        start_date=FIXTURE_START,
        end_date=FIXTURE_START + timedelta(days=FIXTURE_DAYS - 1),
        booking_horizons=FIXTURE_HORIZONS,
    )

    records = [
        {
            "route_id": o.route_id,
            "origin_code": o.origin_code,
            "destination_code": o.destination_code,
            "departure_date": o.departure_date.isoformat(),
            "collection_datetime": o.collection_datetime.isoformat(),
            "booking_horizon_days": o.booking_horizon_days,
            "airline_code": o.airline_code,
            "airline_name": o.airline_name,
            "flight_number": o.flight_number,
            "cabin_class": o.cabin_class,
            "fare_family": o.fare_family,
            "fare_total": o.fare_total,
            "fare_base": o.fare_base,
            "fare_taxes": o.fare_taxes,
            "currency": "INR",
            "stops": o.stops,
            "is_refundable": o.is_refundable,
            "baggage_kg": o.baggage_kg,
            "seats_available": o.seats_available,
        }
        for o in observations
    ]

    payload = {
        "fixture_id": "offline-fares-v2",
        "generated_by": "backend/scripts/generate_offline_fixture.py",
        "derivation": (
            "SIMULATOR-DERIVED. These records were produced by the calibrated fare "
            "simulator, not captured from a live airline or OTA source. They exist so "
            "the collection -> validation -> index pipeline can be exercised "
            "deterministically without network access. Replayed observations carry "
            "source_type='offline' and display as OFFLINE PREVIEW."
        ),
        "not_official_statistics": True,
        "coverage": {
            "route_ids": FIXTURE_ROUTE_IDS,
            "booking_horizons": FIXTURE_HORIZONS,
            "collection_start": FIXTURE_START.isoformat(),
            "collection_end": (FIXTURE_START + timedelta(days=FIXTURE_DAYS - 1)).isoformat(),
            "record_count": len(records),
        },
        "currency": "INR",
        "observations": records,
    }

    out_path = BACKEND_DIR / "fixtures" / "offline_fares.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Compact separators: this file is committed, so keeping it small matters more
    # than pretty-printing 1,500 machine-generated records.
    out_path.write_text(
        json.dumps(payload, separators=(",", ":")), encoding="utf-8"
    )

    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path.relative_to(BACKEND_DIR.parent)} — {len(records)} records, {size_kb:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
