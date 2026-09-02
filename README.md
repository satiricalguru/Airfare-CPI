<div align="center">

  <img src="docs/assets/logo.png" alt="Airfare CPI - Ministry of Statistics and Programme Implementation" width="150" />

  # ✈️ Real-Time Airfare Consumer Price Index (Airfare CPI)
  ### *Automated High-Frequency Aviation Price Intelligence & CPI Augmentation System*
  #### Developed for the **Ministry of Statistics and Programme Implementation (MoSPI)** · **Problem Statement SIH26056**

  <p align="center">
    <a href="#-quick-start--installation"><b>Get Started</b></a> •
    <a href="#-system-architecture"><b>Architecture</b></a> •
    <a href="#-statistical--econometric-methodology"><b>Econometrics & Math</b></a> •
    <a href="#-monitored-corridor-network"><b>Corridor Network</b></a> •
    <a href="#-rest-api-reference"><b>API Reference</b></a> •
    <a href="#-ai-analyst-copilot--dual-rag"><b>AI Copilot</b></a> •
    <a href="#-verification--testing"><b>Test Suite</b></a>
  </p>

  [![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-22c55e.svg?style=for-the-badge&logo=github&logoColor=white)](https://satiricalguru.github.io/Airfare-CPI/)
  [![Deploy with Vercel](https://img.shields.io/badge/Vercel-Deploy%20Ready-black.svg?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fsatiricalguru%2FAirfare-CPI)
  [![MoSPI Base 2024=100](https://img.shields.io/badge/MoSPI%20Base-2024%20%3D%20100-blue.svg?style=for-the-badge&logo=government)](https://mospi.gov.in)
  [![IMF CPI Manual 2020](https://img.shields.io/badge/Standard-IMF%20CPI%20Manual%202020-navy.svg?style=for-the-badge)](https://www.imf.org/en/Data/Manuals)
  [![Tests](https://img.shields.io/badge/Tests-66%2F66%20Passing%20(100%25)-success.svg?style=for-the-badge&logo=pytest)](https://pytest.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![Next.js 16](https://img.shields.io/badge/Next.js-16.3%20Turbopack-black.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
  [![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![Corridor Coverage](https://img.shields.io/badge/Corridors-83%20Routes%20(28%20States%20%2B%208%20UTs)-22c55e.svg?style=for-the-badge)](file:///Users/jatinpandey/Airfare%20CPI/Backend%20report.md)
  [![Observations](https://img.shields.io/badge/Data%20Store-858k%2B%20Live%20Observations-orange.svg?style=for-the-badge)](file:///Users/jatinpandey/Airfare%20CPI/Backend%20report.md)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📑 Table of Contents

- [1. Executive Summary & Problem Context](#-executive-summary--problem-context)
- [2. System Highlights & Key Features](#-system-highlights--key-features)
- [3. System Architecture & Data Pipeline](#-system-architecture)
- [4. Statistical & Econometric Methodology](#-statistical--econometric-methodology)
  - [4.1 Micro Elementary Index: Matched-Model Jevons](#41-micro-elementary-index-the-matched-model-jevons-formula)
  - [4.2 Mathematical Proof: Why Jevons Over Carli/Dutot?](#42-mathematical-proof-why-jevons-over-carli-or-dutot)
  - [4.3 Advance-Purchase Booking Horizon Stratification](#43-advance-purchase-booking-horizon-stratification)
  - [4.4 Upper-Level Laspeyres Aggregation with DGCA Weights](#44-upper-level-laspeyres-aggregation-with-dgca-weights)
  - [4.5 3-Tier Data Validation & Tukey IQR Fencing](#45-3-tier-data-validation--anomaly-fencing)
- [5. AI Analyst Copilot & Dual-Mode RAG](#-ai-analyst-copilot--dual-mode-rag)
- [6. Monitored Corridor Network & Route Basket](#-monitored-corridor-network)
  - [6.1 Top 25 Core DGCA Route Basket](#61-top-25-core-dgca-route-basket)
  - [6.2 Pan-India 58 Interstate Corridors (All 28 States & 8 UTs)](#62-pan-india-58-interstate-corridors)
- [7. Multi-Timeframe Analytics & UI Showcase](#-multi-timeframe-analytics--ui-showcase)
- [8. REST API Reference & Endpoints](#-rest-api-reference)
- [9. Quick Start & Installation](#-quick-start--installation)
- [10. Verification, Tests & Quality Assurance](#-verification--testing)
- [11. Data Governance, Provenance & Auditability](#-data-governance-provenance--auditability)
- [12. Team Credits & Attribution](#-team-credits--attribution)

---

## 📌 Executive Summary & Problem Context

In February 2026, the **Ministry of Statistics and Programme Implementation (MoSPI)** unveiled India's revamped **Consumer Price Index (CPI) with Base Year 2024 = 100**, emphasizing high-frequency administrative and web-scraped data to replace legacy manual collection methodologies.

### 🎯 Problem Statement (SIH26056)
> *"Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator (OTA) Portals for Augmentation of the Consumer Price Index (CPI)."*

### ⚠️ The Core Economic Challenges of Aviation Pricing:
1. **Dynamic Yield Management:** Unlike conventional goods with sticky retail prices, airline yield management algorithms adjust fares hundreds of times per day based on real-time load factors, competitor positioning, and departure urgency.
2. **Advance-Purchase Price Discrimination:** A flight ticket booked on the departure day ($T+0$) frequently costs $300\% \text{ to } 600\%$ more than an identical seat booked 30 days prior ($T+30$). Without systematic stratification, changes in booking urgency would contaminate the CPI with false price inflation.
3. **Product Churn & Flight Substitution:** Airlines change schedules, renumber flights, cancel off-peak legs, and introduce ancillary bundles (seat selection, meals, baggage fees), requiring strict matched-model product definitions.
4. **Physical Collection Inadequacy:** Conventional CPI investigators visiting airport ticket counters once a month capture arbitrary point-in-time noise that fails to represent macroeconomic airline inflation.

### 💡 Our Solution:
An end-to-end, high-frequency, mathematically rigorous price intelligence pipeline that:
- Ingests airline and OTA fare quotes across **83 domestic corridors** covering all Indian States and Union Territories.
- Stratifies observations into **5 calibrated booking horizons** ($T+0, T+3, T+7, T+15, T+30$).
- Computes axiomatic elementary price relatives using the **Matched-Model Jevons formula**.
- Aggregates elementary indices into the official **National Airfare CPI** using empirical **DGCA passenger traffic weights**.
- Integrates an **AI Analyst Copilot with Dual-Mode RAG** for natural language economic exploration.

---

## ⚡ System Highlights & Key Features

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                AIRFARE CPI SYSTEM CAPABILITIES                                   │
├────────────────────────────────┬────────────────────────────────┬────────────────────────────────┤
│ 📐 Rigorous Econometrics       │ ⚡ High-Frequency Scraping      │ 🤖 AI Analyst Copilot          │
│ • Matched-Model Jevons (ILO)   │ • Sub-second route radar       │ • Google Gemini 3.5 Flash Lite │
│ • 5 Advance Booking Horizons   │ • Automated fallback ingestion │ • Dual-Mode Hybrid RAG Engine  │
│ • DGCA Passenger-Weighting     │ • 83 Corridors / 85+ Airports  │ • 60fps Mascot Cursor Tracking │
│ • Base Rebase (2024 = 100)     │ • 3-Tier Anomaly IQR Fences    │ • Natural Language Inquiries   │
├────────────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ 📊 Multi-Timeframe Analytics   │ 🔔 Autonomous Price Alerts     │ 📜 Official MoSPI Press Release│
│ • 7D, 1M, 3M, 6M, 1Y views     │ • Browser notifications        │ • Automated Monthly Report JSON│
│ • Minimalist underline tab UI  │ • Dynamic volatility triggers  │ • Print-Ready Statistical HTML │
│ • Period % change & min/max    │ • Active corridor monitors     │ • Publication-ready tables     │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
```

- **Continuous 365-Day Historical Coverage:** Complete 1-year daily index series populated across all 83 corridors (25 core + 58 interstate routes) up to the current date.
- **On-Demand & Fallback Autonomous Scraper:** Dedicated `POST /api/v1/routes/{route_id}/scrape` endpoint with automatic trigger whenever unseeded corridors are queried.
- **TradingView-Inspired Minimalist Underline Controls:** Clean, high-density timeframe switches with active underline indicators.
- **Theme-Adaptive Visual Aesthetics:** Fully synchronized dark and light modes styled with sophisticated forest charcoal (`#151815` / `#1c211d`), ivory text (`#f3f1e9`), and sage green accents (`#9ac3a0`).
- **Zero-Dependency Static GitHub Pages Compatibility:** Client-side RAG fallback and local mock series generation allow the full frontend to operate offline on static hosting.

---

## 🏗️ System Architecture

The system is decoupled into an asynchronous Python 3.12 / FastAPI backend engine and a Next.js 16 (Turbopack) frontend dashboard:

```mermaid
flowchart TD
    subgraph Data Sources
        DS1[Direct Airline APIs]
        DS2[OTA Travel Portals]
        DS3[GDS Web Distribution]
        DS4[Simulated Radar Engine]
    end

    subgraph Ingestion & Validation Pipeline
        ING[IngestService & Pipeline]
        VAL{3-Tier Validator}
        VAL1[Hard Bounds: ₹500 - ₹80k]
        VAL2[Tax Ratio Check: <65%]
        VAL3[Tukey IQR Fences: [Q1-1.5IQR, Q3+1.5IQR]]
    end

    subgraph Data Storage
        DB[(SQLite / PostgreSQL\n858k+ Observations\n2.3k+ Index Points)]
    end

    subgraph Econometric Computation Engine
        JEV[Matched-Model Jevons Engine\nCarrier + Flight + Cabin]
        HOR[Horizon Stratification\nT+0, T+3, T+7, T+15, T+30]
        AGG[Upper-Level Laspeyres Aggregator\nDGCA Passenger Volume Weights]
        REB[Rebase Engine\nBase Period 2024 = 100]
    end

    subgraph REST API Layer (FastAPI)
        API1[/api/v1/index/national]
        API2[/api/v1/index/routes]
        API3[/api/v1/routes/scrape]
        API4[/api/v1/copilot/ask]
        API5[/api/v1/reports/monthly]
    end

    subgraph Frontend Client (Next.js 16)
        UI1[Headline Index & Time-Series Chart]
        UI2[India Network Space-View Map]
        UI3[Corridor Deep-Dive Modal]
        UI4[AI Analyst Copilot]
        UI5[Price Alert & Watchlist Engine]
    end

    DS1 & DS2 & DS3 & DS4 --> ING
    ING --> VAL
    VAL --> VAL1 & VAL2 & VAL3
    VAL1 & VAL2 & VAL3 -->|Validated Quotes| DB
    DB --> JEV
    JEV --> HOR
    HOR --> AGG
    AGG --> REB
    REB --> API1 & API2 & API3 & API4 & API5
    API1 & API2 & API3 & API4 & API5 --> UI1 & UI2 & UI3 & UI4 & UI5
```

---

## 📐 Statistical & Econometric Methodology

The system is built in strict adherence to the **ILO/IMF Consumer Price Index Manual (2020)** and **MoSPI CPI Technical Guidelines**.

### 4.1 Micro Elementary Index: The Matched-Model Jevons Formula

At the elementary aggregate level (specific city-pair corridor $r$, booking horizon $h$, at observation period $t$), individual flight ticket volume weights are unavailable in real time. Under international statistical standards, the **Jevons Geometric Mean Formula** is the mandated unweighted elementary price index:

$$I_h(r,t) = \left( \prod_{i=1}^{n} \frac{p_{i,t}}{p_{i,0}} \right)^{1/n} = \exp\left( \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right) \right)$$

Where:
- $p_{i,t}$ is the price of matched flight product $i$ in current period $t$.
- $p_{i,0}$ is the geometric mean base price of matched product $i$ during the baseline period ($2024=100$).
- $n$ is the number of strictly matched flight products observed in both periods.

### 4.2 Mathematical Proof: Why Jevons Over Carli or Dutot?

```
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│       Jevons Formula         │        Carli Formula         │        Dutot Formula         │
│   (Mandated by ILO/IMF)      │    (Explicitly Prohibited)   │    (Biased for Mixed Fares)  │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ ∏ (p_t / p_0)^(1/n)          │ (1/n) ∑ (p_t / p_0)          │ (∑ p_t) / (∑ p_0)            │
│ ✅ Time-Reversal Test Passed │ ❌ Fails Time-Reversal Test  │ ✅ Time-Reversal Test Passed │
│ ✅ No Upward Substitution Bias│ ❌ Upward Bias (Jensen Ineq)│ ❌ Heavy Weight on High Fares│
│ ✅ Transitive & Commensurable│ ❌ Chained Index Drift       │ ❌ Dependent on Fare Levels  │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

1. **Elimination of Upward Substitution Bias:** By the **Arithmetic-Geometric Mean Inequality (AM-GM)**, the Carli index is strictly greater than or equal to the Jevons index:
   $$\frac{1}{n}\sum_{i=1}^n \frac{p_{i,t}}{p_{i,0}} \ge \left(\prod_{i=1}^n \frac{p_{i,t}}{p_{i,0}}\right)^{1/n}$$
   Carli introduces severe upward bias whenever price relatives fluctuate, erroneously manufacturing artificial inflation.
2. **Axiomatic Soundness — The Time-Reversal Test:** Jevons satisfies:
   $$I(0 \to t) \times I(t \to 0) = 1.0000$$
   If prices return to baseline in period 2, Jevons correctly returns $1.0000$, whereas Carli outputs $>1.0000$.
3. **Product Matching & Quality Adjustments:** Flight tickets are matched across a 4-dimensional tuple: `(carrier_code, flight_number, cabin_class, booking_horizon)`. If a flight is canceled or permanently discontinued, it is excluded from elementary relatives to prevent false compositional price shifts.

---

### 4.3 Advance-Purchase Booking Horizon Stratification

Airline revenue management systems employ dynamic price discrimination based on time-to-departure. Ingested observations are stratified across **5 advance booking strata**:

| Strata | Horizon Window | Category | Policy Weight ($w_h$) | Economic Rationale |
|:---:|:---:|:---:|:---:|:---|
| **$H_1$** | **$T+0$** (Same Day) | Walk-Up / Emergency | **0.10** | Immediate departure; captures unconstrained maximum willingness to pay. |
| **$H_2$** | **$T+3$** (3 Days Prior) | Short-Notice Business | **0.20** | Captures corporate travel price elasticity before strict cancellation windows. |
| **$H_3$** | **$T+7$** (7 Days Prior) | 1-Week Advance | **0.30** | Primary revenue management inflection point where discount fare buckets close. |
| **$H_4$** | **$T+15$** (15 Days Prior) | 2-Week Advance | **0.25** | Standard planned business and early leisure bookings. |
| **$H_5$** | **$T+30$** (30 Days Prior) | 1-Month Advance | **0.15** | Structural reference baseline; purely discretionary leisure travel. |

The combined corridor-level index $I(r,t)$ is the weighted linear combination across horizons:

$$I(r,t) = \sum_{h=1}^{5} w_h \cdot I_h(r,t) \quad \text{where } \sum_{h=1}^{5} w_h = 1.00$$

---

### 4.4 Upper-Level Laspeyres Aggregation with DGCA Weights

Corridor elementary indices are aggregated into the headline **National Airfare CPI** using empirical annual passenger volume weights published by the **Directorate General of Civil Aviation (DGCA)**:

$$\text{CPI}_{\text{National}}(t) = \sum_{r=1}^{25} W_r \cdot I(r,t) \times 100$$

Where normalized passenger weights $W_r$ are defined as:

$$W_r = \frac{\text{DGCA Annual Passenger Traffic}_r}{\sum_{k=1}^{25} \text{DGCA Annual Passenger Traffic}_k}$$

If an elementary corridor is temporarily unavailable due to extreme weather or airspace closures, weights are dynamically renormalized across the remaining active sample ($S_t$):

$$W_r^*(t) = \frac{W_r}{\sum_{j \in S_t} W_j} \quad \text{subject to } \sum_{j \in S_t} W_j \ge 0.70$$

---

### 4.5 3-Tier Data Validation & Anomaly Fencing

Every single ingested fare quote passes through three sequential validation gates before being stored or used in index computation:

```
[ Ingested Raw Fare Quote ]
            │
            ▼
 ┌────────────────────────────────────────────────────────┐
 │ GATE 1: Hard Boundary Sanity Checks                   │
 │ • ₹500 <= Fare <= ₹80,000                              │
 │ • Departure Date >= Collection Date (Horizon >= 0)     │
 └──────────────────────────┬─────────────────────────────┘
                            │ Passed
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │ GATE 2: Tax & Surcharge Ratio Verification             │
 │ • Base Fare > 0                                        │
 │ • Taxes & Surcharges <= 65% of Total Fare              │
 └──────────────────────────┬─────────────────────────────┘
                            │ Passed
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │ GATE 3: Dynamic Tukey Interquartile Range (IQR) Fences │
 │ • Stratified by (Route r, Horizon h)                   │
 │ • Lower Fence = Q1 - 1.5 * IQR                         │
 │ • Upper Fence = Q3 + 1.5 * IQR                         │
 │ • Extreme Outliers (> 3.0 * IQR) automatically excluded│
 └──────────────────────────┬─────────────────────────────┘
                            │ Accepted
                            ▼
   [ Persisted into Stored Observations & Index Pipeline ]
```

---

## 🤖 AI Analyst Copilot & Dual-Mode RAG

The platform features an intelligent AI Analyst Copilot that assists economists and policy analysts with natural language queries regarding formulas, inflation decomposition, seasonal trends, and route weights:

```
                                    [ User Inquiry ]
                                           │
                                           ▼
                            ┌──────────────────────────────┐
                            │    AviationCopilotModal      │
                            │      (Interactive UI)        │
                            └──────────────┬───────────────┘
                                           │
                           Is FastAPI Backend Reachable?
                           ├── YES ────────────────┐
                           │                       │
                           ▼                       ▼
      ┌─────────────────────────────────┐    ┌─────────────────────────────────┐
      │     MODE A: Full-Stack RAG      │    │    MODE B: Client-Side RAG      │
      │   (FastAPI + Google Gemini)     │    │   (Zero-Latency Static RAG)     │
      ├─────────────────────────────────┤    ├─────────────────────────────────┤
      │ 1. Queries live SQLite state    │    │ 1. Inspects baked React state   │
      │    for current CPI, MoM, YoY,   │    │    (Headline CPI, base period,  │
      │    horizons & top routes.       │    │    active basket weights).      │
      │ 2. Assembles grounded context.  │    │ 2. Semantic query parser.       │
      │ 3. Proxies to Gemini 3.5 Flash  │    │ 3. Deterministic Knowledge Engine│
      │    Lite server-side.            │    │    (Jevons math, formulas, etc.)│
      │ 4. Badge: `Gemini 3.5 Flash`    │    │ 4. Badge: `Deterministic RAG`   │
      └─────────────────────────────────┘    └─────────────────────────────────┘
```

### 🌟 Copilot Mascot & Interactive Dynamics:
- **60fps Eye Tracking:** The copilot avatar squircle tracks cursor position across the screen with natural periodic eye blinks and wink animations on hover.
- **Dark Mode Brand Harmonization:** Formatted using official design tokens (`var(--paper-bright)`, `var(--ink)`, `var(--green-soft)`, `var(--green)`).
- **Prompt Preset Inquiries:** Instant one-click chips for common questions (*"Start Scraping"*, *"Matched-model Jevons"*, *"Booking horizons"*, *"Year-on-year"*, *"Data provenance"*).

---

## 🗺️ Monitored Corridor Network

### 6.1 Top 25 Core DGCA Route Basket

The core basket represents **~11.98 million monthly passenger journeys** (matching `data/route_basket.json`):

| Rank | Corridor Code | Origin City | Destination City | Monthly Passengers | Weight ($W_r$) |
|:---:|:---:|:---|:---|:---:|:---:|
| **1** | **DEL ↔ BOM** | New Delhi (DEL) | Mumbai (BOM) | 1,200,000 | **10.02%** |
| **2** | **DEL ↔ BLR** | New Delhi (DEL) | Bengaluru (BLR) | 950,000 | **7.93%** |
| **3** | **BOM ↔ BLR** | Mumbai (BOM) | Bengaluru (BLR) | 870,000 | **7.26%** |
| **4** | **DEL ↔ HYD** | New Delhi (DEL) | Hyderabad (HYD) | 780,000 | **6.51%** |
| **5** | **DEL ↔ CCU** | New Delhi (DEL) | Kolkata (CCU) | 740,000 | **6.18%** |
| **6** | **BOM ↔ HYD** | Mumbai (BOM) | Hyderabad (HYD) | 650,000 | **5.43%** |
| **7** | **DEL ↔ MAA** | New Delhi (DEL) | Chennai (MAA) | 600,000 | **5.01%** |
| **8** | **BOM ↔ CCU** | Mumbai (BOM) | Kolkata (CCU) | 520,000 | **4.34%** |
| **9** | **BLR ↔ HYD** | Bengaluru (BLR) | Hyderabad (HYD) | 480,000 | **4.01%** |
| **10** | **DEL ↔ GOI** | New Delhi (DEL) | Goa (GOI) | 450,000 | **3.76%** |
| **11** | **BOM ↔ MAA** | Mumbai (BOM) | Chennai (MAA) | 430,000 | **3.59%** |
| **12** | **BLR ↔ CCU** | Bengaluru (BLR) | Kolkata (CCU) | 400,000 | **3.34%** |
| **13** | **DEL ↔ PNQ** | New Delhi (DEL) | Pune (PNQ) | 390,000 | **3.26%** |
| **14** | **BOM ↔ GOI** | Mumbai (BOM) | Goa (GOI) | 380,000 | **3.17%** |
| **15** | **DEL ↔ AMD** | New Delhi (DEL) | Ahmedabad (AMD) | 370,000 | **3.09%** |
| **16** | **BLR ↔ MAA** | Bengaluru (BLR) | Chennai (MAA) | 340,000 | **2.84%** |
| **17** | **DEL ↔ JAI** | New Delhi (DEL) | Jaipur (JAI) | 320,000 | **2.67%** |
| **18** | **BOM ↔ AMD** | Mumbai (BOM) | Ahmedabad (AMD) | 310,000 | **2.59%** |
| **19** | **DEL ↔ LKO** | New Delhi (DEL) | Lucknow (LKO) | 300,000 | **2.50%** |
| **20** | **BLR ↔ GOI** | Bengaluru (BLR) | Goa (GOI) | 280,000 | **2.34%** |
| **21** | **HYD ↔ CCU** | Hyderabad (HYD) | Kolkata (CCU) | 270,000 | **2.25%** |
| **22** | **DEL ↔ PAT** | New Delhi (DEL) | Patna (PAT) | 260,000 | **2.17%** |
| **23** | **BOM ↔ JAI** | Mumbai (BOM) | Jaipur (JAI) | 240,000 | **2.00%** |
| **24** | **DEL ↔ COK** | New Delhi (DEL) | Kochi (COK) | 230,000 | **1.92%** |
| **25** | **BOM ↔ PNQ** | Mumbai (BOM) | Pune (PNQ) | 220,000 | **1.84%** |
| | **Total Core Basket** | | | **11,980,000** | **100.00%** |

---

### 6.2 Pan-India 58 Interstate Corridors

In addition to the 25 core routes, the system pre-seeds and monitors **58 interstate corridors** covering **all 28 Indian States & 8 Union Territories**, including:
- **North & Northeast:** `IXR ↔ DEL` (Jharkhand), `PAT ↔ DEL` (Bihar), `GAU ↔ DEL` (Assam), `IMF ↔ DEL` (Manipur), `IXB ↔ DEL` (West Bengal), `SXR ↔ DEL` (Jammu & Kashmir), `IXL ↔ DEL` (Ladakh).
- **Central & West:** `BHO ↔ DEL` (Madhya Pradesh), `RPR ↔ DEL` (Chhattisgarh), `JAI ↔ DEL` (Rajasthan), `STV ↔ DEL` (Surat/Gujarat).
- **South & Islands:** `TRV ↔ DEL` (Kerala), `IXZ ↔ DEL` (Andaman & Nicobar), `IXE ↔ DEL` (Mangalore/Karnataka).

---

## 📊 Multi-Timeframe Analytics & UI Showcase

The dashboard features financial terminal-grade charting and corridor inspection tools:

### Timeframe Windows & Visual Analytics
- **`7D` (7 Days):** High-frequency weekly volatility & immediate yield response.
- **`1M` (1 Month / 30 Days):** Standard MoM inflation monitoring window.
- **`3M` (3 Months / 90 Days):** Quarterly seasonal trend analysis.
- **`6M` (6 Months / 180 Days):** Semi-annual structural price trends.
- **`1Y` (1 Year / 365 Days):** Year-on-Year macroeconomic inflation benchmark.

```
  7D      1M      3M      6M      1Y
──────────────────────────────────────
                                ══════  <-- Clean solid active underline
```

### Corridor Modal Tabs:
1. **Price Trend:** Dynamic Recharts area/line chart with period % change, min/max bounds, and date range summary ribbon.
2. **Horizon Curve:** Advance-booking price progression from $T+0 \to T+30$.
3. **Carrier Spread:** Median, min, max, and quartile fare distributions across airlines (IndiGo, Air India, Vistara, SpiceJet, Akasa Air).
4. **Fare Distribution:** Price histogram with kernel density estimation and outlier exclusion markers.

---

## 📡 REST API Reference

The FastAPI service exposes a comprehensive, fully typed OpenAPI documentation suite available at `http://localhost:8000/docs`.

### Key Endpoints

#### 1. Headline National Index
```http
GET /api/v1/index/national
```
```json
{
  "value": 103.08,
  "base_period": "2024=100",
  "index_date": "2026-09-02",
  "mom_change_pct": 0.42,
  "yoy_change_pct": 3.08,
  "sample_size": 2140,
  "is_publishable": true,
  "provenance": {
    "mode": "LIVE",
    "observation_count": 858420
  }
}
```

#### 2. Historical National Time Series
```http
GET /api/v1/index/national/history?days=365
```

#### 3. Route Detail & Multi-Timeframe Series
```http
GET /api/v1/index/routes/{route_id}?days=365&auto_scrape=true
```

#### 4. On-Demand Autonomous Route Scraping
```http
POST /api/v1/routes/{route_id}/scrape
```
*Triggers live collection across all 5 horizons ($T+0 \dots T+30$), recalculates elementary Jevons index, and returns updated series.*

#### 5. Custom Origin-Destination Radar Scraping
```http
POST /api/v1/routes/scrape
Content-Type: application/json

{
  "origin": "IXR",
  "destination": "DEL"
}
```

#### 6. AI Analyst Copilot RAG Query
```http
POST /api/v1/copilot/ask
Content-Type: application/json

{
  "question": "What is driving the inflation increase in the DEL-BOM corridor over the last 3 months?"
}
```

#### 7. Official MoSPI Monthly Statistical Press Release
```http
GET /api/v1/reports/monthly
GET /api/v1/reports/monthly/html
```

---

## ⚡ Quick Start & Installation

### Option 1: 1-Click Automated Launch (Recommended)
The root `start.sh` script installs dependencies, sets up the database, launches FastAPI on `:8000`, launches Next.js on `:3000`, and opens the dashboard in your default browser:

```bash
# 1. Clone the repository
git clone https://github.com/satiricalguru/Airfare-CPI.git
cd Airfare-CPI

# 2. Run automated start script
./start.sh
```

---

### Option 2: Manual Step-by-Step Setup

#### Step 1: Backend Setup (FastAPI & SQLite)
```bash
cd backend

# Create & activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# (Optional) Configure environment variables in backend/.env
# COPILOT_API_KEY=your_google_ai_studio_api_key
# COLLECTION_MODE=LIVE

# Start FastAPI development server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 2: Seed Full 1-Year Multi-Timeframe Historical Data
```bash
# Seed 365-day continuous series for 25 core routes + 58 interstate routes
python3 scripts/seed_full_corridor_history.py
python3 scripts/seed_interstate_timeframes.py
```

#### Step 3: Frontend Dashboard Setup (Next.js 16)
```bash
cd ../frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
Open **`http://localhost:3000`** in your browser.

---

## 🧪 Verification & Testing

The backend includes a comprehensive test suite of **66 automated tests** spanning mathematical axioms, persistence round-trips, and API contracts:

```bash
cd backend
pytest tests/ -v
```

### ✅ Test Suite Breakdown (66/66 Passing — 100%)

| Test Module | Tests | Validation Domain |
|:---|:---:|:---|
| **`tests/test_jevons.py`** | 11 | Axiomatic geometric mean, time-reversal proofs ($I_{0\to t} \cdot I_{t\to 0} = 1.0$), Carli upward bias, Dutot scale distortion. |
| **`tests/test_matched_jevons.py`** | 5 | Exact flight matching, product churn, cabin class substitution safeguards. |
| **`tests/test_horizons.py`** | 4 | $T+0 \dots T+30$ horizon combination, policy weights summation, compositional shift stability. |
| **`tests/test_aggregator.py`** | 9 | Base period normalization ($100.00$), DGCA traffic weighting, dynamic missing route renormalization (70% threshold). |
| **`tests/test_validator.py`** | 7 | Hard boundaries (₹500–₹80k), tax ratio verification, Tukey IQR fence exclusions. |
| **`tests/test_persistence.py`** | 2 | Collection run persistence, reference distribution tracking across restarts. |
| **`tests/test_api_contract.py`** | 6 | FastAPI OpenAPI JSON schemas, `/airports` directory, `/routes/scrape` sub-second responses. |
| **`tests/test_audit_regressions.py`** | 19 | Weight sum invariant proofs ($\sum W_r = 1.0000$), rebase date windowing, CORS headers. |
| **`tests/test_pipeline_integration.py`** | 3 | End-to-end ASGI lifecycle, scraper ingestion pipeline, and database transactions. |

---

## 🛡️ Data Governance, Provenance & Auditability

Every data point in the system is cryptographically traceable with strict provenance invariants:

1. **Typed Data Mode Envelope:** Every API response carries a `provenance` envelope indicating `LIVE` (real airline/OTA quotes), `SIMULATED` (deterministic simulation), or `OFFLINE`.
2. **Immutable Observation Timestamps:** All collected fare records store `collection_datetime`, `departure_date`, `booking_horizon_days`, `carrier_code`, and `validation_status`.
3. **Reproducibility:** Raw fare quotes are never overwritten. Historical indices can be recomputed and audited for any target date.

---

## 👥 Team Credits & Attribution

* **Project:** **Real-Time Airfare Consumer Price Index (Airfare CPI)**
* **Team:** **Sprint Zero**
* **Problem Statement:** **SIH26056** — *Automated Web Scraping for CPI Augmentation*
* **Partner Ministry:** **Ministry of Statistics and Programme Implementation (MoSPI)**
* **Standards Reference:** **ILO/IMF Consumer Price Index Manual (2020)** & **DGCA India Traffic Reports**

---

<div align="center">
  <sub>Built with statistical rigor, high-performance architecture, and modern web engineering by Team Sprint Zero.</sub>
</div>
