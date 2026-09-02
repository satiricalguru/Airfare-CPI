"use client";

/**
 * SIH26056 — Route detail modal with multi-timeframe analytics (7D, 1M, 3M, 6M, 1Y),
 * automated on-demand scraping, and today's data verification.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  X,
  RefreshCw,
  Calendar,
  TrendingUp,
  TrendingDown,
  Activity,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Database,
} from "lucide-react";
import {
  loadRouteHistory,
  loadRouteHorizons,
  loadRouteObservations,
  scrapeRouteById,
  NOT_AVAILABLE,
} from "../lib/api";
import {
  fmtCount,
  fmtIndex,
  fmtInr,
  fmtPctFromFraction,
  fmtShortDate,
} from "../lib/format";
import { DataModeChip } from "./DataModeBanner";

const TABS = [
  ["trend", "Index history"],
  ["horizons", "Horizon curve"],
  ["carriers", "Carrier spread"],
  ["distribution", "Fare distribution"],
];

const TIMEFRAME_OPTIONS = [
  { key: "7D", days: 7, label: "7D" },
  { key: "1M", days: 30, label: "1M" },
  { key: "3M", days: 90, label: "3M" },
  { key: "6M", days: 180, label: "6M" },
  { key: "1Y", days: 365, label: "1Y" },
];

function EmptyPanel({ message, onScrape, isScraping }) {
  return (
    <div className="empty-panel-wrapper" data-testid="route-detail-empty">
      <p className="muted-note">{message}</p>
      {onScrape && (
        <button
          className="button button-primary button-sm"
          onClick={onScrape}
          disabled={isScraping}
          style={{ marginTop: 12 }}
        >
          <RefreshCw size={14} className={isScraping ? "spin" : ""} />
          <span>{isScraping ? "Scraping Corridor Data…" : "Scrape & Populate Corridor Data"}</span>
        </button>
      )}
    </div>
  );
}

/**
 * Outer shell. Keying the content on `route_id` means per-route state resets by
 * remounting rather than by a state update inside an effect.
 */
export default function RouteDetailModal({ route, isOpen, onClose, dataMode }) {
  if (!isOpen || !route?.route_id) return null;
  return (
    <RouteDetailContent
      key={route.route_id}
      route={route}
      onClose={onClose}
      dataMode={dataMode}
    />
  );
}

function RouteDetailContent({ route, onClose, dataMode }) {
  const [tab, setTab] = useState("trend");
  const [timeframe, setTimeframe] = useState("1M");
  const [history, setHistory] = useState(null);
  const [horizons, setHorizons] = useState(null);
  const [observations, setObservations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isScraping, setIsScraping] = useState(false);
  const isScrapingRef = useRef(false);
  useEffect(() => {
    isScrapingRef.current = isScraping;
  }, [isScraping]);
  const [scrapeNotice, setScrapeNotice] = useState(null);
  const [errors, setErrors] = useState({});

  const routeId = route.route_id;

  const loadData = useCallback(async () => {
    setLoading(true);
    const [h, hz, obs] = await Promise.all([
      loadRouteHistory(routeId, 365),
      loadRouteHorizons(routeId),
      loadRouteObservations(routeId, 300),
    ]);

    const historyData = h.ok ? h.data?.history ?? h.data?.data ?? [] : [];
    setHistory(historyData);
    setHorizons(hz.ok ? hz.data?.horizons ?? [] : null);
    setObservations(obs.ok ? obs.data?.fares ?? [] : null);
    setErrors({
      history: h.ok ? null : h.error,
      horizons: hz.ok ? null : hz.error,
      observations: obs.ok ? null : obs.error,
    });
    setLoading(false);
    return historyData;
  }, [routeId]);

  const handleTriggerScrape = useCallback(async (showNotice = true) => {
    if (isScrapingRef.current) return;
    setIsScraping(true);
    if (showNotice) {
      setScrapeNotice({ type: "info", text: "Scraping real-time fares and calculating indices for today…" });
    }

    try {
      const res = await scrapeRouteById(routeId);
      if (res.ok) {
        setScrapeNotice({ type: "success", text: "Corridor fares collected and indices refreshed for today!" });
        await loadData();
        setTimeout(() => setScrapeNotice(null), 4000);
      } else {
        setScrapeNotice({
          type: "warning",
          text: `Scrape notice: ${res.error || "Simulated observations updated."}`,
        });
        await loadData();
        setTimeout(() => setScrapeNotice(null), 5000);
      }
    } catch (err) {
      setScrapeNotice({ type: "error", text: `Scrape failed: ${err?.message || "network error"}` });
      setTimeout(() => setScrapeNotice(null), 5000);
    } finally {
      setIsScraping(false);
    }
  }, [routeId, loadData]);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      const data = await loadData();
      // If no history exists for this route, trigger on-demand scraping
      if ((!data || data.length < 2) && !cancelled) {
        handleTriggerScrape(false);
      }
    };

    void init();
    return () => {
      cancelled = true;
    };
  }, [loadData, handleTriggerScrape]);

  // ── derived series for the selected timeframe ──

  const trendSeries = useMemo(() => {
    if (!history?.length) return [];
    const option = TIMEFRAME_OPTIONS.find((t) => t.key === timeframe) || TIMEFRAME_OPTIONS[1];

    // Sort chronologically
    const sorted = history.slice().sort((a, b) => {
      const ta = new Date(a.index_date || a.date).getTime();
      const tb = new Date(b.index_date || b.date).getTime();
      return ta - tb;
    });

    const latestTime = sorted.reduce((max, pt) => {
      const t = new Date(pt.index_date || pt.date).getTime();
      return Number.isFinite(t) && t > max ? t : max;
    }, 0);

    const cutoff = latestTime - option.days * 86400000;
    const filtered = sorted.filter(
      (pt) => new Date(pt.index_date || pt.date).getTime() >= cutoff
    );
    const chosen =
      filtered.length >= 2
        ? filtered
        : sorted.slice(-Math.min(sorted.length, Math.max(2, option.days)));

    return chosen.map((point) => ({
      date: fmtShortDate(point.index_date || point.date),
      fullDate: point.index_date || point.date,
      index: point.value,
      sampleSize: point.matched_products || point.sample_size || null,
    }));
  }, [history, timeframe]);

  // Summary statistics for the chosen timeframe
  const timeframeMetrics = useMemo(() => {
    if (!trendSeries || trendSeries.length < 2) return null;
    const first = trendSeries[0];
    const last = trendSeries[trendSeries.length - 1];
    const vals = trendSeries
      .map((p) => p.index)
      .filter((v) => typeof v === "number" && !isNaN(v));
    const minVal = Math.min(...vals);
    const maxVal = Math.max(...vals);
    const change =
      first.index > 0 ? ((last.index - first.index) / first.index) * 100 : 0;

    return {
      startDate: first.date,
      endDate: last.date,
      startVal: first.index,
      endVal: last.index,
      change,
      minVal,
      maxVal,
      count: trendSeries.length,
    };
  }, [trendSeries]);

  const horizonSeries = useMemo(
    () =>
      (horizons || [])
        .slice()
        .sort((a, b) => a.booking_horizon - b.booking_horizon)
        .map((row) => ({
          horizon: row.horizon_label,
          index: row.value,
          meanFare: row.geometric_mean_price_inr,
          matched: row.matched_products,
        })),
    [horizons]
  );

  const carrierSpread = useMemo(() => {
    if (!observations?.length) return [];
    const byCarrier = new Map();
    for (const o of observations) {
      if (!o.validation?.is_valid) continue;
      const key = o.airline_name || o.airline_code;
      if (!byCarrier.has(key)) byCarrier.set(key, []);
      byCarrier.get(key).push(o.fare_total);
    }
    return [...byCarrier.entries()]
      .map(([carrier, fares]) => {
        const sorted = fares.slice().sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        return {
          carrier,
          median:
            sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2,
          min: sorted[0],
          max: sorted[sorted.length - 1],
          count: sorted.length,
        };
      })
      .sort((a, b) => a.median - b.median);
  }, [observations]);

  const distribution = useMemo(() => {
    const fares = (observations || [])
      .filter((o) => o.validation?.is_valid)
      .map((o) => o.fare_total)
      .sort((a, b) => a - b);

    if (fares.length < 4) return null;

    const quantile = (p) => {
      const pos = (fares.length - 1) * p;
      const lower = Math.floor(pos);
      const upper = Math.ceil(pos);
      if (lower === upper) return fares[lower];
      return fares[lower] + (fares[upper] - fares[lower]) * (pos - lower);
    };

    const q1 = quantile(0.25);
    const median = quantile(0.5);
    const q3 = quantile(0.75);
    const iqr = q3 - q1;

    return {
      count: fares.length,
      min: fares[0],
      q1,
      median,
      q3,
      max: fares[fares.length - 1],
      iqr,
      lowerFence: q1 - 3 * iqr,
      upperFence: q3 + 3 * iqr,
      belowFence: fares.filter((f) => f < q1 - 3 * iqr).length,
      aboveFence: fares.filter((f) => f > q3 + 3 * iqr).length,
    };
  }, [observations]);

  return (
    <div className="modal-backdrop" onClick={onClose} data-testid="route-detail-modal">
      <div className="modal-panel modal-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">Corridor detail</p>
            <h3>{route.route_code || `Route ${route.route_id}`}</h3>
            <p className="muted-note">
              {route.origin_city} → {route.destination_city} · index{" "}
              {fmtIndex(route.value)} · weight {fmtPctFromFraction(route.weight, 2)}
            </p>
          </div>
          <div className="modal-header-actions">
            <button
              className="button button-outline button-sm"
              onClick={() => handleTriggerScrape(true)}
              disabled={isScraping}
              title="Scrape and update live observations & indices for this corridor"
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              <RefreshCw size={13} className={isScraping ? "spin" : ""} />
              <span>{isScraping ? "Scraping Data…" : "Scrape / Update Live Data"}</span>
            </button>
            <DataModeChip mode={dataMode} />
            <button className="icon-button" aria-label="Close" onClick={onClose} data-testid="route-detail-close-button">
              <X size={18} />
            </button>
          </div>
        </div>

        {scrapeNotice && (
          <div
            className={`scrape-alert-banner ${scrapeNotice.type === "success" ? "alert-success" : scrapeNotice.type === "error" ? "alert-error" : "alert-info"}`}
            style={{
              margin: "0 24px 12px 24px",
              padding: "10px 14px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "12px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid var(--line)",
            }}
          >
            {scrapeNotice.type === "success" ? (
              <CheckCircle2 size={16} color="var(--green)" />
            ) : scrapeNotice.type === "error" ? (
              <AlertCircle size={16} color="var(--amber)" />
            ) : (
              <RefreshCw size={16} className="spin" color="var(--cyan)" />
            )}
            <span>{scrapeNotice.text}</span>
          </div>
        )}

        <div className="segmented-control route-detail-tabs">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "is-active" : ""}
              onClick={() => setTab(key)}
              data-testid={`route-detail-tab-${key}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="route-detail-body">
          {loading && <p className="muted-note">Loading stored data for this corridor…</p>}

          {!loading && tab === "trend" && (
            <>
              {/* Multi-Timeframe Minimal Underline Bar (Image 2 Style) */}
              <div
                className="corridor-timeframe-header"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "14px",
                  marginBottom: "16px",
                  paddingBottom: "4px",
                }}
              >
                <div className="minimal-timeframe-bar">
                  {TIMEFRAME_OPTIONS.map((tf) => {
                    const isActive = timeframe === tf.key;
                    return (
                      <button
                        key={tf.key}
                        className={`minimal-timeframe-btn ${isActive ? "is-active" : ""}`}
                        onClick={() => setTimeframe(tf.key)}
                        data-testid={`timeframe-btn-${tf.key}`}
                      >
                        <span>{tf.label}</span>
                        {isActive && <span className="active-underline" />}
                      </button>
                    );
                  })}
                </div>

                {timeframeMetrics && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                      fontSize: "11px",
                      color: "var(--muted)",
                    }}
                  >
                    <span>
                      <strong>{timeframeMetrics.startDate}</strong> → <strong>{timeframeMetrics.endDate}</strong>
                    </span>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "3px",
                        fontWeight: "700",
                        color: timeframeMetrics.change >= 0 ? "var(--green)" : "var(--amber)",
                      }}
                    >
                      {timeframeMetrics.change >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                      {timeframeMetrics.change >= 0 ? "+" : ""}
                      {timeframeMetrics.change.toFixed(2)}%
                    </span>
                    <span>
                      Range: <strong>{fmtIndex(timeframeMetrics.minVal)}</strong> –{" "}
                      <strong>{fmtIndex(timeframeMetrics.maxVal)}</strong>
                    </span>
                    <span>
                      Points: <strong>{timeframeMetrics.count}</strong>
                    </span>
                  </div>
                )}
              </div>

              {trendSeries.length >= 2 ? (
                <>
                  <div className="chart-wrap chart-wrap-modal">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={trendSeries}>
                        <CartesianGrid vertical={false} stroke="rgba(128,128,128,0.15)" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11, fill: "var(--muted)" }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          domain={["auto", "auto"]}
                          tick={{ fontSize: 11, fill: "var(--muted)" }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            fontSize: 12,
                            background: "var(--paper-bright)",
                            color: "var(--ink)",
                            border: "1px solid var(--line)",
                            borderRadius: 8,
                          }}
                          formatter={(val) => [fmtIndex(val), "Corridor Index"]}
                          labelFormatter={(label) => `Date: ${label}`}
                        />
                        <Line
                          type="monotone"
                          dataKey="index"
                          name="Route index"
                          stroke="var(--green)"
                          strokeWidth={2.5}
                          dot={trendSeries.length <= 15 ? { r: 3, fill: "var(--green)" } : false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="muted-note" style={{ marginTop: "12px" }}>
                    Showing <strong>{trendSeries.length} stored index point(s)</strong> for the selected{" "}
                    <strong>{TIMEFRAME_OPTIONS.find((t) => t.key === timeframe)?.label}</strong> window.
                    This is the published matched-model Jevons series for this corridor up to today, not a smoothed curve.
                  </p>
                </>
              ) : (
                <EmptyPanel
                  message={
                    errors.history
                      ? `Index history could not be loaded: ${errors.history}`
                      : isScraping
                      ? "Scraping live corridor fares and computing historical Jevons index points…"
                      : `This corridor currently has ${trendSeries.length} stored index point(s) for the selected timeframe. Click below to scrape and calculate data.`
                  }
                  onScrape={() => handleTriggerScrape(true)}
                  isScraping={isScraping}
                />
              )}
            </>
          )}

          {!loading && tab === "horizons" && (
            horizonSeries.length > 0 ? (
              <>
                <div className="chart-wrap chart-wrap-modal">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={horizonSeries}>
                      <CartesianGrid vertical={false} stroke="rgba(128,128,128,0.15)" />
                      <XAxis dataKey="horizon" tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: "var(--paper-bright)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: 8 }} />
                      <Bar dataKey="index" name="Horizon index" fill="var(--green)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Horizon</th>
                        <th>Index</th>
                        <th>Geometric mean fare</th>
                        <th>Matched products</th>
                      </tr>
                    </thead>
                    <tbody>
                      {horizonSeries.map((h) => (
                        <tr key={h.horizon}>
                          <td>{h.horizon}</td>
                          <td><strong>{fmtIndex(h.index)}</strong></td>
                          <td className="mono">{fmtInr(h.meanFare)}</td>
                          <td>{fmtCount(h.matched)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="muted-note">
                  Each horizon is indexed against its own base level, so these values are
                  comparable with one another as price CHANGE even though the underlying
                  fare levels differ by construction.
                </p>
              </>
            ) : (
              <EmptyPanel
                message={
                  errors.horizons
                    ? `Horizon indices could not be loaded: ${errors.horizons}`
                    : "No horizon index has been computed for this corridor."
                }
                onScrape={() => handleTriggerScrape(true)}
                isScraping={isScraping}
              />
            )
          )}

          {!loading && tab === "carriers" && (
            carrierSpread.length > 0 ? (
              <>
                <div className="spotlight-bars">
                  {carrierSpread.map((c) => {
                    const widest = Math.max(...carrierSpread.map((x) => x.median));
                    return (
                      <div className="spotlight-bar" key={c.carrier}>
                        <div>
                          <span>{c.carrier}</span>
                          <strong>{fmtInr(c.median)}</strong>
                        </div>
                        <i>
                          <b style={{ width: `${Math.round((c.median / widest) * 100)}%` }} />
                        </i>
                        <small>
                          {fmtCount(c.count)} observation(s) · range {fmtInr(c.min)} –{" "}
                          {fmtInr(c.max)}
                        </small>
                      </div>
                    );
                  })}
                </div>
                <p className="muted-note">
                  Median observed fare per carrier, from stored observations. These are
                  price LEVELS, not index values, and are not adjusted for differences in
                  cabin, fare family or baggage between carriers.
                </p>
              </>
            ) : (
              <EmptyPanel
                message={
                  errors.observations
                    ? `Observations could not be loaded: ${errors.observations}`
                    : "No valid observations are stored for this corridor."
                }
                onScrape={() => handleTriggerScrape(true)}
                isScraping={isScraping}
              />
            )
          )}

          {!loading && tab === "distribution" && (
            distribution ? (
              <>
                <div className="distribution-grid">
                  {[
                    ["Minimum", distribution.min],
                    ["Q1", distribution.q1],
                    ["Median", distribution.median],
                    ["Q3", distribution.q3],
                    ["Maximum", distribution.max],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <small>{label}</small>
                      <strong>{fmtInr(value)}</strong>
                    </div>
                  ))}
                </div>
                <div className="distribution-fences">
                  <p>
                    <strong>IQR</strong> {fmtInr(distribution.iqr)} · fences at 3× IQR:{" "}
                    {fmtInr(distribution.lowerFence)} to {fmtInr(distribution.upperFence)}
                  </p>
                  <p>
                    {distribution.belowFence + distribution.aboveFence === 0
                      ? "No stored observation for this corridor falls outside the fences."
                      : `${distribution.belowFence} below and ${distribution.aboveFence} above the fences.`}
                  </p>
                </div>
                <p className="muted-note">
                  Quartiles computed from {fmtCount(distribution.count)} stored valid
                  observation(s), using the same 3× IQR multiplier the backend validator
                  applies. Flagged outliers are kept in the index — they are treated as
                  genuine volatility unless review confirms a collection error.
                </p>
              </>
            ) : (
              <EmptyPanel
                message={
                  errors.observations
                    ? `Observations could not be loaded: ${errors.observations}`
                    : `Fewer than four valid observations are stored for this corridor, so quartiles would not be meaningful. Value shown: ${NOT_AVAILABLE}.`
                }
                onScrape={() => handleTriggerScrape(true)}
                isScraping={isScraping}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
