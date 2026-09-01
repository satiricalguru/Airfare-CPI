"use client";

/**
 * SIH26056 — Route detail.
 *
 * What the audit found here
 * -------------------------
 * The "30-day historical trend" was `Math.sin(i * 0.45) * 450 + …` — a sine wave drawn
 * to look like a price series, presented as history. The "IQR box plot" was fixed
 * multipliers of a single number, presented as statistical analysis. Neither was
 * derived from data.
 *
 * Both are replaced by real stored values fetched from the API:
 *
 *   - the trend is the route's stored index history (`/api/v1/index/routes/{id}`)
 *   - the horizon curve is the route's stored horizon indices
 *   - the carrier spread and fare distribution come from stored observations
 *
 * When a series is unavailable, the tab says so. Nothing is synthesised to fill a
 * panel.
 */

import { useEffect, useMemo, useState } from "react";
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
import { X } from "lucide-react";
import {
  loadRouteHistory,
  loadRouteHorizons,
  loadRouteObservations,
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

function EmptyPanel({ message }) {
  return (
    <p className="muted-note" data-testid="route-detail-empty">
      {message}
    </p>
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
  const [history, setHistory] = useState(null);
  const [horizons, setHorizons] = useState(null);
  const [observations, setObservations] = useState(null);
  // Starts true: the component only mounts when a route is selected, and loading
  // begins immediately. Set to false after the awaited fetch, never synchronously.
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState({});

  const routeId = route.route_id;

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      const [h, hz, obs] = await Promise.all([
        loadRouteHistory(routeId, 90),
        loadRouteHorizons(routeId),
        loadRouteObservations(routeId, 300),
      ]);
      if (cancelled) return;

      setHistory(h.ok ? h.data?.history ?? [] : null);
      setHorizons(hz.ok ? hz.data?.horizons ?? [] : null);
      setObservations(obs.ok ? obs.data?.fares ?? [] : null);
      setErrors({
        history: h.ok ? null : h.error,
        horizons: hz.ok ? null : hz.error,
        observations: obs.ok ? null : obs.error,
      });
      setLoading(false);
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [routeId]);

  // ── derived series, all from stored data ──

  const trendSeries = useMemo(
    () =>
      (history || []).map((point) => ({
        date: fmtShortDate(point.index_date),
        index: point.value,
      })),
    [history],
  );

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
    [horizons],
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

  /**
   * Fare distribution with genuine quartiles and IQR fences.
   *
   * Computed from the actual observations, using the same 3x multiplier the backend
   * validator applies. Requires at least four observations; below that a quartile is
   * not meaningful and the panel says so rather than drawing a box.
   */
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
            <DataModeChip mode={dataMode} />
            <button className="icon-button" aria-label="Close" onClick={onClose} data-testid="route-detail-close-button">
              <X size={18} />
            </button>
          </div>
        </div>

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
          {loading && <p className="muted-note">Loading stored data for this route…</p>}

          {!loading && tab === "trend" && (
            trendSeries.length >= 2 ? (
              <>
                <div className="chart-wrap chart-wrap-modal">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendSeries}>
                      <CartesianGrid vertical={false} stroke="rgba(128,128,128,0.15)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                      <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, background: "var(--paper-bright)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: 8 }} />
                      <Line type="monotone" dataKey="index" name="Route index" stroke="var(--green)" strokeWidth={2.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="muted-note">
                  {trendSeries.length} stored index point(s). This is the published
                  series for this corridor, not a smoothed or synthesised curve.
                </p>
              </>
            ) : (
              <EmptyPanel
                message={
                  errors.history
                    ? `Index history could not be loaded: ${errors.history}`
                    : `This corridor has ${trendSeries.length} stored index point(s). At least two are needed to draw a trend, and no curve is synthesised to fill the panel.`
                }
              />
            )
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
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
