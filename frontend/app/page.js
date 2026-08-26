"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* ── Animated Counter ── */
function AnimatedNumber({ value, decimals = 2, prefix = "", suffix = "" }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value == null) return;
    const target = parseFloat(value);
    const duration = 1200;
    const steps = 60;
    const stepTime = duration / steps;
    let current = display;
    const increment = (target - current) / steps;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      current += increment;
      setDisplay(current);
      if (step >= steps) {
        setDisplay(target);
        clearInterval(timer);
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [value]);

  return (
    <span>
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}

/* ── Sidebar ── */
function Sidebar({ activePage, setActivePage }) {
  const navItems = [
    { id: "overview", icon: "📊", label: "National Overview" },
    { id: "routes", icon: "✈️", label: "Route Explorer" },
    { id: "health", icon: "💚", label: "Pipeline Health" },
    { id: "methodology", icon: "📐", label: "Methodology" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">✈</div>
          <div className="sidebar-logo-text">
            <h1>Airfare CPI</h1>
            <span>SIH26056 · MoSPI</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activePage === item.id ? "active" : ""}`}
            onClick={() => setActivePage(item.id)}
          >
            <span className="nav-item-icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-badge">
          <span className="live-dot" />
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
}

/* ── Custom Tooltip ── */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "rgba(17,24,39,0.95)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 8,
        padding: "10px 14px",
        fontSize: 12,
        fontFamily: "var(--font-mono)",
      }}
    >
      <div style={{ color: "#94a3b8", marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   NATIONAL OVERVIEW PAGE
   ═══════════════════════════════════════════════ */
function NationalOverview({ data, onTriggerScrape, scrapeLoading }) {
  const national = data.national;
  const history = data.history || [];
  const routeIndices = data.routeIndices || [];
  const horizons = data.horizons || [];
  const fareStats = data.fareStats || {};

  const latestCPI = national?.airfare_cpi || 100;
  const momChange = national?.mom_change_pct;
  const routesIncluded = national?.routes_included || 0;
  const totalObs = fareStats?.total_observations || 0;

  // Format history for chart
  const chartData = history.map((d) => ({
    date: d.index_date?.slice(5) || "",
    cpi: d.airfare_cpi,
  }));

  // Format horizon data
  const horizonData = horizons.map((h) => ({
    name: `T+${h.horizon_days}`,
    avg: h.avg_fare,
    median: h.median_fare,
  }));

  // Route contributions
  const contributions = national?.route_contributions || [];
  const topRoutes = contributions.slice(0, 10);

  return (
    <>
      <div className="page-header">
        <h2>National Airfare CPI</h2>
        <p>Real-time Consumer Price Index for domestic air travel — India</p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">National Airfare CPI</div>
          <div className="kpi-value" style={{ color: "var(--text-accent)" }}>
            <AnimatedNumber value={latestCPI} decimals={2} />
          </div>
          {momChange != null && (
            <div className={`kpi-change ${momChange >= 0 ? "up" : "down"}`}>
              {momChange >= 0 ? "▲" : "▼"} {Math.abs(momChange).toFixed(2)}%
            </div>
          )}
          <div className="kpi-icon">📈</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Routes Monitored</div>
          <div className="kpi-value">
            <AnimatedNumber value={routesIncluded} decimals={0} />
          </div>
          <div className="kpi-change neutral">
            of 25 in basket
          </div>
          <div className="kpi-icon">🗺️</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Fare Observations</div>
          <div className="kpi-value">
            <AnimatedNumber value={totalObs} decimals={0} />
          </div>
          <div className="kpi-change up">✓ validated</div>
          <div className="kpi-icon">📋</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Median Fare</div>
          <div className="kpi-value" style={{ fontSize: 28 }}>
            <AnimatedNumber
              value={fareStats?.median_fare || 0}
              decimals={0}
              prefix="₹"
            />
          </div>
          <div className="kpi-change neutral">across all routes</div>
          <div className="kpi-icon">💰</div>
        </div>
      </div>

      {/* Trigger Scrape Button */}
      <div style={{ marginBottom: 24, display: "flex", gap: 12, alignItems: "center" }}>
        <button
          className="btn btn-primary"
          onClick={onTriggerScrape}
          disabled={scrapeLoading}
        >
          {scrapeLoading ? "⏳ Scraping..." : "🔄 Trigger Live Scrape"}
        </button>
        <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
          Runs the full pipeline: Scrape → Validate → Jevons → National CPI
        </span>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* CPI Time Series */}
        <div className="chart-container full-width">
          <div className="card-header">
            <span className="card-title">📈 National CPI Time Series</span>
            <span className="badge info">Base = 100</span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="cpiGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                domain={["auto", "auto"]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="cpi"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#cpiGrad)"
                name="Airfare CPI"
                dot={false}
                activeDot={{ r: 4, fill: "#3b82f6" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Booking Horizon Analysis */}
        <div className="chart-container">
          <div className="card-header">
            <span className="card-title">🎯 Booking Window Analysis</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={horizonData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="avg"
                fill="#3b82f6"
                name="Avg Fare (₹)"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="median"
                fill="#8b5cf6"
                name="Median Fare (₹)"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Route Contributions */}
        <div className="chart-container">
          <div className="card-header">
            <span className="card-title">🗺️ Route Contributions to National CPI</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={topRoutes.map((r) => ({
                route: `${r.origin_code}-${r.destination_code}`,
                contribution: r.contribution_pct,
                index: r.jevons_index,
              }))}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" stroke="#64748b" fontSize={11} />
              <YAxis
                dataKey="route"
                type="category"
                stroke="#64748b"
                fontSize={11}
                width={70}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="contribution"
                fill="#10b981"
                name="Contribution %"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════
   ROUTE EXPLORER PAGE
   ═══════════════════════════════════════════════ */
function RouteExplorer({ data }) {
  const routes = data.routes || [];
  const routeIndicesData = data.routeIndicesData || {};

  return (
    <>
      <div className="page-header">
        <h2>Route Explorer</h2>
        <p>
          Explore individual route indices — 25 DGCA-weighted domestic corridors
        </p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">Route Basket — DGCA Weighted</span>
          <span className="badge info">{routes.length} routes</span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Route</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Monthly Pax</th>
                <th>Weight</th>
                <th>Jevons Index</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r, i) => {
                const idx = routeIndicesData[r.route_id];
                return (
                  <tr key={r.route_id}>
                    <td className="mono" style={{ color: "var(--text-muted)" }}>
                      {i + 1}
                    </td>
                    <td>
                      <strong style={{ color: "var(--text-accent)" }}>
                        {r.origin_code} ↔ {r.destination_code}
                      </strong>
                    </td>
                    <td>{r.origin_city}</td>
                    <td>{r.destination_city}</td>
                    <td className="mono">
                      {(r.dgca_monthly_pax || 0).toLocaleString()}
                    </td>
                    <td className="mono">{(r.weight * 100).toFixed(2)}%</td>
                    <td className="mono">
                      {idx ? (
                        <span
                          style={{
                            color:
                              idx.jevons_index > 1.05
                                ? "var(--color-down)"
                                : idx.jevons_index < 0.95
                                ? "var(--color-up)"
                                : "var(--text-primary)",
                          }}
                        >
                          {idx.jevons_index.toFixed(4)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <span className="badge success">Active</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════
   PIPELINE HEALTH PAGE
   ═══════════════════════════════════════════════ */
function PipelineHealth({ data }) {
  const health = data.health || {};
  const anomalies = data.anomalies || [];

  return (
    <>
      <div className="page-header">
        <h2>Pipeline Health</h2>
        <p>Monitor scraper status, data quality, and anomalies</p>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">System Status</div>
          <div className="kpi-value" style={{ color: "var(--color-up)" }}>
            {health.status === "healthy" ? "Healthy" : "Degraded"}
          </div>
          <div className="kpi-icon">💚</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total Observations</div>
          <div className="kpi-value">
            <AnimatedNumber value={health.total_observations || 0} decimals={0} />
          </div>
          <div className="kpi-icon">📊</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Active Routes</div>
          <div className="kpi-value">
            <AnimatedNumber value={health.total_routes || 0} decimals={0} />
          </div>
          <div className="kpi-icon">🗺️</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Anomalies Detected</div>
          <div className="kpi-value" style={{ color: "var(--color-warning)" }}>
            <AnimatedNumber value={anomalies.length} decimals={0} />
          </div>
          <div className="kpi-icon">⚠️</div>
        </div>
      </div>

      {/* Anomaly Log */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">⚠️ Recent Anomalies</span>
          <span className="badge warning">{anomalies.length} flagged</span>
        </div>
        <div style={{ overflowX: "auto", maxHeight: 400, overflowY: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Route</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Fare</th>
                <th>Action</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.slice(0, 20).map((a, i) => (
                <tr key={i}>
                  <td className="mono" style={{ color: "var(--text-accent)" }}>
                    {a.origin_code}-{a.destination_code}
                  </td>
                  <td>
                    <span className="badge info">{a.anomaly_type}</span>
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        a.severity === "high"
                          ? "danger"
                          : a.severity === "medium"
                          ? "warning"
                          : "info"
                      }`}
                    >
                      {a.severity}
                    </span>
                  </td>
                  <td className="mono">
                    ₹{a.fare_observed?.toLocaleString() || "—"}
                  </td>
                  <td>
                    <span className="badge success">{a.action_taken}</span>
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: 12, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {a.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════
   METHODOLOGY PAGE
   ═══════════════════════════════════════════════ */
function Methodology() {
  return (
    <>
      <div className="page-header">
        <h2>Statistical Methodology</h2>
        <p>
          ILO/IMF CPI Manual-compliant methodology for airfare price indexing
        </p>
      </div>

      <div className="charts-grid" style={{ gridTemplateColumns: "1fr" }}>
        {/* Jevons Index */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📐 Route-Level: Jevons Index</span>
            <span className="badge info">Elementary Aggregate</span>
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, textAlign: "center", padding: "20px 0", color: "var(--text-accent)" }}>
            I(r,t) = [Π (p<sub>i,t</sub> / p<sub>i,0</sub>)]<sup>1/n</sup>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.8 }}>
            <p>The <strong>Jevons index</strong> computes the geometric mean of price relatives (current ÷ base) for each matched fare observation on a route.</p>
            <br />
            <p><strong>Why geometric mean?</strong></p>
            <ul style={{ paddingLeft: 20, marginTop: 8 }}>
              <li>Allows implicit substitution between products → lower bias than arithmetic mean (Carli)</li>
              <li>Satisfies the <strong>time-reversal test</strong>: I(0→t) × I(t→0) = 1</li>
              <li>Recommended by ILO, IMF, Statistics Canada, UK ONS, and ABS</li>
              <li>Less sensitive to extreme airfare spikes than arithmetic alternatives</li>
            </ul>
          </div>
        </div>

        {/* National Aggregation */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🇮🇳 National: Laspeyres/Young Aggregation</span>
            <span className="badge success">Upper-Level</span>
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, textAlign: "center", padding: "20px 0", color: "var(--color-up)" }}>
            CPI(t) = Σ<sub>r</sub> [w<sub>r</sub> × I(r,t)]
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.8 }}>
            <p>Route-level indices are aggregated using <strong>DGCA passenger-volume weights</strong> in a Laspeyres/Young-type weighted sum.</p>
            <br />
            <p><strong>Weight calculation:</strong> w<sub>r</sub> = DGCA_pax<sub>r</sub> / Σ DGCA_pax</p>
            <br />
            <p><strong>Note:</strong> Pure passenger volume is a proxy for expenditure weight. True CPI expenditure = volume × average_price. For the prototype, volume-only weights are justified by data availability.</p>
          </div>
        </div>

        {/* Booking Windows */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎯 Booking-Window Stratification</span>
            <span className="badge warning">Novel Component</span>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.8 }}>
            <p>Fares are stratified by <strong>5 booking horizons</strong> that bracket key airline revenue management thresholds:</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginTop: 16 }}>
              {[
                { label: "T+0", desc: "Same-day", mult: "2.5×", color: "#ef4444" },
                { label: "T+3", desc: "3-day", mult: "2.0×", color: "#f59e0b" },
                { label: "T+7", desc: "1-week", mult: "1.5×", color: "#3b82f6" },
                { label: "T+15", desc: "2-week", mult: "1.2×", color: "#8b5cf6" },
                { label: "T+30", desc: "1-month", mult: "1.0×", color: "#10b981" },
              ].map((h) => (
                <div
                  key={h.label}
                  style={{
                    background: "var(--bg-glass)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    padding: 16,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color: h.color }}>
                    {h.label}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>{h.desc}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, marginTop: 8, color: h.color }}>
                    {h.mult} base
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════════ */
export default function Home() {
  const [activePage, setActivePage] = useState("overview");
  const [data, setData] = useState({
    national: null,
    history: [],
    routes: [],
    routeIndicesData: {},
    horizons: [],
    fareStats: {},
    health: {},
    anomalies: [],
  });
  const [loading, setLoading] = useState(true);
  const [scrapeLoading, setScrapeLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const endpoints = [
        fetch(`${API_BASE}/index/national`).then((r) => r.ok ? r.json() : null),
        fetch(`${API_BASE}/index/national/history?days=30`).then((r) => r.ok ? r.json() : { data: [] }),
        fetch(`${API_BASE}/routes`).then((r) => r.ok ? r.json() : { routes: [] }),
        fetch(`${API_BASE}/index/routes`).then((r) => r.ok ? r.json() : { routes: [] }),
        fetch(`${API_BASE}/analysis/booking-horizons`).then((r) => r.ok ? r.json() : { horizons: [] }),
        fetch(`${API_BASE}/fares/stats`).then((r) => r.ok ? r.json() : {}),
        fetch(`${API_BASE}/health`).then((r) => r.ok ? r.json() : {}),
        fetch(`${API_BASE}/anomalies?limit=50`).then((r) => r.ok ? r.json() : { anomalies: [] }),
      ];

      const [national, historyRes, routesRes, routeIndicesRes, horizonsRes, fareStats, health, anomaliesRes] =
        await Promise.all(endpoints);

      // Build route index lookup
      const routeIndicesData = {};
      (routeIndicesRes?.routes || []).forEach((ri) => {
        routeIndicesData[ri.route_id] = ri;
      });

      setData({
        national,
        history: historyRes?.data || [],
        routes: routesRes?.routes || [],
        routeIndicesData,
        horizons: horizonsRes?.horizons || [],
        fareStats,
        health,
        anomalies: anomaliesRes?.anomalies || [],
      });
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleTriggerScrape = async () => {
    setScrapeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scraper/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ compute_index: true }),
      });
      if (res.ok) {
        // Refresh data after scrape
        setTimeout(fetchData, 1000);
      }
    } catch (err) {
      console.error("Scrape trigger error:", err);
    } finally {
      setScrapeLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app-layout">
        <Sidebar activePage={activePage} setActivePage={setActivePage} />
        <main className="main-content">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✈️</div>
              <div className="kpi-value pulse" style={{ color: "var(--text-accent)" }}>
                Loading Airfare CPI...
              </div>
              <div style={{ color: "var(--text-muted)", marginTop: 8, fontSize: 13 }}>
                Generating historical data and computing indices
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />
      <main className="main-content">
        {activePage === "overview" && (
          <NationalOverview
            data={data}
            onTriggerScrape={handleTriggerScrape}
            scrapeLoading={scrapeLoading}
          />
        )}
        {activePage === "routes" && <RouteExplorer data={data} />}
        {activePage === "health" && <PipelineHealth data={data} />}
        {activePage === "methodology" && <Methodology />}
      </main>
    </div>
  );
}
