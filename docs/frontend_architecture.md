# Airfare CPI (SIH26056) — Frontend Architecture, UI & Design System

**Document Version:** 3.0.0 (Production Release)  
**Framework:** Next.js 16.3.3 (Turbopack) · React 19 · Vanilla Modular CSS  
**Target Repository:** `satiricalguru/Airfare-CPI`  
**Author:** Antigravity System Engineer  

---

## 1. Executive Summary & Design Philosophy

The **Airfare Consumer Price Index (Airfare CPI)** dashboard is an enterprise-grade financial intelligence interface designed for economists at the **Ministry of Statistics and Programme Implementation (MoSPI)** and the **Reserve Bank of India (RBI)**.

### Visual & Architectural Principles
1. **Editorial Financial Elegance:** Curated typography combining *Iowan Old Style* (serif headlines), *Avenir Next* (readable UI body), and *SFMono* (numerical tabular alignment). Warm paper light mode (`#f7f5f0`) and obsidian glass dark mode (`#151815`).
2. **Statistical Transparency:** Clear visual separation of raw observations, elementary indices, and aggregated national figures, with uncertainty bounds and provenance indicators.
3. **Dual-Benchmark Verification:** Direct interactive back-testing against **DGCA monthly domestic yields** and official **MoSPI e-Sankhyiki (COICOP 07)** retail inflation series.
4. **Resilient Data Modes:** Operates both as a full-stack dashboard connected to FastAPI and as a zero-dependency static deployment on GitHub Pages.

---

## 2. Information Architecture & Key Components

### 2.1 DGCA & MoSPI Back-Testing Panel (`frontend/app/components/DGCABacktestPanel.jsx`)
* **Encapsulated Segmented Pill Switcher:** 4-tab control with active elevation and icons:
  1. `30-Day Series ({count}D)`: Daily index trajectory against DGCA yields.
  2. `Lead-Time Elasticity`: Dynamic price multipliers across booking horizons ($T+1$ to $T+45$).
  3. `25 Core Corridors`: Filterable tabular comparison across trunk routes with passenger load factors (PLF).
  4. `MoSPI e-Sankhyiki (COICOP 07)`: Official 13-month comparison, 41-day lead-time advantage hero callout, and September 2026 nowcasting projection.
* **Elevated KPI Rail:** 4 glassmorphism metric cards:
  * Pearson Correlation ($r = 0.437$) with dynamic threshold badging (Amber alert if $< 0.85$, Green if $\ge 0.85$).
  * Mean Absolute % Error (MAPE) with $\le 5.0\%$ target verification.
  * Tracking Error (RMSE) residual bounds.
  * MoSPI Compliance status pill with glowing indicator.
* **Interactive Recharts Dual-Line Area Chart:** 320px responsive chart comparing **Airfare CPI (APIx Daily Jevons)** in indigo with the **DGCA Monthly Benchmark** in emerald, accompanied by view mode toggles (`Chart`, `Table`, `Both`).

### 2.2 Theme-Adaptive Space View India Map (`frontend/app/components/IndiaNetworkMap.jsx`)
* High-resolution satellite basemap centered on the Indian subcontinent.
* 60FPS canvas animation drawing geodesic quadratic bezier flight paths with photon particle animations.
* Golden Trunk quick selectors (`DEL ⇄ BOM`, `DEL ⇄ BLR`, `BOM ⇄ BLR`, `DEL ⇄ HYD`, etc.).

### 2.3 Indian Festive Spikes & Flight Movers (`frontend/app/components/FestiveAndFlightMovers.jsx`)
* Real-time monitoring of seasonal festival price surges (Diwali, Chhath Puja, Durga Puja, Eid, Christmas).
* Top surging and dropping flight tracking with carrier brand comparisons.

### 2.4 AI Analyst Copilot (`frontend/app/components/AviationCopilotModal.jsx`)
* **Interactive Mascot:** 60FPS cursor-tracking gaze calculation with natural eye blinking.
* **Grounded RAG Execution:** Queries `POST /api/v1/copilot/ask` powered by Google Gemini, grounded on real-time database state and statistical formulas.

---

## 3. Styling & Design Tokens (`frontend/app/globals.css`)

```css
:root {
  --paper: #f7f5f0;
  --paper-bright: #fffdf8;
  --surface: #fffdf8;
  --surface-subtle: rgba(0, 0, 0, 0.03);
  --ink: #191917;
  --muted: #77746d;
  --line: rgba(25, 25, 23, 0.13);
  --line-light: rgba(25, 25, 23, 0.07);
  --green: #3b6d4d;
  --green-soft: #e6eee5;
  --amber: #b27a31;
  --shadow: 0 18px 50px rgba(31, 31, 24, 0.08);
  --serif: "Iowan Old Style", "Baskerville", "Times New Roman", serif;
  --sans: "Avenir Next", "Helvetica Neue", Arial, sans-serif;
  --mono: "SFMono-Regular", Consolas, monospace;
}

html.dark {
  --paper: #151815;
  --paper-bright: #1c211d;
  --surface: #1c211d;
  --surface-subtle: rgba(255, 255, 255, 0.05);
  --ink: #f3f1e9;
  --muted: #aaa9a0;
  --line: rgba(255, 255, 255, 0.15);
  --line-light: rgba(255, 255, 255, 0.08);
  --green: #9ac3a0;
  --green-soft: #25352b;
  --shadow: 0 22px 60px rgba(0, 0, 0, 0.25);
}
```

---

## 4. Build & Verification Standards

* **Linter:** `npm run lint` — strictly 0 ESLint errors and warnings.
* **Production Build:** `npm run build` — Turbopack static prerendering for all routes (`/`, `/_not-found`, `/privacy`, `/terms`).
