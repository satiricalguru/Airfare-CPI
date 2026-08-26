"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

import CustomCursor from "./components/CustomCursor";
import IndiaNetworkMap from "./components/IndiaNetworkMap";
import {
  STATISTICAL_CONSTANTS,
  BOOKING_HORIZONS,
  TIME_SERIES_DATA,
  ROUTE_HEATMAP_DATA,
  SCRAPER_MONITOR_SOURCES,
  API_ENDPOINTS_LIST,
} from "./data/mockData";

// Dynamically import 3D Aircraft for pure client-side rendering
const HeroAircraft = dynamic(() => import("./components/HeroAircraft"), {
  ssr: false,
  loading: () => (
    <div style={{ height: "100%", width: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="live-green-dot" style={{ width: 14, height: 14 }} />
    </div>
  ),
});

export default function AppleAirfareCPI() {
  const [chartRange, setChartRange] = useState("30D");
  const [volatilityIndex, setVolatilityIndex] = useState(2); // T+7
  const [isScrapingRunning, setIsScrapingRunning] = useState(false);
  const [scrapeStep, setScrapeStep] = useState(0);
  const [selectedApiIndex, setSelectedApiIndex] = useState(0);
  const [apiActiveTab, setApiActiveTab] = useState("response"); // "response" | "curl" | "js" | "python"
  const [isApiLoading, setIsApiLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [showBulletinModal, setShowBulletinModal] = useState(false);

  // Scraper Simulation Run
  const handleTriggerScrape = () => {
    if (isScrapingRunning) return;
    setIsScrapingRunning(true);
    setScrapeStep(1);

    setTimeout(() => setScrapeStep(2), 800);
    setTimeout(() => setScrapeStep(3), 1600);
    setTimeout(() => setScrapeStep(4), 2400);
    setTimeout(() => {
      setIsScrapingRunning(false);
      setScrapeStep(0);
    }, 3200);
  };

  // API Playground Run Query Simulation
  const handleRunApiQuery = () => {
    if (isApiLoading) return;
    setIsApiLoading(true);
    setTimeout(() => {
      setIsApiLoading(false);
    }, 350);
  };

  const handleCopyCode = (text) => {
    navigator.clipboard?.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const currentHorizon = BOOKING_HORIZONS[volatilityIndex];
  const activeEndpoint = API_ENDPOINTS_LIST[selectedApiIndex];

  // Code snippets generator for active endpoint
  const getCodeSnippet = (tab) => {
    const baseUrl = `https://api.airfare-cpi.mospi.gov.in${activeEndpoint.path}`;
    if (tab === "curl") {
      return activeEndpoint.method === "GET"
        ? `curl -X GET "${baseUrl}" \\\n  -H "Authorization: Bearer mospi_live_key_9f8a2" \\\n  -H "Accept: application/json"`
        : `curl -X POST "${baseUrl}" \\\n  -H "Authorization: Bearer mospi_live_key_9f8a2" \\\n  -H "Content-Type: application/json" \\\n  -d '{"trigger_source": "manual_admin", "depth": "full"}'`;
    }
    if (tab === "js") {
      return activeEndpoint.method === "GET"
        ? `const res = await fetch("${baseUrl}", {\n  headers: {\n    "Authorization": "Bearer mospi_live_key_9f8a2",\n    "Accept": "application/json"\n  }\n});\nconst data = await res.json();\nconsole.log(data);`
        : `const res = await fetch("${baseUrl}", {\n  method: "POST",\n  headers: {\n    "Authorization": "Bearer mospi_live_key_9f8a2",\n    "Content-Type": "application/json"\n  },\n  body: JSON.stringify({ trigger_source: "manual_admin" })\n});\nconst data = await res.json();\nconsole.log(data);`;
    }
    if (tab === "python") {
      return activeEndpoint.method === "GET"
        ? `import requests\n\nurl = "${baseUrl}"\nheaders = {\n    "Authorization": "Bearer mospi_live_key_9f8a2",\n    "Accept": "application/json"\n}\n\nresponse = requests.get(url, headers=headers)\nprint(response.json())`
        : `import requests\n\nurl = "${baseUrl}"\nheaders = {"Authorization": "Bearer mospi_live_key_9f8a2"}\npayload = {"trigger_source": "manual_admin"}\n\nresponse = requests.post(url, json=payload, headers=headers)\nprint(response.json())`;
    }
    return JSON.stringify(activeEndpoint.response, null, 2);
  };

  return (
    <div style={{ position: "relative", minHeight: "100vh", backgroundColor: "#ffffff" }}>
      {/* Precision Apple Cursor */}
      <CustomCursor />

      {/* ── Apple Translucent Navbar ── */}
      <header className="apple-navbar">
        <div className="container apple-nav-inner">
          <a href="#" className="apple-nav-logo">
            <span style={{ color: "#0071e3", fontSize: 20 }}>✈</span>
            <span>Airfare <span style={{ color: "#0071e3" }}>CPI</span></span>
          </a>

          <ul className="apple-nav-links">
            <li><a href="#overview" className="apple-nav-link">Overview</a></li>
            <li><a href="#volatility" className="apple-nav-link">Volatility</a></li>
            <li><a href="#index" className="apple-nav-link">Index</a></li>
            <li><a href="#network" className="apple-nav-link">Network</a></li>
            <li><a href="#heatmap" className="apple-nav-link">Heatmap</a></li>
            <li><a href="#methodology" className="apple-nav-link">Methodology</a></li>
            <li><a href="#pipeline" className="apple-nav-link">Pipeline</a></li>
            <li><a href="#api" className="apple-nav-link">API</a></li>
          </ul>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div className="live-pill">
              <span className="live-green-dot" />
              <span>LIVE</span>
            </div>
            <button
              onClick={() => setShowBulletinModal(true)}
              className="apple-btn-secondary"
              style={{ padding: "7px 16px", fontSize: 12 }}
            >
              MoSPI Bulletin
            </button>
          </div>
        </div>
      </header>

      {/* ── 1. HERO SECTION (Headline clearly above the cruising Airbus A320) ── */}
      <section id="overview" className="apple-hero" style={{ height: "92vh", minHeight: 680, paddingTop: 130, justifyContent: "flex-start" }}>
        {/* 3D Straight-Flying Airplane Canvas in Background */}
        <div className="aircraft-bg-stage">
          <HeroAircraft />
        </div>

        {/* Minimalist Top Foreground Content */}
        <div className="container hero-content-wrap" style={{ zIndex: 10, marginTop: 0 }}>
          <h1 className="apple-heading" style={{ fontSize: 72, fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 16 }}>
            The Price of Flight.
          </h1>

          <div className="hero-interactive" style={{ display: "flex", gap: 14 }}>
            <a href="#index" className="apple-btn-primary">
              <span>Explore Live Index</span>
              <span>➔</span>
            </a>
            <a href="#methodology" className="apple-btn-secondary">
              How It Works
            </a>
          </div>
        </div>
      </section>

      {/* ── SYSTEM STATUS RIBBON (Placed cleanly below hero) ── */}
      <div style={{ display: "flex", justifyContent: "center", marginTop: -32, position: "relative", zIndex: 20 }}>
        <div className="apple-ribbon">
          <div className="apple-ribbon-item">
            <span style={{ color: "#86868b" }}>BASKET:</span>
            <strong style={{ color: "#1d1d1f" }}>25 / 25 Routes</strong>
          </div>
          <div className="apple-ribbon-item">
            <span className="live-green-dot" />
            <span style={{ color: "#86868b" }}>HEALTH:</span>
            <strong style={{ color: "#34c759" }}>HEALTHY</strong>
          </div>
          <div className="apple-ribbon-item">
            <span style={{ color: "#86868b" }}>UPDATED:</span>
            <strong style={{ color: "#1d1d1f" }}>{STATISTICAL_CONSTANTS.lastUpdate}</strong>
          </div>
          <div className="apple-ribbon-item">
            <span style={{ color: "#86868b" }}>ENGINE:</span>
            <strong style={{ color: "#0071e3" }}>ONLINE (Jevons)</strong>
          </div>
        </div>
      </div>

      {/* ── 2. AIRFARE VOLATILITY SECTION (DEL ➔ BOM) ── */}
      <section id="volatility" className="section-wrap" style={{ backgroundColor: "#fbfbfd", marginTop: 40 }}>
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Booking Horizon Dynamics</div>
            <h2 className="apple-section-title">Airfares Don't Behave Like Ordinary Prices.</h2>
            <p className="apple-section-desc">
              Airlines dynamically adjust seat buckets as flight departures approach. True CPI isolates price changes by indexing within homogenous booking windows.
            </p>
          </div>

          <div className="apple-card" style={{ maxWidth: 1000, margin: "0 auto", padding: 40 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20, marginBottom: 32 }}>
              <div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#0071e3", fontWeight: 700, textTransform: "uppercase" }}>
                  Benchmark Corridor
                </span>
                <h3 style={{ fontSize: 28, fontWeight: 800, color: "#1d1d1f", marginTop: 4 }}>
                  New Delhi (DEL) ➔ Mumbai (BOM)
                </h3>
              </div>

              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: 11, color: "#86868b", fontWeight: 600 }}>CURRENT HORIZON FARE</span>
                <div style={{ fontSize: 40, fontWeight: 800, color: "#0071e3", fontFamily: "var(--font-mono)" }}>
                  ₹{currentHorizon.price.toLocaleString()}
                </div>
                <div style={{ fontSize: 13, color: "#ff9500", fontWeight: 600 }}>
                  {currentHorizon.multiplier} vs Baseline ({currentHorizon.tag})
                </div>
              </div>
            </div>

            {/* Interactive Horizon Slider Cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 12,
                margin: "32px 0 20px",
              }}
            >
              {BOOKING_HORIZONS.map((h, i) => {
                const isActive = volatilityIndex === i;
                return (
                  <button
                    key={h.horizon}
                    onClick={() => setVolatilityIndex(i)}
                    style={{
                      background: isActive ? "#ffffff" : "#f5f5f7",
                      border: isActive ? "2px solid #0071e3" : "1px solid rgba(0,0,0,0.06)",
                      borderRadius: 14,
                      padding: "20px 14px",
                      textAlign: "center",
                      cursor: "pointer",
                      transition: "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
                      boxShadow: isActive ? "0 8px 24px rgba(0, 113, 227, 0.15)" : "none",
                      transform: isActive ? "translateY(-4px)" : "none",
                    }}
                  >
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 800, color: isActive ? "#0071e3" : "#1d1d1f" }}>
                      {h.horizon}
                    </div>
                    <div style={{ fontSize: 11, color: "#86868b", marginTop: 4 }}>
                      {h.days === 0 ? "Same-Day" : `${h.days} Days Prior`}
                    </div>
                    <div style={{ fontSize: 19, fontWeight: 800, color: "#1d1d1f", fontFamily: "var(--font-mono)", marginTop: 10 }}>
                      ₹{h.price.toLocaleString()}
                    </div>
                  </button>
                );
              })}
            </div>

            <div style={{ marginTop: 24, padding: "16px 20px", background: "#f5f5f7", borderRadius: 12, fontSize: 13, color: "#86868b" }}>
              <strong>Methodology Note:</strong> {currentHorizon.desc}
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. LIVE INDIA AVIATION CPI TIME SERIES ── */}
      <section id="index" className="section-wrap">
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">National Economic Signal</div>
            <h2 className="apple-section-title">All-India Airfare Consumer Price Index</h2>
            <p className="apple-section-desc">
              Laspeyres/Young upper-level aggregation of Jevons micro-indices with DGCA volume weights.
            </p>
          </div>

          <div className="apple-card" style={{ padding: 40 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20, marginBottom: 28 }}>
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
                  <span style={{ fontSize: 52, fontWeight: 900, color: "#1d1d1f", fontFamily: "var(--font-mono)", letterSpacing: "-0.03em" }}>
                    {STATISTICAL_CONSTANTS.headlineCPI}
                  </span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: "#34c759", fontFamily: "var(--font-mono)" }}>
                    {STATISTICAL_CONSTANTS.momChange} MoM
                  </span>
                  <span style={{ fontSize: 13, color: "#86868b" }}>
                    (Base {STATISTICAL_CONSTANTS.baseYear})
                  </span>
                </div>
              </div>

              {/* Time Range Pills */}
              <div style={{ display: "flex", background: "#f5f5f7", padding: 4, borderRadius: 100, gap: 2 }}>
                {["7D", "30D", "90D", "1Y"].map((r) => (
                  <button
                    key={r}
                    onClick={() => setChartRange(r)}
                    style={{
                      padding: "6px 16px",
                      borderRadius: 100,
                      fontSize: 12,
                      fontWeight: 600,
                      fontFamily: "var(--font-mono)",
                      background: chartRange === r ? "#ffffff" : "transparent",
                      color: chartRange === r ? "#1d1d1f" : "#86868b",
                      boxShadow: chartRange === r ? "0 2px 6px rgba(0,0,0,0.06)" : "none",
                      border: "none",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Area Chart */}
            <div style={{ width: "100%", height: 380 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={TIME_SERIES_DATA[chartRange]}>
                  <defs>
                    <linearGradient id="appleChartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0071e3" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#0071e3" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
                  <XAxis dataKey="date" stroke="#86868b" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis domain={["auto", "auto"]} stroke="#86868b" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      border: "1px solid rgba(0, 0, 0, 0.08)",
                      borderRadius: 12,
                      boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpi"
                    stroke="#0071e3"
                    strokeWidth={3}
                    fill="url(#appleChartGradient)"
                    name="Headline Airfare CPI"
                    dot={{ r: 4, fill: "#0071e3" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. INDIA AVIATION ROUTE NETWORK ── */}
      <section id="network" className="section-wrap" style={{ backgroundColor: "#fbfbfd" }}>
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Spatial Network Topology</div>
            <h2 className="apple-section-title">India Domestic Aviation Corridor Grid</h2>
            <p className="apple-section-desc">
              Continuous monitoring across top high-density metro and tier-1 airport pairs.
            </p>
          </div>

          <div className="apple-card" style={{ padding: 24 }}>
            <IndiaNetworkMap />
          </div>
        </div>
      </section>

      {/* ── 5. ROUTE PRICE HEATMAP ── */}
      <section id="heatmap" className="section-wrap">
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Cross-Sectional Intensity</div>
            <h2 className="apple-section-title">Domestic Route Price Pressure Heatmap</h2>
            <p className="apple-section-desc">
              Granular fare pricing across the 25 DGCA basket routes and 5 booking horizons.
            </p>
          </div>

          <div className="apple-card" style={{ padding: 32, overflowX: "auto" }}>
            <div className="apple-heatmap-grid" style={{ fontWeight: 700, color: "#86868b", borderBottom: "1px solid rgba(0,0,0,0.06)", paddingBottom: 12, marginBottom: 12 }}>
              <div>CORRIDOR</div>
              <div style={{ textAlign: "center" }}>T+0 (WALKUP)</div>
              <div style={{ textAlign: "center" }}>T+3</div>
              <div style={{ textAlign: "center" }}>T+7</div>
              <div style={{ textAlign: "center" }}>T+15</div>
              <div style={{ textAlign: "center" }}>T+30</div>
              <div style={{ textAlign: "right" }}>JEVONS CPI</div>
            </div>

            {ROUTE_HEATMAP_DATA.map((row) => (
              <div key={row.route} className="apple-heatmap-grid" style={{ alignItems: "center", padding: "8px 0", borderBottom: "1px solid rgba(0,0,0,0.03)" }}>
                <div style={{ fontWeight: 700, color: "#1d1d1f" }}>
                  {row.route}
                  <span style={{ fontSize: 10, color: "#86868b", display: "block" }}>{row.pax} Pax ({row.weight}%)</span>
                </div>

                <div className="apple-heatmap-cell" style={{ backgroundColor: "#fef2f2", color: "#b91c1c" }}>
                  ₹{row.t0.toLocaleString()}
                </div>
                <div className="apple-heatmap-cell" style={{ backgroundColor: "#fffbeb", color: "#b45309" }}>
                  ₹{row.t3.toLocaleString()}
                </div>
                <div className="apple-heatmap-cell" style={{ backgroundColor: "#eff6ff", color: "#1d4ed8" }}>
                  ₹{row.t7.toLocaleString()}
                </div>
                <div className="apple-heatmap-cell" style={{ backgroundColor: "#f0fdfa", color: "#0f766e" }}>
                  ₹{row.t15.toLocaleString()}
                </div>
                <div className="apple-heatmap-cell" style={{ backgroundColor: "#f0fdf4", color: "#15803d" }}>
                  ₹{row.t30.toLocaleString()}
                </div>

                <div style={{ textAlign: "right", fontWeight: 700, color: "#0071e3" }}>
                  {row.cpi}
                  <span style={{ fontSize: 10, color: "#34c759", display: "block" }}>{row.change}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. DATA PIPELINE ARCHITECTURE ── */}
      <section id="pipeline" className="section-wrap" style={{ backgroundColor: "#fbfbfd" }}>
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Automated Ingestion Flow</div>
            <h2 className="apple-section-title">From Web Quotes to National Index</h2>
            <p className="apple-section-desc">
              5-stage automated statistical intelligence pipeline designed for national scale.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
            {[
              { step: "01", name: "INGEST", desc: "Headless Playwright + XHR interception sampling live airline and aggregator portals." },
              { step: "02", name: "VALIDATE", desc: "Hard exclusions (₹0, corrupted tax ratios) and rolling IQR anomaly fencing." },
              { step: "03", name: "STRATIFY", desc: "Clustering fare quotes into T+0, T+3, T+7, T+15, and T+30 booking buckets." },
              { step: "04", name: "COMPUTE", desc: "Jevons Geometric Mean micro-indices aggregated via DGCA passenger weights." },
              { step: "05", name: "PUBLISH", desc: "Real-time API dissemination and MoSPI-format official statistical bulletins." },
            ].map((node) => (
              <div key={node.name} className="apple-card" style={{ padding: 24 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 900, color: "#0071e3" }}>
                  {node.step}
                </div>
                <h4 style={{ fontSize: 17, fontWeight: 800, color: "#1d1d1f", margin: "10px 0 6px" }}>
                  {node.name}
                </h4>
                <p style={{ fontSize: 13, color: "#86868b", lineHeight: 1.6 }}>
                  {node.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 7. ECONOMETRIC ENGINE ── */}
      <section id="methodology" className="section-wrap">
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Mathematical Rigor</div>
            <h2 className="apple-section-title">The Econometric Formulation</h2>
            <p className="apple-section-desc">
              ILO/IMF CPI Manual compliant index formulas eliminating substitution bias.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div className="apple-card" style={{ padding: 36 }}>
              <div style={{ fontSize: 11, color: "#0071e3", fontWeight: 700, textTransform: "uppercase" }}>
                1. Elementary Micro-Index (Route Level)
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 800, color: "#1d1d1f", marginTop: 4 }}>
                Jevons Geometric Price Index
              </h3>
              <div
                style={{
                  background: "#f5f5f7",
                  borderRadius: 12,
                  padding: "20px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 18,
                  textAlign: "center",
                  color: "#0071e3",
                  margin: "20px 0",
                  fontWeight: 700,
                }}
              >
                I(r, t) = [ ∏ (p_i,t / p_i,0) ] ^ (1/n)
              </div>
              <ul style={{ fontSize: 14, color: "#86868b", lineHeight: 1.8, paddingLeft: 20 }}>
                <li>Computed in log-space: <code style={{ color: "#0071e3" }}>ln I = (1/n) ∑ ln(p_t / p_0)</code></li>
                <li>Satisfies the <strong>Time-Reversal Test</strong>: <code style={{ color: "#34c759" }}>I(0→t) × I(t→0) = 1.0</code></li>
                <li>Eliminates upward arithmetic substitution bias inherent in Carli formulations.</li>
              </ul>
            </div>

            <div className="apple-card" style={{ padding: 36 }}>
              <div style={{ fontSize: 11, color: "#34c759", fontWeight: 700, textTransform: "uppercase" }}>
                2. Upper-Level Aggregation (National Headline)
              </div>
              <h3 style={{ fontSize: 22, fontWeight: 800, color: "#1d1d1f", marginTop: 4 }}>
                Laspeyres / Young with DGCA Weights
              </h3>
              <div
                style={{
                  background: "#f5f5f7",
                  borderRadius: 12,
                  padding: "20px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 18,
                  textAlign: "center",
                  color: "#15803d",
                  margin: "20px 0",
                  fontWeight: 700,
                }}
              >
                CPI(t) = ∑ [ w_r × I(r, t) ] × 100
              </div>
              <ul style={{ fontSize: 14, color: "#86868b", lineHeight: 1.8, paddingLeft: 20 }}>
                <li>Weighted by empirical DGCA city-pair monthly passenger volumes.</li>
                <li><code style={{ color: "#0071e3" }}>w_r = DGCA_Pax_r / ∑ DGCA_Pax</code> across 25 routes.</li>
                <li>Provides stable economic weighting unaffected by ticket fare fluctuations.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── 8. LIVE SCRAPER SIMULATION ── */}
      <section className="section-wrap" style={{ backgroundColor: "#fbfbfd" }}>
        <div className="container">
          <div className="apple-card" style={{ padding: 40 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20, marginBottom: 28 }}>
              <div>
                <div style={{ fontSize: 11, color: "#0071e3", fontWeight: 700, textTransform: "uppercase" }}>
                  Live Sampling Pipeline Diagnostics
                </div>
                <h3 style={{ fontSize: 26, fontWeight: 800, color: "#1d1d1f", marginTop: 4 }}>
                  Scraper Fleet & Airline Source Health
                </h3>
              </div>

              <button
                onClick={handleTriggerScrape}
                disabled={isScrapingRunning}
                className="apple-btn-primary"
                style={{
                  background: isScrapingRunning ? "#86868b" : "#0071e3",
                  cursor: isScrapingRunning ? "wait" : "pointer",
                }}
              >
                {isScrapingRunning ? `Ingesting (Stage ${scrapeStep}/4)...` : "Trigger Scrape Cycle"}
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {SCRAPER_MONITOR_SOURCES.map((src) => (
                <div key={src.name} style={{ background: "#f5f5f7", borderRadius: 14, padding: "16px 20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: 15, color: "#1d1d1f" }}>{src.name}</strong>
                    <span style={{ fontSize: 11, color: "#34c759", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                      ● {src.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontSize: 12, color: "#86868b", fontFamily: "var(--font-mono)" }}>
                    <span>Latency: <strong style={{ color: "#1d1d1f" }}>{src.latency}</strong></span>
                    <span>Quotes: <strong style={{ color: "#0071e3" }}>{src.observations}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 9. DEVELOPER-GRADE API PLAYGROUND (Stripe/Apple Level Console) ── */}
      <section id="api" className="section-wrap">
        <div className="container">
          <div className="apple-section-header">
            <div className="apple-section-eyebrow">Enterprise & Statistical Dissemination</div>
            <h2 className="apple-section-title">One Index. Infinite Interfaces.</h2>
            <p className="apple-section-desc">
              High-throughput REST API with microsecond responses, automated schema documentation, and multi-language SDK integrations.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.35fr", gap: 24, alignItems: "start" }}>
            {/* Left: Interactive Endpoint List */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {API_ENDPOINTS_LIST.map((ep, i) => {
                const isSelected = selectedApiIndex === i;
                return (
                  <div
                    key={ep.path}
                    onClick={() => setSelectedApiIndex(i)}
                    style={{
                      background: isSelected ? "#ffffff" : "#f5f5f7",
                      border: isSelected ? "2px solid #0071e3" : "1px solid rgba(0, 0, 0, 0.05)",
                      borderRadius: 14,
                      padding: "16px 20px",
                      cursor: "pointer",
                      transition: "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
                      boxShadow: isSelected ? "0 8px 24px rgba(0, 113, 227, 0.12)" : "none",
                      transform: isSelected ? "translateX(4px)" : "none",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 800,
                            fontFamily: "var(--font-mono)",
                            backgroundColor: ep.method === "GET" ? "rgba(52, 199, 89, 0.15)" : "rgba(0, 113, 227, 0.15)",
                            color: ep.method === "GET" ? "#15803d" : "#0071e3",
                          }}
                        >
                          {ep.method}
                        </span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: isSelected ? "#0071e3" : "#1d1d1f", fontWeight: 700 }}>
                          {ep.path}
                        </span>
                      </div>
                      <span style={{ fontSize: 11, color: "#34c759", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                        ● ~14ms
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: "#86868b", marginTop: 8, lineHeight: 1.5 }}>
                      {ep.description}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Right: Apple/macOS Interactive Terminal Playground */}
            <div
              style={{
                background: "#161618",
                borderRadius: 18,
                border: "1px solid rgba(255, 255, 255, 0.08)",
                overflow: "hidden",
                boxShadow: "0 20px 50px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.8)",
              }}
            >
              {/* macOS Window Title Bar */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 18px",
                  backgroundColor: "#1f1f23",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                {/* Traffic Light Dots */}
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ff5f56" }} />
                  <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ffbd2e" }} />
                  <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#27c93f" }} />
                  <span style={{ fontSize: 11, color: "#86868b", marginLeft: 12, fontFamily: "var(--font-mono)" }}>
                    MoSPI Live Dissemination Console
                  </span>
                </div>

                {/* Live Latency & Status */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    style={{
                      fontSize: 10,
                      padding: "2px 8px",
                      borderRadius: 100,
                      background: "rgba(52, 199, 89, 0.15)",
                      color: "#34c759",
                      fontFamily: "var(--font-mono)",
                      fontWeight: 700,
                    }}
                  >
                    HTTP 200 OK
                  </span>
                  <span style={{ fontSize: 11, color: "#86868b", fontFamily: "var(--font-mono)" }}>14ms</span>
                </div>
              </div>

              {/* Playground Navigation Tabs & Actions */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 16px",
                  backgroundColor: "#161618",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                }}
              >
                {/* Language / View Switcher */}
                <div style={{ display: "flex", gap: 4 }}>
                  {[
                    { id: "response", label: "Response (JSON)" },
                    { id: "curl", label: "cURL" },
                    { id: "js", label: "JavaScript" },
                    { id: "python", label: "Python" },
                  ].map((tab) => {
                    const isActive = apiActiveTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setApiActiveTab(tab.id)}
                        style={{
                          background: isActive ? "rgba(255, 255, 255, 0.1)" : "transparent",
                          color: isActive ? "#ffffff" : "#86868b",
                          border: "none",
                          borderRadius: 8,
                          padding: "6px 12px",
                          fontSize: 11,
                          fontWeight: 600,
                          fontFamily: "var(--font-mono)",
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                        }}
                      >
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                {/* Playground Action Buttons */}
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => handleCopyCode(getCodeSnippet(apiActiveTab))}
                    style={{
                      background: "rgba(255, 255, 255, 0.06)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: copiedCode ? "#34c759" : "#d1d5db",
                      borderRadius: 8,
                      padding: "5px 12px",
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <span>{copiedCode ? "Copied" : "Copy"}</span>
                  </button>

                  <button
                    onClick={handleRunApiQuery}
                    disabled={isApiLoading}
                    style={{
                      background: "#0071e3",
                      border: "none",
                      color: "#ffffff",
                      borderRadius: 8,
                      padding: "5px 14px",
                      fontSize: 11,
                      fontWeight: 700,
                      fontFamily: "var(--font-mono)",
                      cursor: isApiLoading ? "wait" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      boxShadow: "0 2px 8px rgba(0, 113, 227, 0.4)",
                    }}
                  >
                    <span>{isApiLoading ? "Running..." : "Send Request"}</span>
                  </button>
                </div>
              </div>

              {/* Live Terminal Output Window */}
              <div
                style={{
                  padding: 20,
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  lineHeight: 1.65,
                  minHeight: 320,
                  maxHeight: 460,
                  overflowY: "auto",
                  color: "#e2e8f0",
                }}
              >
                {isApiLoading ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#0071e3", padding: "40px 0", justifyContent: "center" }}>
                    <div className="live-green-dot" style={{ background: "#0071e3", width: 12, height: 12 }} />
                    <span>Executing HTTP query to MoSPI Node...</span>
                  </div>
                ) : (
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {apiActiveTab === "response" ? (
                      <code style={{ color: "#38bdf8" }}>
                        {JSON.stringify(activeEndpoint.response, null, 2)}
                      </code>
                    ) : (
                      <code style={{ color: "#a5b4fc" }}>
                        {getCodeSnippet(apiActiveTab)}
                      </code>
                    )}
                  </pre>
                )}
              </div>

              {/* Terminal Bottom Security & Metadata Bar */}
              <div
                style={{
                  padding: "10px 18px",
                  backgroundColor: "#1a1a1e",
                  borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: 11,
                  color: "#6b7280",
                  fontFamily: "var(--font-mono)",
                }}
              >
                <span>Auth: Bearer Token Verified</span>
                <span>Payload: ~1.4 KB · Jevons Geometric Engine</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 10. STATISTICAL BULLETIN MODAL ── */}
      {showBulletinModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            backdropFilter: "blur(20px)",
            zIndex: 99999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <div
            className="apple-card"
            style={{
              maxWidth: 720,
              width: "100%",
              maxHeight: "88vh",
              overflowY: "auto",
              padding: 40,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(0,0,0,0.08)", paddingBottom: 16 }}>
              <div>
                <span style={{ fontSize: 11, color: "#0071e3", fontWeight: 700, textTransform: "uppercase" }}>Government of India · MoSPI</span>
                <h3 style={{ fontSize: 18, color: "#1d1d1f", fontWeight: 800, marginTop: 2 }}>Monthly Statistical Release Bulletin</h3>
              </div>
              <button
                onClick={() => setShowBulletinModal(false)}
                style={{ background: "none", border: "none", color: "#86868b", fontSize: 22, cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginTop: 24, color: "#1d1d1f", lineHeight: 1.7, fontSize: 14 }}>
              <div style={{ textAlign: "center", margin: "16px 0", borderBottom: "1px solid #e2e8f0", paddingBottom: 12 }}>
                <strong style={{ fontSize: 15, textTransform: "uppercase" }}>PRESS RELEASE: ALL-INDIA CONSUMER PRICE INDEX FOR DOMESTIC AIR TRAVEL</strong>
                <div style={{ fontSize: 12, color: "#86868b" }}>Base Year: 2024 = 100 | Reference Period: August 2026</div>
              </div>

              <div style={{ background: "#f5f5f7", padding: 16, borderRadius: 12, margin: "16px 0" }}>
                <div>ALL-INDIA AIRFARE CPI (PROVISIONAL): <strong style={{ color: "#0071e3", fontSize: 20 }}>107.42</strong></div>
                <div>Month-on-Month Movement: <strong style={{ color: "#34c759" }}>+2.84%</strong></div>
                <div style={{ fontSize: 12, color: "#86868b" }}>Based on 48,200 validated quotes across 25 high-traffic DGCA corridors.</div>
              </div>

              <p style={{ fontSize: 13, color: "#475569" }}>
                The All-India Airfare Price Index reflects price fluctuations of scheduled domestic commercial passenger flights across 25 high-density routes weighted by Directorate General of Civil Aviation (DGCA) city-pair passenger traffic. Micro-level route indices are computed using the <strong>Jevons geometric mean formula</strong>, stratified across five advance-purchase booking horizons (T+0, T+3, T+7, T+15, and T+30).
              </p>
            </div>

            <div style={{ textAlign: "right", marginTop: 24 }}>
              <button onClick={() => setShowBulletinModal(false)} className="apple-btn-primary" style={{ padding: "8px 20px" }}>
                Close Bulletin
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 11. FOOTER ── */}
      <footer style={{ borderTop: "1px solid rgba(0,0,0,0.06)", padding: "48px 0", backgroundColor: "#fbfbfd" }}>
        <div className="container" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "#1d1d1f" }}>
              Airfare <span style={{ color: "#0071e3" }}>CPI</span>
            </div>
            <div style={{ fontSize: 12, color: "#86868b", marginTop: 4 }}>
              Smart India Hackathon 2026 · Problem Statement SIH26056 (MoSPI)
            </div>
          </div>

          <div style={{ fontSize: 12, color: "#86868b" }}>
            Designed with Apple-level minimalist precision and official statistical rigor.
          </div>
        </div>
      </footer>
    </div>
  );
}
