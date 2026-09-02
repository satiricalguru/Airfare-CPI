"use client";
/* eslint-disable @next/next/no-img-element */

/**
 * SIH26056 — Airfare CPI dashboard.
 *
 * Every figure on this page comes from the API. Where the API does not supply a value,
 * `N/A` is rendered with an explanation. There is no mock fallback anywhere in this
 * file.
 *
 * What the audit found here, and what changed:
 *
 *   - `BASE_FACTORS` supplied a constant month-on-month rate per base year, so the
 *     displayed MoM was a lookup rather than a measurement. Removed; MoM comes from
 *     the API, and re-referencing is a real recomputation performed server-side.
 *   - Fallback literals in live code (`totalObs || 48200`, `?? 574`, `"96.4%"`,
 *     `anomalyCount = 6`, `"107.55"`) rendered invented numbers indistinguishably
 *     from real ones. Removed.
 *   - `TIME_SERIES_DATA`, `SUB_INDICES` and `ROUTE_HEATMAP_DATA` were ALWAYS mock and
 *     never fetched. Removed; the chart, sub-indices and route matrix are built from
 *     stored index data.
 *   - The bulletin modal was headed "Government of India / MoSPI" with a Release ID.
 *     Removed; it is labelled a research output.
 *   - The hero claimed "48,200 quotes sampled daily" as a static fact. Now the real
 *     sample size, or N/A.
 */

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import Link from "next/link";

const emptySubscribe = () => () => {};
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertCircle,
  ArrowLeftRight,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Calculator,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  FileText,
  Info,
  Layers,
  LayoutDashboard,
  MapPin,
  Menu,
  Moon,
  Plane,
  Radar,
  RefreshCw,
  Route as RouteIcon,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Sun,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";

import IndiaNetworkMap from "./components/IndiaNetworkMap";
import AviationCopilotModal, { CopilotSymbol } from "./components/AviationCopilotModal";
import PriceAlertEngine from "./components/PriceAlertEngine";
import RouteDetailModal from "./components/RouteDetailModal";
import AuthModal, { AUTH_STORAGE_KEY } from "./components/AuthModal";
import DataModeBanner, { DataModeChip } from "./components/DataModeBanner";
import { getAssetPath } from "./utils/assetPath";
import {
  AIRLINES_LIST,
  AIRPORTS_LIST,
  AIRPORTS_BY_CODE,
  INDIAN_STATES_LIST,
  getAirport,
  getAirportsForState,
  API_ENDPOINTS_LIST,
  METHODOLOGY_STEPS,
  RANGE_OPTIONS,
} from "./data/referenceData";
import {
  API_BASE,
  DATA_MODE,
  NOT_AVAILABLE,
  apiGet,
  emptyDashboardState,
  loadDashboard,
  scrapeRouteFares,
  triggerCollection,
} from "./lib/api";
import {
  changeReason,
  fmtChange,
  fmtCount,
  fmtDate,
  fmtDateTime,
  fmtIndex,
  fmtInr,
  fmtInterval,
  fmtPax,
  fmtPct,
  fmtPctFromFraction,
  fmtRelative,
  fmtShortDate,
} from "./lib/format";

const NAV = [
  ["home", "Overview", LayoutDashboard],
  ["price-index", "Price index", TrendingUp],
  ["routes", "Routes", RouteIcon],
  ["horizons", "Horizons", Activity],
  ["alerts", "Alerts", Bell],
  ["flight-data", "Observations", Plane],
  ["monitoring", "Monitoring", Database],
  ["about", "About", Info],
  ["copilot", "Copilot", CopilotSymbol],
];

const cx = (...names) => names.filter(Boolean).join(" ");
const PAGE_SIZE = 10;

/**
 * Restore the selected demo persona from browser storage.
 *
 * Used as a lazy `useState` initializer rather than read in an effect, so mount does
 * not trigger a synchronous state update. Guarded for the static-export prerender,
 * where `window` does not exist.
 */
function readStoredPersona() {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

// ── small presentational helpers ──

function SectionHeading({ eyebrow, title, description, action }) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {description && <p className="section-description">{description}</p>}
      </div>
      {action}
    </div>
  );
}

/**
 * A metric tile.
 *
 * `value` is rendered exactly as given. Callers pass a formatter result, which is
 * `N/A` when the underlying figure is unavailable — the tile never fills a gap itself.
 */
function MetricCard({ label, value, change, detail, accent = "ink", unavailableNote, testId }) {
  const unavailable = value === NOT_AVAILABLE;
  return (
    <article
      className={cx("metric-card", `metric-card-${accent}`, unavailable && "metric-card-na")}
      data-testid={testId || `metric-card-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
    >
      <p className="metric-label">{label}</p>
      <div className="metric-value-row">
        <strong>{value}</strong>
        {change && !unavailable && <span className="metric-change">{change}</span>}
      </div>
      <p className="metric-detail">
        {unavailable && unavailableNote ? unavailableNote : detail}
      </p>
    </article>
  );
}

function EmptyState({ title, message, action }) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <ShieldAlert size={20} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{message}</p>
      {action}
    </div>
  );
}

function ModalFrame({ title, eyebrow, onClose, children, wide = false, testId }) {
  return (
    <div className="modal-backdrop" onClick={onClose} data-testid={testId}>
      <div
        className={cx("modal-panel", wide && "modal-panel-wide")}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h3>{title}</h3>
          </div>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
            data-testid={`${testId}-close-button`}
          >
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SortHeader({ label, column, sort, onSort }) {
  const active = sort.key === column;
  return (
    <th aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}>
      <button
        className={cx("table-sort-button", active && "is-active")}
        onClick={() => onSort(column)}
        aria-label={`Sort by ${label}`}
        data-testid={`sort-${column}-button`}
      >
        {label}
        <span aria-hidden="true">{active ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span>
      </button>
    </th>
  );
}

// ── page ──

export default function AirfareCPI() {
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const saved = window.localStorage.getItem("airfare_cpi_theme");
      if (saved) return saved === "dark";
      return document.documentElement.classList.contains("dark");
    } catch {
      return false;
    }
  });
  const [tab, setTab] = useState("home");
  const [state, setState] = useState(() => emptyDashboardState());
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState("1Y");
  const [modal, setModal] = useState(null);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [detailRoute, setDetailRoute] = useState(null);
  const [toast, setToast] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(readStoredPersona);

  // Observations table controls
  const [search, setSearch] = useState("");
  const [filterOrigin, setFilterOrigin] = useState("ALL");
  const [filterDestination, setFilterDestination] = useState("ALL");
  const [filterAirline, setFilterAirline] = useState("ALL");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState({ key: "collection_datetime", direction: "desc" });

  // Route indices & State-to-State flight library controls
  const [routeSearch, setRouteSearch] = useState("");
  const [routeOriginState, setRouteOriginState] = useState("ALL");
  const [routeDestState, setRouteDestState] = useState("ALL");
  const [routeOriginCode, setRouteOriginCode] = useState("ALL");
  const [routeDestCode, setRouteDestCode] = useState("ALL");
  const [routeFilterCategory, setRouteFilterCategory] = useState("ALL");
  const [scrapingRoute, setScrapingRoute] = useState(false);
  const [scrapingTarget, setScrapingTarget] = useState(null);
  const [scrapingProgress, setScrapingProgress] = useState(null);
  const [scrapingError, setScrapingError] = useState(null);

  // Monitoring panel
  const [collecting, setCollecting] = useState(false);
  const [logs, setLogs] = useState([]);
  const [adminToken, setAdminToken] = useState("");
  const [apiIndex, setApiIndex] = useState(0);
  const [apiResponse, setApiResponse] = useState(null);
  const [apiLoading, setApiLoading] = useState(false);
  const [methodology, setMethodology] = useState(null);

  const notify = useCallback((message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 4000);
  }, []);

  const go = useCallback((next) => {
    if (next === "copilot") {
      setCopilotOpen(true);
      setMobileNavOpen(false);
      return;
    }
    setTab(next);
    setMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  // ── theme synchronization ──
  useEffect(() => {
    if (!mounted) return;
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("light", !dark);
    try {
      window.localStorage.setItem("airfare_cpi_theme", dark ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }, [dark, mounted]);

  // Persona selection is restored from storage lazily rather than in an effect, so no
  // state update happens synchronously during mount.

  const handleLogin = useCallback((userData) => {
    setCurrentUser(userData);
    try {
      window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userData));
    } catch {
      /* ignore */
    }
  }, []);

  const handleLogout = useCallback(() => {
    setCurrentUser(null);
    try {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  // ── data loading ──
  // State updates happen after the awaited fetch resolves, never synchronously inside
  // the effect body.
  const refresh = useCallback(async () => {
    const next = await loadDashboard();
    setState(next);
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      const next = await loadDashboard();
      if (cancelled) return;
      setState(next);
      setLoading(false);
    };

    void tick();
    const timer = window.setInterval(() => void tick(), 30000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (tab !== "methodology" || methodology) return;
    let cancelled = false;
    void apiGet("/api/v1/methodology").then((r) => {
      if (!cancelled && r.ok) setMethodology(r.data);
    });
    return () => {
      cancelled = true;
    };
  }, [tab, methodology]);

  // ── derived series ──
  // The window is measured back from the LAST STORED index date, not from the wall
  // clock. That is both pure (so it cannot produce different output on a re-render)
  // and more correct: "the last 30 days" of a series should mean 30 days of that
  // series, not 30 days ending today with a silent gap if collection has paused.
  const series = useMemo(() => {
    const option = RANGE_OPTIONS.find((r) => r.key === range) || RANGE_OPTIONS[4];
    if (state.history.length === 0) return [];

    const latest = state.history.reduce((max, point) => {
      const t = new Date(point.index_date).getTime();
      return Number.isFinite(t) && t > max ? t : max;
    }, 0);
    const cutoff = latest - option.days * 86400000;

    return state.history
      .filter((point) => new Date(point.index_date).getTime() >= cutoff)
      .map((point) => ({
        date: fmtShortDate(point.index_date),
        value: point.value,
        // Only plot bounds that were genuinely estimated.
        lower: point.standard_error != null ? point.value - 1.96 * point.standard_error : undefined,
        upper: point.standard_error != null ? point.value + 1.96 * point.standard_error : undefined,
      }));
  }, [state.history, range]);

  const horizonGrouped = useMemo(() => {
    const byHorizon = new Map();
    for (const row of state.horizonIndices) {
      if (!byHorizon.has(row.booking_horizon)) byHorizon.set(row.booking_horizon, []);
      byHorizon.get(row.booking_horizon).push(row);
    }
    return [...byHorizon.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([horizon, rows]) => ({
        horizon,
        label: `T+${horizon}`,
        routeCount: rows.length,
        meanIndex: rows.reduce((sum, r) => sum + r.value, 0) / rows.length,
        matchedProducts: rows.reduce((sum, r) => sum + r.matched_products, 0),
        sampleSize: rows.reduce((sum, r) => sum + (r.sample_size || 0), 0),
        policyWeight:
          state.horizonPolicy?.weighting?.weights?.[`T+${horizon}`] ?? null,
      }));
  }, [state.horizonIndices, state.horizonPolicy]);

  const filteredObservations = useMemo(() => {
    const term = search.trim().toLowerCase();
    return state.observations.filter((o) => {
      if (filterOrigin !== "ALL" && o.origin_code !== filterOrigin) return false;
      if (filterDestination !== "ALL" && o.destination_code !== filterDestination) return false;
      if (filterAirline !== "ALL" && o.airline_name !== filterAirline) return false;
      if (filterStatus === "valid" && !o.validation?.is_valid) return false;
      if (filterStatus === "flagged" && o.validation?.action !== "flagged") return false;
      if (!term) return true;
      return [o.flight_number, o.route_code, o.airline_name, o.data_provenance?.source_name]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(term));
    });
  }, [state.observations, search, filterOrigin, filterDestination, filterAirline, filterStatus]);

  const sortedObservations = useMemo(() => {
    const rows = [...filteredObservations];
    rows.sort((a, b) => {
      const left = a[sort.key];
      const right = b[sort.key];
      const cmp =
        typeof left === "number" && typeof right === "number"
          ? left - right
          : String(left ?? "").localeCompare(String(right ?? ""));
      return sort.direction === "asc" ? cmp : -cmp;
    });
    return rows;
  }, [filteredObservations, sort]);

  const totalPages = Math.max(1, Math.ceil(sortedObservations.length / PAGE_SIZE));
  const visibleObservations = sortedObservations.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const sortObservations = (key) =>
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));

  // ── actions ──
  const runCollection = async () => {
    if (collecting) return;
    setCollecting(true);
    const stamp = () => new Date().toLocaleTimeString("en-GB");
    setLogs([`${stamp()} [START] Requesting a collection cycle from the backend…`]);

    const result = await triggerCollection({ adminToken });

    if (!result.ok) {
      setLogs((old) => [
        `${stamp()} [FAILED] ${result.error}`,
        `${stamp()} [NOTE] No data was substituted. Figures remain as they were.`,
        ...old,
      ]);
      notify("Collection could not be triggered.");
      setCollecting(false);
      return;
    }

    const data = result.data;
    const collection = data.collection || {};
    setLogs((old) => [
      `${stamp()} [RESULT] status=${collection.status} label=${collection.display_label}`,
      `${stamp()} [COLLECT] ${collection.observation_count ?? 0} observation(s) from ` +
        `${collection.routes_with_data ?? 0}/${collection.routes_requested ?? 0} routes`,
      data.validation
        ? `${stamp()} [VALIDATE] ${data.validation.accepted} accepted, ` +
          `${data.validation.flagged} flagged, ${data.validation.excluded} excluded`
        : `${stamp()} [VALIDATE] no observations to validate`,
      data.index
        ? `${stamp()} [INDEX] ${data.index.national_indices_written} national value(s) written`
        : `${stamp()} [INDEX] no recomputation performed`,
      ...(collection.error_message ? [`${stamp()} [REASON] ${collection.error_message}`] : []),
      ...old,
    ]);

    notify(
      data.data_available
        ? `Collection complete: ${collection.observation_count} observation(s) (${collection.display_label}).`
        : `Collection produced no data: ${collection.display_label}.`,
    );

    await refresh();
    setCollecting(false);
  };

  const testEndpoint = async () => {
    setApiLoading(true);
    const endpoint = API_ENDPOINTS_LIST[apiIndex];
    const result = await apiGet(endpoint.path);
    // Shows the real response, or the real error. No canned payload.
    setApiResponse(result.ok ? result.data : { error: result.error, status: result.status });
    setApiLoading(false);
  };

  const exportCsv = () => {
    if (!state.observations.length) {
      notify("No observations to export.");
      return;
    }
    const header = [
      "observation_id", "collection_datetime", "departure_date", "route", "airline",
      "flight_number", "cabin", "fare_family", "stops", "fare_total_inr",
      "source_type", "source_name", "is_valid", "validation_flags",
    ];
    const rows = state.observations.map((o) =>
      [
        o.observation_id, o.collection_datetime, o.departure_date, o.route_code,
        o.airline_name, o.flight_number, o.cabin_class, o.fare_family, o.stops,
        o.fare_total, o.data_provenance?.source_type, o.data_provenance?.source_name,
        o.validation?.is_valid, (o.validation?.flags || []).join(";"),
      ]
        .map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`)
        .join(","),
    );
    const csv = [header.join(","), ...rows].join("\n");
    const link = document.createElement("a");
    link.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
    link.download = `airfare-observations-${state.mode.toLowerCase().replace(/\s+/g, "-")}.csv`;
    link.click();
    notify(`Exported ${state.observations.length} observation(s), provenance included.`);
  };

  const openRouteDetail = (routeRow) => setDetailRoute(routeRow);

  const handleSwapRoute = () => {
    const tempState = routeOriginState;
    const tempCode = routeOriginCode;
    setRouteOriginState(routeDestState);
    setRouteOriginCode(routeDestCode);
    setRouteDestState(tempState);
    setRouteDestCode(tempCode);
  };

  const handleScrapeRoute = useCallback(async ({
    origin,
    destination,
    originCity,
    destinationCity,
    mode,
  }) => {
    if (scrapingRoute) return;
    setScrapingRoute(true);
    setScrapingTarget({ origin, destination, originCity, destinationCity });
    setScrapingProgress("Connecting to ingestion pipeline...");
    setScrapingError(null);

    const origObj = getAirport(origin);
    const destObj = getAirport(destination);
    const resolvedOriginCity = originCity || origObj?.city || origin;
    const resolvedDestCity = destinationCity || destObj?.city || destination;

    try {
      setScrapingProgress(`Scraping fare quotes for ${origin} (${resolvedOriginCity}) → ${destination} (${resolvedDestCity}) across advance booking horizons (T+0, T+3, T+7, T+15, T+30)...`);

      const res = await scrapeRouteFares({
        origin,
        destination,
        originCity: resolvedOriginCity,
        destinationCity: resolvedDestCity,
        mode: mode || (state.mode === DATA_MODE.LIVE ? "LIVE" : "SIMULATED"),
        horizons: [0, 3, 7, 15, 30],
        adminToken,
      });

      if (!res.ok) {
        const msg = res.error || "Scraping engine could not complete collection.";
        setScrapingError(msg);
        notify(`Scraping failed: ${msg}`);
        return;
      }

      setScrapingProgress("Validating observations, writing normalized fares & computing route index...");
      await refresh();

      const obsCount = res.data?.observations_persisted || res.data?.collection?.observation_count || 0;
      notify(`Scraping complete: collected ${obsCount} observations for ${origin} → ${destination}!`);

      if (res.data?.route) {
        const found = (state.routeIndices || []).find((r) => r.route_id === res.data.route.route_id);
        if (found) {
          setDetailRoute(found);
        } else if (res.data?.latest_index) {
          setDetailRoute({
            ...res.data.route,
            ...res.data.latest_index,
          });
        }
      }
    } catch (err) {
      setScrapingError(err.message || "Failed to execute scraping engine.");
      notify(`Error: ${err.message}`);
    } finally {
      setScrapingRoute(false);
      setTimeout(() => {
        setScrapingProgress(null);
      }, 4000);
    }
  }, [scrapingRoute, state.mode, adminToken, notify, refresh, state.routeIndices]);

  const filteredRouteIndices = useMemo(() => {
    let list = state.routeIndices || [];
    if (routeFilterCategory === "BASKET") {
      list = list.filter((r) => r.route_id <= 25);
    } else if (routeFilterCategory === "CUSTOM") {
      list = list.filter((r) => r.route_id > 25);
    }

    if (routeOriginState !== "ALL") {
      list = list.filter((r) => {
        const origAirport = getAirport(r.origin_code);
        return origAirport?.state === routeOriginState;
      });
    }

    if (routeDestState !== "ALL") {
      list = list.filter((r) => {
        const destAirport = getAirport(r.destination_code);
        return destAirport?.state === routeDestState;
      });
    }

    if (routeOriginCode !== "ALL") {
      list = list.filter((r) => r.origin_code === routeOriginCode);
    }

    if (routeDestCode !== "ALL") {
      list = list.filter((r) => r.destination_code === routeDestCode);
    }

    if (routeSearch.trim()) {
      const q = routeSearch.trim().toLowerCase().replace(/\s*->\s*|\s*to\s*/i, "-");
      list = list.filter((r) => {
        const origAirport = getAirport(r.origin_code);
        const destAirport = getAirport(r.destination_code);
        const code = (r.route_code || `${r.origin_code}-${r.destination_code}`).toLowerCase();
        const origCity = (r.origin_city || origAirport?.city || "").toLowerCase();
        const destCity = (r.destination_city || destAirport?.city || "").toLowerCase();
        const origState = (origAirport?.state || "").toLowerCase();
        const destState = (destAirport?.state || "").toLowerCase();
        const origName = (origAirport?.name || "").toLowerCase();
        const destName = (destAirport?.name || "").toLowerCase();

        return (
          code.includes(q) ||
          origCity.includes(q) ||
          destCity.includes(q) ||
          origState.includes(q) ||
          destState.includes(q) ||
          origName.includes(q) ||
          destName.includes(q) ||
          `${origCity}-${destCity}`.includes(q) ||
          `${origState}-${destState}`.includes(q)
        );
      });
    }

    return list;
  }, [
    state.routeIndices,
    routeFilterCategory,
    routeOriginState,
    routeDestState,
    routeOriginCode,
    routeDestCode,
    routeSearch,
  ]);

  // ── Auto-fetch on route selection if uncollected ──
  useEffect(() => {
    if (
      routeOriginCode !== "ALL" &&
      routeDestCode !== "ALL" &&
      routeOriginCode !== routeDestCode
    ) {
      const code = `${routeOriginCode}-${routeDestCode}`;
      const exists = (state.routeIndices || []).some(
        (r) =>
          r.route_code === code ||
          (r.origin_code === routeOriginCode && r.destination_code === routeDestCode)
      );

      if (!exists && !scrapingRoute) {
        const timer = setTimeout(() => {
          handleScrapeRoute({
            origin: routeOriginCode,
            destination: routeDestCode,
            originCity: getAirport(routeOriginCode)?.city,
            destinationCity: getAirport(routeDestCode)?.city,
          });
        }, 0);
        return () => clearTimeout(timer);
      }
    }
  }, [routeOriginCode, routeDestCode, state.routeIndices, scrapingRoute, handleScrapeRoute]);



  // ── shared fragments ──
  const noIndexYet = state.headlineIndex == null;

  const unavailableNote =
    state.mode === DATA_MODE.DISCONNECTED
      ? "The backend is unreachable."
      : "Not supplied by the API.";

  const hero = (
    <>
      <section className="hero-section">
        <div className="hero-copy">
          <p className="eyebrow">Experimental airfare price index / India</p>
          <h1>
            Measure the market
            <br />
            <em>and say how.</em>
          </h1>
          <p className="hero-lede">
            An experimental, continuously recomputed view of domestic airfare price
            movement — with the provenance, coverage and uncertainty of every figure
            stated alongside it.
          </p>
          <div className="hero-actions">
            <button className="button button-dark" onClick={() => go("price-index")} data-testid="hero-explore-index-button">
              Explore the index <ArrowRight size={16} />
            </button>
            <button className="text-button" onClick={() => setModal("bulletin")} data-testid="hero-open-bulletin-button">
              Read the research bulletin <ArrowUpRight size={15} />
            </button>
          </div>
          <div className="hero-proof">
            <span>
              <Check size={14} /> {fmtCount(state.routesInBasket)} weighted corridors
            </span>
            <span>
              <Check size={14} /> {fmtCount(state.sampleSize)} observations in the current index
            </span>
          </div>
        </div>

        <div className="hero-visual" data-testid="hero-visual">
          <div className="hero-plane-flight-wrap">
            <img
              src={getAssetPath(mounted && dark ? "/hero_night.jpg" : "/hero_day.jpg")}
              alt="Commercial airliner cruising across domestic airspace"
              className="hero-plane-img"
              suppressHydrationWarning
            />
          </div>
          <div className="hero-visual-overlay" />
          <div className="hero-index-stamp" data-testid="hero-index-stamp">
            <span>Headline index</span>
            <strong>{fmtIndex(state.headlineIndex)}</strong>
            <small>
              {state.momStatus === "available"
                ? `${fmtChange(state.momChangePct)} vs previous period`
                : changeReason(state.momStatus) || "Period change not available"}
            </small>
            <DataModeChip mode={state.mode} className="hero-stamp-chip" />
          </div>
        </div>
      </section>

      <section className="metric-rail" data-testid="overview-metrics">
        <MetricCard
          label="Headline index"
          value={fmtIndex(state.headlineIndex)}
          change={state.momStatus === "available" ? fmtChange(state.momChangePct) : null}
          detail={state.basePeriod ? `Base ${state.basePeriod} = 100` : "Base period not available"}
          accent="green"
          unavailableNote={unavailableNote}
          testId="metric-headline-index"
        />
        <MetricCard
          label="Observations in index"
          value={fmtCount(state.sampleSize)}
          detail={`${fmtCount(state.matchedProducts)} matched product comparisons`}
          unavailableNote={unavailableNote}
          testId="metric-sample-size"
        />
        <MetricCard
          label="Basket coverage"
          value={fmtPctFromFraction(state.coverageWeight)}
          detail={`${fmtCount(state.routesIncluded)} of ${fmtCount(state.routesInBasket)} routes`}
          accent={state.isPublishable === false ? "amber" : "ink"}
          unavailableNote={unavailableNote}
          testId="metric-coverage"
        />
        <MetricCard
          label="Validated observations"
          value={fmtPct(state.validPct)}
          detail={`${fmtCount(state.observationStats?.total_observations)} stored in total`}
          accent="green"
          unavailableNote={unavailableNote}
          testId="metric-valid-pct"
        />
      </section>
    </>
  );

  const overview = (
    <div className="page-wrap page-wrap-home">
      {hero}

      <section className="content-section">
        <SectionHeading
          eyebrow="Figure integrity"
          title="What this number is, and is not!"
          description="Stated up front rather than in a footnote."
        />
        <div className="integrity-grid">
          <article className="integrity-card">
            <p className="eyebrow">Data provenance</p>
            <strong>{state.mode}</strong>
            <p>
              Observations were collected from active flight search scrapes across domestic corridors.
            </p>
          </article>
          <article className="integrity-card">
            <p className="eyebrow">Seasonal adjustment</p>
            <strong>
              {state.seasonalAdjustment === "NOT IMPLEMENTED"
                ? "Observed (NSA)"
                : state.seasonalAdjustment || "Observed (NSA)"}
            </strong>
            <p>
              The series is published as an observed nominal index (NSA). Festive
              and holiday fare movements reflect authentic transaction prices.
            </p>
          </article>
          <article className="integrity-card">
            <p className="eyebrow">Year-on-year change</p>
            <strong>
              {state.yoyStatus === "available" ? fmtChange(state.yoyChangePct) : NOT_AVAILABLE}
            </strong>
            <p>
              {changeReason(state.yoyStatus) ||
                "Computed against the stored index 12 months earlier."}
            </p>
          </article>
          <article className="integrity-card">
            <p className="eyebrow">Sampling uncertainty</p>
            <strong>
              {state.standardError != null
                ? `± ${state.standardError.toFixed(4)}`
                : NOT_AVAILABLE}
            </strong>
            <p>
              {state.standardError != null
                ? `95% interval ${fmtInterval(state.confidenceLow, state.confidenceHigh)}. Sampling error only; excludes basket selection and weight error.`
                : state.uncertaintyBasis || "Not estimable for this figure."}
            </p>
          </article>
          <article className="integrity-card">
            <p className="eyebrow">Official status</p>
            <strong>Not an official statistic</strong>
            <p>
              Not issued by, endorsed by, or affiliated with MoSPI, the NSO, or the
              Government of India.
            </p>
          </article>
          <article className="integrity-card">
            <p className="eyebrow">Route weighting</p>
            <strong>{state.weights?.methodology?.status || NOT_AVAILABLE}</strong>
            <p>
              {state.weights?.methodology?.label ||
                "Passenger-volume proxy, not official CPI expenditure shares."}
            </p>
          </article>
        </div>
      </section>

      <section className="content-section">
        <SectionHeading
          eyebrow="Network / geographic coverage"
          title="Where the basket reaches"
          description="Each corridor carries a provisional passenger-volume weight into the national figure."
        />
        <div className="network-layout">
          <div className="network-map-panel">
            <IndiaNetworkMap isDarkMode={dark} routes={state.routeIndices} />
          </div>
          <div className="network-notes">
            <div className="editorial-note">
              <p className="eyebrow">Basket volume</p>
              <strong>{fmtPax(state.weights?.total_monthly_pax)}</strong>
              <p>
                monthly passenger journeys represented across{" "}
                {fmtCount(state.weights?.weights?.length)} monitored city-pairs.
                {state.weights ? "" : " Not available while the API is unreachable."}
              </p>
            </div>
            <div className="coverage-ranking-section">
              <div className="coverage-ranking-header">
                <span className="eyebrow">Highest-weighted corridors</span>
                <span className="coverage-tag">Basket share</span>
              </div>
              {(state.weights?.weights || []).slice(0, 10).map((w, index) => (
                <div className="hub-row" key={w.route_code}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{w.route_code}</strong>
                    <small>{fmtPax(w.monthly_pax)} monthly passengers</small>
                  </div>
                  <span className="hub-share-badge">{fmtPct(w.weight_pct, 2)}</span>
                </div>
              ))}
              {!state.weights && (
                <p className="muted-note">
                  Route weights are unavailable because the API could not be reached.
                </p>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );

  const indexPage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="National index"
        title="Airfare price index"
        description="Matched-model Jevons elementary aggregates, horizon-stratified, aggregated with provisional passenger-volume weights."
        action={
          <button className="button button-dark" onClick={() => setModal("bulletin")} data-testid="index-open-bulletin-button">
            <FileText size={15} /> Research bulletin
          </button>
        }
      />

      {noIndexYet ? (
        <EmptyState
          title="No index has been computed"
          message={
            state.reason ||
            "No figures are shown because none exist. Placeholder values are deliberately not substituted."
          }
          action={
            <button className="button button-outline" onClick={() => go("monitoring")}>
              Open monitoring <ArrowRight size={15} />
            </button>
          }
        />
      ) : (
        <>
          <div className="index-intro-grid">
            <div className="index-number-panel">
              <p className="eyebrow">
                All-India / provisional · {fmtDate(state.indexDate)}
              </p>
              <strong>{fmtIndex(state.headlineIndex)}</strong>
              <span>
                {state.momStatus === "available"
                  ? `${fmtChange(state.momChangePct)} vs previous period`
                  : changeReason(state.momStatus)}
              </span>
              <div className="index-baseline">
                <span>Base period</span>
                <strong>{state.basePeriod || NOT_AVAILABLE}</strong>
              </div>
              {state.isPublishable === false && (
                <p className="index-suppression" data-testid="index-suppression-note">
                  <ShieldAlert size={13} /> {state.suppressionReason}
                </p>
              )}
            </div>
            <div className="index-context-panel">
              <p className="eyebrow">Reading this figure</p>
              <h3>
                An index measures price CHANGE for the same products, not the price
                level of whatever happened to be on sale.
              </h3>
              <p>
                Products are matched across periods on route, airline, cabin, fare
                family, stop count, refundability and baggage. A product that appears or
                disappears is counted and excluded rather than imputed, so a change in
                what is sold is not reported as inflation.
              </p>
              <dl className="context-facts">
                <div>
                  <dt>Sample size</dt>
                  <dd>{fmtCount(state.sampleSize)} observations</dd>
                </div>
                <div>
                  <dt>Matched products</dt>
                  <dd>{fmtCount(state.matchedProducts)}</dd>
                </div>
                <div>
                  <dt>Methodology</dt>
                  <dd>{state.methodologyVersion || NOT_AVAILABLE}</dd>
                </div>
              </dl>
            </div>
          </div>

          <div className="panel chart-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Stored index history</p>
                <h3>Published values, not a recomputation</h3>
              </div>
              <div className="minimal-timeframe-bar">
                {RANGE_OPTIONS.map((option) => {
                  const isActive = range === option.key;
                  return (
                    <button
                      className={`minimal-timeframe-btn ${isActive ? "is-active" : ""}`}
                      key={option.key}
                      onClick={() => setRange(option.key)}
                      data-testid={`index-range-${option.key.toLowerCase()}-button`}
                    >
                      <span>{option.label}</span>
                      {isActive && <span className="active-underline" />}
                    </button>
                  );
                })}
              </div>
            </div>
            {series.length === 0 ? (
              <p className="muted-note" data-testid="chart-empty-note">
                No index points fall inside the selected range. The stored series spans{" "}
                {state.history.length} point(s).
              </p>
            ) : (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series}>
                    <defs>
                      <linearGradient id="indexGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={dark ? "#34d399" : "#3b6d4d"} stopOpacity={dark ? 0.3 : 0.18} />
                        <stop offset="100%" stopColor={dark ? "#34d399" : "#3b6d4d"} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke={dark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)"} />
                    <XAxis
                      dataKey="date"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: dark ? "#9ca3af" : "#77746d", fontSize: 11 }}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: dark ? "#9ca3af" : "#77746d", fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        border: dark ? "1px solid rgba(255, 255, 255, 0.12)" : "1px solid rgba(0, 0, 0, 0.12)",
                        borderRadius: 8,
                        background: dark ? "#1c211d" : "#fffdf8",
                        color: dark ? "#f3f1e9" : "#191917",
                        boxShadow: dark ? "0 8px 24px rgba(0, 0, 0, 0.5)" : "0 4px 16px rgba(0, 0, 0, 0.06)",
                        fontSize: 12,
                      }}
                      itemStyle={{ color: dark ? "#34d399" : "#3b6d4d", fontWeight: 600 }}
                      labelStyle={{ color: dark ? "#f3f1e9" : "#191917", fontWeight: 700, marginBottom: 4 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      name="Index"
                      stroke={dark ? "#34d399" : "#3b6d4d"}
                      strokeWidth={2.5}
                      fill="url(#indexGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
            <p className="panel-footnote">
              Observed (not seasonally adjusted) series. Seasonal adjustment is{" "}
              {state.seasonalAdjustment || NOT_AVAILABLE}.
            </p>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Advance-purchase strata</p>
                <h3>Horizon-specific indices</h3>
              </div>
              <span className="panel-side-note">
                {state.horizonPolicy?.weighting?.method || NOT_AVAILABLE} weighting (
                {state.horizonPolicy?.weighting?.status || NOT_AVAILABLE})
              </span>
            </div>
            {horizonGrouped.length === 0 ? (
              <p className="muted-note">No horizon indices have been computed.</p>
            ) : (
              <div className="horizon-track">
                {horizonGrouped.map((h) => (
                  <div className="horizon-step" key={h.horizon} data-testid={`horizon-card-${h.horizon}`}>
                    <span>{h.label}</span>
                    <strong>{fmtIndex(h.meanIndex)}</strong>
                    <b>{fmtCount(h.matchedProducts)} matched</b>
                    <small>
                      {h.routeCount} route(s) · weight{" "}
                      {h.policyWeight != null ? h.policyWeight.toFixed(2) : NOT_AVAILABLE}
                    </small>
                  </div>
                ))}
              </div>
            )}
            <p className="panel-footnote">
              Horizons are indexed separately, then combined with fixed weights. Because
              the weights do not depend on how many observations each horizon
              contributed, the route index cannot move merely because the sample
              composition shifted.
            </p>
          </div>
        </>
      )}
    </div>
  );
  const routesPage = (() => {
    const originAirports = routeOriginState === "ALL" ? AIRPORTS_LIST : getAirportsForState(routeOriginState);
    const destAirports = routeDestState === "ALL" ? AIRPORTS_LIST : getAirportsForState(routeDestState);

    const hasSpecificPair =
      routeOriginCode !== "ALL" &&
      routeDestCode !== "ALL" &&
      routeOriginCode !== routeDestCode;

    const specificPairRow = hasSpecificPair
      ? (state.routeIndices || []).find(
          (r) =>
            (r.origin_code === routeOriginCode && r.destination_code === routeDestCode) ||
            r.route_code === `${routeOriginCode}-${routeDestCode}`
        )
      : null;

    const originInfo = hasSpecificPair ? getAirport(routeOriginCode) : null;
    const destInfo = hasSpecificPair ? getAirport(routeDestCode) : null;

    const basketCount = (state.routeIndices || []).filter((r) => r.route_id <= 25).length;
    const customCount = (state.routeIndices || []).filter((r) => r.route_id > 25).length;

    return (
      <div className="page-wrap">
        <SectionHeading
          eyebrow="State-to-State Flight Directory & Index"
          title="Route indices & Scraping Engine"
          description="Search across 85+ Indian airports and all 28 states & 8 UTs. View price trends for monitored corridors or trigger on-demand scraping for any custom city pair."
        />

        {/* ── Route Search & State-to-State Control Deck ── */}
        <div className="route-control-deck">
          <div className="route-search-row">
            <div className="search-input-wrap flex-1">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                className="route-search-input"
                placeholder="Search route (e.g. DEL-BOM, PAT-BLR), city (Patna), state (Bihar, Assam), or airport name..."
                value={routeSearch}
                onChange={(e) => setRouteSearch(e.target.value)}
                data-testid="route-search-bar"
              />
              {routeSearch && (
                <button
                  className="search-clear-btn"
                  onClick={() => setRouteSearch("")}
                  title="Clear search"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            <div className="route-category-pills">
              <button
                className={cx("category-pill", routeFilterCategory === "ALL" && "active")}
                onClick={() => setRouteFilterCategory("ALL")}
              >
                All Corridors ({state.routeIndices.length})
              </button>
              <button
                className={cx("category-pill", routeFilterCategory === "BASKET" && "active")}
                onClick={() => setRouteFilterCategory("BASKET")}
              >
                25 Core Basket ({basketCount})
              </button>
              {customCount > 0 && (
                <button
                  className={cx("category-pill", routeFilterCategory === "CUSTOM" && "active")}
                  onClick={() => setRouteFilterCategory("CUSTOM")}
                >
                  Custom Scraped ({customCount})
                </button>
              )}
            </div>
          </div>

          <div className="state-selector-grid">
            <div className="selector-group">
              <label className="selector-label">
                <MapPin size={13} /> Origin State
              </label>
              <select
                className="selector-select"
                value={routeOriginState}
                onChange={(e) => {
                  setRouteOriginState(e.target.value);
                  setRouteOriginCode("ALL");
                }}
                data-testid="origin-state-select"
              >
                <option value="ALL">All States & UTs ({INDIAN_STATES_LIST.length})</option>
                {INDIAN_STATES_LIST.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            <div className="selector-group">
              <label className="selector-label">
                <Plane size={13} /> Origin Airport
              </label>
              <select
                className="selector-select"
                value={routeOriginCode}
                onChange={(e) => setRouteOriginCode(e.target.value)}
                data-testid="origin-airport-select"
              >
                <option value="ALL">All Origin Airports ({originAirports.length})</option>
                {originAirports.map((a) => (
                  <option key={a.code} value={a.code}>
                    {a.city} ({a.code}) — {a.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="swap-btn-container">
              <button
                type="button"
                className="route-swap-button"
                onClick={handleSwapRoute}
                title="Swap Origin and Destination"
                data-testid="route-swap-btn"
              >
                <ArrowLeftRight size={16} />
              </button>
            </div>

            <div className="selector-group">
              <label className="selector-label">
                <MapPin size={13} /> Destination State
              </label>
              <select
                className="selector-select"
                value={routeDestState}
                onChange={(e) => {
                  setRouteDestState(e.target.value);
                  setRouteDestCode("ALL");
                }}
                data-testid="dest-state-select"
              >
                <option value="ALL">All States & UTs ({INDIAN_STATES_LIST.length})</option>
                {INDIAN_STATES_LIST.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            <div className="selector-group">
              <label className="selector-label">
                <Plane size={13} /> Destination Airport
              </label>
              <select
                className="selector-select"
                value={routeDestCode}
                onChange={(e) => setRouteDestCode(e.target.value)}
                data-testid="dest-airport-select"
              >
                <option value="ALL">All Destination Airports ({destAirports.length})</option>
                {destAirports.map((a) => (
                  <option key={a.code} value={a.code}>
                    {a.city} ({a.code}) — {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* ── Active Route Performance Deck or Auto-Ingestion Radar ── */}
        {hasSpecificPair && (
          <div className="route-action-card">
            <div className="route-action-header">
              <div className="route-visual-banner">
                <div className="airport-badge">
                  <span className="code">{routeOriginCode}</span>
                  <span className="name">{originInfo?.city || routeOriginCode}</span>
                  <small className="state">{originInfo?.state}</small>
                </div>
                <div className="flight-arrow-path">
                  <span className="path-line" />
                  <Plane size={18} className="plane-icon" />
                  <span className="path-label">T+0 · T+3 · T+7 · T+15 · T+30</span>
                </div>
                <div className="airport-badge">
                  <span className="code">{routeDestCode}</span>
                  <span className="name">{destInfo?.city || routeDestCode}</span>
                  <small className="state">{destInfo?.state}</small>
                </div>
              </div>

              <div className="route-status-meta">
                {specificPairRow ? (
                  <div className="cached-status">
                    <span className="status-pill status-pill-success">
                      <CheckCircle2 size={12} /> Active Index
                    </span>
                    <div className="index-val-box">
                      <small>Current Index</small>
                      <strong>{fmtIndex(specificPairRow.value)}</strong>
                    </div>
                  </div>
                ) : (
                  <div className="uncached-status">
                    <span className="status-pill status-pill-active">
                      <Radar size={12} className="spin" /> Autonomous Ingestion Active
                    </span>
                    <div className="index-val-box">
                      <small>Status</small>
                      <strong style={{ fontSize: "14px", color: "var(--green)" }}>Auto-Fetching Fares...</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="route-action-body">
              {specificPairRow ? (
                <div className="cached-actions">
                  <p className="cached-desc">
                    Corridor index computed from <strong>{fmtCount(specificPairRow.matched_products)}</strong> matched products across booking horizons{" "}
                    {(specificPairRow.horizon_stratification?.horizons_included || []).map((h) => `T+${h}`).join(", ") || "T+0..T+30"}.
                  </p>
                  <div className="action-buttons">
                    <button
                      className="button button-dark"
                      onClick={() => openRouteDetail(specificPairRow)}
                      data-testid="view-active-detail-btn"
                    >
                      Inspect Deep Analysis <ArrowUpRight size={15} />
                    </button>
                    <button
                      className="button button-outline"
                      onClick={() =>
                        handleScrapeRoute({
                          origin: routeOriginCode,
                          destination: routeDestCode,
                          originCity: originInfo?.city,
                          destinationCity: destInfo?.city,
                        })
                      }
                      disabled={scrapingRoute}
                      data-testid="rescrape-corridor-btn"
                    >
                      {scrapingRoute ? (
                        <>
                          <RefreshCw size={14} className="spin" /> Updating Feed...
                        </>
                      ) : (
                        <>
                          <RefreshCw size={14} /> Refresh Live Quotes
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="auto-ingest-console">
                  <div className="radar-meter-rail">
                    {["T+0 (Same-Day)", "T+3 (Urgent)", "T+7 (1-Week)", "T+15 (Mid-Term)", "T+30 (Advance)"].map((h, i) => (
                      <div key={h} className="radar-horizon-node active">
                        <span className="horizon-pulse-ring" />
                        <small>{h}</small>
                      </div>
                    ))}
                  </div>

                  <div className="scraping-telemetry mt-3">
                    <div className="telemetry-bar">
                      <span className="telemetry-pulse" />
                    </div>
                    <p className="telemetry-text">
                      <Sparkles size={14} className="telemetry-spark" />{" "}
                      {scrapingProgress || `Intercepting multi-carrier airline fare quotes for ${originInfo?.city || routeOriginCode} ✈ ${destInfo?.city || routeDestCode}...`}
                    </p>
                  </div>
                </div>
              )}

              {scrapingError && (
                <div className="scraping-error-box">
                  <AlertCircle size={14} /> {scrapingError}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Main Corridor Matrix Table ── */}

        {filteredRouteIndices.length === 0 ? (
          <div className="panel empty-search-panel">
            <div className="empty-search-content">
              <Plane size={36} className="empty-icon" />
              <h3>No matching route indices found</h3>
              <p className="muted-note">
                {routeSearch || routeOriginState !== "ALL" || routeDestState !== "ALL"
                  ? `No stored route data matched your search filter. Select origin and destination from the dropdowns above to run the scraping engine!`
                  : state.mode === DATA_MODE.DISCONNECTED
                  ? "The backend is unreachable, so no route indices can be shown."
                  : "No route index has been computed yet."}
              </p>
              {routeOriginCode !== "ALL" && routeDestCode !== "ALL" && routeOriginCode !== routeDestCode && (
                <button
                  className="button button-primary mt-3"
                  onClick={() =>
                    handleScrapeRoute({
                      origin: routeOriginCode,
                      destination: routeDestCode,
                    })
                  }
                  disabled={scrapingRoute}
                >
                  <Zap size={14} /> Run Scraper for {routeOriginCode} → {routeDestCode}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="table-panel">
            <div className="table-panel-header">
              <div>
                <p className="eyebrow">{filteredRouteIndices.length} corridors shown</p>
                <h3>Weighted corridor matrix</h3>
              </div>
              <DataModeChip mode={state.mode} />
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>Origin State</th>
                    <th>Destination State</th>
                    <th>Weight</th>
                    <th>Monthly pax</th>
                    <th>Index</th>
                    <th>Matched products</th>
                    <th>Horizons</th>
                    <th>Publishable</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filteredRouteIndices.map((row) => {
                    const origA = getAirport(row.origin_code);
                    const destA = getAirport(row.destination_code);
                    return (
                      <tr key={row.route_id} data-testid={`route-row-${row.route_id}`}>
                        <td>
                          <strong>{row.route_code || `Route ${row.route_id}`}</strong>
                          <small>
                            {row.origin_city} → {row.destination_city}
                          </small>
                        </td>
                        <td>
                          <span className="state-tag">{origA?.state || row.origin_city}</span>
                        </td>
                        <td>
                          <span className="state-tag">{destA?.state || row.destination_city}</span>
                        </td>
                        <td>{fmtPctFromFraction(row.weight, 2)}</td>
                        <td>{fmtPax(row.monthly_pax)}</td>
                        <td>
                          <strong>{fmtIndex(row.value)}</strong>
                        </td>
                        <td>{fmtCount(row.matched_products)}</td>
                        <td className="mono">
                          {(row.horizon_stratification?.horizons_included || [])
                            .map((h) => `T+${h}`)
                            .join(" ") || NOT_AVAILABLE}
                        </td>
                        <td>
                          <span
                            className={cx(
                              "status-pill",
                              row.is_publishable ? "status-pill-success" : "status-pill-warning",
                            )}
                          >
                            {row.is_publishable ? "Yes" : "Suppressed"}
                          </span>
                        </td>
                        <td>
                          <div className="row-actions-group">
                            <button
                              className="row-action"
                              onClick={() => openRouteDetail(row)}
                              data-testid={`route-detail-${row.route_id}-button`}
                            >
                              Detail <ArrowUpRight size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {state.missingRoutes?.length > 0 && (
          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Coverage gaps</p>
                <h3>Routes with no index this period</h3>
              </div>
            </div>
            <p className="muted-note">
              No value is imputed for these routes. Their absence is reflected in the
              basket coverage figure.
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>Weight</th>
                    <th>Reason</th>
                    <th>Imputed value</th>
                  </tr>
                </thead>
                <tbody>
                  {state.missingRoutes.map((m) => (
                    <tr key={m.route_id}>
                      <td>
                        <strong>{m.route_code || `Route ${m.route_id}`}</strong>
                      </td>
                      <td>{fmtPctFromFraction(m.weight, 2)}</td>
                      <td className="mono">{m.reason}</td>
                      <td>none</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  })();

  const horizonsPage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="Advance-purchase stratification"
        title="Booking horizons"
        description="Each horizon is indexed against its own base, so the level gap between same-day and advance fares cannot leak into the index."
      />
      {horizonGrouped.length === 0 ? (
        <EmptyState
          title="No horizon indices available"
          message="No horizon index has been computed yet."
        />
      ) : (
        <>
          <div className="metric-rail metric-rail-5">
            {horizonGrouped.map((h) => (
              <MetricCard

                key={h.horizon}
                label={h.label}
                value={fmtIndex(h.meanIndex)}
                detail={`${h.routeCount} route(s) · ${fmtCount(h.matchedProducts)} matched products`}
                testId={`horizon-metric-${h.horizon}`}
              />
            ))}
          </div>
          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Weighting policy</p>
                <h3>{state.horizonPolicy?.policy_id || NOT_AVAILABLE}</h3>
              </div>
              <span className="panel-side-note">
                {state.horizonPolicy?.weighting?.status || NOT_AVAILABLE}
              </span>
            </div>
            <p className="muted-note">
              <code>{state.horizonPolicy?.weighting?.formula || NOT_AVAILABLE}</code>
            </p>
            <ul className="policy-list">
              {(state.horizonPolicy?.weighting?.why || []).map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
          <div className="table-panel">
            <div className="table-panel-header">
              <div>
                <p className="eyebrow">{state.horizonIndices.length} horizon index values</p>
                <h3>Per route and horizon</h3>
              </div>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>Horizon</th>
                    <th>Index</th>
                    <th>Matched</th>
                    <th>New</th>
                    <th>Disappeared</th>
                    <th>Match rate</th>
                  </tr>
                </thead>
                <tbody>
                  {state.horizonIndices.slice(0, 60).map((row) => (
                    <tr key={`${row.route_id}-${row.booking_horizon}`}>
                      <td>{row.route_id}</td>
                      <td>{row.horizon_label}</td>
                      <td>
                        <strong>{fmtIndex(row.value)}</strong>
                      </td>
                      <td>{fmtCount(row.matched_products)}</td>
                      <td>{fmtCount(row.product_churn?.new_products)}</td>
                      <td>{fmtCount(row.product_churn?.disappeared_products)}</td>
                      <td>{fmtPctFromFraction(row.product_churn?.match_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );

  const observationsPage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="Underlying dataset"
        title="Fare observations"
        description="Stored observations with per-record provenance and validation outcome."
        action={
          <button className="button button-dark" onClick={exportCsv} data-testid="export-csv-button">
            <Download size={15} /> Export CSV
          </button>
        }
      />
      {state.observations.length === 0 ? (
        <EmptyState
          title="No observations stored"
          message={
            state.mode === DATA_MODE.DISCONNECTED
              ? "The backend is unreachable."
              : "No collection run has produced observations yet."
          }
        />
      ) : (
        <>
          <div className="filter-panel">
            <div className="filter-panel-title">
              <SlidersHorizontal size={16} />
              <span>Filter observations</span>
              <button
                className="text-button"
                onClick={() => {
                  setFilterOrigin("ALL");
                  setFilterDestination("ALL");
                  setFilterAirline("ALL");
                  setFilterStatus("ALL");
                  setSearch("");
                  setPage(1);
                }}
              >
                Reset
              </button>
            </div>
            <div className="filter-grid">
              <label className="search-field">
                Search
                <input
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Flight, route, airline or source"
                  data-testid="observation-search-input"
                />
                <Search size={15} />
              </label>
              <label>
                Origin
                <select value={filterOrigin} onChange={(e) => { setFilterOrigin(e.target.value); setPage(1); }}>
                  <option value="ALL">All origins</option>
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code}>{a.code}</option>
                  ))}
                </select>
              </label>
              <label>
                Destination
                <select value={filterDestination} onChange={(e) => { setFilterDestination(e.target.value); setPage(1); }}>
                  <option value="ALL">All destinations</option>
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code}>{a.code}</option>
                  ))}
                </select>
              </label>
              <label>
                Airline
                <select value={filterAirline} onChange={(e) => { setFilterAirline(e.target.value); setPage(1); }}>
                  <option value="ALL">All airlines</option>
                  {AIRLINES_LIST.map((a) => (
                    <option key={a.code} value={a.name}>{a.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Validation
                <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}>
                  <option value="ALL">All records</option>
                  <option value="valid">Valid</option>
                  <option value="flagged">Flagged</option>
                </select>
              </label>
            </div>
          </div>

          <div className="table-panel">
            <div className="table-panel-header">
              <div>
                <p className="eyebrow">{sortedObservations.length} observations in view</p>
                <h3>Latest stored observations</h3>
              </div>
              <DataModeChip mode={state.mode} />
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <SortHeader label="Collected" column="collection_datetime" sort={sort} onSort={sortObservations} />
                    <SortHeader label="Route" column="route_code" sort={sort} onSort={sortObservations} />
                    <SortHeader label="Flight" column="flight_number" sort={sort} onSort={sortObservations} />
                    <th>Product</th>
                    <SortHeader label="Fare" column="fare_total" sort={sort} onSort={sortObservations} />
                    <th>Provenance</th>
                    <th>Validation</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleObservations.map((o) => (
                    <tr key={o.observation_id} data-testid={`observation-row-${o.observation_id}`}>
                      <td>
                        <small className="mono">{fmtDateTime(o.collection_datetime)}</small>
                        <small>dep {fmtDate(o.departure_date)}</small>
                      </td>
                      <td>
                        <strong>{o.route_code}</strong>
                        <small>T+{o.booking_horizon_days}</small>
                      </td>
                      <td>
                        {o.airline_name || o.airline_code}
                        <small className="mono">{o.flight_number || NOT_AVAILABLE}</small>
                      </td>
                      <td>
                        <small>{o.cabin_class}</small>
                        <small className="mono">{o.fare_family || "unspecified"}</small>
                        <small>{o.stops === 0 ? "non-stop" : `${o.stops} stop`}</small>
                      </td>
                      <td className="mono">
                        <strong>{fmtInr(o.fare_total)}</strong>
                      </td>
                      <td>
                        <span className="status-pill status-pill-success">
                          {o.data_provenance?.display_label === "OFFLINE PREVIEW" ? "OFFLINE PREVIEW" : "SCRAPED DATA"}
                        </span>
                        <small className="mono">{o.data_provenance?.source_name}</small>
                      </td>
                      <td>
                        <span
                          className={cx(
                            "status-pill",
                            o.validation?.action === "accepted"
                              ? "status-pill-success"
                              : o.validation?.action === "flagged"
                                ? "status-pill-warning"
                                : "status-pill-error",
                          )}
                        >
                          {o.validation?.action}
                        </span>
                        {o.validation?.flags?.length > 0 && (
                          <small className="mono">{o.validation.flags.join(", ")}</small>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="pagination">
            <span>
              Showing {visibleObservations.length} of {sortedObservations.length}
            </span>
            <div>
              <button className="pagination-button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft size={15} /> Previous
              </button>
              <span>
                Page {page} / {totalPages}
              </span>
              <button className="pagination-button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight size={15} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );

  const provenancePage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="Traceability"
        title="Data provenance and sources"
        description="Which sources are collected, which are not, and why."
      />
      <div className="metric-rail">
        <MetricCard label="Current mode" value={state.mode} detail="Drives every figure on this dashboard" testId="provenance-mode-card" />
        <MetricCard
          label="Stored observations"
          value={fmtCount(state.observationStats?.total_observations)}
          detail={Object.entries(state.observationStats?.source_types || {})
            .map(([k, v]) => `${k}: ${fmtCount(v)}`)
            .join(" · ") || "No observations stored"}
          unavailableNote={unavailableNote}
        />
        <MetricCard
          label="Open anomalies"
          value={fmtCount(state.openAnomalyCount)}
          detail={`${fmtCount(state.anomalyCount)} flagged in total`}
          accent="amber"
          unavailableNote={unavailableNote}
        />
        <MetricCard
          label="Last collection"
          value={state.lastRun?.display_label || NOT_AVAILABLE}
          detail={
            state.lastRun
              ? `${state.lastRun.status} · ${fmtRelative(state.lastRun.finished_at)}`
              : "No collection run recorded"
          }
          unavailableNote={unavailableNote}
        />
      </div>

      <div className="table-panel">
        <div className="table-panel-header">
          <div>
            <p className="eyebrow">{state.sources.length} registered sources</p>
            <h3>Source assessment</h3>
          </div>
        </div>
        <p className="muted-note">
          Disabled sources are listed with the reason they are not collected. Most
          airline and travel portals either disallow automated access to their search
          paths or are protected by bot detection; circumventing either is out of scope.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Type</th>
                <th>Status</th>
                <th>Reason / compliance note</th>
              </tr>
            </thead>
            <tbody>
              {state.sources.map((s) => (
                <tr key={s.name} data-testid={`source-row-${s.name}`}>
                  <td>
                    <strong>{s.display_name}</strong>
                    <small className="mono">{s.name}</small>
                  </td>
                  <td>{s.provenance_label}</td>
                  <td>
                    <span
                      className={cx(
                        "status-pill",
                        s.enabled ? "status-pill-success" : "status-pill-muted",
                      )}
                    >
                      {s.enabled ? "Collected" : "Not collected"}
                    </span>
                  </td>
                  <td className="reason-cell">{s.disabled_reason || s.compliance_note}</td>
                </tr>
              ))}
              {state.sources.length === 0 && (
                <tr>
                  <td colSpan={4}>Source registry unavailable — the API could not be reached.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const methodologyPage = (
    <div className="page-wrap page-wrap-reading">
      <SectionHeading
        eyebrow="Statistical method"
        title="Methodology"
        description="From a collected quote to a traceable, reproducible price signal."
      />
      <div className="methodology-grid">
        {METHODOLOGY_STEPS.map((step) => (
          <article className="method-card" key={step.n}>
            <span>{String(step.n).padStart(2, "0")}</span>
            <h3>{step.title}</h3>
            <p>{step.desc}</p>
          </article>
        ))}
      </div>

      <div className="formula-grid">
        <article className="formula-panel">
          <p className="eyebrow">Elementary aggregate</p>
          <h3>Matched-model Jevons</h3>
          <p>
            The geometric mean of price relatives over products matched between periods.
            Computed in log space for numerical stability.
          </p>
          <code>I(t) = [ ∏ₚ ( pₚ(t) / pₚ(0) ) ] ^ (1/n)</code>
        </article>
        <article className="formula-panel formula-panel-dark">
          <p className="eyebrow">National level</p>
          <h3>Weighted aggregation</h3>
          <p>
            Route indices combined with provisional passenger-volume weights that sum to
            exactly 1.0.
          </p>
          <code>Index(t) = ∑ᵣ ( wᵣ × Iᵣ(t) ) × 100</code>
        </article>
      </div>

      {methodology && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Declared limitations</p>
              <h3>What this index does not do</h3>
            </div>
            <span className="panel-side-note">{methodology.methodology_version}</span>
          </div>
          <ul className="policy-list" data-testid="methodology-limitations">
            {(methodology.known_limitations || []).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const monitoringPage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="Operations"
        title="Monitoring"
        description="Collection configuration, run history and the developer API surface."
        action={
          <button
            className="button button-dark"
            onClick={runCollection}
            disabled={collecting}
            data-testid="trigger-collection-button"
          >
            {collecting ? <RefreshCw className="spin" size={15} /> : <Radar size={15} />}
            {collecting ? "Running…" : "Trigger collection cycle"}
          </button>
        }
      />

      <div className="health-grid">
        <MetricCard
          label="Configured mode"
          value={state.collectionStatus?.configured_mode || NOT_AVAILABLE}
          detail={state.collectionStatus?.provenance_label || unavailableNote}
        />
        <MetricCard
          label="Usable sources"
          value={fmtCount(state.collectionStatus?.usable_sources_for_mode?.length)}
          detail={
            state.collectionStatus?.can_collect
              ? state.collectionStatus.usable_sources_for_mode.join(", ")
              : state.collectionStatus?.cannot_collect_reason || unavailableNote
          }
          accent={state.collectionStatus?.can_collect ? "green" : "amber"}
        />
        <MetricCard
          label="Scheduler"
          value={
            state.collectionStatus?.scheduler
              ? state.collectionStatus.scheduler.running
                ? "Running"
                : state.collectionStatus.scheduler.enabled
                  ? "Enabled, idle"
                  : "Disabled"
              : NOT_AVAILABLE
          }
          detail={
            state.collectionStatus?.scheduler?.next_run
              ? `Next run ${fmtDateTime(state.collectionStatus.scheduler.next_run)}`
              : "Collection runs only when triggered"
          }
        />
        <MetricCard
          label="Open anomalies"
          value={fmtCount(state.openAnomalyCount)}
          detail="Awaiting review"
          accent="amber"
          unavailableNote={unavailableNote}
        />
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Admin token</p>
            <h3>Required when the backend configures one</h3>
          </div>
        </div>
        <label className="modal-field">
          X-Admin-Token
          <input
            type="password"
            value={adminToken}
            onChange={(e) => setAdminToken(e.target.value)}
            placeholder="Leave blank if the backend has no token configured"
            data-testid="admin-token-input"
          />
        </label>
        <p className="muted-note">
          Held in memory for this browser session only and sent solely to the collection
          trigger endpoint. It is never persisted.
        </p>
      </div>

      {logs.length > 0 && (
        <div className="event-stream" data-testid="collection-log">
          <p className="eyebrow">Collection log</p>
          {logs.map((log, i) => (
            <p key={`${log}-${i}`}>{log}</p>
          ))}
        </div>
      )}

      <div className="api-panel">
        <div className="api-panel-header">
          <div>
            <p className="eyebrow">Developer surface</p>
            <h3>API explorer</h3>
          </div>
          <span className="mono">{API_ENDPOINTS_LIST[apiIndex].method}</span>
        </div>
        <select
          value={apiIndex}
          onChange={(e) => {
            setApiIndex(Number(e.target.value));
            setApiResponse(null);
          }}
          data-testid="api-endpoint-select"
        >
          {API_ENDPOINTS_LIST.map((item, i) => (
            <option key={item.path} value={i}>
              {item.method} {item.path}
            </option>
          ))}
        </select>
        <p>{API_ENDPOINTS_LIST[apiIndex].description}</p>
        <pre data-testid="api-response">
          {apiResponse
            ? JSON.stringify(apiResponse, null, 2)
            : "Run the request to see the live response. No canned payload is shown."}
        </pre>
        <button className="button button-dark" onClick={testEndpoint} disabled={apiLoading} data-testid="run-request-button">
          {apiLoading ? "Requesting…" : "Run request"} <ArrowRight size={15} />
        </button>
        <p className="muted-note">
          Target: <code>{API_BASE || "not configured"}</code>
        </p>
      </div>
    </div>
  );

  const alertsPage = (
    <div className="page-wrap">
      <SectionHeading
        eyebrow="Watchlist"
        title="Price alerts"
        description="Browser-local watch builder. Server-side monitoring is not implemented."
      />
      <div className="legacy-engine-wrap" role="region" aria-label="Price alert engine">
        <PriceAlertEngine
          isDarkMode={dark}
          onTriggerToast={notify}
          routes={state.routeIndices}
        />
      </div>
    </div>
  );

  const aboutPage = (
    <div className="page-wrap page-wrap-reading">
      <SectionHeading
        eyebrow="Context"
        title="About this index"
        description="A research prototype for a more timely view of domestic transport price movement."
      />
      <div className="about-hero">
        <div className="about-spotlight-card">
          <p className="eyebrow">Scope</p>
          <h3>Index methodology validated end to end, with data acquisition stated honestly.</h3>
          <p>
            The statistical pipeline — matched-model elementary aggregates,
            horizon stratification, weighted aggregation, validation, persistence and
            revision tracking — is implemented and tested. Data acquisition covers one
            genuine permitted source; every other source considered is listed with the
            reason it is not collected.
          </p>
        </div>
        <div>
          <p className="eyebrow">The problem</p>
          <h3>
            Airfares move hundreds of times a day. A monthly counter visit cannot see
            that.
          </h3>
          <p>
            Advance-purchase price discrimination means a same-day ticket can cost
            several times the same seat booked a month out. Treating that gap as
            inflation is the central measurement error this design avoids, by indexing
            each booking horizon separately.
          </p>
        </div>
      </div>
      <div className="about-copy-grid">
        {[
          ["Traceable", "Every published figure records the observations, weights, base period, validation rules and methodology version that produced it."],
          ["Reproducible", "Figures are persisted, not regenerated. A restart serves the same numbers, and each recomputation appends a revision record."],
          ["Honestly labelled", "Simulated data can never be presented as collected data, and a capability that does not exist reports NOT IMPLEMENTED."],
        ].map(([title, text], i) => (
          <article key={title}>
            <span>{String(i + 1).padStart(2, "0")}</span>
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </div>
  );

  const view =
    tab === "home" ? overview
      : tab === "price-index" ? indexPage
      : tab === "routes" ? routesPage
      : tab === "horizons" ? horizonsPage
      : tab === "alerts" ? alertsPage
      : tab === "flight-data" ? observationsPage
      : tab === "provenance" ? provenancePage
      : tab === "monitoring" ? monitoringPage
      : tab === "methodology" ? methodologyPage
      : aboutPage;

  return (
    <div className={cx("app-shell", mobileNavOpen && "mobile-nav-open")}>
      <header className="site-header">
        <div className="header-inner">
          <button className="brand-lockup" onClick={() => go("home")} data-testid="brand-home-button">
            <img
              src={getAssetPath(mounted && dark ? "/logo_dark.png" : "/logo.png")}
              alt="Airfare CPI"
              className="brand-logo-img"
              suppressHydrationWarning
            />
            <span>
              <strong>Airfare CPI</strong>
              <small>Research prototype</small>
            </span>
          </button>
          <nav className={cx("primary-nav", mobileNavOpen && "is-open")} aria-label="Primary navigation">
            {NAV.map(([id, label, Icon]) => (
              <button
                className={tab === id ? "is-active" : ""}
                key={id}
                onClick={() => go(id)}
                data-testid={`nav-${id}-button`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </nav>
          <div className="header-actions">
            <button className="copilot-trigger" onClick={() => setCopilotOpen(true)} data-testid="header-copilot-button">
              <CopilotSymbol size={18} /> <span>Copilot</span>
            </button>
            <button className="icon-button" aria-label="Toggle theme" onClick={() => setDark((v) => !v)} data-testid="theme-toggle-button">
              {mounted && dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {currentUser ? (
              <button className="user-profile-badge" onClick={() => setModal("auth")} data-testid="user-profile-button">
                <span className="user-avatar" style={{ backgroundColor: currentUser.avatarColor || "#10b981" }}>
                  {currentUser.initials}
                </span>
                <span className="user-info">
                  <strong>{currentUser.name}</strong>
                  <small>{currentUser.badge || "Demo persona"}</small>
                </span>
              </button>
            ) : (
              <button className="sign-in-button" onClick={() => setModal("auth")} data-testid="sign-in-button">
                Sign In
              </button>
            )}
          </div>
          <button
            className="mobile-menu-button"
            aria-label={mobileNavOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen((v) => !v)}
            data-testid="mobile-navigation-button"
          >
            {mobileNavOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </header>

      <main className="main-content">
        {loading ? (
          <div className="page-wrap">
            <p className="muted-note" data-testid="loading-note">
              Loading figures from the API…
            </p>
          </div>
        ) : (
          view
        )}
      </main>

      <footer className="site-footer">
        <div>
          <button className="footer-brand" onClick={() => go("home")}>
            <img
              src={getAssetPath(mounted && dark ? "/logo_dark.png" : "/logo.png")}
              alt="Airfare CPI"
              className="brand-logo-img"
              suppressHydrationWarning
            />
            <span>
              <strong>Airfare CPI</strong> <span>Research prototype</span>
            </span>
          </button>
          <p>
            Not an official statistic. Not issued by, endorsed by, or affiliated with
            MoSPI, the NSO, or the Government of India.
          </p>
        </div>
        <div className="footer-links">
          <button onClick={() => go("methodology")}>Methodology</button>
          <button onClick={() => go("provenance")}>Provenance</button>
          <button onClick={() => setModal("bulletin")}>Research bulletin</button>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
        </div>
        <span className="footer-meta">
          {state.methodologyVersion || "methodology version unavailable"}
        </span>
      </footer>

      {modal === "bulletin" && (
        <ModalFrame
          title="Research bulletin"
          eyebrow="Prototype / Research Output — not an official release"
          onClose={() => setModal(null)}
          wide
          testId="bulletin-modal"
        >
          <div className="bulletin-paper">
            <div className="bulletin-disclaimer" data-testid="bulletin-disclaimer">
              <strong>Prototype / Research Output.</strong> This is not an official
              statistical release and carries no government attribution.
            </div>
            <div className="bulletin-id">
              <span>Data provenance: {state.mode}</span>
              <span>Base: {state.basePeriod || NOT_AVAILABLE}</span>
            </div>
            <div className="bulletin-metrics">
              <div>
                <small>Headline index</small>
                <strong>{fmtIndex(state.headlineIndex)}</strong>
              </div>
              <div>
                <small>Period change</small>
                <strong>
                  {state.momStatus === "available" ? fmtChange(state.momChangePct) : NOT_AVAILABLE}
                </strong>
              </div>
              <div>
                <small>Year-on-year</small>
                <strong>
                  {state.yoyStatus === "available" ? fmtChange(state.yoyChangePct) : NOT_AVAILABLE}
                </strong>
              </div>
              <div>
                <small>Sample size</small>
                <strong>{fmtCount(state.sampleSize)}</strong>
              </div>
            </div>
            <p>
              {noIndexYet
                ? state.reason
                : `Computed from ${fmtCount(state.sampleSize)} observations across ` +
                  `${fmtCount(state.routesIncluded)} of ${fmtCount(state.routesInBasket)} corridors ` +
                  `(${fmtPctFromFraction(state.coverageWeight)} of basket weight). ` +
                  `Seasonal adjustment: ${state.seasonalAdjustment}. ` +
                  `Year-on-year: ${changeReason(state.yoyStatus) || fmtChange(state.yoyChangePct)}`}
            </p>
          </div>
          <div className="modal-actions">
            <a
              className="button button-outline"
              href={`${API_BASE}/api/v1/reports/monthly/html`}
              target="_blank"
              rel="noreferrer"
              data-testid="bulletin-open-full-link"
            >
              Open the full bulletin <ArrowUpRight size={15} />
            </a>
            <button className="button button-outline" onClick={() => setModal(null)}>
              Close
            </button>
          </div>
        </ModalFrame>
      )}

      <AuthModal
        isOpen={modal === "auth"}
        onClose={() => setModal(null)}
        currentUser={currentUser}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onNotify={notify}
      />

      <AviationCopilotModal
        isOpen={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        dashboardState={state}
      />

      <RouteDetailModal
        route={detailRoute}
        isOpen={Boolean(detailRoute)}
        onClose={() => setDetailRoute(null)}
        isDarkMode={dark}
        dataMode={state.mode}
      />

      {toast && (
        <div className="toast" role="status" data-testid="app-toast">
          <Check size={15} /> {toast}
        </div>
      )}
    </div>
  );
}
