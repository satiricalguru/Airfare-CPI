# SIH26056 — Real-Time Airfare Price Intelligence for India

An experimental system for collecting permitted online airfare quotations, cleaning and standardising them, computing route and booking-horizon price relatives, and exposing an experimental Airfare Price Index through a dashboard and API.

> This is an independent research prototype. It is not an official statistic and is not issued by, endorsed by, or affiliated with MoSPI, the NSO, RBI, DGCA, or the Government of India.

## What the project measures

A fare-comparison product asks which ticket is cheapest. This project asks how comparable airfare offers move over time across representative Indian routes, airlines, and advance-purchase windows.

The intended pipeline is:

```text
COLLECT → VALIDATE → NORMALISE → MATCH → INDEX → AGGREGATE → VISUALISE/API
```

The operational observation schema includes route, airline/flight attributes, travel and collection dates, booking horizon, fare components where supplied, total fare, availability, validation outcome, and source provenance.

## Current implementation status

Implemented:

- FastAPI read and protected mutation APIs;
- persistent SQLite or PostgreSQL storage through SQLAlchemy;
- a permitted live Amadeus Self-Service source adapter;
- explicit `LIVE`, `SIMULATED`, and `OFFLINE` provenance modes with no live-to-simulator fallback;
- scheduled and on-demand collection through one ingestion service;
- deduplication, hard-bound/tax checks, anomaly flags, and persisted validator state;
- matched-model Jevons indices by route and horizon;
- weighted route aggregation, missing-route coverage metadata, uncertainty diagnostics, and revisions;
- Next.js dashboard, route inspection, reports, and a server-side optional Copilot proxy.
- per-process rate limits for Copilot and protected mutations, returning HTTP 429 and
  `Retry-After` when the configured rolling window is exhausted.

Important limitations:

- only the Amadeus adapter is currently enabled for live collection; airline/OTA website adapters remain disabled until access permission and source-specific compliance are established;
- route passenger volumes and horizon weights are provisional research inputs, not official CPI expenditure weights;
- seasonal adjustment and DGCA validation are not yet implemented;
- the current committed static snapshot contains legacy generated/mixed-provenance data and is automatically labelled `SIMULATED DATA`; do not treat it as measured market evidence;
- schema changes are Alembic-managed from the clean initial migration; a PostgreSQL
  deployment test and a separately reviewed legacy-data migration are still required.

The detailed whole-project assessment and remediation state are in [PROJECT_AUDIT_2026-09-03.md](PROJECT_AUDIT_2026-09-03.md).

## Data provenance contract

Every collection and index response identifies its source type:

| Source type | Display label | Meaning |
|---|---|---|
| `live` | `LIVE DATA` | Obtained from a configured permitted external source. |
| `simulated` | `SIMULATED DATA` | Deterministically generated for pipeline demonstrations. |
| `offline` | `OFFLINE PREVIEW` | Replayed from a bundled fixture. |
| unavailable | `SOURCE UNAVAILABLE` | No usable observations; no substitute values are created. |

Simulation is opt-in. `COLLECTION_MODE=LIVE` is the default; missing credentials or a provider failure produces zero observations and an explicit unavailable result.

## Booking horizons

Observations are stratified at the required advance-purchase windows:

| Horizon | Current provisional weight |
|---|---:|
| T+1 | 0.20 |
| T+7 | 0.20 |
| T+15 | 0.20 |
| T+30 | 0.20 |
| T+45 | 0.20 |

Each horizon is indexed against its own base-period products before horizon indices are combined. Equal weights are a transparent placeholder until a defensible purchase-timing distribution is adopted.

## Index method

For route `r`, horizon `h`, and date `t`, matched product price relatives are combined with the Jevons geometric mean:

```text
I(r,h,t) = exp(mean(log(p(i,t) / p(i,0))))
```

Horizon-specific route values are combined using the configured fixed horizon policy. Route values are then aggregated with the provisional passenger-volume shares in `data/route_basket.json`. The API reports included routes, coverage, matching, missing components, provenance, methodology version, and publication gate alongside the value.

Month-on-month comparisons use the same calendar day in the previous month, clamped for shorter months, with a bounded ±7-day lookup inside that month. Year-on-year values are unavailable until a comparable prior-year point exists.

## Live collection configuration

Copy `.env.example` to `.env`, choose a strong admin token, and provide live-source credentials:

```dotenv
COLLECTION_MODE=LIVE
ENABLED_SOURCES=amadeus
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
AMADEUS_ENVIRONMENT=test
ADMIN_API_TOKEN=replace_with_a_long_random_secret
BOOKING_HORIZONS=1,7,15,30,45
API_COPILOT_RATE_LIMIT=20
API_COPILOT_RATE_WINDOW_SECONDS=600
API_MUTATION_RATE_LIMIT=6
API_MUTATION_RATE_WINDOW_SECONDS=60
```

Amadeus test and production environments have different coverage and quota characteristics. A successful API response demonstrates source retrieval, not national representativeness.

## Run locally

The simplest local workflow is:

```bash
./start.sh
```

It checks that ports 8000 and 3000 are free, applies Alembic migrations before
starting the API, and stops immediately with the relevant log if startup fails.
By default it creates `backend/airfare_cpi_managed.db`; the historical
`backend/airfare_cpi.db` is intentionally left untouched because it has not been
through a reviewed evidence-preserving migration.

Backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade "pip>=26.2,<27"
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Docker and CI use Python 3.12; the refreshed pinned API stack also supports the local
Python 3.14 runtime. On a shared database, `DB_AUTO_CREATE_SCHEMA` must remain
`false`: Alembic is the only supported schema path. The clean initial migration
deliberately refuses a legacy database rather than overwriting, relabelling, or
guessing how to transform its historical fares.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`.

Docker Compose starts PostgreSQL and the API:

```bash
docker compose up --build
```

Compose runs `alembic upgrade head` before starting the API. Do not point a new build
at a legacy database without a reviewed, evidence-preserving migration.

## Core API

Public, read-only:

```text
GET /api/v1/health
GET /api/v1/provenance
GET /api/v1/sources
GET /api/v1/routes
GET /api/v1/index/national
GET /api/v1/index/national/history
GET /api/v1/index/routes
GET /api/v1/index/routes/{route_id}
GET /api/v1/index/horizons
GET /api/v1/fares/latest
GET /api/v1/fares/stats
GET /api/v1/reports/monthly
```

State-changing endpoints require `X-Admin-Token`. They return HTTP 503 when `ADMIN_API_TOKEN` is not configured:

```text
POST /api/v1/collection/trigger
POST /api/v1/routes/scrape
POST /api/v1/routes/{route_id}/scrape
POST /api/v1/collection/backfill-simulated
POST /api/v1/anomalies/{anomaly_id}/review
```

Example collection request:

```bash
curl -X POST http://localhost:8000/api/v1/collection/trigger \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: replace_with_a_long_random_secret' \
  -d '{"mode":"LIVE","routes":[1,2],"horizons":[1,7,15,30,45],"compute_index":true}'
```

Reads never start scraping or mutate the statistical series.

## Verification

Backend tests are isolated to temporary databases so they cannot read or mutate an operational dataset:

```bash
cd backend
pytest -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Safe use of simulation

Simulation exists to test collection, validation, persistence, matching, aggregation, and UI behavior without external calls. Use it only by explicit selection:

```dotenv
COLLECTION_MODE=SIMULATED
```

Keep simulated and live series in separate databases until the storage schema has a fully enforced series identifier across observations and all derived index tables.

## Roadmap to statistical validation

Before presenting the index as empirical evidence:

1. quarantine the legacy contaminated database and regenerate all derived artifacts from verified source records;
2. operate the live collector for at least 30 days with freshness, failure, route, airline, and horizon coverage monitoring;
3. reproduce the route basket and weights from cited DGCA source tables and choose an expenditure-weight methodology;
4. implement the DGCA comparison/back-test with documented alignment, error metrics, and revisions;
5. add overlap/churn publication gates, durable job locking, distributed gateway rate limits, PostgreSQL migration tests, backups, and recovery tests;
6. obtain source-permission, privacy/security, and independent statistical-method review.

## License

Repository source code is provided under the included [MIT License](LICENSE). That software license does not grant rights over third-party provider data or override provider terms.
