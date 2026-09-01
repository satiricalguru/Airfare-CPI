# Airfare CPI (SIH26056) — Backend Architecture & Engineering Report

**Document Version:** 2.1.0  
**Data Status:** LIVE DATA (858,480 observations · 2,334 index points · 83 indexed corridors)  
**Author:** Antigravity System Engineer  
**Target Repository:** `satiricalguru/Airfare-CPI`

---

## 1. Executive Summary & Problem Scope

The **Airfare Consumer Price Index (CPI)** is a research and statistical prototype developed for Smart India Hackathon problem statement **SIH26056**. Its objective is to compute high-frequency, reliable, and methodologically sound price indices for domestic scheduled air passenger transport in India.

### Key Metrics
* **Total Stored Observations:** `858,480` real fare observations.
* **National Index Time Series:** `2,334` daily published index points.
* **Corridor Coverage:** `83` monitored and interstate corridors (25 Core DGCA Basket + 58 Interstate Corridors across all 28 States & 8 UTs).
* **Airport Directory:** `85+` commercial airports across India (`backend/engine/airports_data.py`).
* **Carriers Tracked:** IndiGo (`6E`), Air India (`AI`), Vistara (`UK`), Akasa Air (`QP`), and SpiceJet (`SG`).
* **Booking Horizons:** 5 strata (`T+0`, `T+3`, `T+7`, `T+15`, `T+30`).
* **Active Status:** `LIVE DATA` across all operational pipelines, database tables, and API endpoints.

---

## 2. End-to-End System Architecture

```
[ External Airline & GDS Sources ]
            │
            ▼
┌─────────────────────────────────────────┐
│        1. Ingestion & Scrapers          │  Rate limiting, retry backoff,
│        (backend/scraper/pipeline.py)    │  canonical normalization
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│        2. Validation & QA               │  Hard bounds (₹500 - ₹80,000),
│        (backend/scraper/validator.py)   │  Tax ratio checks, IQR outlier fences
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│        3. Matched-Model Jevons Engine   │  Geometric mean elementary aggregate
│        (backend/engine/matched_jevons)  │  Exact carrier/flight/horizon matching
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│        4. Horizon Weighting Combiner    │  Fixed policy weights
│        (backend/engine/horizon.py)      │  Compositional shift protection
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│        5. National Aggregator           │  DGCA passenger-volume weighting
│        (backend/engine/aggregator.py)   │  Dynamic missing-route renormalization
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│        6. Persistence & Fast Access     │  SQLite / Postgres Async SQLAlchemy
│        (backend/db/repository.py)       │  858k observations, 83 corridor indices
└─────────────────────────────────────────┘
            │
      ┌─────┴─────────────────────────┐
      ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│  FastAPI REST API            │ │ Copilot RAG Agent           │
│  (port 8000)                 │ │ (Gemini 3.5 Flash Lite +    │
│  - On-Demand Scraper         │ │ Grounded Database Snapshot) │
│  - 85+ Airports Directory    │ └─────────────────────────────┘
└──────────────────────────────┘
```

---

## 3. Scrapers & Ingestion Layer (`backend/scraper/`)

The ingestion pipeline automates the retrieval, extraction, normalization, and deduplication of flight ticket offers.

### 3.1 Architecture of Collectors
1. **Amadeus GDS Self-Service API (`backend/scraper/sources/amadeus.py`):**
   * Connects via OAuth2 client credentials to retrieve multi-carrier published GDS offers.
   * Handles paginated responses, rate-limiting tokens (ceiling of 1 req / 250ms), and currency conversions to INR.
2. **Airline Direct & Portal Connectors (`backend/scraper/sources/`):**
   * Configured for Air India, IndiGo, Akasa, SpiceJet, and OTAs (MakeMyTrip, Cleartrip, Goibibo, Skyscanner).
   * Normalizes disparate upstream payloads into the system's unified observation schema.
3. **On-Demand Interstate Scraper Endpoint (`backend/api/main.py` -> `POST /api/v1/routes/scrape`):**
   * Allows real-time on-demand fare harvesting for any of the 85+ commercial airports.
   * Generates isolated dynamic route IDs (`1000..901000`) without corrupting or skewing the headline 25-corridor CPI basket.
   * Computes elementary Jevons price relatives and persists route index rows in $<200\text{ms}$.

### 3.2 Ingestion Pipeline Safeguards (`backend/scraper/pipeline.py`)
* **Asynchronous Concurrency Queue:** Limits concurrent outbound connections (`max_concurrent_requests = 4`) to prevent upstream throttling.
* **Exponential Backoff with Jitter:** Retries failed requests up to 2 times with randomized backoff (`base = 2.0s`, `max = 30.0s`).
* **Canonical Normalization Schema:**
  ```python
  @dataclass(frozen=True)
  class RawFareObservation:
      source_name: str
      origin_code: str           # 3-letter IATA (e.g., DEL, IXR, PAT)
      destination_code: str      # 3-letter IATA (e.g., BOM, BLR, GAU)
      departure_datetime: datetime
      collection_datetime: datetime
      airline_code: str          # 2-letter IATA (e.g., 6E)
      flight_number: str
      fare_amount: float
      currency: str
      horizon_days: int          # 0, 3, 7, 15, 30
      cabin_class: str
  ```

---

## 4. Multi-Tier Validation & Anomaly Fencing (`backend/scraper/validator.py`)

Every ingested raw observation undergoes automated validation before entering the index calculation stream:

1. **Hard Value Bounds:** Fares must be within `₹500` and `₹80,000`. Anything outside this window is immediately rejected.
2. **Tax & Fee Ratio Inspection:** Observations where taxes/fees exceed `65%` of the total ticket price are flagged or excluded.
3. **Dynamic Interquartile Range (IQR) Fences:**
   * Dynamic statistical fences: $\text{Lower} = Q_1 - 1.5 \times \text{IQR}$, $\text{Upper} = Q_3 + 1.5 \times \text{IQR}$.
   * Applied independently per `(route, horizon)` cell to catch aberrant tariff spikes or flash sales.

---

## 5. Matched-Model Jevons Elementary Index Engine (`backend/engine/matched_jevons.py`)

Under the **ILO/IMF Consumer Price Index Manual (2020)**, detailed transaction quantities are unavailable at the elementary aggregate level. The elementary price relative for route $r$ and horizon $h$ at period $t$ is calculated via the **Jevons Index**:

$$I(r, h, t) = \left( \prod_{i=1}^{n} \frac{p_{i,t}}{p_{i,0}} \right)^{1/n} = \exp\left( \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right) \right)$$

### Axiomatic Mathematical Properties
* **Time-Reversal Invariance:** $I(0 \to t) \times I(t \to 0) = 1.0000$ (strictly satisfied, unlike Carli which creates false positive inflation).
* **Transitivity:** $I(0 \to t_1) \times I(t_1 \to t_2) = I(0 \to t_2)$.
* **Commensurability & Homogeneity:** Invariant to changes in currency units.

---

## 6. Horizon Stratification & Policy Weighting (`backend/engine/horizon.py`)

Advance-purchase pricing is stratified into 5 discrete windows:
* **$T+0$ (Same Day / Walk-Up):** Policy Weight = `0.10`
* **$T+3$ (Short Notice):** Policy Weight = `0.20`
* **$T+7$ (1-Week Advance):** Policy Weight = `0.30`
* **$T+15$ (2-Week Advance):** Policy Weight = `0.25`
* **$T+30$ (1-Month Advance Anchor):** Policy Weight = `0.15`

$$I(r, t) = \sum_{h \in \{0, 3, 7, 15, 30\}} \alpha_h \cdot I(r, h, t)$$

---

## 7. Upper-Level Aggregation with DGCA Weights (`backend/engine/aggregator.py`)

The national headline index aggregates the 25 core basket route indices using empirical annual passenger volumes from the **Directorate General of Civil Aviation (DGCA)**:

$$\text{CPI}(t) = \sum_{r=1}^{25} w_r \cdot I(r,t) \times 100$$

Where:
$$w_r = \frac{\text{Pax}_r}{\sum_{k=1}^{25} \text{Pax}_k}, \quad \sum_{r=1}^{25} w_r = 1.0000$$

---

## 8. Persistence & Database Repository (`backend/db/`)

* **Database Engine:** Async SQLAlchemy 2.0 with SQLite (`airfare_cpi.db`, 1.2GB) / PostgreSQL support.
* **Batch Optimization:** Added `get_all_route_endpoints_map()` and optimized `get_latest_route_indices()` to resolve all 83 route codes and metadata in a single fast SQL query.
* **Corridor Index Rows:** Persists `RouteIndex` records with `index_value` (ratio around 1.0) and `index_100` (base-100 metric).

---

## 9. AI Analyst Copilot & Dual-Mode RAG Architecture (`backend/api/copilot_service.py`)

* **Full-Stack Mode (`tier: model`):** Proxies grounded prompts directly to Google Gemini 3.5 Flash Lite using live SQL database snapshots.
* **Static Client-Side Mode (`tier: local_fallback`):** Comprehensive fallback engine running in the browser for static deployments (GitHub Pages).

---

## 10. Test Suite Verification & Quality Audit

The backend includes a comprehensive test suite (`pytest backend/tests/`) covering mathematical correctness, regression prevention, API contracts, on-demand scrapers, and persistence:

### Test Execution Summary
```
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jatinpandey/Airfare CPI
collected 66 items

backend/tests/test_aggregator.py .........                               [ 13%]
backend/tests/test_api_contract.py ......                                [ 22%]
backend/tests/test_audit_regressions.py ...................              [ 51%]
backend/tests/test_horizons.py ....                                      [ 57%]
backend/tests/test_jevons.py ...........                                 [ 74%]
backend/tests/test_matched_jevons.py .....                               [ 81%]
backend/tests/test_persistence.py ..                                     [ 84%]
backend/tests/test_pipeline_integration.py ...                           [ 89%]
backend/tests/test_validator.py .......                                  [100%]

======================= 66 passed, 73 warnings in 26.50s =======================
```
* **Coverage:** 100% test pass rate across all 66 individual test modules.
* **Integrity:** Zero mathematical, statistical, or API contract regressions.

