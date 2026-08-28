/**
 * SIH26056 — Airfare CPI Centralized Mock Data & Statistical Constants
 * High-fidelity, consistent mock data layer matching Base44 Fare Pulse specifications.
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
  validRecordsPct: "96.4%",
  flaggedAnomaliesCount: 42,
};

export const AIRPORTS_LIST = [
  { code: "DEL", city: "New Delhi", name: "Indira Gandhi International" },
  { code: "BOM", city: "Mumbai", name: "Chhatrapati Shivaji Maharaj International" },
  { code: "BLR", city: "Bengaluru", name: "Kempegowda International" },
  { code: "HYD", city: "Hyderabad", name: "Rajiv Gandhi International" },
  { code: "MAA", city: "Chennai", name: "Chennai International" },
  { code: "CCU", city: "Kolkata", name: "Netaji Subhash Chandra Bose International" },
  { code: "AMD", city: "Ahmedabad", name: "Sardar Vallabhbhai Patel International" },
  { code: "GOI", city: "Goa", name: "Dabolim / Manohar International" },
  { code: "PNQ", city: "Pune", name: "Pune Airport" },
  { code: "COK", city: "Kochi", name: "Cochin International" },
];

export const AIRLINES_LIST = [
  { code: "6E", name: "IndiGo", marketShare: "62.8%" },
  { code: "AI", name: "Air India", marketShare: "14.2%" },
  { code: "UK", name: "Vistara", marketShare: "9.6%" },
  { code: "SG", name: "SpiceJet", marketShare: "5.4%" },
  { code: "QP", name: "Akasa Air", marketShare: "4.8%" },
  { code: "IX", name: "Air India Express", marketShare: "3.2%" },
];

export const BOOKING_HORIZONS = [
  { horizon: "T+30", days: 30, price: 4180, multiplier: "1.0×", tag: "Baseline Anchor", desc: "Discretionary leisure; planned 1-month advance bookings." },
  { horizon: "T+15", days: 15, price: 4850, multiplier: "1.16×", tag: "Early Leisure", desc: "Standard 2-week advance window; discount seats tightening." },
  { horizon: "T+7", days: 7, price: 6920, multiplier: "1.65×", tag: "1-Week Cutoff", desc: "Critical revenue threshold; lowest fare classes closed." },
  { horizon: "T+3", days: 3, price: 9840, multiplier: "2.35×", tag: "Short-Notice", desc: "Corporate & urgent travel; premium fare buckets dominate." },
  { horizon: "T+0", days: 0, price: 14870, multiplier: "3.56×", tag: "Same-Day Walkup", desc: "Emergency unconstrained demand; highest dynamic pricing band." },
];

export const TIME_SERIES_DATA = {
  "7D": [
    { date: "Aug 22", cpi: 106.80, del_bom: 104.9, del_blr: 106.5, bom_blr: 107.9, nonstop: 106.2, onestop: 108.1 },
    { date: "Aug 23", cpi: 107.10, del_bom: 105.3, del_blr: 106.9, bom_blr: 108.3, nonstop: 106.5, onestop: 108.4 },
    { date: "Aug 24", cpi: 107.25, del_bom: 105.5, del_blr: 107.1, bom_blr: 108.5, nonstop: 106.7, onestop: 108.6 },
    { date: "Aug 25", cpi: 107.38, del_bom: 105.8, del_blr: 107.3, bom_blr: 108.7, nonstop: 106.9, onestop: 108.8 },
    { date: "Aug 26", cpi: 107.42, del_bom: 106.0, del_blr: 107.5, bom_blr: 108.9, nonstop: 107.0, onestop: 109.0 },
    { date: "Aug 27", cpi: 107.48, del_bom: 106.2, del_blr: 107.6, bom_blr: 109.1, nonstop: 107.1, onestop: 109.2 },
    { date: "Aug 28", cpi: 107.55, del_bom: 106.4, del_blr: 107.8, bom_blr: 109.3, nonstop: 107.2, onestop: 109.4 },
  ],
  "1M": [
    { date: "Jul 28", cpi: 104.20, del_bom: 102.1, del_blr: 103.5, bom_blr: 105.0, nonstop: 103.8, onestop: 105.2 },
    { date: "Aug 04", cpi: 104.95, del_bom: 103.0, del_blr: 104.2, bom_blr: 105.8, nonstop: 104.5, onestop: 106.1 },
    { date: "Aug 11", cpi: 105.80, del_bom: 103.9, del_blr: 105.1, bom_blr: 106.9, nonstop: 105.2, onestop: 107.0 },
    { date: "Aug 18", cpi: 106.50, del_bom: 104.8, del_blr: 106.2, bom_blr: 107.6, nonstop: 106.0, onestop: 107.8 },
    { date: "Aug 28", cpi: 107.55, del_bom: 106.4, del_blr: 107.8, bom_blr: 109.3, nonstop: 107.2, onestop: 109.4 },
  ],
  "3M": [
    { date: "Jun 01", cpi: 101.80, del_bom: 100.2, del_blr: 101.1, bom_blr: 102.4, nonstop: 101.2, onestop: 102.8 },
    { date: "Jun 20", cpi: 102.90, del_bom: 101.3, del_blr: 102.4, bom_blr: 103.8, nonstop: 102.4, onestop: 104.0 },
    { date: "Jul 10", cpi: 103.85, del_bom: 102.0, del_blr: 103.2, bom_blr: 104.9, nonstop: 103.2, onestop: 105.1 },
    { date: "Aug 01", cpi: 104.60, del_bom: 102.8, del_blr: 104.0, bom_blr: 105.6, nonstop: 104.0, onestop: 105.9 },
    { date: "Aug 28", cpi: 107.55, del_bom: 106.4, del_blr: 107.8, bom_blr: 109.3, nonstop: 107.2, onestop: 109.4 },
  ],
  "6M": [
    { date: "Mar 01", cpi: 99.40, del_bom: 98.8, del_blr: 99.2, bom_blr: 100.1, nonstop: 99.0, onestop: 100.2 },
    { date: "Apr 01", cpi: 100.80, del_bom: 99.9, del_blr: 100.5, bom_blr: 101.5, nonstop: 100.2, onestop: 101.8 },
    { date: "May 01", cpi: 101.50, del_bom: 100.4, del_blr: 101.0, bom_blr: 102.1, nonstop: 101.0, onestop: 102.4 },
    { date: "Jun 01", cpi: 101.80, del_bom: 100.2, del_blr: 101.1, bom_blr: 102.4, nonstop: 101.2, onestop: 102.8 },
    { date: "Jul 01", cpi: 103.20, del_bom: 101.5, del_blr: 102.8, bom_blr: 104.2, nonstop: 102.7, onestop: 104.5 },
    { date: "Aug 28", cpi: 107.55, del_bom: 106.4, del_blr: 107.8, bom_blr: 109.3, nonstop: 107.2, onestop: 109.4 },
  ],
  "1Y": [
    { date: "Sep 25", cpi: 100.00, del_bom: 100.0, del_blr: 100.0, bom_blr: 100.0, nonstop: 100.0, onestop: 100.0 },
    { date: "Dec 25", cpi: 102.30, del_bom: 101.5, del_blr: 102.0, bom_blr: 103.1, nonstop: 101.9, onestop: 103.0 },
    { date: "Mar 26", cpi: 104.10, del_bom: 103.2, del_blr: 103.9, bom_blr: 105.0, nonstop: 103.6, onestop: 105.2 },
    { date: "Jun 26", cpi: 105.60, del_bom: 104.5, del_blr: 105.2, bom_blr: 106.8, nonstop: 105.0, onestop: 107.1 },
    { date: "Aug 28", cpi: 107.55, del_bom: 106.4, del_blr: 107.8, bom_blr: 109.3, nonstop: 107.2, onestop: 109.4 },
  ],
};

// Aliases for backwards compatibility
TIME_SERIES_DATA["30D"] = TIME_SERIES_DATA["1M"];

export const SUB_INDICES = [
  { name: "Headline National CPI", code: "CPI_ALL", value: 107.55, change: "+2.84%", weight: "100.0%" },
  { name: "Domestic Non-Stop", code: "CPI_DIRECT", value: 107.20, change: "+2.60%", weight: "74.5%" },
  { name: "Connecting / 1-Stop", code: "CPI_CONNECT", value: 109.40, change: "+3.45%", weight: "25.5%" },
  { name: "Horizon T+0 (Walkup)", code: "CPI_H0", value: 114.80, change: "+5.12%", weight: "15.0%" },
  { name: "Horizon T+3 (Urgent)", code: "CPI_H3", value: 110.20, change: "+3.80%", weight: "20.0%" },
  { name: "Horizon T+7 (1-Week)", code: "CPI_H7", value: 108.90, change: "+2.95%", weight: "25.0%" },
  { name: "Horizon T+15 (Advance)", code: "CPI_H15", value: 105.40, change: "+1.90%", weight: "20.0%" },
  { name: "Horizon T+30 (Baseline)", code: "CPI_H30", value: 102.10, change: "+0.85%", weight: "20.0%" },
];

export const ROUTE_HEATMAP_DATA = [
  { route: "DEL–BOM", origin: "DEL", destination: "BOM", weight: 7.84, pax: "1.20M", avgFare: 6240, minFare: 4180, maxFare: 14870, medianFare: 5980, t0: 14870, t3: 9840, t7: 6920, t15: 4850, t30: 4180, cpi: 106.0, change: "+3.2%", distance: 1148, observations: 3420 },
  { route: "DEL–BLR", origin: "DEL", destination: "BLR", weight: 6.21, pax: "0.95M", avgFare: 6850, minFare: 4450, maxFare: 15420, medianFare: 6520, t0: 15420, t3: 10250, t7: 7420, t15: 5120, t30: 4450, cpi: 107.5, change: "+2.9%", distance: 1740, observations: 2980 },
  { route: "BOM–BLR", origin: "BOM", destination: "BLR", weight: 5.69, pax: "0.87M", avgFare: 5420, minFare: 3680, maxFare: 13150, medianFare: 5120, t0: 13150, t3: 8740, t7: 5980, t15: 4210, t30: 3680, cpi: 108.9, change: "+4.1%", distance: 842, observations: 2650 },
  { route: "DEL–HYD", origin: "DEL", destination: "HYD", weight: 5.10, pax: "0.78M", avgFare: 5910, minFare: 3950, maxFare: 13900, medianFare: 5650, t0: 13900, t3: 9150, t7: 6420, t15: 4620, t30: 3950, cpi: 105.8, change: "+1.8%", distance: 1253, observations: 2410 },
  { route: "DEL–CCU", origin: "DEL", destination: "CCU", weight: 4.84, pax: "0.74M", avgFare: 6380, minFare: 4120, maxFare: 14250, medianFare: 6050, t0: 14250, t3: 9480, t7: 6810, t15: 4790, t30: 4120, cpi: 108.2, change: "+3.5%", distance: 1305, observations: 2320 },
  { route: "BOM–HYD", origin: "BOM", destination: "HYD", weight: 4.25, pax: "0.65M", avgFare: 4950, minFare: 3450, maxFare: 12450, medianFare: 4720, t0: 12450, t3: 8120, t7: 5480, t15: 3980, t30: 3450, cpi: 104.9, change: "+1.2%", distance: 620, observations: 2150 },
  { route: "DEL–MAA", origin: "DEL", destination: "MAA", weight: 3.92, pax: "0.60M", avgFare: 7120, minFare: 4620, maxFare: 16100, medianFare: 6850, t0: 16100, t3: 10800, t7: 7850, t15: 5410, t30: 4620, cpi: 106.8, change: "+2.4%", distance: 1760, observations: 1980 },
  { route: "BOM–CCU", origin: "BOM", destination: "CCU", weight: 3.40, pax: "0.52M", avgFare: 6890, minFare: 4510, maxFare: 15800, medianFare: 6610, t0: 15800, t3: 10450, t7: 7620, t15: 5240, t30: 4510, cpi: 107.1, change: "+2.7%", distance: 1660, observations: 1840 },
  { route: "BLR–HYD", origin: "BLR", destination: "HYD", weight: 3.14, pax: "0.48M", avgFare: 4210, minFare: 2950, maxFare: 9850, medianFare: 3980, t0: 9850, t3: 6720, t7: 4620, t15: 3380, t30: 2950, cpi: 103.8, change: "+0.9%", distance: 500, observations: 1720 },
  { route: "DEL–GOI", origin: "DEL", destination: "GOI", weight: 2.94, pax: "0.45M", avgFare: 7850, minFare: 4950, maxFare: 17200, medianFare: 7420, t0: 17200, t3: 11950, t7: 8450, t15: 5820, t30: 4950, cpi: 109.1, change: "+5.2%", distance: 1515, observations: 1650 },
  { route: "BOM–MAA", origin: "BOM", destination: "MAA", weight: 2.81, pax: "0.43M", avgFare: 5240, minFare: 3620, maxFare: 12850, medianFare: 4980, t0: 12850, t3: 8450, t7: 5890, t15: 4150, t30: 3620, cpi: 105.2, change: "+1.5%", distance: 1030, observations: 1540 },
  { route: "BLR–CCU", origin: "BLR", destination: "CCU", weight: 2.61, pax: "0.40M", avgFare: 6420, minFare: 4280, maxFare: 15100, medianFare: 6150, t0: 15100, t3: 9980, t7: 7120, t15: 4950, t30: 4280, cpi: 107.8, change: "+3.1%", distance: 1540, observations: 1480 },
];

export const RAW_FLIGHT_OBSERVATIONS = [
  { id: "OBS-9481", collectedAt: "2026-08-28 10:30", travelDate: "2026-09-04", origin: "DEL", destination: "BOM", airline: "IndiGo", flightNumber: "6E-204", depTime: "06:15", arrTime: "08:35", stops: "Non-stop", fareType: "Economy Saver", baseFare: 5420, taxes: 820, totalFare: 6240, source: "IndiGo Direct API", status: "Valid" },
  { id: "OBS-9482", collectedAt: "2026-08-28 10:30", travelDate: "2026-09-04", origin: "DEL", destination: "BOM", airline: "Air India", flightNumber: "AI-805", depTime: "07:00", arrTime: "09:15", stops: "Non-stop", fareType: "Economy Flex", baseFare: 5950, taxes: 910, totalFare: 6860, source: "MakeMyTrip OTA", status: "Valid" },
  { id: "OBS-9483", collectedAt: "2026-08-28 10:30", travelDate: "2026-09-04", origin: "DEL", destination: "BLR", airline: "Vistara", flightNumber: "UK-811", depTime: "08:30", arrTime: "11:15", stops: "Non-stop", fareType: "Standard", baseFare: 6120, taxes: 940, totalFare: 7060, source: "EaseMyTrip", status: "Valid" },
  { id: "OBS-9484", collectedAt: "2026-08-28 10:29", travelDate: "2026-08-28", origin: "DEL", destination: "BOM", airline: "Akasa Air", flightNumber: "QP-1102", depTime: "14:20", arrTime: "16:40", stops: "Non-stop", fareType: "Same-Day Walkup", baseFare: 13200, taxes: 1670, totalFare: 14870, source: "Akasa Web", status: "Valid" },
  { id: "OBS-9485", collectedAt: "2026-08-28 10:28", travelDate: "2026-09-12", origin: "BOM", destination: "BLR", airline: "IndiGo", flightNumber: "6E-5338", depTime: "10:15", arrTime: "11:55", stops: "Non-stop", fareType: "Advance Discount", baseFare: 3680, taxes: 530, totalFare: 4210, source: "IndiGo Direct API", status: "Valid" },
  { id: "OBS-9486", collectedAt: "2026-08-28 10:27", travelDate: "2026-09-01", origin: "DEL", destination: "GOI", airline: "SpiceJet", flightNumber: "SG-8169", depTime: "09:45", arrTime: "12:20", stops: "Non-stop", fareType: "Holiday Fare", baseFare: 7350, taxes: 1100, totalFare: 8450, source: "Yatra OTA", status: "Valid" },
  { id: "OBS-9487", collectedAt: "2026-08-28 10:26", travelDate: "2026-09-04", origin: "DEL", destination: "CCU", airline: "Air India Express", flightNumber: "IX-924", depTime: "17:10", arrTime: "19:25", stops: "Non-stop", fareType: "Standard", baseFare: 5540, taxes: 840, totalFare: 6380, source: "Air India Direct", status: "Valid" },
  { id: "OBS-9488", collectedAt: "2026-08-28 10:25", travelDate: "2026-08-31", origin: "BLR", destination: "HYD", airline: "IndiGo", flightNumber: "6E-412", depTime: "19:00", arrTime: "20:10", stops: "Non-stop", fareType: "Standard", baseFare: 4050, taxes: 570, totalFare: 4620, source: "IndiGo Direct API", status: "Valid" },
  { id: "OBS-9489", collectedAt: "2026-08-28 10:24", travelDate: "2026-09-27", origin: "DEL", destination: "BOM", airline: "Vistara", flightNumber: "UK-995", depTime: "10:20", arrTime: "12:35", stops: "Non-stop", fareType: "Super Saver 30D", baseFare: 3620, taxes: 560, totalFare: 4180, source: "Vistara Direct", status: "Valid" },
  { id: "OBS-9490", collectedAt: "2026-08-28 10:22", travelDate: "2026-09-04", origin: "DEL", destination: "BOM", airline: "IndiGo", flightNumber: "6E-102", depTime: "04:50", arrTime: "07:05", stops: "1 stop (AMD)", fareType: "Connecting", baseFare: 6850, taxes: 1040, totalFare: 7890, source: "MakeMyTrip OTA", status: "Valid" },
  { id: "OBS-9491", collectedAt: "2026-08-28 10:20", travelDate: "2026-09-04", origin: "BOM", destination: "CCU", airline: "Air India", flightNumber: "AI-772", depTime: "11:45", arrTime: "14:20", stops: "Non-stop", fareType: "Standard", baseFare: 6620, taxes: 1000, totalFare: 7620, source: "Air India Direct", status: "Valid" },
  { id: "OBS-9492", collectedAt: "2026-08-28 10:18", travelDate: "2026-09-04", origin: "DEL", destination: "MAA", airline: "IndiGo", flightNumber: "6E-2191", depTime: "15:30", arrTime: "18:20", stops: "Non-stop", fareType: "Standard", baseFare: 6850, taxes: 1000, totalFare: 7850, source: "IndiGo Direct API", status: "Valid" },
  { id: "OBS-9493", collectedAt: "2026-08-28 10:15", travelDate: "2026-09-04", origin: "DEL", destination: "BOM", airline: "SpiceJet", flightNumber: "SG-152", depTime: "18:15", arrTime: "20:30", stops: "Non-stop", fareType: "Flash Promo", baseFare: 299, taxes: 850, totalFare: 1149, source: "Yatra OTA", status: "Flagged (anomaly)" },
  { id: "OBS-9494", collectedAt: "2026-08-28 10:12", travelDate: "2026-09-04", origin: "BLR", destination: "DEL", airline: "Akasa Air", flightNumber: "QP-1354", depTime: "21:00", arrTime: "23:45", stops: "Non-stop", fareType: "Standard", baseFare: 6450, taxes: 970, totalFare: 7420, source: "Akasa Web", status: "Valid" },
];

export const METHODOLOGY_STEPS = [
  { n: 1, title: "Data Collection", desc: "Fare observations collected from airline APIs, OTA portals and GDS feeds via modular adapters with timestamps and source provenance." },
  { n: 2, title: "Data Cleaning & Quarantine", desc: "Duplicates, zero-fares, impossible pricing outliers, and invalid airport codes are quarantined via Tukey IQR anomaly detection." },
  { n: 3, title: "Fare Normalization", desc: "Fares are standardized to a common INR tax-inclusive total price with consistent fare-type classification (Economy Saver, Flex, Walkup)." },
  { n: 4, title: "Route Classification", desc: "Observations are mapped into directional origin–destination route pairs with distance, frequency, and airport cluster metadata." },
  { n: 5, title: "DGCA Weight Assignment", desc: "Each route receives a normalized weight reflecting official DGCA passenger volume shares, ensuring high-density corridors guide the index." },
  { n: 6, title: "Elementary Jevons Index", desc: "Unweighted geometric mean of price relatives is computed per route and booking horizon against the 2024 baseline period." },
  { n: 7, title: "Laspeyres National Aggregation", desc: "Upper-level macro index is synthesized using fixed DGCA passenger basket weights across all 25 corridors and 5 horizons." },
  { n: 8, title: "Quality Audit & Release", desc: "Completeness, staleness, and volatility threshold evaluations run prior to publishing official provisional bulletins." },
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
      index_date: "2026-08-28",
      base_period: "2024 = 100",
      headline_cpi: 107.55,
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
      timestamp: "2026-08-28T10:30:00Z",
    },
  },
  {
    method: "POST",
    path: "/api/v1/scraper/trigger",
    description: "Manually triggers an end-to-end data ingestion, validation, and Jevons recomputation cycle.",
    response: {
      status: "SUCCESS",
      cycle_id: "CYC-20260828-09",
      quotes_scraped: 580,
      validated_clean: 574,
      flagged_iqr: 6,
      recomputed_cpi: 107.55,
      execution_time_ms: 382,
    },
  },
];

// Explicit export alias for network graph visualization
export const NETWORK_ROUTES = ROUTE_HEATMAP_DATA;
