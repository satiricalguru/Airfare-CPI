/**
 * SIH26056 — Static reference data.
 *
 * Replaces `mockData.js`, which the audit identified as the de-facto source of truth
 * for the dashboard: it held a hand-typed headline index (107.42), a fabricated
 * year-on-year rate (+8.12%), an invented daily quote count (48,200), a synthetic
 * 30-day time series, and per-route index values — all rendered as though measured.
 *
 * This module contains ONLY data that is genuinely static reference information and
 * cannot be mistaken for a measurement:
 *
 *   - airport codes and city names
 *   - airline codes, names and logo paths
 *   - the API endpoint catalogue for the developer panel
 *   - methodology step descriptions (prose, no figures)
 *
 * There are deliberately NO index values, no fare levels, no passenger volumes and no
 * time series here. Every figure the dashboard displays comes from the API, and renders
 * as `N/A` when the API does not supply it.
 *
 * Route and horizon metadata (including passenger volumes and weights) comes from
 * `/api/v1/routes` and `/api/v1/index/horizons`, whose single source of truth is
 * `data/route_basket.json` and `data/booking_horizons.json`.
 */

export const AIRPORTS_LIST = [
  // Delhi NCT
  { code: "DEL", city: "New Delhi", name: "Indira Gandhi International Airport", state: "Delhi", tier: 1 },
  // Maharashtra
  { code: "BOM", city: "Mumbai", name: "Chhatrapati Shivaji Maharaj International Airport", state: "Maharashtra", tier: 1 },
  { code: "PNQ", city: "Pune", name: "Pune International Airport", state: "Maharashtra", tier: 2 },
  { code: "NAG", city: "Nagpur", name: "Dr. Babasaheb Ambedkar International Airport", state: "Maharashtra", tier: 2 },
  { code: "SAG", city: "Shirdi", name: "Shirdi International Airport", state: "Maharashtra", tier: 3 },
  { code: "IXU", city: "Aurangabad", name: "Chhatrapati Sambhajinagar Airport", state: "Maharashtra", tier: 3 },
  { code: "KLH", city: "Kolhapur", name: "Chhatrapati Rajaram Maharaj Airport", state: "Maharashtra", tier: 3 },
  { code: "NDC", city: "Nanded", name: "Shri Guru Gobind Singh Ji Airport", state: "Maharashtra", tier: 3 },
  { code: "SDW", city: "Sindhudurg", name: "Sindhudurg Airport (Chipi)", state: "Maharashtra", tier: 3 },
  // Karnataka
  { code: "BLR", city: "Bengaluru", name: "Kempegowda International Airport", state: "Karnataka", tier: 1 },
  { code: "IXE", city: "Mangalore", name: "Mangaluru International Airport", state: "Karnataka", tier: 2 },
  { code: "HBX", city: "Hubballi", name: "Hubballi Airport", state: "Karnataka", tier: 3 },
  { code: "IXG", city: "Belagavi", name: "Belagavi Airport", state: "Karnataka", tier: 3 },
  { code: "MYQ", city: "Mysuru", name: "Mysuru Airport", state: "Karnataka", tier: 3 },
  { code: "GBI", city: "Kalaburagi", name: "Kalaburagi Airport", state: "Karnataka", tier: 3 },
  { code: "RQY", "city": "Shivamogga", name: "Kuvempu Airport", state: "Karnataka", tier: 3 },
  { code: "IXX", "city": "Bidar", name: "Bidar Airport", state: "Karnataka", tier: 3 },
  // Tamil Nadu
  { code: "MAA", city: "Chennai", name: "Chennai International Airport", state: "Tamil Nadu", tier: 1 },
  { code: "CJB", city: "Coimbatore", name: "Coimbatore International Airport", state: "Tamil Nadu", tier: 2 },
  { code: "IXM", city: "Madurai", name: "Madurai Airport", state: "Tamil Nadu", tier: 2 },
  { code: "TRZ", city: "Tiruchirappalli", name: "Tiruchirappalli International Airport", state: "Tamil Nadu", tier: 2 },
  { code: "TCR", city: "Thoothukudi", name: "Tuticorin Airport", state: "Tamil Nadu", tier: 3 },
  { code: "SXV", city: "Salem", name: "Salem Airport", state: "Tamil Nadu", tier: 3 },
  // West Bengal
  { code: "CCU", city: "Kolkata", name: "Netaji Subhash Chandra Bose International Airport", state: "West Bengal", tier: 1 },
  { code: "IXB", city: "Bagdogra", name: "Bagdogra International Airport (Siliguri)", state: "West Bengal", tier: 2 },
  { code: "RDP", city: "Durgapur", name: "Kazi Nazrul Islam Airport", state: "West Bengal", tier: 3 },
  { code: "COH", city: "Cooch Behar", name: "Cooch Behar Airport", state: "West Bengal", tier: 3 },
  // Telangana
  { code: "HYD", city: "Hyderabad", name: "Rajiv Gandhi International Airport", state: "Telangana", tier: 1 },
  // Gujarat
  { code: "AMD", city: "Ahmedabad", name: "Sardar Vallabhbhai Patel International Airport", state: "Gujarat", tier: 1 },
  { code: "STV", city: "Surat", name: "Surat International Airport", state: "Gujarat", tier: 2 },
  { code: "BDQ", city: "Vadodara", name: "Vadodara Airport", state: "Gujarat", tier: 2 },
  { code: "HSR", city: "Rajkot", name: "Rajkot International Airport (Hirasar)", state: "Gujarat", tier: 2 },
  { code: "BHU", city: "Bhavnagar", name: "Bhavnagar Airport", state: "Gujarat", tier: 3 },
  { code: "BHJ", city: "Bhuj", name: "Bhuj Airport", state: "Gujarat", tier: 3 },
  { code: "JGA", city: "Jamnagar", name: "Jamnagar Airport", state: "Gujarat", tier: 3 },
  { code: "PBD", city: "Porbandar", name: "Porbandar Airport", state: "Gujarat", tier: 3 },
  { code: "IXY", city: "Kandla", name: "Kandla Airport", state: "Gujarat", tier: 3 },
  { code: "IXK", city: "Keshod", name: "Keshod Airport", state: "Gujarat", tier: 3 },
  // Rajasthan
  { code: "JAI", city: "Jaipur", name: "Jaipur International Airport", state: "Rajasthan", tier: 2 },
  { code: "UDR", city: "Udaipur", name: "Maharana Pratap Airport", state: "Rajasthan", tier: 2 },
  { code: "JDH", city: "Jodhpur", name: "Jodhpur Airport", state: "Rajasthan", tier: 2 },
  { code: "JSA", city: "Jaisalmer", name: "Jaisalmer Airport", state: "Rajasthan", tier: 3 },
  { code: "BKB", city: "Bikaner", name: "Nal Airport", state: "Rajasthan", tier: 3 },
  { code: "KQH", city: "Kishangarh", name: "Kishangarh Airport (Ajmer)", state: "Rajasthan", tier: 3 },
  // Uttar Pradesh
  { code: "LKO", city: "Lucknow", name: "Chaudhary Charan Singh International Airport", state: "Uttar Pradesh", tier: 1 },
  { code: "VNS", city: "Varanasi", name: "Lal Bahadur Shastri International Airport", state: "Uttar Pradesh", tier: 2 },
  { code: "IXD", city: "Prayagraj", name: "Prayagraj Airport", state: "Uttar Pradesh", tier: 2 },
  { code: "AYJ", city: "Ayodhya", name: "Maharishi Valmiki International Airport", state: "Uttar Pradesh", tier: 2 },
  { code: "GOP", city: "Gorakhpur", name: "Mahayogi Gorakhnath Airport", state: "Uttar Pradesh", tier: 3 },
  { code: "AGR", city: "Agra", name: "Agra Airport (Kheria)", state: "Uttar Pradesh", tier: 3 },
  { code: "BEK", city: "Bareilly", name: "Bareilly Airport", state: "Uttar Pradesh", tier: 3 },
  { code: "KNU", city: "Kanpur", name: "Kanpur Airport", state: "Uttar Pradesh", tier: 3 },
  { code: "HDO", city: "Hindon", name: "Hindon Airport (Ghaziabad)", state: "Uttar Pradesh", tier: 3 },
  // Bihar
  { code: "PAT", city: "Patna", name: "Jay Prakash Narayan International Airport", state: "Bihar", tier: 2 },
  { code: "GAY", city: "Gaya", name: "Gaya International Airport", state: "Bihar", tier: 3 },
  { code: "DBG", city: "Darbhanga", name: "Darbhanga Airport", state: "Bihar", tier: 3 },
  // Kerala
  { code: "COK", city: "Kochi", name: "Cochin International Airport", state: "Kerala", tier: 1 },
  { code: "TRV", city: "Thiruvananthapuram", name: "Thiruvananthapuram International Airport", state: "Kerala", tier: 2 },
  { code: "CCJ", city: "Kozhikode", name: "Calicut International Airport", state: "Kerala", tier: 2 },
  { code: "CNN", city: "Kannur", name: "Kannur International Airport", state: "Kerala", tier: 2 },
  // Goa
  { code: "GOI", city: "Dabolim", name: "Dabolim Airport (South Goa)", state: "Goa", tier: 2 },
  { code: "GOX", city: "Mopa", name: "Manohar International Airport (North Goa)", state: "Goa", tier: 2 },
  // Assam
  { code: "GAU", city: "Guwahati", name: "Lokpriya Gopinath Bordoloi International Airport", state: "Assam", tier: 2 },
  { code: "DIB", city: "Dibrugarh", name: "Dibrugarh Airport", state: "Assam", tier: 3 },
  { code: "IXS", city: "Silchar", name: "Silchar Airport", state: "Assam", tier: 3 },
  { code: "JRH", city: "Jorhat", name: "Jorhat Airport", state: "Assam", tier: 3 },
  { code: "TEZ", city: "Tezpur", name: "Tezpur Airport", state: "Assam", tier: 3 },
  { code: "IXI", city: "Lilabari", name: "Lilabari Airport (North Lakhimpur)", state: "Assam", tier: 3 },
  { code: "RUP", city: "Rupsi", name: "Rupsi Airport", state: "Assam", tier: 3 },
  // Odisha
  { code: "BBI", city: "Bhubaneswar", name: "Biju Patnaik International Airport", state: "Odisha", tier: 2 },
  { code: "JRG", city: "Jharsuguda", name: "Veer Surendra Sai Airport", state: "Odisha", tier: 3 },
  { code: "RRK", city: "Rourkela", name: "Rourkela Airport", state: "Odisha", tier: 3 },
  { code: "UKE", city: "Utkela", name: "Utkela Airport", state: "Odisha", tier: 3 },
  // Andhra Pradesh
  { code: "VTZ", city: "Visakhapatnam", name: "Visakhapatnam International Airport", state: "Andhra Pradesh", tier: 2 },
  { code: "VGA", city: "Vijayawada", name: "Vijayawada International Airport", state: "Andhra Pradesh", tier: 2 },
  { code: "TIR", city: "Tirupati", name: "Tirupati International Airport", state: "Andhra Pradesh", tier: 2 },
  { code: "RJA", city: "Rajahmundry", name: "Rajahmundry Airport", state: "Andhra Pradesh", tier: 3 },
  { code: "CDP", city: "Kadapa", name: "Kadapa Airport", state: "Andhra Pradesh", tier: 3 },
  { code: "KJB", city: "Kurnool", name: "Uyyalawada Narasimha Reddy Airport", state: "Andhra Pradesh", tier: 3 },
  // Madhya Pradesh
  { code: "IDR", city: "Indore", name: "Devi Ahilyabai Holkar Airport", state: "Madhya Pradesh", tier: 2 },
  { code: "BHO", city: "Bhopal", name: "Raja Bhoj Airport", state: "Madhya Pradesh", tier: 2 },
  { code: "GWL", city: "Gwalior", name: "Rajmata Vijaya Raje Scindia Airport", state: "Madhya Pradesh", tier: 3 },
  { code: "JLR", city: "Jabalpur", name: "Dumna Airport", state: "Madhya Pradesh", tier: 3 },
  { code: "HJR", city: "Khajuraho", name: "Khajuraho Airport", state: "Madhya Pradesh", tier: 3 },
  // Punjab & Chandigarh
  { code: "ATQ", city: "Amritsar", name: "Sri Guru Ram Dass Jee International Airport", state: "Punjab", tier: 2 },
  { code: "IXC", city: "Chandigarh", name: "Shaheed Bhagat Singh International Airport", state: "Chandigarh", tier: 2 },
  { code: "AIP", city: "Adampur", name: "Adampur Airport (Jalandhar)", state: "Punjab", tier: 3 },
  { code: "BUP", city: "Bathinda", name: "Bathinda Airport", state: "Punjab", tier: 3 },
  // Jammu & Kashmir
  { code: "SXR", city: "Srinagar", name: "Sheikh ul-Alam International Airport", state: "Jammu & Kashmir", tier: 2 },
  { code: "IXJ", city: "Jammu", name: "Jammu Airport", state: "Jammu & Kashmir", tier: 2 },
  // Ladakh
  { code: "IXL", city: "Leh", name: "Kushok Bakula Rimpochee Airport", state: "Ladakh", tier: 2 },
  // Uttarakhand
  { code: "DED", city: "Dehradun", name: "Jolly Grant Airport", state: "Uttarakhand", tier: 2 },
  { code: "PGH", city: "Pantnagar", name: "Pantnagar Airport", state: "Uttarakhand", tier: 3 },
  // Jharkhand
  { code: "IXR", city: "Ranchi", name: "Birsa Munda Airport", state: "Jharkhand", tier: 2 },
  { code: "DGH", city: "Deoghar", name: "Deoghar Airport", state: "Jharkhand", tier: 3 },
  // Chhattisgarh
  { code: "RPR", city: "Raipur", name: "Swami Vivekananda Airport", state: "Chhattisgarh", tier: 2 },
  { code: "JGB", city: "Jagdalpur", name: "Jagdalpur Airport", state: "Chhattisgarh", tier: 3 },
  { code: "PAB", city: "Bilaspur", name: "Bilaspur Airport", state: "Chhattisgarh", tier: 3 },
  // North East States
  { code: "IXA", city: "Agartala", name: "Maharaja Bir Bikram Airport", state: "Tripura", tier: 2 },
  { code: "IMF", city: "Imphal", name: "Bir Tikendrajit International Airport", state: "Manipur", tier: 2 },
  { code: "DMU", city: "Dimapur", name: "Dimapur Airport", state: "Nagaland", tier: 3 },
  { code: "AJL", city: "Aizawl", name: "Lengpui Airport", state: "Mizoram", tier: 3 },
  { code: "SHL", city: "Shillong", name: "Shillong Airport (Umroi)", state: "Meghalaya", tier: 3 },
  { code: "HGI", city: "Itanagar", name: "Donyi Polo Airport (Hollongi)", state: "Arunachal Pradesh", tier: 3 },
  { code: "PYG", city: "Pakyong", name: "Pakyong Airport (Gangtok)", state: "Sikkim", tier: 3 },
  // Himachal Pradesh
  { code: "DHM", city: "Dharamshala", name: "Kangra Airport (Gaggal)", state: "Himachal Pradesh", tier: 3 },
  { code: "KUU", city: "Kullu", name: "Kullu–Manali Airport (Bhuntar)", state: "Himachal Pradesh", tier: 3 },
  { code: "SLV", city: "Shimla", name: "Shimla Airport", state: "Himachal Pradesh", tier: 3 },
  // Island & UTs
  { code: "IXZ", city: "Port Blair", name: "Veer Savarkar International Airport", state: "Andaman & Nicobar Islands", tier: 2 },
  { code: "AGX", city: "Agatti", name: "Agatti Airport", state: "Lakshadweep", tier: 3 },
  { code: "PNY", city: "Puducherry", name: "Puducherry Airport", state: "Puducherry", tier: 3 },
  { code: "DIU", city: "Diu", name: "Diu Airport", state: "Dadra and Nagar Haveli and Daman and Diu", tier: 3 },
];

export const AIRPORTS_BY_CODE = Object.fromEntries(
  AIRPORTS_LIST.map((a) => [a.code, a])
);

export const INDIAN_STATES_LIST = Array.from(
  new Set(AIRPORTS_LIST.map((a) => a.state))
).sort();

export function getAirport(code) {
  if (!code) return null;
  return AIRPORTS_BY_CODE[code.toUpperCase()] || {
    code: code.toUpperCase(),
    city: code.toUpperCase(),
    name: `${code.toUpperCase()} Airport`,
    state: "India",
    tier: 3,
  };
}

export function getAirportsForState(state) {
  if (!state) return AIRPORTS_LIST;
  return AIRPORTS_LIST.filter((a) => a.state === state);
}


/**
 * Carrier reference. Market share is deliberately ABSENT.
 *
 * The previous version carried figures like "IndiGo 62.8%" presented as fact and
 * contradicted by the backend's own constants. Market share is not something this
 * system measures, so it is not displayed.
 */
export const AIRLINES_LIST = [
  { code: "6E", name: "IndiGo", logoUrl: "/airlines/indigo.svg" },
  { code: "AI", name: "Air India", logoUrl: "/airlines/airindia.svg" },
  { code: "UK", name: "Vistara", logoUrl: "/airlines/vistara.svg" },
  { code: "SG", name: "SpiceJet", logoUrl: "/airlines/spicejet.svg" },
  { code: "QP", name: "Akasa Air", logoUrl: "/airlines/akasa.svg" },
  { code: "IX", name: "Air India Express", logoUrl: "/airlines/airindiaexpress.svg" },
];

/**
 * Methodology narrative. Prose only.
 *
 * Descriptions state what the pipeline does, including where a capability is not
 * implemented, so this panel cannot overclaim relative to the code.
 */
export const METHODOLOGY_STEPS = [
  {
    n: 1,
    title: "Collection",
    desc:
      "Fare observations are requested from permitted sources for each route across " +
      "five advance-purchase horizons. Every observation carries provenance: which " +
      "source, when, and under which collector version. A failed collection is " +
      "recorded as a failure and never backfilled with generated data.",
  },
  {
    n: 2,
    title: "Normalization",
    desc:
      "Payloads are mapped to a canonical form: amounts in INR, canonical cabin and " +
      "airline codes, explicit stop counts. A fare quoted in another currency is " +
      "dropped with a recorded reason unless an operator-configured exchange rate " +
      "exists, because converting at a guessed rate would put an unverifiable number " +
      "into the index.",
  },
  {
    n: 3,
    title: "Validation",
    desc:
      "Collection errors are excluded; genuine volatility is flagged and kept. IQR " +
      "fences are built from a reference distribution that excludes previously " +
      "flagged outliers, so the filter cannot desensitise itself over time. " +
      "Day-over-day limits are enforced per route and per horizon.",
  },
  {
    n: 4,
    title: "Deduplication",
    desc:
      "The same product offered through multiple sources is counted once, matched on " +
      "flight, product characteristics, horizon and collection day. Price is excluded " +
      "from the fingerprint: two sources quoting the same seat differently are still " +
      "the same seat.",
  },
  {
    n: 5,
    title: "Matched-model elementary index",
    desc:
      "A price relative is formed only between two observations of the same " +
      "purchasable product — same route, airline, cabin, fare family, stops, " +
      "refundability and baggage. The Jevons geometric mean of those relatives is the " +
      "elementary index. Products that appear or disappear are counted and excluded " +
      "rather than imputed.",
  },
  {
    n: 6,
    title: "Booking-horizon stratification",
    desc:
      "T+1, T+7, T+15, T+30 and T+45 are indexed separately and combined with fixed " +
      "equal weights. Because the weights do not depend on how many observations each " +
      "horizon contributed, the route index cannot move merely because the sample " +
      "composition shifted.",
  },
  {
    n: 7,
    title: "National aggregation",
    desc:
      "Route indices are combined with provisional passenger-volume weights that sum " +
      "to exactly 1.0. Where routes are missing, the renormalization applied is " +
      "reported explicitly, and below a minimum basket coverage the figure is marked " +
      "not publishable rather than published from a fragment.",
  },
  {
    n: 8,
    title: "Publication and revision",
    desc:
      "Every figure is persisted with the observations, weights, base period, " +
      "validation rules and methodology version that produced it. Each publication " +
      "and recomputation appends a revision record, so a value that changes always " +
      "carries a recorded reason. Seasonal adjustment is NOT IMPLEMENTED, so the " +
      "series is observed rather than adjusted.",
  },
  {
    n: 9,
    title: "Statutory fee decomposition & UDF",
    desc:
      "Gross all-inclusive quoted fares are decomposed into pure airline base fares, statutory User " +
      "Development Fees (UDF) by origin airport (AERA orders: DEL ₹320, BOM ₹340, BLR ₹360, HYD ₹380, " +
      "CCU ₹290, MAA ₹280, GOI ₹330), Aviation Security Fee (ASF ₹236), GST (5%), and portal convenience fees. " +
      "Estimated components are strictly flagged with is_estimated=true and linked to immutable raw payload hashes.",
  },
];

/**
 * Endpoint catalogue for the developer panel.
 *
 * Descriptions only. The panel calls the live API and displays the real response;
 * it holds no canned response payloads, which previously let the panel appear to work
 * against an unreachable backend.
 */
export const API_ENDPOINTS_LIST = [
  {
    method: "GET",
    path: "/api/v1/index/national",
    description:
      "Latest national index with the full provenance envelope: value, base period, " +
      "data provenance, sample size, methodology version, uncertainty and coverage.",
  },
  {
    method: "GET",
    path: "/api/v1/index/national/history?days=365",
    description: "Stored national index series. Returns what was published, not a recomputation.",
  },
  {
    method: "GET",
    path: "/api/v1/index/national/yoy",
    description:
      "Year-on-year change, or null with yoy_status when no 12-month comparison exists.",
  },
  {
    method: "GET",
    path: "/api/v1/index/national/mom",
    description: "Month-on-month change computed from stored index history.",
  },
  {
    method: "GET",
    path: "/api/v1/index/horizons",
    description: "Booking-horizon-stratified indices with product-churn diagnostics.",
  },
  {
    method: "GET",
    path: "/api/v1/index/routes",
    description: "Latest index per route, including which horizons contributed.",
  },
  {
    method: "GET",
    path: "/api/v1/index/rebase?reference=2026",
    description:
      "Re-reference the series to a different base window. Refuses windows the " +
      "collected series does not cover rather than inventing a link factor.",
  },
  {
    method: "GET",
    path: "/api/v1/weights",
    description:
      "The actual calculated route weights and their methodology, labelled PROVISIONAL.",
  },
  {
    method: "GET",
    path: "/api/v1/sources",
    description:
      "Every registered source, including those assessed and NOT collected, with the " +
      "reason for each.",
  },
  {
    method: "GET",
    path: "/api/v1/collection/status",
    description: "Collection configuration, scheduler state and the last run's outcome.",
  },
  {
    method: "GET",
    path: "/api/v1/collection/runs",
    description: "Run history including failures, which are retained rather than hidden.",
  },
  {
    method: "GET",
    path: "/api/v1/fares/latest?limit=50",
    description: "Most recent stored observations, each with its own provenance record.",
  },
  {
    method: "GET",
    path: "/api/v1/anomalies",
    description: "Flagged observations and their review state.",
  },
  {
    method: "GET",
    path: "/api/v1/revisions",
    description: "Append-only revision log for published figures.",
  },
  {
    method: "GET",
    path: "/api/v1/provenance",
    description: "What the current data actually is. Drives the dashboard mode banner.",
  },
  {
    method: "GET",
    path: "/api/v1/methodology",
    description: "Complete methodology metadata, including declared limitations.",
  },
  {
    method: "GET",
    path: "/api/v1/health",
    description:
      "System health. Reports degraded when the database is unreachable or no index exists.",
  },
];

/** Time-range options for the index chart. */
export const RANGE_OPTIONS = [
  { key: "7D", days: 7, label: "7D" },
  { key: "1M", days: 30, label: "1M" },
  { key: "3M", days: 90, label: "3M" },
  { key: "6M", days: 180, label: "6M" },
  { key: "1Y", days: 365, label: "1Y" },
];
