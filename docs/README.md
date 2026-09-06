# Airfare CPI (SIH26056) — Documentation Hub

Welcome to the central technical and econometric documentation repository for the **Real-Time Airfare Consumer Price Index for India**.

---

## Documentation Index

| Document | Focus Area | Description |
|---|---|---|
| [`backend_architecture.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/docs/backend_architecture.md) | **Backend & Engine** | Playwright browser scraper, 4 departure time bands, statutory fee decomposition, Jevons engine, and API endpoints. |
| [`frontend_architecture.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/docs/frontend_architecture.md) | **Frontend & UI** | Next.js 16.3.3 (Turbopack) dashboard, Recharts dual-line back-testing chart, 60FPS space-view map, design system. |
| [`research_and_methodology.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/docs/research_and_methodology.md) | **Econometric Theory** | ILO/IMF Consumer Price Index formulation, DGCA weighting matrix, advance-purchase elasticity decay, MoSPI COICOP 07. |
| [`implementation_roadmap.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/docs/implementation_roadmap.md) | **Roadmap & Provenance** | SIH26056 problem scope, completed phases, technical matrix, Alembic migrations (`20260903_0004`), verification. |
| [`source-permissions/README.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/docs/source-permissions/README.md) | **Governance & Ethics** | Crawler quota budgeting, robots.txt compliance, data minimization, and legal permissions framework. |
| [`database/README.md`](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/database/README.md) | **Database Storage** | Dedicated database directory, active SQLite store, historical archive, and relational schemas. |

---

## Key Project Specifications

* **Problem Statement:** SIH26056 (MoSPI, Government of India)
* **Base Reference Year:** `2024=100` (Rebased from 2012=100 via HCES 2023-24 Link Factor)
* **Classification:** COICOP 2018 (Division 07: Transport — 8.59% weight; Item: Airfare — 0.07722%)
* **Decision Lead Time:** 41-day advantage over official NSO survey publishing schedule
* **Automated Scraper:** Playwright Chromium headless crawler with rate limiting and anti-bot resilience
* **Back-Testing:** Dual-benchmarked against DGCA monthly yields and MoSPI e-Sankhyiki retail inflation series
* **Database Engine:** Async SQLAlchemy 2.0 with Alembic versioning in `database/airfare_cpi_managed.db`
