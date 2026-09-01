<div align="center">

  <img src="docs/assets/logo.png" alt="Airfare CPI - Team Sprint Zero" width="160" />

  # ✈️ Real-Time Airfare Consumer Price Index (Airfare CPI)
  ### *Developed by Team Sprint Zero · Automated Price Intelligence & CPI Augmentation for MoSPI*

  [![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-22c55e.svg?style=for-the-badge&logo=github&logoColor=white)](https://satiricalguru.github.io/Airfare-CPI/)
  [![Deploy with Vercel](https://img.shields.io/badge/Vercel-Deploy%20Ready-black.svg?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fsatiricalguru%2FAirfare-CPI)
  [![AI Copilot](https://img.shields.io/badge/AI%20Copilot-Gemini%203.5%20Flash%20Lite%20%2B%20Dual%20RAG-4285F4.svg?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
  [![MoSPI](https://img.shields.io/badge/Ministry-MoSPI-blue.svg?style=for-the-badge&logo=government)](https://mospi.gov.in)
  [![Next.js 16](https://img.shields.io/badge/Next.js-16.3%20(Turbopack)-black.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![Tests](https://img.shields.io/badge/Tests-66%2F66%20Passing%20(100%25)-success.svg?style=for-the-badge&logo=pytest)](https://pytest.org)
  [![Corridor Coverage](https://img.shields.io/badge/Corridors-83%20Indexed%20Routes-22c55e.svg?style=for-the-badge)](file:///Users/jatinpandey/Airfare%20CPI/Backend%20report.md)
  [![Data Source](https://img.shields.io/badge/Data%20Source-LIVE%20DATA%20(858k%20Obs)-22c55e.svg?style=for-the-badge)](file:///Users/jatinpandey/Airfare%20CPI/Backend%20report.md)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 🚀 System Status & Operational Capabilities

This system provides a mathematically rigorous, fully auditable, and high-performance Airfare CPI pipeline adhering to the **IMF CPI Manual (2020)** and **MoSPI CPI Base 2024 = 100** standards:

| Component | Status | Implementation Details |
|---|---|---|
| **Data Provenance & Traceability** | ✅ **LIVE DATA** | Enforced via `provenance.py` with typed envelopes (`LIVE`, `SIMULATED`, `OFFLINE`). 858k stored records fully auditable. |
| **Elementary Index Engine** | ✅ **Implemented** | Matched-Model Jevons geometric mean formula (`engine/matched_jevons.py`) with strict carrier/flight matching. |
| **Booking-Horizon Stratification** | ✅ **Implemented** | $T+0, T+3, T+7, T+15, T+30$ advance booking strata with fixed policy weighting (`engine/horizon.py`). |
| **Upper-Level Aggregation** | ✅ **Implemented** | DGCA annual passenger-volume weighting across 25 core basket corridors with dynamic missing-route coverage renormalization (`engine/aggregator.py`). |
| **Pan-India Interstate Coverage** | ✅ **83 Routes / 85+ Airports** | 58 interstate routes pre-seeded across all 28 Indian States & 8 UTs + 85+ commercial airport directory. |
| **On-Demand Autonomous Scraper** | ✅ **Active** | Sub-second route scraping & live aerospace radar ingestion (`POST /api/v1/routes/scrape`). |
| **Persistence Layer** | ✅ **Active** | High-performance async SQLAlchemy layer connected to SQLite (`airfare_cpi.db`, 1.2GB) and PostgreSQL (`db/models.py`, `db/repository.py`). |
| **Validation & Anomaly Fencing** | ✅ **Active** | 3-tier validation (Hard bounds ₹500–₹80k, tax ratio check >65%, dynamic IQR fences per route/horizon) via `scraper/validator.py`. |
| **AI Analyst Copilot & Dual RAG** | ✅ **Active** | Google Gemini 3.5 Flash Lite server-side proxy + Client-Side Deterministic RAG engine for static deployments (GitHub Pages). |
| **Automated Test Suite** | ✅ **66/66 Passing** | Axiomatic mathematical tests, time-reversal proofs, horizon stability, persistence round-trips, and API contracts. |


---

## 📌 Executive Summary & Problem Context

In February 2026, the **Ministry of Statistics and Programme Implementation (MoSPI)** officially transitioned to India's modernized **Consumer Price Index (CPI) with Base Year 2024 = 100**. This transition prioritizes the integration of alternative and administrative high-frequency digital datasets.

### 🎯 Problem Statement (SIH26056)
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)."**

Air transport is one of the most volatile and complex consumer service categories:
1. **Dynamic Yield Management:** Airlines update seat prices hundreds of times per day based on real-time load factor algorithms.
2. **Advance-Purchase Price Discrimination:** A ticket bought on the day of departure ($T+0$) can cost $300\%$ to $500\%$ more than the same seat booked 30 days prior ($T+30$), reflecting consumer urgency rather than inflationary price changes.
3. **Manual Collection Failure:** Traditional physical CPI field investigators visiting airport booking counters once a month capture arbitrary snapshot noise, failing to reflect true economic inflation.

**Our Solution:** An automated statistical pipeline that ingests domestic airfares across **25 high-density city-pairs** and **5 advance-purchase booking horizons**, computes elementary price relatives using the **Matched-Model Jevons formula**, and aggregates them into a headline **National Airfare CPI** weighted by **DGCA passenger traffic volumes**.

---

## 🧠 AI Analyst Copilot & Dual-Mode RAG Architecture

The platform features an intelligent, theme-adaptive AI Copilot assistant with an interactive 60fps cursor-tracking mascot and a **Dual-Mode Retrieval-Augmented Generation (RAG)** pipeline:

```
                             [ User Question ]
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    AviationCopilotModal     │
                      │     (Frontend Client)       │
                      └──────────────┬──────────────┘
                                     │
                    Is Backend API reachable?
                    ├── YES ───────────────┐
                    │                      │
                    ▼                      ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       MODE A: Full-Stack Server      │  │     MODE B: Static GitHub Pages      │
│      (Python FastAPI + SQLite)       │  │     (Client-Side RAG Engine)         │
├──────────────────────────────────────┤  ├──────────────────────────────────────┤
│ 1. FastAPI Ingestion & SQL RAG       │  │ 1. Client-Side State RAG             │
│    Retrieves live headline CPI, MoM, │  │    Extracts baked memory metrics:    │
│    YoY, 25 corridors & sample stats. │  │    Headline index, base period,      │
│ 2. Grounded Prompt Assembly          │  │    MoM/YoY changes, and route basket.│
│ 3. Gemini 3.5 Flash Lite LLM Proxy   │  │ 2. Semantic Intent Parser            │
│    Queries Google AI Studio API key. │  │ 3. Deterministic Knowledge Base      │
│ 4. Output: `tier: "model"`           │  │    Answers formulas, Jevons math,    │
│    Badge: `✨ Gemini 3.5 Flash Lite`  │  │    horizons, sources & inflation.    │
│                                      │  │ 4. Output: `tier: "local_fallback"`  │
│                                      │  │    Badge: `Deterministic RAG`        │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
```

### 🌟 Copilot Capabilities:
* **Interactive Mascot Avatar:** The assistant symbol features dynamic 60fps gaze tracking that smoothly tracks the user's cursor across the screen with periodic natural blinks.
* **Dual-Tier Grounded Engine:**
  * **Full-Stack Mode (`tier: model`)**: Proxies natural language queries to Google AI Studio (`gemini-3.5-flash-lite`), grounded directly on the live SQL database state.
  * **GitHub Pages Static Mode (`tier: local_fallback`)**: Uses the client-side deterministic RAG engine to answer questions on methodology, formulas, booking horizons, inflation rates, and route weights with zero latency.
* **Streamlined Modern UI:** Single-row horizontal scrollable prompt chips, fluid 3-dots wave thinking badge, and high-contrast dark mode styling.

---

## 📐 Statistical & Econometric Methodology

### 1. Route-Level Micro Index: The Matched-Model Jevons Formula
At the elementary aggregate level (individual route $r$ at period $t$), detailed quantity weights for specific flights are unavailable. Under the **ILO/IMF Consumer Price Index Manual**, the **Jevons Index** is the globally accepted standard:

$$I(r,t) = \left( \prod_{i=1}^{n} \frac{p_{i,t}}{p_{i,0}} \right)^{1/n} = \exp\left( \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right) \right)$$

#### ❓ Why Jevons over Carli or Dutot?
* **Elimination of Upward Bias:** The **Carli Index** (arithmetic average of price ratios $\frac{1}{n}\sum \frac{p_t}{p_0}$) is mathematically proven to suffer from upward substitution bias (via Jensen's Inequality / AM-GM inequality). The ILO and IMF explicitly forbid Carli for official CPI series.
* **Axiomatic Soundness (Time-Reversal Test):** Jevons satisfies the strict **time-reversal test**:
  $$I(0 \to t) \times I(t \to 0) = 1.0000$$
  *(Carli fails this test, artificially generating positive inflation if prices fluctuate and return to baseline).*
* **Quality & Product Homogeneity:** Fares are matched at the carrier, flight number, horizon, and cabin class level to ensure price movements reflect true inflation rather than cabin mix changes.

---

### 2. Upper-Level Aggregation: Laspeyres / Young with DGCA Weights
Route-level elementary indices are aggregated into the headline **National Airfare CPI** using empirical passenger traffic volumes published by the **Directorate General of Civil Aviation (DGCA)**:

$$\text{CPI}(t) = \sum_{r=1}^{25} w_r \cdot I(r,t) \times 100$$

Where normalized passenger volume weights $w_r$ are defined as:

$$w_r = \frac{\text{DGCA Monthly Passenger Traffic}_r}{\sum_{k=1}^{25} \text{DGCA Monthly Passenger Traffic}_k}$$

---

### 3. Booking-Window Stratification (Advance-Purchase Horizon Grid)
Airline revenue management systems adjust seat availability across fare booking classes based on time-to-departure. To avoid mistaking last-minute distress purchases for structural inflation, our pipeline stratifies all observations into **5 calibrated horizons**:

| Horizon | Days Prior | Category | Policy Weight | Economic Rationale |
|:---:|:---:|:---:|:---:|:---|
| **$T+0$** | 0 Days | Same-Day / Walk-up | **0.10** | Emergency travel; captures unconstrained maximum willingness to pay. |
| **$T+3$** | 3 Days | Short-Notice | **0.20** | Key 3-day business travel advance-purchase boundary. |
| **$T+7$** | 7 Days | 1-Week Advance | **0.30** | Primary revenue management threshold where discount fare buckets close. |
| **$T+15$** | 15 Days | 2-Week Advance | **0.25** | Standard 14/21-day planned business and early leisure bookings. |
| **$T+30$** | 30 Days | 1-Month Advance | **0.15** | Reference baseline anchor; purely planned discretionary leisure travel. |

---

## 🗺️ Monitored Route Basket (Top 25 DGCA Corridors)

The route basket represents **~11.98 million monthly passenger journeys** (matching `data/route_basket.json`). Weights are derived at runtime as $w_r = \text{pax}_r / \sum \text{pax}$, summing to exactly 1.0:

| Rank | Route | Origin | Destination | Approx. Monthly Pax | Normalized Weight ($w_r$) |
|:---:|:---:|:---|:---|:---:|:---:|
| 1 | **DEL ↔ BOM** | New Delhi | Mumbai | 1,200,000 | **10.02%** |
| 2 | **DEL ↔ BLR** | New Delhi | Bengaluru | 950,000 | **7.93%** |
| 3 | **BOM ↔ BLR** | Mumbai | Bengaluru | 870,000 | **7.26%** |
| 4 | **DEL ↔ HYD** | New Delhi | Hyderabad | 780,000 | **6.51%** |
| 5 | **DEL ↔ CCU** | New Delhi | Kolkata | 740,000 | **6.18%** |
| 6 | **BOM ↔ HYD** | Mumbai | Hyderabad | 650,000 | **5.43%** |
| 7 | **DEL ↔ MAA** | New Delhi | Chennai | 600,000 | **5.01%** |
| 8 | **BOM ↔ CCU** | Mumbai | Kolkata | 520,000 | **4.34%** |
| 9 | **BLR ↔ HYD** | Bengaluru | Hyderabad | 480,000 | **4.01%** |
| 10 | **DEL ↔ GOI** | New Delhi | Goa | 450,000 | **3.76%** |
| 11 | **BOM ↔ MAA** | Mumbai | Chennai | 430,000 | **3.59%** |
| 12 | **BLR ↔ CCU** | Bengaluru | Kolkata | 400,000 | **3.34%** |
| 13 | **DEL ↔ PNQ** | New Delhi | Pune | 390,000 | **3.26%** |
| 14 | **BOM ↔ GOI** | Mumbai | Goa | 380,000 | **3.17%** |
| 15 | **DEL ↔ AMD** | New Delhi | Ahmedabad | 370,000 | **3.09%** |
| 16 | **BLR ↔ MAA** | Bengaluru | Chennai | 340,000 | **2.84%** |
| 17 | **DEL ↔ JAI** | New Delhi | Jaipur | 320,000 | **2.67%** |
| 18 | **BOM ↔ AMD** | Mumbai | Ahmedabad | 310,000 | **2.59%** |
| 19 | **DEL ↔ LKO** | New Delhi | Lucknow | 300,000 | **2.50%** |
| 20 | **BLR ↔ GOI** | Bengaluru | Goa | 280,000 | **2.34%** |
| 21 | **HYD ↔ CCU** | Hyderabad | Kolkata | 270,000 | **2.25%** |
| 22 | **DEL ↔ PAT** | New Delhi | Patna | 260,000 | **2.17%** |
| 23 | **BOM ↔ JAI** | Mumbai | Jaipur | 240,000 | **2.00%** |
| 24 | **DEL ↔ COK** | New Delhi | Kochi | 230,000 | **1.92%** |
| 25 | **BOM ↔ PNQ** | Mumbai | Pune | 220,000 | **1.84%** |
| | **Total** | | | **11,980,000** | **100.00%** |

---

## 📂 Repository Structure

```text
Airfare CPI/
├── backend/                        # FastAPI index-computation service
│   ├── airfare_cpi.db              # 1.2GB SQLite database (858k live observations, 2.3k index points)
│   ├── api/
│   │   ├── main.py                 # REST API endpoints & route handlers
│   │   ├── serializers.py          # Data serialization models
│   │   └── copilot_service.py      # Grounded RAG context builder & LLM proxy
│   ├── db/
│   │   ├── models.py               # SQLAlchemy 2.0 async database models
│   │   └── repository.py           # Async data access layer & query repository
│   ├── engine/
│   │   ├── matched_jevons.py       # Matched-Model Jevons elementary index engine
│   │   ├── horizon.py              # Booking-horizon combination (T+0 to T+30)
│   │   ├── aggregator.py           # DGCA passenger-weighted national aggregation
│   │   ├── airports_data.py        # 85+ Indian commercial airports directory
│   │   ├── weights.py              # DGCA route basket weight loader & dynamic ID generator
│   │   └── rebase.py               # Base period index calculation & rebasing
│   ├── scraper/
│   │   ├── pipeline.py             # Asynchronous collection pipeline & rate limiter
│   │   ├── validator.py            # 3-tier validation (Hard bounds, tax ratios, IQR fences)
│   │   └── sources/                # Amadeus GDS, airline portals & OTA adapters
│   ├── config.py                   # Environment settings & configuration
│   ├── provenance.py               # Mandatory provenance tracking & invariants
│   ├── tests/                      # 66 pytest unit, integration & contract tests
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Modern Next.js 16 (Turbopack) Dashboard
│   ├── app/
│   │   ├── components/
│   │   │   ├── AviationCopilotModal.jsx  # AI Copilot with mouse-tracking eyes & Dual RAG
│   │   │   ├── IndiaNetworkMap.jsx       # Theme-adaptive 60FPS Space View Map
│   │   │   ├── RouteDetailModal.jsx      # 4-tab corridor deep-dive analytics
│   │   │   ├── PriceAlertEngine.jsx      # Clean price watch & alert builder
│   │   │   └── DataModeBanner.jsx        # Provenance badge component
│   │   ├── globals.css             # High-contrast light/dark mode design tokens
│   │   ├── layout.js               # Root layout, Google Fonts & metadata
│   │   └── page.js                 # Multi-view dashboard, state-to-state flight library & radar
│   ├── public/                     # High-res assets, airline carrier logos, icons
│   └── package.json                # Frontend dependencies
│
├── data/                           # Route basket & booking horizon policies
├── docs/                           # Architectural diagrams, methodology & assets
├── Backend report.md               # In-depth backend architecture report
├── Frontend report.md              # In-depth frontend design & UX report
├── start.sh                        # 1-Click Automated startup script (Backend + Frontend)
└── README.md                       # Master documentation
```

---

## ⚡ Quick Start & Installation

### 🚀 Option 1: 1-Click Launch (Recommended)
This script starts both the FastAPI backend and Next.js frontend, performs automated health checks, and launches your default browser:

```bash
# Clone the repository
git clone https://github.com/satiricalguru/Airfare-CPI.git
cd Airfare-CPI

# Launch full system
./start.sh
```

---

### 🌐 Option 2: Live Cloud Deployments
- **GitHub Pages (Static Export)**: [https://satiricalguru.github.io/Airfare-CPI/](https://satiricalguru.github.io/Airfare-CPI/)
- **Vercel Deploy**: Connect the repository to Vercel with Root Directory set to `frontend/`.

---

### 🛠️ Option 3: Manual Step-by-Step Setup

#### 1. Configure Backend Environment
Create `backend/.env`:
```env
COPILOT_API_KEY=your_google_ai_studio_api_key_here
COPILOT_MODEL=gemini-3.5-flash-lite
COLLECTION_MODE=LIVE
```

#### 2. Start Backend Service
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Comprehensive Verification Suite

Run all **66 mathematical, validation, and integration tests**:

```bash
cd backend
pytest tests/ -v
```

### ✅ Test Suite Breakdown (66/66 Passing)
* **`tests/test_jevons.py` (11 tests):** Geometric mean property, time-reversal test ($I_{0\to t} \times I_{t\to 0} = 1.0$), extreme relative Winsorization, Carli upward bias demonstration, Dutot tests.
* **`tests/test_matched_jevons.py` (5 tests):** Exact matched flight pairs, product churn tracking, fare family substitution safeguards.
* **`tests/test_horizons.py` (4 tests):** $T+0 \dots T+30$ horizon policy validation, compositional shift stability, missing horizon renormalization.
* **`tests/test_aggregator.py` (9 tests):** Base period normalization ($I=100.00$), DGCA weighted aggregation, 70% minimum coverage threshold, MoM change decomposition.
* **`tests/test_validator.py` (7 tests):** ₹500–₹80,000 bounds, tax ratio anomalies, IQR fence exclusions.
* **`tests/test_persistence.py` (2 tests):** Collection run persistence, validator reference distribution roundtrips.
* **`tests/test_api_contract.py` (6 tests):** REST API envelope contracts, `/airports` directory, `/routes/scrape` on-demand ingestion, provenance headers, seasonality disclosures.
* **`tests/test_audit_regressions.py` (19 tests):** Rebase date-window filtering, DGCA weight sums (=1.0000), provenance invariants, CORS policy verification.
* **`tests/test_pipeline_integration.py` (3 tests):** Full end-to-end data pipeline integration and live ASGI endpoint verification.

---

## 📡 REST API Documentation

FastAPI provides an interactive OpenAPI / Swagger UI at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/api/v1/health` | System status, database health, observation counts |
| `GET` | `/api/v1/provenance` | Active collection mode, source breakdown, integrity invariants |
| `GET` | `/api/v1/airports` | Comprehensive 85+ Indian commercial airports directory & states |
| `POST` | `/api/v1/routes/scrape` | **On-demand autonomous scraping & instant index computation for any corridor** |
| `GET` | `/api/v1/index/national` | Current headline National Airfare CPI, YoY, MoM, route contributions |
| `GET` | `/api/v1/index/national/history?days=365` | Time-series historical CPI index points (`7D`, `1M`, `3M`, `6M`, `1Y`) |
| `GET` | `/api/v1/index/routes` | Latest Jevons micro-indices for all 83 monitored & custom corridors |
| `GET` | `/api/v1/index/routes/{route_id}` | Historical trend and horizon breakdown for a specific route |
| `GET` | `/api/v1/routes` | Monitored route basket with DGCA traffic weights |
| `GET` | `/api/v1/fares/latest?limit=50` | Stream of latest raw validated fare quotes |
| `GET` | `/api/v1/fares/stats` | Aggregated statistical metrics (Mean, Median, Min, Max, $\sigma$) |
| `GET` | `/api/v1/analysis/booking-horizons` | Advance-purchase price breakdown ($T+0 \to T+30$) |
| `GET` | `/api/v1/sources` | Comprehensive source registry with compliance notes |
| `GET` | `/api/v1/anomalies?limit=50` | Flagged statistical price spikes and outliers |
| `GET` | `/api/v1/reports/monthly` | MoSPI monthly summary JSON payload |
| `GET` | `/api/v1/reports/monthly/html` | Monthly Statistical Press Release Bulletin (HTML) |
| `POST` | `/api/v1/copilot/ask` | **Grounded RAG query endpoint for natural language analysis** |


---

## 👥 Authors & Team Credits

* **Team:** **Sprint Zero**
* Developed for **Smart India Hackathon 2026** (Problem Statement: **SIH26056**).
* Sponsored by: **Ministry of Statistics and Programme Implementation (MoSPI)**.
* Methodological References: **ILO/IMF Consumer Price Index Manual (2020)** & **DGCA India Traffic Reports**.

---
*Built with statistical rigor, high-performance architecture, and modern engineering by Team Sprint Zero.*
