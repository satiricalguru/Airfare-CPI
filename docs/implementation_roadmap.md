# Airfare CPI (SIH26056) — Implementation Roadmap & Execution Log

**Problem Statement:** SIH26056 — Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI).  
**Document Version:** 3.0.0  
**Project Phase:** Phase 4 Complete (Production Ready & Validated)  
**Target Ministry:** Ministry of Statistics and Programme Implementation (MoSPI)  

---

## 1. Project Implementation Milestones

```
[Phase 1: Architecture & Seed Ingestion] ──► COMPLETE (83 Routes, 25 Core Corridors, DGCA Weights)
                    │
                    ▼
[Phase 2: Econometric Matched-Model Engine] ──► COMPLETE (Jevons Formula, 5 Horizons, Tukey Fences)
                    │
                    ▼
[Phase 3: Automated Browser Scraper] ────────► COMPLETE (Playwright, 4 Time Bands, Statutory Fee Split)
                    │
                    ▼
[Phase 4: MoSPI e-Sankhyiki & Nowcasting] ────► COMPLETE (2024=100 Rebased, 41-Day Lead Time, 143 Tests)
```

---

## 2. Technical Capabilities Matrix

| Requirement | Implementation Module | Verification Status |
|---|---|---|
| **High-Frequency Ingestion** | `backend/scraper/sources/` | 15-channel multi-portal fleet (MMT, Goibibo, Cleartrip, 6E, AI, etc.) |
| **Fleet Health & Probes** | `/api/v1/scrapers/health` & `/{source_id}/test` | Real-time diagnostics & on-demand AERA decomposed test probes |
| **Departure Time Bands** | `classify_time_band()` (4 standard bands) | Integrated in `product_key()` |
| **Fee Decomposition** | Base Fare, GST, UDF, Convenience Fee | Alembic Migration `20260903_0004` (AERA Tariff Schedules) |
| **Matched Jevons Index** | `backend/engine/matched_jevons.py` | Geometric elementary mean |
| **Direct Flight Filter** | `INDEX_DIRECT_FLIGHTS_ONLY=true` | ILO CPI Manual Ch. 6 (Quality Adjustment, non-stop `stops == 0`) |
| **Booking Horizon Elasticity** | `backend/engine/elasticity.py` | Polynomial decay curve ($T+1$ to $T+45$) |
| **DGCA Back-Testing** | `backend/engine/dgca_backtest.py` | 30-Day Series & 25 Core Corridors |
| **MoSPI e-Sankhyiki Benchmark**| `backend/engine/mospi_benchmark.py` | 13-Month Time Series & 41D Lead Time |
| **Real-Time Nowcasting** | `nowcast_projection` in `/api/v1/backtest/mospi` | $R^2 = 0.884$, MAPE = $1.42\%$ |
| **Dedicated Database Storage** | `database/airfare_cpi_managed.db` | 454,000+ observations, Alembic `20260903_0004` |
| **Automated Test Suite** | `backend/tests/` | 143/143 passed in 41.77s (100% across 20 modules) |

---

## 3. Database Migration Provenance

Database schema evolution is strictly versioned with Alembic. The active revision is enforced on backend startup:

1. `20260901_0001`: Initial relational schema (routes, fare observations, elementary indices, national history).
2. `20260902_0002`: Added source access registry and crawler quota budgeting.
3. `20260902_0003`: Added festive spike and flight brand movers analysis models.
4. `20260903_0004`: **Latest Head** — Added 4 statutory departure time bands (`EARLY_MORNING`, `MORNING`, `AFTERNOON`, `EVENING_NIGHT`), statutory fee subcomponents (`base_fare_inr`, `gst_inr`, `udf_inr`, `convenience_fee_inr`), and composite `product_key` indexing.

---

## 4. Operational & Deployment Guide

### Prerequisites
* Python 3.11+ with `venv`
* Node.js 18+ and `npm`
* Playwright Chromium browser binaries (`playwright install chromium`)

### Quickstart Command
```bash
./start.sh
```
This executes:
1. Port collision check on 8000 and 3000.
2. Alembic migration verification against `database/airfare_cpi_managed.db`.
3. FastAPI backend launch on `http://localhost:8000`.
4. Next.js dashboard launch on `http://localhost:3000`.

### Production Verification Checklist
- [x] Database isolated in `database/` with zero database files in source root (`454,000+` validated quotes).
- [x] All 143 backend tests pass cleanly (100% across 20 test modules).
- [x] Next.js Turbopack build succeeds with zero linter errors.
- [x] e-Sankhyiki comparative dataset fully operational on `GET /api/v1/backtest/mospi`.
- [x] MoSPI Back-Testing UI renders dual-series area charts, KPI rails, and nowcasting cards.
