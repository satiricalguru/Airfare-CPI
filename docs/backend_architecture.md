# Airfare CPI (SIH26056) — Backend Architecture & Engineering Specification

**Document Version:** 3.0.0 (Production Release)  
**Base Period Reference:** `2024=100` (Rebased from 2012=100 via HCES 2023-24 Link Factor)  
**Database Location:** `database/airfare_cpi_managed.db` (Alembic Revision: `20260903_0004`)  
**Target Repository:** `satiricalguru/Airfare-CPI`  
**Author:** Antigravity System Engineer  

---

## 1. Executive Summary & Problem Scope

The **Real-Time Airfare Consumer Price Index (Airfare CPI)** is an automated econometric and price intelligence system designed for the **Ministry of Statistics and Programme Implementation (MoSPI)** under Smart India Hackathon problem statement **SIH26056**.

### The Core Problem Solved
Currently, the National Statistical Office (NSO) measures retail transport inflation using manual price quotes collected with a **30-day field survey cycle plus a 12-day compilation and publication lag** (a total **42-day decision lag**). Dynamic airline fare algorithms make once-a-month manual quotes unrepresentative. 

This platform replaces manual collection with an automated, high-frequency web-scraping engine that continuously ingests real airline fares, computes an elementary **Matched-Model Jevons Index**, and provides the Reserve Bank of India (RBI) and MoSPI with a **41-day decision lead-time advantage**.

### System Metrics
* **Total Ingested Observations:** Over `858,480` validated flight fare observations.
* **Corridor Coverage:** `83` active routes (25 Core DGCA Trunk Corridors + 58 Interstate Corridors spanning all 28 States and 8 Union Territories).
* **Airport Master Directory:** `85+` commercial airport nodes mapped with IATA codes, geographic coordinates, and regional hubs.
* **Carriers Tracked:** IndiGo (`6E`), Air India (`AI`), Vistara (`UK`), Akasa Air (`QP`), and SpiceJet (`SG`).
* **Departure Time Bands:** 4 statutory intervals (`EARLY_MORNING`: 00:00–06:00, `MORNING`: 06:00–12:00, `AFTERNOON`: 12:00–18:00, `EVENING_NIGHT`: 18:00–24:00).
* **Statutory Fee Decomposition:** Base Fare, Goods & Services Tax (GST), User Development Fee (UDF), and Passenger Convenience Fee.
* **Booking Horizons:** 5 strata (`T+1`, `T+7`, `T+15`, `T+30`, `T+45`).
* **Test Suite:** 126/126 passing tests with zero regressions (`pytest tests/ -q`).

---

## 2. End-to-End System Pipeline

```
[ Airline Direct & OTA Portals ]
              │
              ▼
┌──────────────────────────────────────────────┐
│  1. Ingestion Engine                         │  Playwright headless browser,
│  (backend/scraper/sources/live_portal_adapter)│  4 time bands, fee breakdown,
│                                              │  anti-bot evasion, budget quotas
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  2. Validation & Quality Assurance           │  Hard bounds (₹500 - ₹80,000),
│  (backend/scraper/validator.py)              │  tax ratio bounds, Tukey fences
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  3. Matched-Model Jevons Index Engine        │  Elementary geometric mean
│  (backend/engine/matched_jevons.py)          │  Exact carrier, time-band,
│                                              │  and booking horizon matching
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  4. Booking Horizon Elasticity Combiner      │  Polynomial advance-purchase decay,
│  (backend/engine/elasticity.py)              │  compositional shift protection
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  5. National Aggregator & MoSPI Benchmarker │  DGCA passenger volume weights,
│  (backend/engine/mospi_benchmark.py)         │  e-Sankhyiki COICOP 07 comparison,
│                                              │  41-day lead time nowcasting
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  6. Async FastAPI Service & Database Storage │  SQLite (database/airfare_cpi_managed.db)
│  (backend/api/main.py)                       │  PostgreSQL production compatibility
└──────────────────────────────────────────────┘
```

---

## 3. Core Modules & Engineering Implementation

### 3.1 Live Browser Scraper (`backend/scraper/sources/live_portal_adapter.py`)
* **Browser Automation:** Headless Chromium via Playwright navigating single-page flight search interfaces.
* **Dynamic Content Extraction:** Selects flight cards, extracts carrier codes, flight numbers, departure timestamps, and decomposes total fare into statutory subcomponents:
  * **Base Fare:** Net carrier tariff.
  * **GST:** 5% economy statutory tax.
  * **UDF / PSF:** Airport development charges.
  * **Convenience Fee:** Mandatory booking overhead.
* **Departure Time Classification:** Classifies flights into standard operational bands via `classify_time_band(departure_time)`.
* **Product Key Matching:** Generates composite unique keys:
  $$\text{Product Key} = \text{Route} \times \text{Carrier} \times \text{Time Band} \times \text{Booking Horizon}$$

### 3.2 Econometric Matched-Model Jevons Aggregator (`backend/engine/matched_jevons.py`)
In accordance with **ILO/IMF Consumer Price Index Manual (2020)** guidelines, elementary index aggregates use the Jevons geometric mean formula to prevent upward substitution bias:

$$I_{Jevons}^{0:t} = \prod_{i=1}^{n} \left( \frac{p_{i,t}}{p_{i,0}} \right)^{\frac{1}{n}} = \exp\left( \frac{1}{n} \sum_{i=1}^{n} \ln\left(\frac{p_{i,t}}{p_{i,0}}\right) \right)$$

* Exact matching on carrier, corridor, time-band, and horizon prevents compositional shifts.
* Strict minimum matched product threshold ($n \ge 3$) before publishing an elementary index point.

### 3.3 Advance-Purchase Elasticity Engine (`backend/engine/elasticity.py`)
Models the dynamic ticket pricing multiplier curve across booking horizons:
$$P(t) = P_{\text{base}} \cdot \left(1 + \alpha \cdot e^{-\beta t}\right)$$

| Horizon | Lead Time | Multiplier | Demand Share | Economic Rationale |
|---|---|---|---|---|
| **T+1** | 1 Day | **2.25x** | 10.5% | Emergency corporate & distress bookings (maximum dynamic surge) |
| **T+7** | 7 Days | **1.48x** | 21.0% | Short-lead discretionary and business travel |
| **T+15** | 15 Days | **1.18x** | 31.5% | Standard domestic planning window (modal window) |
| **T+30** | 30 Days | **1.00x** | 23.0% | Baseline reference threshold |
| **T+45** | 45 Days | **0.89x** | 14.0% | Advance purchase discount & low-season inventory |

### 3.4 Official MoSPI e-Sankhyiki Benchmarking (`backend/engine/mospi_benchmark.py`)
Integrates directly with data from the official e-Sankhyiki portal (`https://esankhyiki.mospi.gov.in`):
* **Classification:** COICOP 2018 Division 07: Transport.
* **Weights:** Division 07 Transport carries **8.59%** of the All-India CPI; Airfare carries **0.07722%**.
* **Base Year:** 2024=100 (Rebased from 2012=100 via HCES 2023-24 link factor).
* **Nowcasting Engine:** Forward-looking econometric regression predicting next month's inflation print with 95% confidence intervals and $R^2 = 0.884$.

---

## 4. Database Architecture & Storage

All persistent databases are isolated in the top-level `database/` directory:
* `database/airfare_cpi_managed.db`: Active SQLite database tracked by Alembic.
* `database/airfare_cpi.db`: Historical archive.
* `database/schema.sql`: Master relational DDL.
* `database/seed_routes.sql`: 25 core trunk routes.

Migrations are enforced at startup via `db/migration_guard.py`, preventing unversioned schema drift. Active migration head: `20260903_0004`.

---

## 5. API Endpoint Reference

| HTTP Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health, active database engine, and Alembic revision |
| `GET` | `/api/v1/index/national` | Current headline National Airfare CPI (Base 2024=100) |
| `GET` | `/api/v1/index/national/history` | Historical daily national index series |
| `GET` | `/api/v1/index/routes` | Corridor-specific price indices for all 83 routes |
| `GET` | `/api/v1/index/horizons` | Booking-horizon stratified indices and policy weights |
| `GET` | `/api/v1/fares/latest` | Latest validated raw fare observations with fee breakdown |
| `GET` | `/api/v1/quality` | Unified data quality and Tukey outlier detection metrics |
| `GET` | `/api/v1/analysis/elasticity` | Booking horizon price multipliers and demand shares |
| `GET` | `/api/v1/backtest/dgca` | 30-day DGCA domestic yield benchmark back-test |
| `GET` | `/api/v1/backtest/mospi` | MoSPI e-Sankhyiki 13-month comparison & nowcasting |
| `POST` | `/api/v1/collection/trigger` | Trigger an automated collection and index computation run |
| `POST` | `/api/v1/copilot/ask` | AI Analyst grounded RAG assistant (Google Gemini) |
