/**
 * SIH26056 — API client and data-mode resolution.
 *
 * The only place the dashboard talks to the backend, and the only place the
 * dashboard's honesty contract is enforced:
 *
 *   1. There is NO mock fallback. When a value is unavailable this module returns
 *      `null`, and the UI renders `N/A` with an explanation. It never substitutes a
 *      plausible-looking constant, because on screen a fabricated fallback is
 *      indistinguishable from a measurement.
 *   2. Every payload carries the backend's `data_provenance`, which resolves to one
 *      of the four modes in `DATA_MODE`. That drives a persistent, prominent banner —
 *      not a tooltip.
 *
 * The audit found the previous version doing the opposite: `totalObs || 48200`,
 * `?? 574`, `"96.4%"`, `anomalyCount = 6`, and a `BASE_FACTORS` lookup table that
 * supplied a constant month-on-month rate per base year. All of it is gone.
 */

const RAW_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE = RAW_BASE.replace(/\/api\/v1\/?$/, "").replace(/\/$/, "");

/** Display modes. These strings are what the banner renders, verbatim. */
export const DATA_MODE = {
  LIVE: "LIVE DATA",
  SIMULATED: "SIMULATED DATA",
  OFFLINE: "OFFLINE PREVIEW",
  UNAVAILABLE: "SOURCE UNAVAILABLE",
  DISCONNECTED: "BACKEND UNREACHABLE",
};

/** Value rendered wherever a figure is genuinely unavailable. */
export const NOT_AVAILABLE = "N/A";

const DEFAULT_TIMEOUT_MS = 25000;

/**
 * Map a backend `data_provenance` block onto a display mode.
 *
 * A missing or null `source_type` means there is no data, which resolves to
 * SOURCE UNAVAILABLE rather than to any data label.
 */
export function resolveDataMode(provenance) {
  const sourceType = provenance?.source_type;
  if (sourceType === "live") return DATA_MODE.LIVE;
  if (sourceType === "simulated") return DATA_MODE.SIMULATED;
  if (sourceType === "offline") return DATA_MODE.OFFLINE;
  return DATA_MODE.UNAVAILABLE;
}

/** True only for genuinely collected observations. */
export function isRealData(mode) {
  return mode === DATA_MODE.LIVE;
}

/**
 * Fetch JSON from the backend.
 *
 * Returns `{ ok, data, error, status }`. Never throws, and never returns
 * substitute data on failure — an error is reported as an error.
 */
export async function apiGet(path, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  if (!API_BASE) {
    return {
      ok: false,
      data: null,
      status: 0,
      error: "NEXT_PUBLIC_API_URL is not configured, so no backend can be reached.",
    };
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: AbortSignal.timeout(timeoutMs),
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      return {
        ok: false,
        data: null,
        status: response.status,
        error: `The API returned HTTP ${response.status} for ${path}.`,
      };
    }

    return { ok: true, data: await response.json(), status: response.status, error: null };
  } catch (err) {
    return {
      ok: false,
      data: null,
      status: 0,
      error: `Could not reach ${path}: ${err?.name === "TimeoutError" ? "request timed out" : err?.message || "network error"}.`,
    };
  }
}

/** POST JSON to the backend. Same no-fallback contract as {@link apiGet}. */
export async function apiPost(path, body, { timeoutMs = 60000, adminToken = "" } = {}) {
  if (!API_BASE) {
    return {
      ok: false,
      data: null,
      status: 0,
      error: "NEXT_PUBLIC_API_URL is not configured, so no backend can be reached.",
    };
  }

  const headers = { "Content-Type": "application/json", Accept: "application/json" };
  if (adminToken) headers["X-Admin-Token"] = adminToken;

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body ?? {}),
      signal: AbortSignal.timeout(timeoutMs),
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      return {
        ok: false,
        data,
        status: response.status,
        error:
          data?.detail ||
          `The API returned HTTP ${response.status} for ${path}.`,
      };
    }

    return { ok: true, data, status: response.status, error: null };
  } catch (err) {
    return {
      ok: false,
      data: null,
      status: 0,
      error: `Could not reach ${path}: ${err?.message || "network error"}.`,
    };
  }
}

/**
 * The shape the dashboard consumes.
 *
 * Every numeric field is `null` when unavailable. Nothing here has a default that
 * could be mistaken for a measurement.
 */
export function emptyDashboardState(mode = DATA_MODE.DISCONNECTED, reason = null) {
  return {
    connected: false,
    mode,
    reason,
    provenance: null,
    isOfficialStatistic: false,

    headlineIndex: null,
    indexDate: null,
    basePeriod: null,
    momChangePct: null,
    momStatus: null,
    yoyChangePct: null,
    yoyStatus: null,
    sampleSize: null,
    matchedProducts: null,
    routesIncluded: null,
    routesInBasket: null,
    coverageWeight: null,
    isPublishable: null,
    suppressionReason: null,
    standardError: null,
    confidenceLow: null,
    confidenceHigh: null,
    uncertaintyBasis: null,
    seasonalAdjustment: null,
    methodologyVersion: null,

    history: [],
    routeIndices: [],
    horizonIndices: [],
    horizonPolicy: null,
    observations: [],
    observationStats: null,
    anomalyCount: null,
    openAnomalyCount: null,
    validPct: null,
    collectionStatus: null,
    lastRun: null,
    sources: [],
    weights: null,
    lastUpdated: null,
  };
}

/**
 * Load everything the dashboard needs, in parallel.
 *
 * A failed sub-request leaves its slice null rather than failing the whole load, so
 * the dashboard degrades field by field with each gap visible.
 */
export async function loadDashboard() {
  const health = await apiGet("/api/v1/health");

  if (!health.ok) {
    return emptyDashboardState(
      DATA_MODE.DISCONNECTED,
      health.error ||
        "The backend is unreachable. No figures are shown because none are available; " +
          "placeholder values are deliberately not substituted.",
    );
  }

  const [
    national,
    history,
    routes,
    horizons,
    fares,
    stats,
    anomalies,
    collection,
    sources,
    weights,
  ] = await Promise.all([
    apiGet("/api/v1/index/national"),
    apiGet("/api/v1/index/national/history?days=400"),
    apiGet("/api/v1/index/routes"),
    apiGet("/api/v1/index/horizons"),
    apiGet("/api/v1/fares/latest?limit=120"),
    apiGet("/api/v1/fares/stats"),
    apiGet("/api/v1/anomalies?limit=60"),
    apiGet("/api/v1/collection/status"),
    apiGet("/api/v1/sources"),
    apiGet("/api/v1/weights"),
  ]);

  const index = national.ok ? national.data : null;
  // A payload carrying `status` rather than `value` is the backend reporting that no
  // index exists. That is a real state, not an error to paper over.
  const hasIndex = Boolean(index && index.value != null);

  const provenance = hasIndex ? index.data_provenance : null;
  const mode = hasIndex ? resolveDataMode(provenance) : DATA_MODE.UNAVAILABLE;

  const statsData = stats.ok ? stats.data : null;
  const anomalyTotal = anomalies.ok ? anomalies.data?.total_count ?? null : null;
  const openAnomalies = anomalies.ok ? anomalies.data?.open_count ?? null : null;

  // Derived only when both inputs exist. Previously this displayed a hardcoded
  // "96.4%" whenever the real figure was missing.
  const validPct =
    statsData && statsData.total_observations > 0 && statsData.valid_observations != null
      ? (statsData.valid_observations / statsData.total_observations) * 100
      : null;

  return {
    connected: true,
    mode,
    reason: hasIndex
      ? null
      : index?.reason ||
        "No index has been computed yet. Run a collection cycle to produce one.",
    provenance,
    isOfficialStatistic: false,

    headlineIndex: hasIndex ? index.value : null,
    indexDate: hasIndex ? index.index_date : null,
    basePeriod: hasIndex ? index.base_period : null,
    momChangePct: hasIndex ? index.mom_change_pct : null,
    momStatus: hasIndex ? index.mom_status : null,
    yoyChangePct: hasIndex ? index.yoy_change_pct : null,
    yoyStatus: hasIndex ? index.yoy_status : null,
    sampleSize: hasIndex ? index.sample_size : null,
    matchedProducts: hasIndex ? index.matched_products : null,
    routesIncluded: hasIndex ? index.routes_included : null,
    routesInBasket: hasIndex ? index.routes_in_basket : null,
    coverageWeight: hasIndex ? index.coverage_weight : null,
    isPublishable: hasIndex ? index.is_publishable : null,
    suppressionReason: hasIndex ? index.suppression_reason : null,
    standardError: hasIndex ? index.uncertainty?.standard_error ?? null : null,
    confidenceLow: hasIndex ? index.uncertainty?.confidence_interval_low ?? null : null,
    confidenceHigh: hasIndex ? index.uncertainty?.confidence_interval_high ?? null : null,
    uncertaintyBasis: hasIndex ? index.uncertainty?.basis ?? null : null,
    seasonalAdjustment: hasIndex ? index.seasonal_adjustment : null,
    methodologyVersion: hasIndex ? index.methodology_version : null,
    routeContributions: hasIndex ? index.route_contributions ?? [] : [],
    missingRoutes: hasIndex ? index.missing_routes ?? [] : [],

    history: history.ok ? history.data?.data ?? [] : [],
    routeIndices: routes.ok ? routes.data?.routes ?? [] : [],
    horizonIndices: horizons.ok ? horizons.data?.horizons ?? [] : [],
    horizonPolicy: horizons.ok ? horizons.data?.policy ?? null : null,
    observations: fares.ok ? fares.data?.fares ?? [] : [],
    observationStats: statsData,
    anomalyCount: anomalyTotal,
    openAnomalyCount: openAnomalies,
    validPct,
    collectionStatus: collection.ok ? collection.data : null,
    lastRun: collection.ok ? collection.data?.last_run ?? null : null,
    sources: sources.ok ? sources.data?.sources ?? [] : [],
    weights: weights.ok ? weights.data : null,
    lastUpdated: new Date().toISOString(),
  };
}

/** Trigger a collection cycle. */
export async function triggerCollection({ mode, adminToken } = {}) {
  return apiPost(
    "/api/v1/collection/trigger",
    { mode: mode || null, compute_index: true },
    { adminToken },
  );
}

/** Ask the Copilot through the server-side proxy. The browser holds no API key. */
export async function askCopilot(question, context) {
  return apiPost("/api/v1/copilot/ask", { question, context: context ?? null }, {
    timeoutMs: 45000,
  });
}

/** Fetch stored index history for one route. */
export async function loadRouteHistory(routeId, days = 30) {
  return apiGet(`/api/v1/index/routes/${routeId}?days=${days}`);
}

/** Fetch horizon indices for one route. */
export async function loadRouteHorizons(routeId) {
  return apiGet(`/api/v1/index/horizons?route_id=${routeId}`);
}

/** Fetch stored observations for one route. */
export async function loadRouteObservations(routeId, limit = 200) {
  return apiGet(`/api/v1/fares/route/${routeId}?limit=${limit}`);
}

/** Fetch methodology metadata. */
export async function loadMethodology() {
  return apiGet("/api/v1/methodology");
}

/** Scrape flight fares on-demand for a specific origin and destination route. */
export async function scrapeRouteFares({
  origin,
  destination,
  originCity,
  destinationCity,
  mode,
  horizons = [0, 3, 7, 15, 30],
  adminToken = "",
} = {}) {
  return apiPost(
    "/api/v1/routes/scrape",
    {
      origin: origin?.toUpperCase(),
      destination: destination?.toUpperCase(),
      origin_city: originCity || null,
      destination_city: destinationCity || null,
      mode: mode || null,
      horizons,
      compute_index: true,
    },
    { timeoutMs: 90000, adminToken }
  );
}

/** Fetch comprehensive Indian airports directory. */
export async function loadAirportsDirectory() {
  return apiGet("/api/v1/airports");
}

