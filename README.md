<div align="center">

  <img src="docs/assets/logo.png" alt="Airfare CPI - Team Sprint Zero" width="160" />

  # ✈️ Real-Time Airfare Consumer Price Index (Airfare CPI)
  ### *Developed by Team Sprint Zero · Automated Price Intelligence & CPI Augmentation for MoSPI*

  [![Smart India Hackathon](https://img.shields.io/badge/SIH-2026-orange.svg?style=for-the-badge&logo=target)](https://sih.gov.in)
  [![Team Sprint Zero](https://img.shields.io/badge/Team-Sprint%20Zero-blueviolet.svg?style=for-the-badge&logo=rocket)](https://github.com/satiricalguru/Prototype-2)
  [![MoSPI](https://img.shields.io/badge/Ministry-MoSPI-blue.svg?style=for-the-badge&logo=government)](https://mospi.gov.in)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![Next.js 16](https://img.shields.io/badge/Next.js-16.3-black.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
  [![Tests](https://img.shields.io/badge/Tests-30%2F30%20Passing%20(100%25)-success.svg?style=for-the-badge&logo=pytest)](https://pytest.org)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📌 Executive Summary & Problem Context

In February 2026, the **Ministry of Statistics and Programme Implementation (MoSPI)** officially released India's modernized **Consumer Price Index (CPI) with Base Year 2024 = 100**. This landmark transition expands the national basket to 358 items and establishes the integration of alternative and administrative data sources (e.g., IRCTC rail ticketing feeds, PPAC petroleum prices, and online market price scraping).

### 🎯 Problem Statement (SIH26056)
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)."**

Air transport is one of the most volatile and complex consumer service categories:
1. **Dynamic Yield Management:** Airlines update seat prices hundreds of times per day based on load factor algorithms.
2. **Advance-Purchase Price Discrimination:** A ticket bought on the day of departure ($T+0$) can cost $300\%$ to $500\%$ more than the same seat booked 30 days prior ($T+30$), reflecting consumer urgency rather than inflationary price changes.
3. **Manual Collection Failure:** Traditional physical CPI field investigators visiting airport booking counters once a month capture arbitrary snapshot noise, failing to reflect true economic inflation.

**Our Solution:** An end-to-end, statistically defensible, automated intelligence platform that continuously samples domestic airfares across **25 high-density city-pairs**, stratifies observations across **5 advance-purchase booking horizons**, computes elementary price relatives using the **Jevons Geometric Mean formula**, and aggregates them into a headline **National Airfare CPI** weighted by **Directorate General of Civil Aviation (DGCA) passenger traffic**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph S1["1. DATA INGESTION LAYER"]
        A["✈️ Scheduled Airline & OTA Portals<br/><b>IndiGo (6E) · Air India (AI) · SpiceJet (SG) · Vistara (UK) · Akasa (QP) · MakeMyTrip</b>"]
    end

    subgraph S2["2. SCRAPING & VALIDATION PIPELINE"]
        B1["🛡️ Playwright Engine + Stealth Anti-Detection<br/><i>XHR / Network Response Interception & Rate-Limiting Governance</i>"]
        B2["🔍 FareValidator Quality Gate<br/><i>Hard Exclusions (INR 0, Out-of-Range) + Rolling IQR Anomaly Fencing</i>"]
        B3["⏱️ Advance-Purchase Stratification<br/><i>T+0, T+3, T+7, T+15, T+30 Booking Horizons</i>"]
    end

    subgraph S3["3. ECONOMETRIC COMPUTATION ENGINE"]
        C1["📐 Route-Level Micro-Index (Jevons Elementary Aggregate)<br/><b>I(r, t) = [ ∏ (p_i,t / p_i,0) ]^(1/n)</b><br/><i>Log-space calculation with Winsorization</i>"]
        C2["🇮🇳 National Upper-Level Aggregator (Laspeyres / Young)<br/><b>CPI(t) = ∑ [ w_r × I(r, t) ] × 100</b><br/><i>Weighted by DGCA City-Pair Monthly Passenger Traffic Volume</i>"]
    end

    subgraph S4["4. API & OUTPUT DISTRIBUTION"]
        D1["⚡ FastAPI High-Performance Backend<br/><i>13 Async REST Endpoints · In-Memory & PostgreSQL 16 Store</i>"]
        D2["📊 Next.js 16 Glassmorphism Dashboard<br/><i>Real-time CPI Trendlines, Route Heatmaps & Interactive Trigger</i>"]
        D3["🏛️ Official MoSPI Statistical Bulletin<br/><i>Publication-ready Monthly Press Release</i>"]
    end

    A --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> D1
    D1 --> D2
    D1 --> D3

    style S1 fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style S2 fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc
    style S3 fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc
    style S4 fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f8fafc
```

---

## 📐 Statistical & Econometric Methodology

### 1. Route-Level Micro Index: The Jevons Formula
At the elementary aggregate level (individual route $r$ at period $t$), detailed quantity weights for every specific flight are unavailable. Under the **ILO/IMF Consumer Price Index Manual**, the **Jevons Index** is the globally accepted standard:

$$I(r,t) = \left( \prod_{i=1}^{n} \frac{p_{i,t}}{p_{i,0}} \right)^{1/n}$$

To ensure numerical stability against floating-point underflow/overflow:

$$\ln I(r,t) = \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right)$$

#### ❓ Why Jevons over Carli or Dutot?
* **Elimination of Upward Bias:** The **Carli Index** (arithmetic average of price ratios $\frac{1}{n}\sum \frac{p_t}{p_0}$) is mathematically proven to suffer from upward substitution bias (via Jensen's Inequality / AM-GM inequality). The ILO and IMF explicitly forbid Carli for official CPI series.
* **Axiomatic Soundness (Time-Reversal Test):** Jevons satisfies the strict **time-reversal test**:
  $$I(0 \to t) \times I(t \to 0) = 1.0000$$
  *(Carli fails this test, artificially generating positive inflation if prices fluctuate and return to baseline).*
* **Product Heterogeneity:** The **Dutot Index** (ratio of arithmetic averages $\frac{\bar{p}_t}{\bar{p}_0}$) is distorted by absolute price levels and fails when product quality differs. Jevons standardizes all price relatives into a scale-invariant geometric mean.

---

### 2. Upper-Level Aggregation: Laspeyres / Young with DGCA Weights
Route-level elementary indices are aggregated into the headline **National Airfare CPI** using empirical passenger traffic volumes published by the **Directorate General of Civil Aviation (DGCA)**:

$$\text{CPI}(t) = \sum_{r=1}^{R} w_r \cdot I(r,t) \times 100$$

Where normalized passenger volume weights $w_r$ are defined as:

$$w_r = \frac{\text{DGCA Monthly Passenger Traffic}_r}{\sum_{k=1}^{R} \text{DGCA Monthly Passenger Traffic}_k}$$

---

### 3. Booking-Window Stratification (Advance-Purchase Horizon Grid)
Airline revenue management systems adjust seat availability across fare booking classes based on time-to-departure. To avoid mistaking last-minute distress purchases for structural inflation, our pipeline stratifies all observations into **5 calibrated horizons**:

| Horizon | Days Prior | Category | Multiplier | Economic Rationale |
|:---:|:---:|:---:|:---:|:---|
| **$T+0$** | 0 Days | Same-Day / Walk-up | ~2.50× Base | Emergency travel; captures unconstrained maximum willingness to pay. |
| **$T+3$** | 3 Days | Short-Notice | ~2.00× Base | Key 3-day business travel advance-purchase boundary. |
| **$T+7$** | 7 Days | 1-Week Advance | ~1.50× Base | Primary revenue management threshold where discount fare buckets close. |
| **$T+15$** | 15 Days | 2-Week Advance | ~1.20× Base | Standard 14/21-day planned business and early leisure bookings. |
| **$T+30$** | 30 Days | 1-Month Advance | 1.00× Base | Reference baseline anchor; purely planned discretionary leisure travel. |

---

## 🗺️ Monitored Route Basket (Top 25 DGCA Corridors)

The route basket represents **~15.3 Million monthly passenger journeys**, accounting for the vast majority of scheduled domestic traffic:

| Rank | Route | Origin | Destination | Approx. Monthly Pax | Normalized Weight ($w_r$) |
|:---:|:---:|:---|:---|:---:|:---:|
| 1 | **DEL ↔ BOM** | New Delhi | Mumbai | 1,200,000 | **7.84%** |
| 2 | **DEL ↔ BLR** | New Delhi | Bengaluru | 950,000 | **6.21%** |
| 3 | **BOM ↔ BLR** | Mumbai | Bengaluru | 870,000 | **5.69%** |
| 4 | **DEL ↔ HYD** | New Delhi | Hyderabad | 780,000 | **5.10%** |
| 5 | **DEL ↔ CCU** | New Delhi | Kolkata | 740,000 | **4.84%** |
| 6 | **BOM ↔ HYD** | Mumbai | Hyderabad | 650,000 | **4.25%** |
| 7 | **DEL ↔ MAA** | New Delhi | Chennai | 600,000 | **3.92%** |
| 8 | **BOM ↔ CCU** | Mumbai | Kolkata | 520,000 | **3.40%** |
| 9 | **BLR ↔ HYD** | Bengaluru | Hyderabad | 480,000 | **3.14%** |
| 10 | **DEL ↔ GOI** | New Delhi | Goa | 450,000 | **2.94%** |
| 11 | **BOM ↔ MAA** | Mumbai | Chennai | 430,000 | **2.81%** |
| 12 | **BLR ↔ CCU** | Bengaluru | Kolkata | 400,000 | **2.61%** |
| 13 | **DEL ↔ PNQ** | New Delhi | Pune | 390,000 | **2.55%** |
| 14 | **BOM ↔ GOI** | Mumbai | Goa | 380,000 | **2.48%** |
| 15 | **DEL ↔ AMD** | New Delhi | Ahmedabad | 370,000 | **2.42%** |
| 16 | **BLR ↔ MAA** | Bengaluru | Chennai | 340,000 | **2.22%** |
| 17 | **DEL ↔ JAI** | New Delhi | Jaipur | 320,000 | **2.09%** |
| 18 | **BOM ↔ AMD** | Mumbai | Ahmedabad | 310,000 | **2.03%** |
| 19 | **DEL ↔ LKO** | New Delhi | Lucknow | 300,000 | **1.96%** |
| 20 | **BLR ↔ GOI** | Bengaluru | Goa | 280,000 | **1.83%** |
| 21 | **HYD ↔ CCU** | Hyderabad | Kolkata | 270,000 | **1.76%** |
| 22 | **DEL ↔ PAT** | New Delhi | Patna | 260,000 | **1.70%** |
| 23 | **BOM ↔ JAI** | Mumbai | Jaipur | 240,000 | **1.57%** |
| 24 | **DEL ↔ COK** | New Delhi | Kochi | 230,000 | **1.50%** |
| 25 | **BOM ↔ PNQ** | Mumbai | Pune | 220,000 | **1.44%** |

---

## ⚡ Quick Start & Installation

### 🚀 Option 1: 1-Click Launch (Recommended)
This script starts both the FastAPI backend and Next.js frontend, performs automated health checks, and launches your default browser:

```bash
# Clone the repository
git clone https://github.com/satiricalguru/Prototype-2.git
cd Prototype-2

# Launch full system
./start.sh
```

---

### 🐳 Option 2: Docker Compose
Run the containerized PostgreSQL database and backend service:

```bash
cp .env.example .env
docker compose up -d
```

---

### 🛠️ Option 3: Manual Step-by-Step Setup

#### 1. Backend Service
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Comprehensive Verification Suite

Run all **30 mathematical, validation, and integration tests**:

```bash
cd backend
python3 -m pytest tests/ -v
```

### ✅ Test Suite Breakdown (30/30 Passing)
- `tests/test_jevons.py`:
  - `test_identical_prices_yield_100` (Identity property)
  - `test_uniform_increase` & `test_uniform_decrease`
  - `test_geometric_mean_property`
  - `test_time_reversal` ($I_{0\to t} \times I_{t\to 0} = 1.0$)
  - `test_insufficient_observations` & `test_zero_prices_filtered`
  - `test_extreme_relative_capped` (Winsorization)
  - `test_carli_upward_bias` (Mathematical demonstration of Carli failure)
  - `test_dutot_basic`
- `tests/test_aggregator.py`:
  - `test_base_period_equals_100`
  - `test_uniform_10pct_increase` & `test_weighted_average`
  - `test_missing_route_rescaling` (Graceful degradation)
  - `test_contributions_sum_to_100`
  - `test_mom_change_calculation` & `test_decompose_change`
- `tests/test_validator.py`:
  - `test_valid_fare_accepted`
  - `test_zero_fare_excluded` & `test_negative_fare_excluded`
  - `test_below_minimum_excluded` & `test_above_maximum_excluded`
  - `test_high_tax_ratio_flagged` & `test_low_sameday_fare_flagged`
  - `test_batch_validation`
- `tests/test_pipeline_integration.py`:
  - `test_full_engine_pipeline_integration` (End-to-end synthetic pipeline)
  - `test_api_endpoints_live` (HTTP 200 checks on all 13 REST routes)
  - `test_scraper_trigger_endpoint` (Real-time live pipeline execution)

---

## 📡 REST API Documentation

FastAPI provides an interactive OpenAPI / Swagger UI at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/api/v1/index/national` | Current headline National Airfare CPI |
| `GET` | `/api/v1/index/national/history?days=30` | Time-series historical CPI index points |
| `GET` | `/api/v1/index/routes` | Latest Jevons micro-indices for all 25 routes |
| `GET` | `/api/v1/index/routes/{route_id}` | Historical trend for a specific city-pair |
| `GET` | `/api/v1/routes` | Monitored route basket with DGCA traffic weights |
| `GET` | `/api/v1/fares/latest?limit=50` | Stream of latest raw validated fare quotes |
| `GET` | `/api/v1/fares/stats` | Aggregated statistical metrics (Mean, Median, Min, Max, $\sigma$) |
| `GET` | `/api/v1/analysis/booking-horizons` | Advance-purchase price breakdown ($T+0 \to T+30$) |
| `GET` | `/api/v1/health` | Scraper uptime, latency, and throughput health metrics |
| `GET` | `/api/v1/anomalies?limit=50` | Flagged statistical price spikes and outliers |
| `GET` | `/api/v1/reports/monthly` | MoSPI monthly summary JSON payload |
| `GET` | `/api/v1/reports/monthly/html` | **Official Government Statistical Release Bulletin (HTML)** |
| `POST` | `/api/v1/scraper/trigger` | **Live Pipeline Trigger (Simulate/Execute Ingestion Cycle)** |

---

## 🎨 Interactive Dashboard & Tab Breakdown

The frontend is built with **Next.js 16 App Router (Turbopack)**, modern **Vanilla CSS Design System**, **Google Fonts (`Outfit` & `Plus Jakarta Sans`)**, and **Recharts**:

1. **🏠 Home (Aviation Intelligence Hub):**
   - **Left-Aligned Intelligence:** Dynamic headline, real-time live pulse badge, and dual primary CTAs (`Explore Price Index` and `View CPI Bulletin`).
   - **3 Single-Row Glass Cards:** `Real-Time Updates`, `Comprehensive Coverage` (25 DGCA corridors across 85+ domestic airports), and `Data You Can Trust` (automated scraping with DGCA passenger weights).
   - **Floating 5-Column Live Index Bar:** Real-time headline CPI (`109.40` / `107.55`), 24h delta, sampled quote count (`48,200`), top corridor median fare (`₹6,240`), and animated green sparkline trend.
   - **Cruising Aircraft Backdrop:** Pixel-crisp, realistic flight cruise animation with seamless day/night theme support.

2. **📈 Price Index (National Macro & Sub-indices):**
   - Headline composite CPI and 4 sub-indices (Non-Stop, Connecting, Advance Bookings, Last-Minute).
   - Interactive zoomable AreaChart with default **1-Year (`1Y`)** time-horizon selector (`7D`, `1M`, `3M`, `6M`, `1Y`), fully formatted Y-axis padding, and tooltip inspect.
   - Advance-purchase strata step-chart ($T+0$, $T+3$, $T+7$, $T+15$, $T+30$).

3. **🗺️ Routes Matrix & Corridor Deep-Dive Modal:**
   - Complete 25-route matrix with DGCA passenger traffic volume, normalized weights ($w_r$), and live Jevons micro-indices.
   - **Interactive Route Details Modal:** Click any route or `"View Details →"` to view airport IATA metadata, advance-purchase stratification curves, operating airline market shares (IndiGo, Air India, Vistara, Akasa), and a direct 1-click filter into Flight Data.

4. **✈️ Flight Data Explorer:**
   - Real-time stream of validated domestic fare observations across all 25 city pairs.
   - Multi-parameter filtering by Origin, Destination, Airline carrier, and Booking Horizon.

5. **📐 Methodology & Mathematical Proofs:**
   - Step-by-step mathematical breakdown of the Jevons elementary formula vs. Carli upward bias demonstrations.
   - Axiomatic time-reversal test proofs ($I_{0\to t} \times I_{t\to 0} = 1.0$) and DGCA Laspeyres aggregation equations.

6. **💚 Monitoring & Data Quality Engine:**
   - Scraper throughput diagnostic gauges, request latency indicators, and automated Interquartile Range (IQR) outlier fences.
   - **Live Scraper Trigger:** 1-click interactive button to execute or simulate a live ingestion and index recalculation cycle.

7. **🏛️ Official MoSPI Bulletin:**
   - Publication-ready HTML/JSON monthly statistical press release for official CPI augmentation.

8. **📜 Legal & Compliance Pages:**
   - Standalone `/privacy` (Privacy Policy) and `/terms` (Terms of Service) pages with full dark/light theme persistence.

---

## 🛡️ Legal, Ethical & Production Architecture

### Prototype Compliance
* Strictly adheres to `robots.txt` rate-limiting (randomized delays between 0.5s and 2.0s).
* Zero storage of Personally Identifiable Information (PII) — strictly public airfare metadata.
* Resilient dual-mode architecture: live web queries with calibrated econometric fallback to guarantee $100\%$ uptime during hackathon jury evaluation.

### MoSPI Production Roadmap
* **NDC & GDS Integration:** Direct partnership feeds from airline New Distribution Capability (NDC) APIs and Global Distribution Systems (Amadeus, Sabre).
* **Automated DGCA Ingestion:** Direct database synchronization with DGCA monthly traffic tables for continuous automatic weight recalibration.
* **COICOP 2018 Sub-Index Ingestion:** Automated export into MoSPI's central e-Sankhyiki retail inflation database.

---

## 🏛️ Smart India Hackathon Jury Defense (FAQ)

<details>
<summary><strong>Q1: Why use Jevons instead of Laspeyres at the route level?</strong></summary>

> *At the elementary route level, individual flight-by-flight quantity weights do not exist. Using an arithmetic mean like Carli introduces an upward substitution bias. Jevons (geometric mean of price relatives) assumes an elasticity of substitution equal to 1, accurately modeling consumers switching between flight times or carriers when relative prices shift. It also satisfies the axiomatic Time-Reversal Test.*
</details>

<details>
<summary><strong>Q2: Why use DGCA passenger traffic as weights instead of revenue?</strong></summary>

> *DGCA publishes scheduled monthly city-pair passenger numbers, providing the most accurate volume proxy for consumer air transport expenditure in India. For production rollout, passenger volumes multiplied by observed geometric mean fares ($Pax_r \times \bar{P}_r$) yield exact expenditure shares.*
</details>

<details>
<summary><strong>Q3: How do you prevent dynamic pricing and festival spikes from distorting CPI?</strong></summary>

> *By stratifying data into 5 advance-purchase booking horizons ($T+0, T+3, T+7, T+15, T+30$), we compare apples-to-apples (e.g., $T+7$ Diwali fares against $T+7$ baseline fares). Our `FareValidator` uses rolling Interquartile Range (IQR) fences: genuine market surges are preserved with flags, while scraper corruption errors are cleanly excluded.*
</details>

---

## 👥 Authors & Team Credits

* **Team:** **Sprint Zero**
* Developed for **Smart India Hackathon 2026** (Problem Statement: **SIH26056**).
* Sponsored by: **Ministry of Statistics and Programme Implementation (MoSPI)**.
* Methodological References: **ILO/IMF Consumer Price Index Manual (2020)** & **DGCA India Traffic Reports**.

---
*Built with statistical rigor, high-performance architecture, and modern engineering by Team Sprint Zero.*
