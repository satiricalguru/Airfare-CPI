# Implementation Plan: Nivora Fare Pulse Feature Integration

Incorporate and enhance the key features identified from **Nivora Fare Pulse** (`https://nivora-fare-pulse.base44.app/`) into our **Airfare CPI Platform (Team Sprint Zero)** to provide advanced price intelligence, proactive alerts, interactive route deep-dives, and an AI-powered conversational assistant for MoSPI and aviation analysts.

---

## 📊 Feature Comparison & Opportunity Matrix

| Feature Area | Nivora Fare Pulse (Base44) | Our Current Airfare CPI App | Planned Enhancement & Elevation |
| :--- | :--- | :--- | :--- |
| **AI Assistant** | Simple pre-set text answers for 8 demo questions | None currently | **"Airfare CPI AI Copilot"**: Full streaming AI assistant with live RAG context (route median, 7D momentum, Jevons index, booking horizon recommendations, and MoSPI methodology explainer). |
| **Market Momentum** | "Routes Heating Up" & "Routes Cooling Down" simple 2-column card | Generic corridor table | **"Aviation Velocity Radar"**: Real-time momentum analyzer showing top 5 surging routes vs top 5 cooling routes with percentage change, volatility badges, and one-click alert creation. |
| **Price Alert Engine** | Basic static form (Origin, Destination, Target Price) | None currently | **"Smart Alert Engine"**: Interactive watch creator with threshold triggers (Drop below ₹X or Surge > Y%), email/webhook simulation, active watches list, and live status badges (Watching / Triggered). |
| **Route Deep Dive** | Modal with 30D line chart and quick stats | Map corridor focus + Price Index table | **"Route Intelligence Drawer"**: Comprehensive modal with 30-day historical trend, Price Distribution Boxplot / IQR fences, Advance Booking Horizon Decay ($T+0 \to T+30$), and Carrier Price Spread on that route. |
| **City Hub Sector Index** | City filter dropdown | Single airport filter | **"City Hub & Sector Matrix"**: Metro hub aggregation (DEL, BOM, BLR, CCU, HYD, MAA) showing outbound sector indices and traffic volume weights. |

---

## 🎯 Proposed Enhancements

### 1. 🤖 AI Airfare & CPI Copilot (`AviationCopilotModal.jsx` / Drawer)
- **Conversational Intelligence**: An intuitive assistant accessible via a floating action button or navbar "Ask AI Copilot" button.
- **Pre-Seeded One-Click Prompt Pills**:
  - *"Is ₹4,850 a fair price on Delhi → Mumbai?"*
  - *"Which domestic routes are heating up fastest this week?"*
  - *"How does the Jevons Geometric Mean formula eliminate extreme surge bias?"*
  - *"When is the optimal advance-purchase booking window for Bengaluru?"*
  - *"Compare IndiGo and Air India pricing spread on high-density corridors."*
- **Dynamic Context Injection**: The assistant pulls real-time statistical metrics from current loaded routes, calculating exact deviations from 30-day medians and MoSPI 2024=100 base indexes.

---

### 2. ⚡ Aviation Velocity Radar ("Routes Heating Up & Cooling Down")
- **Surge Radar (Heating Up)**: Highlights routes experiencing upward fare pressure ($\ge +3.5\%$ MoM/WoW) driven by holiday demand or capacity constraints.
- **Cooling Radar (Cooling Down)**: Highlights routes with falling fares ($\le -2.0\%$) where airline discounts or promotional inventory are active.
- **Micro-Metrics**: Displays Current Fare, 7D Movement %, Volatility Score, and a quick *"Set Watch"* action.

---

### 3. 🔔 Smart Route Alert & Threshold Watch Engine (`PriceAlertEngine.jsx`)
- **Interactive Alert Builder**:
  - Route Selector (e.g. `DEL → BOM`, `BLR → DEL`, `BOM → GOI`).
  - Alert Condition: *Target Price Drops Below (₹)* OR *Weekly Index Surge Exceeds (%)*.
  - Target Date / Advance Horizon Selection ($T+0, T+7, T+15, T+30$).
- **Active Watch Management**:
  - Card list of active watches with live delta vs current fare (e.g. `Current: ₹5,240 | Target: ₹4,800 | Gap: -₹440`).
  - Status indicators: `Watching (Active)` vs `Triggered (Target Reached)`.
  - In-app toast simulation for triggered alerts.

---

### 4. 📈 Comprehensive Route Intelligence Modal (`RouteDetailModal.jsx`)
- Clicking any route card, map beacon, or table row triggers an in-depth analytics modal:
  1. **30-Day Historical Trend & Moving Average (7D SMA)**.
  2. **Advance Purchase Decay Curve**: Comparison of fares at $T+0, T+3, T+7, T+15, T+30$.
  3. **Carrier Pricing Spread**: Side-by-side fare comparison across IndiGo, Air India, Vistara, Akasa, and SpiceJet with official vector logos.
  4. **Statistical IQR Fencing**: Visual representation of the lower quartile ($Q_1$), median ($Q_2$), upper quartile ($Q_3$), and anomaly rejection thresholds.

---

## 🛠️ Proposed File Changes

### [NEW] [AviationCopilotModal.jsx](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/frontend/app/components/AviationCopilotModal.jsx)
- Interactive AI conversational assistant with rich markdown answers, prompt chips, and real-time route telemetry lookup.

### [NEW] [PriceAlertEngine.jsx](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/frontend/app/components/PriceAlertEngine.jsx)
- Custom price alert creator, active watch list, and simulated notification triggers.

### [NEW] [RouteDetailModal.jsx](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/frontend/app/components/RouteDetailModal.jsx)
- Deep-dive modal with multi-horizon curves, carrier breakdowns, and IQR anomaly fence charts.

### [MODIFY] [frontend/app/page.js](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/frontend/app/page.js)
- Integrate "Aviation Velocity Radar" (Routes Heating Up / Cooling Down) into the Home dashboard.
- Add "Ask AI Copilot" button in navbar and hero section.
- Add Route Detail Modal trigger on route clicks.
- Add Alerts management section / tab.

### [MODIFY] [frontend/app/data/mockData.js](file:///Users/jatinpandey/Antigravity/Airfare%20CPI/frontend/app/data/mockData.js)
- Add enriched historical time series, velocity metrics (heating/cooling tags), and default alert watch samples.

---

## 🧪 Verification Plan

### Automated Build Verification:
- Run `npm run build` in `frontend/` to confirm static export compatibility with zero TypeScript/ESLint/Next.js errors.

### Functional Verification:
1. **AI Copilot**: Click each suggested prompt chip and verify accurate, formatted analytical responses with live route statistics.
2. **Velocity Radar**: Verify "Routes Heating Up" and "Routes Cooling Down" display accurate percentage changes and color-coded momentum badges.
3. **Alert Engine**: Create an alert (e.g. `DEL → BOM` at `₹4,500`), verify it appears in Active Watches, and verify delete/dismiss functionality.
4. **Route Detail Modal**: Click on any route from the India Map, Velocity Radar, or Heatmap table and verify the detailed charts render seamlessly in both Light and Dark modes.
5. **CI/CD Deployment**: Push to `main` and verify automatic deployment to GitHub Pages (`https://satiricalguru.github.io/Prototype-2/`).
