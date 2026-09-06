<div align="center">

  <img src="docs/assets/logo.png" alt="Airfare CPI - Team Sprint Zero" width="160" />

  # ✈️ Real-Time Airfare Consumer Price Index (Airfare CPI)
  ### *Automated High-Frequency Price Intelligence & CPI Augmentation for MoSPI (SIH26056)*

  [![SIH26056](https://img.shields.io/badge/SIH-26056-blue.svg?style=for-the-badge&logo=target)](https://www.sih.gov.in/)
  [![Live Deployment](https://img.shields.io/badge/Live%20Deployment-satiricalguru.github.io%2FAirfare--CPI-2563eb.svg?style=for-the-badge&logo=githubpages&logoColor=white)](https://satiricalguru.github.io/Airfare-CPI/)
  [![Base Year](https://img.shields.io/badge/Base%20Year-2024%3D100%20(Rebased)-green.svg?style=for-the-badge)](docs/research_and_methodology.md)
  [![MoSPI e-Sankhyiki](https://img.shields.io/badge/MoSPI-e--Sankhyiki%20COICOP%2007-orange.svg?style=for-the-badge&logo=government)](https://esankhyiki.mospi.gov.in)
  [![Lead Time](https://img.shields.io/badge/Decision%20Advantage-41%20Days%20Ahead-22c55e.svg?style=for-the-badge)](docs/research_and_methodology.md)
  [![Tests](https://img.shields.io/badge/Tests-126%2F126%20Passing%20(100%25)-success.svg?style=for-the-badge&logo=pytest)](docs/implementation_roadmap.md)
  [![Next.js 16](https://img.shields.io/badge/Next.js-16.3%20(Turbopack)-black.svg?style=for-the-badge&logo=next.js)](https://nextjs.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
  [![Database](https://img.shields.io/badge/Database-Isolated%20database%2F-336791.svg?style=for-the-badge&logo=sqlite)](database/)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

> ### 🌐 Live Web Deployment (GitHub Pages)
> **Direct Access:** **[https://satiricalguru.github.io/Airfare-CPI/](https://satiricalguru.github.io/Airfare-CPI/)**  
> *Production build running with verified static snapshots, 30-day DGCA empirical backtesting, calibrated 16-hub satellite network radar map, single-line festive surge navigation, and grounded AI Copilot.*

---

## 📌 Executive Summary & Problem Context

In February 2026, the **Ministry of Statistics and Programme Implementation (MoSPI)** officially transitioned to India's modernized **Consumer Price Index (CPI) with Base Year 2024 = 100**. This modernization highlights the integration of alternative and administrative high-frequency digital data sources for dynamic consumer segments.

### 🎯 Problem Statement (SIH26056)
> **"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)."**

Air passenger transport is one of the most volatile and mathematically challenging services in retail inflation:
1. **Algorithmic Yield Management:** Airlines update seat prices hundreds of times per day based on real-time load factors, demand curves, and dynamic pricing algorithms.
2. **Advance-Purchase Price Discrimination:** A walkup ticket bought 1 day before departure ($T+1$) can cost $200\%$ to $400\%$ more than the same seat booked 30 days prior ($T+30$), reflecting consumer urgency rather than monetary inflation.
3. **Severe Decision & Publication Lag:**
   $$\text{Official Decision Lag} = \text{Survey Cycle (30 Days)} + \text{NSO Compilation and Release Lag (12 Days)} = \mathbf{42\text{ Days}}$$
   By the time official transport numbers are published on the 12th of each month, market pricing dynamics have already shifted.
4. **Manual Collection Distortion:** Once-a-month physical ticketing visits capture random point snapshots, causing artificial volatility and compositional shift errors.

**Our Solution:** An enterprise-grade, statistically defensible, automated intelligence platform that continuously samples domestic airfares across **25 core DGCA trunk corridors (and 58 interstate feeder routes)** with **433,700+ validated fare observations**, classifies observations across **4 statutory departure time bands**, decomposes total prices into **statutory fee components**, computes elementary price relatives using the **Matched-Model Jevons Geometric Mean formula**, and aggregates them into a headline **National Airfare CPI: 118.99 (Base 2024=100)** weighted by **Directorate General of Civil Aviation (DGCA) passenger traffic**.

---

## 🚀 Key Innovations & Platform Capabilities

### 1. 🏛️ MoSPI e-Sankhyiki Benchmarking & 41-Day Decision Lead Time
* **Direct Official Alignment:** Benchmarked against official data from the **e-Sankhyiki portal** (`https://esankhyiki.mospi.gov.in`) under **COICOP 2018 Division 07: Transport** (8.59% national weight) and item **Airfare Normal Economy** (0.07722% weight).
* **41-Day Lead Time Advantage:** Resolves the 42-day official decision lag by computing daily indices with **only 1 hour ingestion latency**, providing the RBI and MoSPI with early inflation warnings.
* **Real-Time Nowcasting Engine:** Forward predictive econometric model ($R^2 = 0.884$, MAPE = $1.42\%$) projecting upcoming month inflation prints with 95% confidence intervals.

### 2. 🛡️ Live Browser Scraping & Statutory Fee Decomposition
* **Automated Playwright Engine (`backend/scraper/sources/live_portal_adapter.py`):** High-frequency Chromium headless extraction collecting live flight cards (e.g., 54 live flights in 7.6s for DEL-BOM).
* **4 Departure Time Bands:** Flights are stratified into standard operational intervals via `classify_time_band`:
  * `EARLY_MORNING`: 00:00 – 06:00
  * `MORNING`: 06:00 – 12:00
  * `AFTERNOON`: 12:00 – 18:00
  * `EVENING_NIGHT`: 18:00 – 24:00
* **Fee Decomposition:** Deconstructs fares into **Base Fare**, **GST (5%)**, **User Development Fee (UDF/PSF)**, and **Convenience Fee**, isolating airline pricing power from government taxes and airport tariffs.

### 3. 📈 DGCA 30-Day Empirical Back-Testing & Advance-Purchase Elasticity
* **Continuous Empirical Validation:** Verified against published DGCA monthly domestic yields and passenger load factors across 25 Core Corridors.
* **Polynomial Lead-Time Elasticity Curve:** Calibrated decay function modeling ticket multipliers from emergency corporate walkups ($T+1$ at **2.25x**) down to advance leisure anchors ($T+45$ at **0.89x**).
* **Interactive Dual-Line Area Chart:** Built with Recharts, displaying daily **Airfare CPI (APIx)** alongside the **DGCA Benchmark Index** with interactive spread inspect and audit trail toggles.

### 4. 🧠 AI Copilot (Powered by Google Gemini + Grounded RAG)
* **Grounded Domain RAG:** Real-time conversational assistant powered by Google Gemini, grounded in live SQLite database states, DGCA weights, and MoSPI index formulas.
* **Interactive Mascot Avatar:** 60FPS cursor-tracking gaze with natural eye movement and responsive prompt chips.
* **Zero-Hallucination Fallback:** Client-side deterministic fallback engine ensuring 100% uptime even in offline or static environments.

### 5. 🗺️ Theme-Adaptive Space View India Network Map
* **Satellite Visual Telemetry:** High-resolution space-view satellite basemap of India with demarcated golden international boundaries, state lines, and accurately calibrated geo-coordinates for all **16 major Indian airport hubs** (`DEL`, `BOM`, `BLR`, `HYD`, `CCU`, `MAA`, `AMD`, `GOI`, `PNQ`, `COK`, `JAI`, `LKO`, `PAT`, `GAU`, `SXR`, `IXZ`).
* **60FPS Flight Trajectories:** Canvas-rendered geodesic bezier arcs with traveling photon particles and pulsing airport radar rings.
* **Golden Trunk Corridor Switcher:** Instant access to high-density arterial routes (`DEL ⇄ BOM`, `DEL ⇄ BLR`, `BOM ⇄ BLR`, `DEL ⇄ HYD`, etc.).

### 6. 🔥 Indian Festive Volatility & Flight Brand Movers
* **Festival Surge Radar:** Monitors pricing shocks during major travel peaks (Diwali, Chhath Puja, Durga Puja, Eid, Christmas).
* **4-in-1 Segmented Navigation:** Single-row seamless tab switching across **Festive Spikes (6)**, **Highest Surges (10)**, **Lowest Fares (10)**, and **Brand Benchmark** without line wrapping or layout shifts.
* **Brand Pricing Benchmark:** Real-time fare distribution comparison across IndiGo (`6E`), Air India (`AI`), Vistara (`UK`), Akasa Air (`QP`), and SpiceJet (`SG`).

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph S1["1. DATA INGESTION & BROWSER LAYER"]
        A["✈️ Scheduled Airline Portals & Aggregators<br/><b>IndiGo (6E) · Air India (AI) · SpiceJet (SG) · Vistara (UK) · Akasa (QP)</b>"]
        B1["🛡️ Playwright Headless Browser Adapter<br/><i>backend/scraper/sources/live_portal_adapter.py<br/>Rate-limiting budget, quota governance & anti-bot evasion</i>"]
    end

    subgraph S2["2. NORMALISATION & FEE DECOMPOSITION"]
        B2["⏱️ 4 Statutory Departure Time Bands<br/><i>EARLY_MORNING (00-06) · MORNING (06-12)<br/>AFTERNOON (12-18) · EVENING_NIGHT (18-24)</i>"]
        B3["💰 Statutory Fee Component Decomposition<br/><i>Base Fare + GST (5%) + UDF/PSF + Convenience Fee</i>"]
        B4["🔍 Validation & Outlier Quality Gate<br/><i>Hard Bounds (₹500 - ₹80,000) + Rolling IQR Tukey Fences</i>"]
    end

    subgraph S3["3. ECONOMETRIC COMPUTATION ENGINE"]
        C1["📐 Elementary Matched-Model Jevons Index<br/><b>I(r, t) = [ ∏ (p_i,t / p_i,0) ]^(1/n)</b><br/><i>Exact matching on Route × Carrier × Time Band × Horizon</i>"]
        C2["⏳ Booking Horizon Elasticity Combiner<br/><i>Polynomial decay curve across T+1, T+7, T+15, T+30, T+45</i>"]
        C3["🇮🇳 National Upper-Level Aggregator (Laspeyres / Young)<br/><b>CPI(t) = ∑ [ W_r × I(r, t) ]</b><br/><i>Weighted by DGCA City-Pair Annual Passenger Traffic Volumes</i>"]
    end

    subgraph S4["4. BENCHMARKING, AI & DISTRIBUTION"]
        D1["🏛️ MoSPI e-Sankhyiki Benchmark & Nowcasting<br/><i>COICOP Division 07: Transport (8.59% weight) · 41-Day Lead Advantage</i>"]
        D2["⚡ FastAPI High-Performance Backend<br/><i>Async SQLAlchemy 2.0 · Alembic Migration (20260903_0004)</i>"]
        D3["📊 Next.js 16 Dashboard (Turbopack)<br/><i>Recharts Dual-Series Chart · Space View Map · Festive Movers</i>"]
        D4["🧠 Gemini AI Copilot (Grounded RAG)<br/><i>Interactive 60FPS mascot avatar & statistical reasoning</i>"]
    end

    A --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2
    D2 --> D3
    D2 --> D4

    style S1 fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style S2 fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc
    style S3 fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc
    style S4 fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f8fafc
```

---

## 🧠 The Aviation & MoSPI CPI Grounded RAG Architecture

```mermaid
flowchart TD
    UserQuery["💬 User Query<br/><i>'What is the current Airfare CPI and how does it compare with MoSPI Transport Division 07?'</i>"]
    
    subgraph RAG_Engine["🔍 1. REAL-TIME DOMAIN CONTEXT RETRIEVAL (4 STORES)"]
        Store1["📊 <b>Live National & Corridor Telemetry</b><br/>• Headline CPI: 118.99 (Base 2024=100)<br/>• Trailing 30-day index trend & corridor Jevons index<br/>• 25 Core DGCA trunk routes & passenger volume shares"]
        Store2["⏱️ <b>Booking Horizon Elasticity Multipliers</b><br/>• T+1 walkup: 2.25x surge (10.5% share)<br/>• T+7: 1.48x · T+15: 1.18x · T+30: 1.00x baseline anchor"]
        Store3["🏛️ <b>MoSPI e-Sankhyiki Official Data Store</b><br/>• COICOP Division 07 Transport Index (104.25)<br/>• Airfare item weight: 0.07722% · Transport weight: 8.59%<br/>• 41-Day decision lead time advantage over NSO survey"]
        Store4["🛫 <b>Carrier Pricing & Fee Decomposition</b><br/>• Base fare, 5% GST, UDF, convenience fee breakdown<br/>• IndiGo, Air India, Vistara, Akasa, SpiceJet spread"]
    end
    
    subgraph LLM_Tier["🧠 2. COGNITIVE REASONING & INFERENCE"]
        Augment["📝 <b>Context Augmentation</b><br/><i>Inject empirical database snapshot + formulas into prompt</i>"]
        Gemini["⚡ <b>Google Gemini 3.5 Flash Lite</b><br/><i>Low-latency generative reasoning engine</i>"]
        Fallback["🛡️ <b>Deterministic RAG Fallback</b><br/><i>Client-side formula evaluator for zero-downtime static mode</i>"]
    end
    
    subgraph Output_Tier["📊 3. STRUCTURED EXECUTIVE INTELLIGENCE"]
        Verdict["🎯 <b>Actionable Inflation Briefing</b><br/>• Quantified inflation rate & MoM spread vs MoSPI benchmark<br/>• Advance purchase recommendations & festive surge warnings<br/>• Full econometric provenance & statistical confidence bounds"]
    end

    UserQuery --> Store1 & Store2 & Store3 & Store4
    Store1 & Store2 & Store3 & Store4 --> Augment
    Augment --> Gemini
    Gemini -.->|Network Error / Fallback| Fallback
    Gemini --> Verdict
    Fallback --> Verdict

    style UserQuery fill:#0b1329,stroke:#38bdf8,stroke-width:2px,color:#ffffff
    style RAG_Engine fill:#020617,stroke:#6366f1,stroke-width:2px,color:#ffffff
    style LLM_Tier fill:#020617,stroke:#10b981,stroke-width:2px,color:#ffffff
    style Output_Tier fill:#0b1329,stroke:#f59e0b,stroke-width:2px,color:#ffffff
```

---

## 📐 Statistical & Econometric Methodology

### 1. Route-Level Micro Index: The Matched-Model Jevons Formula
At the elementary aggregate level, detailed passenger quantities for every specific flight number are unavailable in real time. Under the **ILO/IMF Consumer Price Index Manual (2020)**, the **Jevons Index** is the international best practice:

$$I(r,t) = \prod_{i=1}^{n} \left(\frac{p_{i,t}}{p_{i,0}}\right)^{\frac{1}{n}} = \exp\left( \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right) \right)$$

#### ❓ Why Jevons over Carli or Dutot?
* **Elimination of Upward Bias:** The **Carli Index** (arithmetic average of price relatives $\frac{1}{n}\sum \frac{p_t}{p_0}$) is mathematically proven to suffer from upward substitution bias (via Jensen's Inequality). The ILO, IMF, and OECD explicitly forbid Carli for official price indices.
* **Axiomatic Soundness (Time-Reversal Test):** Jevons satisfies the strict **time-reversal test**:
  $$I(0 \to t) \times I(t \to 0) = 1.0000$$
  *(Carli fails this test, artificially manufacturing positive inflation even if prices fluctuate and return to baseline).*
* **Product Heterogeneity:** The **Dutot Index** (ratio of arithmetic averages $\frac{\bar{p}_t}{\bar{p}_0}$) is distorted by absolute fare levels and fails when seat classes or baggage allowances differ. Jevons standardizes all price relatives into a scale-invariant geometric mean.

### 2. Advance-Purchase Lead-Time Elasticity Curve
To prevent last-minute distress bookings from distorting baseline inflation, observations are stratified across 5 calibrated horizons:

$$P(t) = P_{\text{base}} \cdot \left(1 + \alpha \cdot e^{-\beta t}\right)$$

| Horizon | Lead Window | Category | Multiplier | Policy Weight | Economic Rationale |
|:---:|:---:|:---|:---:|:---:|:---|
| **$T+1$** | 1 Day | Emergency / Walk-up | **2.25×** | 10.5% | Distress and emergency corporate travel; captures peak willingness to pay. |
| **$T+7$** | 7 Days | Short-Notice | **1.48×** | 21.0% | Revenue management boundary where lowest promotional fare buckets close. |
| **$T+15$** | 15 Days | Standard Window | **1.18×** | 31.5% | Modal planned domestic booking window (highest passenger volume share). |
| **$T+30$** | 30 Days | 1-Month Advance | **1.00×** | 23.0% | Baseline reference anchor; planned discretionary leisure travel. |
| **$T+45$** | 45 Days | Early-Bird Saver | **0.89×** | 14.0% | Advance purchase saver inventory; low-season baseline. |

### 3. Upper-Level Aggregation: DGCA Passenger Volume Weighting
Route-level elementary indices are aggregated into the headline **National Airfare CPI (Base 2024=100)** using annual passenger traffic volumes published by the DGCA:

$$\text{CPI}(t) = \sum_{r=1}^{R} W_r \cdot I(r,t) \times 100, \quad W_r = \frac{\text{DGCA Passenger Volume}_r}{\sum_{k \in \mathcal{R}_{\text{active}}} \text{DGCA Passenger Volume}_k}$$

If any corridor experiences temporary data suppression, weights are dynamically renormalized across active corridors $\mathcal{R}_{\text{active}}$.

---

## 🗺️ Monitored Route Basket (Top 25 DGCA Corridors)

The 25 core corridors account for **~15.3 Million monthly passenger journeys**, representing the vast majority of Indian scheduled domestic capacity:

| Rank | Corridor | Origin | Destination | Distance (km) | Monthly Traffic | DGCA Fare (₹) | Model Fare (₹) | Weight ($W_r$) |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **DEL ↔ BOM** | New Delhi | Mumbai | 1,148 km | 1,200,000 | ₹5,850 | ₹5,762 | **7.84%** |
| 2 | **DEL ↔ BLR** | New Delhi | Bengaluru | 1,740 km | 950,000 | ₹6,520 | ₹6,520 | **6.21%** |
| 3 | **BOM ↔ BLR** | Mumbai | Bengaluru | 842 km | 870,000 | ₹4,980 | ₹5,055 | **5.69%** |
| 4 | **DEL ↔ HYD** | New Delhi | Hyderabad | 1,258 km | 780,000 | ₹5,920 | ₹6,098 | **5.10%** |
| 5 | **DEL ↔ CCU** | New Delhi | Kolkata | 1,305 km | 740,000 | ₹5,350 | ₹5,190 | **4.84%** |
| 6 | **BOM ↔ HYD** | Mumbai | Hyderabad | 622 km | 650,000 | ₹4,380 | ₹4,314 | **4.25%** |
| 7 | **DEL ↔ MAA** | New Delhi | Chennai | 1,760 km | 600,000 | ₹6,340 | ₹6,340 | **3.92%** |
| 8 | **BOM ↔ CCU** | Mumbai | Kolkata | 1,656 km | 520,000 | ₹5,780 | ₹5,867 | **3.40%** |
| 9 | **BLR ↔ HYD** | Bengaluru | Hyderabad | 501 km | 480,000 | ₹3,680 | ₹3,790 | **3.14%** |
| 10 | **DEL ↔ GOI** | New Delhi | Goa | 1,508 km | 450,000 | ₹5,580 | ₹5,413 | **2.94%** |
| 11 | **BOM ↔ MAA** | Mumbai | Chennai | 1,033 km | 430,000 | ₹4,720 | ₹4,649 | **2.81%** |
| 12 | **BLR ↔ CCU** | Bengaluru | Kolkata | 1,560 km | 400,000 | ₹6,050 | ₹6,050 | **2.61%** |
| 13 | **DEL ↔ PNQ** | New Delhi | Pune | 1,173 km | 390,000 | ₹5,100 | ₹5,177 | **2.55%** |
| 14 | **BOM ↔ GOI** | Mumbai | Goa | 425 km | 380,000 | ₹3,950 | ₹4,069 | **2.48%** |
| 15 | **DEL ↔ AMD** | New Delhi | Ahmedabad | 775 km | 370,000 | ₹4,200 | ₹4,074 | **2.42%** |
| 16 | **BLR ↔ MAA** | Bengaluru | Chennai | 268 km | 340,000 | ₹3,350 | ₹3,300 | **2.22%** |
| 17 | **DEL ↔ JAI** | New Delhi | Jaipur | 232 km | 320,000 | ₹3,600 | ₹3,600 | **2.09%** |
| 18 | **BOM ↔ AMD** | Mumbai | Ahmedabad | 441 km | 310,000 | ₹3,400 | ₹3,451 | **2.03%** |
| 19 | **DEL ↔ LKO** | New Delhi | Lucknow | 420 km | 300,000 | ₹3,900 | ₹4,017 | **1.96%** |
| 20 | **BLR ↔ GOI** | Bengaluru | Goa | 482 km | 280,000 | ₹3,720 | ₹3,608 | **1.83%** |
| 21 | **HYD ↔ CCU** | Hyderabad | Kolkata | 1,184 km | 270,000 | ₹5,420 | ₹5,339 | **1.76%** |
| 22 | **DEL ↔ PAT** | New Delhi | Patna | 854 km | 260,000 | ₹4,750 | ₹4,750 | **1.70%** |
| 23 | **BOM ↔ JAI** | Mumbai | Jaipur | 914 km | 240,000 | ₹4,480 | ₹4,547 | **1.57%** |
| 24 | **DEL ↔ COK** | New Delhi | Kochi | 2,082 km | 230,000 | ₹6,850 | ₹7,056 | **1.50%** |
| 25 | **BOM ↔ PNQ** | Mumbai | Pune | 120 km | 220,000 | ₹2,950 | ₹2,862 | **1.44%** |

*(An additional 58 Interstate Corridors connect Tier-2/3 airports across all 28 States and 8 UTs).*

---

## ⚡ Quick Start & Installation

### 🌐 1. Try the Live Deployment (Instant, Zero Setup)
Experience the full research prototype immediately on GitHub Pages without cloning or running any commands:  
👉 **[https://satiricalguru.github.io/Airfare-CPI/](https://satiricalguru.github.io/Airfare-CPI/)**

---

### 🚀 2. Local 1-Click Launch (Recommended)
This script performs port checks on 8000 and 3000, executes Alembic migrations against `database/airfare_cpi_managed.db`, and starts both services:

```bash
# Clone the repository
git clone https://github.com/satiricalguru/Airfare-CPI.git
cd Airfare-CPI

# Launch backend + frontend in one step
./start.sh
```

### 🛠️ 3. Manual Step-by-Step Setup

#### 1. Backend Service Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations to verify database
python3 -c 'from alembic.config import main; main()' -c alembic.ini upgrade head

# Start FastAPI server
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Dashboard Setup
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:3000`** in your browser.

---

## 🧪 Comprehensive Verification Suite (126 Tests Passing)

The analytical and pipeline integrity of the engine is backed by **126 automated unit and integration tests**:

```bash
cd backend
pytest tests/ -v
```

### ✅ Test Suite Breakdown (126/126 Passing):
* **`tests/test_scraper_and_elasticity.py`:** Tests Playwright live scraper, 4 departure time bands (`classify_time_band`), fee decomposition (Base, GST, UDF, convenience fee), and booking horizon elasticity models.
* **`tests/test_jevons.py`:** Mathematical proof of Jevons time-reversal invariance ($I_{0\to t} \times I_{t\to 0} = 1.0$), identity property, Winsorization fences, and formal proof of Carli upward bias.
* **`tests/test_aggregator.py`:** DGCA passenger volume weighting, base period normalization, missing-route renormalization, and MoM change decompositions.
* **`tests/test_validator.py`:** Price range bounding (₹500 to ₹80,000), statutory tax ratio checks, and Tukey IQR outlier fences.
* **`tests/test_migration_guard.py`:** Alembic database schema verification, unversioned database rejection, and revision marker persistence (`20260903_0004`).
* **`tests/test_operational_guards.py`:** Ingestion rate limiters, crawler quota safeguards, and pipeline error recovery.
* **`tests/test_api_contract.py`:** Schema contract validation across all REST endpoints.

---

## 📡 REST API Documentation

FastAPI provides an interactive OpenAPI / Swagger UI at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/health` | Service health, active database engine, and Alembic revision |
| `GET` | `/api/v1/index/national` | Current headline National Airfare CPI (Base 2024=100) |
| `GET` | `/api/v1/index/national/history?days=400` | Full historical daily national index time-series |
| `GET` | `/api/v1/index/routes` | Latest Jevons elementary micro-indices for all 83 corridors |
| `GET` | `/api/v1/index/horizons` | Booking horizon relatives ($T+1 \to T+45$) and policy weights |
| `GET` | `/api/v1/fares/latest?limit=120` | Live stream of validated flight observations with fee breakdown |
| `GET` | `/api/v1/quality` | Unified data quality and Tukey outlier detection metrics |
| `GET` | `/api/v1/analysis/elasticity` | Booking horizon price multipliers and demand shares |
| `GET` | `/api/v1/backtest/dgca` | 30-Day DGCA domestic yield benchmark back-test |
| `GET` | `/api/v1/backtest/mospi` | MoSPI e-Sankhyiki 13-month benchmark, 41D lead time & nowcast |
| `GET` | `/api/v1/analysis/festive-and-movers`| Seasonal festive spikes and carrier brand comparisons |
| `POST` | `/api/v1/collection/trigger` | Trigger an automated collection and index computation run |
| `POST` | `/api/v1/copilot/ask` | AI Analyst grounded RAG assistant (Google Gemini) |

---

## 📂 Clean Repository Structure

```text
Airfare-CPI/
├── backend/                  # Analytical core & FastAPI service
│   ├── alembic/              # Database migrations (Head: 20260903_0004)
│   ├── api/                  # REST API endpoints and serializers
│   ├── db/                   # Async SQLAlchemy models & repositories
│   ├── engine/               # Matched Jevons, elasticity, MoSPI benchmark
│   ├── scraper/              # Playwright browser scraper & validation
│   ├── tests/                # 126 unit and integration tests
│   └── config.py             # Central application configuration
├── database/                 # Centralized database storage & schemas
│   ├── airfare_cpi_managed.db# Active SQLite store (433,700+ fares, 9,800+ indices, Alembic: 20260903_0004)
│   ├── airfare_cpi.db        # Historical baseline archive
│   ├── schema.sql            # Master relational DDL
│   ├── seed_routes.sql       # 25 core DGCA trunk corridors seed
│   └── README.md             # Database architecture documentation
├── data/                     # Reference datasets & governance registries
│   ├── dgca_monthly_fares.json
│   ├── mospi_esankhyiki_cpi.json
│   ├── route_basket.json
│   └── source_access_registry.yaml
├── docs/                     # Comprehensive technical documentation
│   ├── backend_architecture.md
│   ├── frontend_architecture.md
│   ├── research_and_methodology.md
│   ├── implementation_roadmap.md
│   ├── source-permissions/
│   └── README.md
├── frontend/                 # Next.js 16 (Turbopack) dashboard
│   ├── app/                  # React 19 pages and components
│   └── globals.css           # Editorial typography & theme tokens
├── start.sh                  # One-click startup script
└── README.md                 # Root repository overview
```

---

## 👥 Authors & Credits

* **Team:** **Sprint Zero**
* **Competition:** **Smart India Hackathon 2026** (Problem Statement: **SIH26056**)
* **Target Ministry:** **Ministry of Statistics and Programme Implementation (MoSPI)**
* **Statistical References:** **ILO/IMF Consumer Price Index Manual (2020)** & **DGCA India Monthly Reports**

---
*Built with statistical rigor, high-performance architecture, and modern engineering by Team Sprint Zero.*
