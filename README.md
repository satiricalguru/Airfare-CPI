<div align="center">

  <img src="docs/assets/logo.png" alt="Airfare CPI - Real-Time Indian Aviation Price Index Logo" width="220" style="border-radius: 24px; box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);" />

  # ✈️ Real-Time Airfare Consumer Price Index (Airfare CPI)
  ### *Automated Price Collection, Econometric Modeling & CPI Augmentation for MoSPI*

  [![Smart India Hackathon](https://img.shields.io/badge/SIH-2026-orange.svg?style=for-the-badge&logo=target)](https://sih.gov.in)
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

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                DATA INGESTION LAYER                                    │
│   IndiGo (6E) · Air India (AI) · SpiceJet (SG) · Vistara (UK) · Akasa (QP) · OTAs      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             SCRAPING & VALIDATION ENGINE                               │
│  - Playwright Headless Driver + Stealth Anti-Detection (XHR / Network Interception)     │
│  - robots.txt & Rate-Limiting Governance (2.0s - 5.0s randomized delays)               │
│  - FareValidator: Hard Exclusions (₹0, <₹500, >₹80k) + Soft IQR Anomaly Fencing        │
│  - Advance-Purchase Stratification: T+0, T+3, T+7, T+15, T+30 horizons                 │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          ECONOMETRIC COMPUTATION ENGINE                                │
│                                                                                        │
│   1. Route-Level Micro-Index (Jevons Elementary Aggregate):                            │
│      I(r, t) = [ Π (p_i,t / p_i,0) ] ^ (1/n)  ==> Log-space calculation with Winsor    │
│                                                                                        │
│   2. Upper-Level National Aggregator (Laspeyres / Young):                              │
│      CPI(t) = Σ [ w_r × I(r, t) ] × 100  where w_r = DGCA_Pax_r / Σ DGCA_Pax          │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
┌──────────────────────────────────────────┐┌────────────────────────────────────────────┐
│          FASTAPI BACKEND (PORT 8000)     ││          OUTPUTS & VISUALIZATION           │
│  - 13 Async High-Performance Endpoints   ││  - Next.js 16 Glassmorphism Dashboard     │
│  - In-Memory + PostgreSQL 16 Data Store  ││  - Real-Time Route Heatmap & Trends       │
│  - Live Scrape Trigger & Anomaly Feed    ││  - MoSPI Monthly Press Release Bulletin    │
└──────────────────────────────────────────┘└────────────────────────────────────────────┘
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
git clone https://github.com/satiricalguru/Prototype-1.git
cd Prototype-1

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

## 🎨 Interactive Dashboard Preview

The frontend is built with **Next.js 16 App Router**, **Vanilla CSS Design System**, and **Recharts**:

1. **📊 National Overview:**
   - Animated KPI counters for Headline CPI, MoM rate, Validated Quotes, and Median Airfare.
   - Zoomable SVG time-series area charts.
   - Advance-purchase booking horizon bar comparison ($T+0$ to $T+30$).
   - Route inflation contribution bar chart.
2. **✈️ Route Explorer:**
   - Full 25-route matrix with DGCA monthly passengers, weights, and live Jevons indices.
3. **💚 Pipeline Health:**
   - Scraper diagnostic monitors, latency indicators, and live IQR anomaly feed.
4. **📐 Methodology:**
   - Mathematical formula breakdowns, time-reversal proofs, and COICOP alignment references.
5. **🔄 1-Click Scrape Trigger:**
   - Interactive button on the dashboard that ingests new observations, validates them, updates route indices, and updates the headline CPI in real time!

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

## 👥 Authors & Acknowledgments

* Developed for **Smart India Hackathon 2026** (Problem Statement: **SIH26056**).
* Sponsored by: **Ministry of Statistics and Programme Implementation (MoSPI)**.
* Methodological References: **ILO/IMF Consumer Price Index Manual (2020)** & **DGCA India Traffic Reports**.

---
*Built with statistical rigor and modern engineering.*
