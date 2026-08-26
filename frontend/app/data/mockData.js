/**
 * SIH26056 — Airfare CPI Centralized Mock Data & Statistical Constants
 * High-fidelity, consistent mock data layer across all components.
 */

export const STATISTICAL_CONSTANTS = {
  headlineCPI: 107.42,
  baseYear: "2024 = 100",
  momChange: "+2.84%",
  yoyChange: "+8.12%",
  totalRoutes: 25,
  totalHorizons: 5,
  monthlyPaxVolume: "15.3M",
  activeAirlines: 6,
  dailyQuotesSampled: "48,200",
  lastUpdate: "12s ago",
  pipelineStatus: "HEALTHY",
  indexEngineStatus: "ONLINE",
};

export const BOOKING_HORIZONS = [
  { horizon: "T+30", days: 30, price: 4180, multiplier: "1.0×", tag: "Baseline Anchor", desc: "Discretionary leisure; planned 1-month advance bookings." },
  { horizon: "T+15", days: 15, price: 4850, multiplier: "1.16×", tag: "Early Leisure", desc: "Standard 2-week advance window; discount seats tightening." },
  { horizon: "T+7", days: 7, price: 6920, multiplier: "1.65×", tag: "1-Week Cutoff", desc: "Critical revenue threshold; lowest fare classes closed." },
  { horizon: "T+3", days: 3, price: 9840, multiplier: "2.35×", tag: "Short-Notice", desc: "Corporate & urgent travel; premium fare buckets dominate." },
  { horizon: "T+0", days: 0, price: 14870, multiplier: "3.56×", tag: "Same-Day Walkup", desc: "Emergency unconstrained demand; highest dynamic pricing band." },
];

export const TIME_SERIES_DATA = {
  "7D": [
    { date: "Aug 20", cpi: 106.12, del_bom: 104.2, del_blr: 105.8, bom_blr: 107.1 },
    { date: "Aug 21", cpi: 106.45, del_bom: 104.5, del_blr: 106.1, bom_blr: 107.4 },
    { date: "Aug 22", cpi: 106.80, del_bom: 104.9, del_blr: 106.5, bom_blr: 107.9 },
    { date: "Aug 23", cpi: 107.10, del_bom: 105.3, del_blr: 106.9, bom_blr: 108.3 },
    { date: "Aug 24", cpi: 107.25, del_bom: 105.5, del_blr: 107.1, bom_blr: 108.5 },
    { date: "Aug 25", cpi: 107.38, del_bom: 105.8, del_blr: 107.3, bom_blr: 108.7 },
    { date: "Aug 26", cpi: 107.42, del_bom: 106.0, del_blr: 107.5, bom_blr: 108.9 },
  ],
  "30D": [
    { date: "Jul 28", cpi: 104.20, del_bom: 102.1, del_blr: 103.5, bom_blr: 105.0 },
    { date: "Aug 04", cpi: 104.95, del_bom: 103.0, del_blr: 104.2, bom_blr: 105.8 },
    { date: "Aug 11", cpi: 105.80, del_bom: 103.9, del_blr: 105.1, bom_blr: 106.9 },
    { date: "Aug 18", cpi: 106.50, del_bom: 104.8, del_blr: 106.2, bom_blr: 107.6 },
    { date: "Aug 26", cpi: 107.42, del_bom: 106.0, del_blr: 107.5, bom_blr: 108.9 },
  ],
  "90D": [
    { date: "Jun 01", cpi: 101.80, del_bom: 100.2, del_blr: 101.1, bom_blr: 102.4 },
    { date: "Jun 20", cpi: 102.90, del_bom: 101.3, del_blr: 102.4, bom_blr: 103.8 },
    { date: "Jul 10", cpi: 103.85, del_bom: 102.0, del_blr: 103.2, bom_blr: 104.9 },
    { date: "Aug 01", cpi: 104.60, del_bom: 102.8, del_blr: 104.0, bom_blr: 105.6 },
    { date: "Aug 26", cpi: 107.42, del_bom: 106.0, del_blr: 107.5, bom_blr: 108.9 },
  ],
  "1Y": [
    { date: "Sep 25", cpi: 100.00, del_bom: 100.0, del_blr: 100.0, bom_blr: 100.0 },
    { date: "Dec 25", cpi: 102.30, del_bom: 101.5, del_blr: 102.0, bom_blr: 103.1 },
    { date: "Mar 26", cpi: 104.10, del_bom: 103.2, del_blr: 103.9, bom_blr: 105.0 },
    { date: "Jun 26", cpi: 105.60, del_bom: 104.5, del_blr: 105.2, bom_blr: 106.8 },
    { date: "Aug 26", cpi: 107.42, del_bom: 106.0, del_blr: 107.5, bom_blr: 108.9 },
  ],
};

export const ROUTE_NETWORK_HUBS = [
  { code: "DEL", city: "New Delhi", x: 38, y: 28, pax: 1200000, cpi: 106.0 },
  { code: "BOM", city: "Mumbai", x: 26, y: 58, pax: 870000, cpi: 107.4 },
  { code: "BLR", city: "Bengaluru", x: 42, y: 76, pax: 950000, cpi: 107.5 },
  { code: "HYD", city: "Hyderabad", x: 44, y: 62, pax: 780000, cpi: 105.8 },
  { code: "MAA", city: "Chennai", x: 48, y: 78, pax: 600000, cpi: 106.8 },
  { code: "CCU", city: "Kolkata", x: 74, y: 46, pax: 740000, cpi: 108.2 },
  { code: "COK", city: "Kochi", x: 36, y: 88, pax: 230000, cpi: 104.5 },
  { code: "AMD", city: "Ahmedabad", x: 24, y: 44, pax: 370000, cpi: 106.2 },
  { code: "PNQ", city: "Pune", x: 28, y: 61, pax: 390000, cpi: 105.4 },
  { code: "GOI", city: "Goa", x: 26, y: 70, pax: 450000, cpi: 109.1 },
];

export const NETWORK_ROUTES = [
  { from: "DEL", to: "BOM", fare: "₹6,240", cpi: 106.0, change: "+3.2%", status: "Active" },
  { from: "DEL", to: "BLR", fare: "₹6,850", cpi: 107.5, change: "+2.9%", status: "Active" },
  { from: "BOM", to: "BLR", fare: "₹5,420", cpi: 108.9, change: "+4.1%", status: "Surging" },
  { from: "DEL", to: "HYD", fare: "₹5,910", cpi: 105.8, change: "+1.8%", status: "Stable" },
  { from: "DEL", to: "CCU", fare: "₹6,380", cpi: 108.2, change: "+3.5%", status: "Active" },
  { from: "BOM", to: "GOI", fare: "₹4,120", cpi: 109.1, change: "+5.2%", status: "Surging" },
  { from: "BLR", to: "MAA", fare: "₹3,450", cpi: 104.9, change: "+0.8%", status: "Stable" },
  { from: "DEL", to: "AMD", fare: "₹4,890", cpi: 106.2, change: "+2.1%", status: "Active" },
];

export const ROUTE_HEATMAP_DATA = [
  { route: "DEL–BOM", weight: 7.84, pax: "1.20M", t0: 14870, t3: 9840, t7: 6920, t15: 4850, t30: 4180, cpi: 106.0, change: "+3.2%" },
  { route: "DEL–BLR", weight: 6.21, pax: "0.95M", t0: 15420, t3: 10250, t7: 7420, t15: 5120, t30: 4450, cpi: 107.5, change: "+2.9%" },
  { route: "BOM–BLR", weight: 5.69, pax: "0.87M", t0: 13150, t3: 8740, t7: 5980, t15: 4210, t30: 3680, cpi: 108.9, change: "+4.1%" },
  { route: "DEL–HYD", weight: 5.10, pax: "0.78M", t0: 13900, t3: 9150, t7: 6420, t15: 4620, t30: 3950, cpi: 105.8, change: "+1.8%" },
  { route: "DEL–CCU", weight: 4.84, pax: "0.74M", t0: 14250, t3: 9480, t7: 6810, t15: 4790, t30: 4120, cpi: 108.2, change: "+3.5%" },
  { route: "BOM–HYD", weight: 4.25, pax: "0.65M", t0: 12450, t3: 8120, t7: 5480, t15: 3980, t30: 3450, cpi: 104.9, change: "+1.2%" },
  { route: "DEL–MAA", weight: 3.92, pax: "0.60M", t0: 16100, t3: 10800, t7: 7850, t15: 5410, t30: 4620, cpi: 106.8, change: "+2.4%" },
  { route: "BOM–CCU", weight: 3.40, pax: "0.52M", t0: 15800, t3: 10450, t7: 7620, t15: 5240, t30: 4510, cpi: 107.1, change: "+2.7%" },
  { route: "BLR–HYD", weight: 3.14, pax: "0.48M", t0: 9850, t3: 6720, t7: 4620, t15: 3380, t30: 2950, cpi: 103.8, change: "+0.9%" },
  { route: "DEL–GOI", weight: 2.94, pax: "0.45M", t0: 17200, t3: 11950, t7: 8450, t15: 5820, t30: 4950, cpi: 109.1, change: "+5.2%" },
  { route: "BOM–MAA", weight: 2.81, pax: "0.43M", t0: 12850, t3: 8450, t7: 5890, t15: 4150, t30: 3620, cpi: 105.2, change: "+1.5%" },
  { route: "BLR–CCU", weight: 2.61, pax: "0.40M", t0: 15100, t3: 9980, t7: 7120, t15: 4950, t30: 4280, cpi: 107.8, change: "+3.1%" },
  { route: "DEL–PNQ", weight: 2.55, pax: "0.39M", t0: 13450, t3: 8920, t7: 6250, t15: 4380, t30: 3820, cpi: 105.4, change: "+1.9%" },
  { route: "BOM–GOI", weight: 2.48, pax: "0.38M", t0: 11200, t3: 7450, t7: 5120, t15: 3650, t30: 3150, cpi: 108.4, change: "+4.4%" },
  { route: "DEL–AMD", weight: 2.42, pax: "0.37M", t0: 11850, t3: 7920, t7: 5480, t15: 3850, t30: 3340, cpi: 106.2, change: "+2.1%" },
];

export const SCRAPER_MONITOR_SOURCES = [
  { name: "IndiGo (6E)", marketShare: "62.8%", status: "ONLINE", latency: "380ms", observations: "24,800", lastPing: "4s ago" },
  { name: "Air India (AI)", marketShare: "14.2%", status: "ONLINE", latency: "420ms", observations: "9,600", lastPing: "6s ago" },
  { name: "SpiceJet (SG)", marketShare: "5.4%", status: "ONLINE", latency: "510ms", observations: "4,100", lastPing: "11s ago" },
  { name: "Vistara (UK)", marketShare: "9.6%", status: "ONLINE", latency: "395ms", observations: "6,200", lastPing: "5s ago" },
  { name: "Akasa Air (QP)", marketShare: "4.8%", status: "ONLINE", latency: "340ms", observations: "3,500", lastPing: "8s ago" },
  { name: "MakeMyTrip (OTA)", marketShare: "Aggregator", status: "ONLINE", latency: "620ms", observations: "12,400", lastPing: "3s ago" },
];

export const API_ENDPOINTS_LIST = [
  {
    method: "GET",
    path: "/api/v1/index/national",
    description: "Returns the real-time Headline All-India Airfare CPI with MoM and YoY rates.",
    response: {
      index_date: "2026-08-26",
      base_period: "2024 = 100",
      headline_cpi: 107.42,
      mom_change_pct: 2.84,
      yoy_change_pct: 8.12,
      routes_evaluated: 25,
      total_observations: 48200,
      status: "OFFICIAL_PROVISIONAL",
    },
  },
  {
    method: "GET",
    path: "/api/v1/index/routes",
    description: "Fetches Jevons micro-indices and DGCA passenger weights for all 25 domestic routes.",
    response: {
      routes_count: 25,
      data: [
        { route_id: 1, pair: "DEL-BOM", weight: 0.0784, jevons_index: 106.0, pax_monthly: 1200000 },
        { route_id: 2, pair: "DEL-BLR", weight: 0.0621, jevons_index: 107.5, pax_monthly: 950000 },
        { route_id: 3, pair: "BOM-BLR", weight: 0.0569, jevons_index: 108.9, pax_monthly: 870000 },
      ],
    },
  },
  {
    method: "GET",
    path: "/api/v1/analysis/booking-horizons",
    description: "Retrieves price dispersion and dynamic pricing curves across the 5 advance-purchase horizons.",
    response: {
      horizons: [
        { horizon: "T+0", avg_fare: 14870, multiplier: 3.56, observations: 9600 },
        { horizon: "T+3", avg_fare: 9840, multiplier: 2.35, observations: 9700 },
        { horizon: "T+7", avg_fare: 6920, multiplier: 1.65, observations: 9650 },
        { horizon: "T+15", avg_fare: 4850, multiplier: 1.16, observations: 9600 },
        { horizon: "T+30", avg_fare: 4180, multiplier: 1.0, observations: 9650 },
      ],
    },
  },
  {
    method: "GET",
    path: "/api/v1/health",
    description: "Provides scraper uptime, network response latency, and validator throughput statistics.",
    response: {
      system_status: "HEALTHY",
      uptime: "99.98%",
      active_scrapers: 6,
      validator_rejections_24h: 142,
      iqr_anomalies_flagged: 18,
      timestamp: "2026-08-26T14:30:00Z",
    },
  },
  {
    method: "POST",
    path: "/api/v1/scraper/trigger",
    description: "Manually triggers an end-to-end data ingestion, validation, and Jevons recomputation cycle.",
    response: {
      status: "SUCCESS",
      cycle_id: "CYC-20260826-09",
      quotes_scraped: 580,
      validated_clean: 574,
      flagged_iqr: 6,
      recomputed_cpi: 107.42,
      execution_time_ms: 382,
    },
  },
];
