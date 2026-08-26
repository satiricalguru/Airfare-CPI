"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
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

// Dynamically import 3D Aircraft to prevent SSR canvas issues
const HeroAircraft = dynamic(() => import("./components/HeroAircraft"), {
  ssr: false,
  loading: () => (
    <div style={{ height: "100%", minHeight: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="pulse-dot" style={{ width: 14, height: 14 }} />
    </div>
  ),
});

export default function AirfareCPIFrontend() {
  // Navigation & Page State
  const [activeTab, setActiveTab] = useState("overview");
  const [isScrolled, setIsScrolled] = useState(false);
  const [isAircraftHovered, setIsAircraftHovered] = useState(false);

  // Time Series Chart State
  const [chartRange, setChartRange] = useState("30D");

  // Volatility Timeline State
  const [volatilityIndex, setVolatilityIndex] = useState(2); // T+7 default

  // Scraper Simulation State
  const [isScrapingRunning, setIsScrapingRunning] = useState(false);
  const [scrapeStep, setScrapeStep] = useState(0);

  // Selected API endpoint for explorer
  const [selectedApiIndex, setSelectedApiIndex] = useState(0);

  // Bulletin Modal State
  const [showBulletinModal, setShowBulletinModal] = useState(false);

  // Scroll listener for floating navbar
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Trigger Live Scrape Simulation
  const handleTriggerScrape = () => {
    if (isScrapingRunning) return;
    setIsScrapingRunning(true);
    setScrapeStep(1);

    setTimeout(() => setScrapeStep(2), 900);
    setTimeout(() => setScrapeStep(3), 1800);
    setTimeout(() => setScrapeStep(4), 2700);
    setTimeout(() => {
      setIsScrapingRunning(false);
      setScrapeStep(0);
    }, 3600);
  };

  const currentHorizon = BOOKING_HORIZONS[volatilityIndex];

  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
      {/* Custom Precision Cursor */}
      <CustomCursor isAircraftHovered={isAircraftHovered} />

      {/* Floating Glass Navbar */}
      <header className={`floating-navbar ${isScrolled ? "scrolled" : ""}`}>
        <div className="container nav-content">
          <a href="#" className="nav-logo">
            <span style={{ fontSize: 22, color: "#4cd7f6" }}>✈</span>
            <span>AIRFARE <span style={{ color: "#4cd7f6" }}>CPI</span></span>
          </a>

          <ul className="nav-links">
            <li><a href="#overview" className="nav-link">Overview</a></li>
            <li><a href="#volatility" className="nav-link">Airfare Volatility</a></li>
            <li><a href="#index" className="nav-link">Live CPI</a></li>
            <li><a href="#network" className="nav-link">Network</a></li>
            <li><a href="#heatmap" className="nav-link">Route Heatmap</a></li>
            <li><a href="#methodology" className="nav-link">Econometrics</a></li>
            <li><a href="#pipeline" className="nav-link">Pipeline</a></li>
            <li><a href="#api" className="nav-link">API</a></li>
          </ul>

          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="live-badge">
              <span className="pulse-dot" />
              <span>LIVE</span>
            </div>
            <button
              onClick={() => setShowBulletinModal(true)}
              className="btn-glass-outline"
              style={{ padding: "8px 16px", fontSize: 11 }}
            >
              MoSPI Bulletin
            </button>
          </div>
        </div>
      </header>

      {/* 1. HERO SECTION */}
      <section id="overview" className="hero-section">
        <div className="container">
          <div className="hero-grid">
            {/* Left: Text & Key Metrics */}
            <div>
              <div className="hero-eyebrow">
                <span>🏛️</span>
                <span>MINISTRY OF STATISTICS & PROGRAMME IMPLEMENTATION</span>
              </div>

              <h1 className="hero-heading">
                The Price of Flight, <br />
                <span className="hero-heading-gradient">Measured in Real Time.</span>
              </h1>

              <p className="hero-description">
                AIRFARE CPI continuously transforms high-frequency domestic airfare observations into a statistically rigorous, ILO/IMF-compliant measure of aviation price movement for India.
              </p>

              <div className="hero-buttons">
                <a href="#index" className="btn-primary-glow">
                  <span>Explore Live Index</span>
                  <span>➔</span>
                </a>
                <a href="#methodology" className="btn-glass-outline">
                  How It Works
                </a>
              </div>

              {/* Floating Live Stat Badges */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 12,
                  marginTop: 40,
                }}
              >
                <div className="glass-card" style={{ padding: "14px 18px" }}>
                  <div style={{ fontSize: 10, color: "#64748b", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>National CPI</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#4cd7f6", fontFamily: "var(--font-mono)", marginTop: 2 }}>
                    {STATISTICAL_CONSTANTS.headlineCPI}
                  </div>
                  <div style={{ fontSize: 11, color: "#10b981", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                    {STATISTICAL_CONSTANTS.momChange} MoM
                  </div>
                </div>

                <div className="glass-card" style={{ padding: "14px 18px" }}>
                  <div style={{ fontSize: 10, color: "#64748b", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Basket Monitored</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#ffffff", fontFamily: "var(--font-mono)", marginTop: 2 }}>
                    25 <span style={{ fontSize: 14, color: "#94a3b8" }}>Routes</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                    5 Booking Horizons
                  </div>
                </div>

                <div className="glass-card" style={{ padding: "14px 18px" }}>
                  <div style={{ fontSize: 10, color: "#64748b", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Monthly Volume</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#f9bd22", fontFamily: "var(--font-mono)", marginTop: 2 }}>
                    15.3M
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                    DGCA Pax Weights
                  </div>
                </div>
              </div>
            </div>

            {/* Right: 3D Aircraft Interactive Canvas */}
            <div
              style={{
                height: 520,
                width: "100%",
                position: "relative",
                borderRadius: 24,
                overflow: "hidden",
                border: "1px solid rgba(76, 215, 246, 0.15)",
                background: "radial-gradient(circle at 60% 40%, rgba(59, 130, 246, 0.15), rgba(8, 13, 26, 0.95) 75%)",
              }}
            >
              <HeroAircraft isHovered={isAircraftHovered} onHoverChange={setIsAircraftHovered} />

              {/* Floating Aerospace Badge on Canvas */}
              <div
                style={{
                  position: "absolute",
                  top: 18,
                  left: 20,
                  background: "rgba(8, 13, 26, 0.75)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid rgba(76, 215, 246, 0.3)",
                  borderRadius: 100,
                  padding: "6px 14px",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span className="pulse-dot" />
                <span style={{ color: "#4cd7f6", fontWeight: 600 }}>Interactive 3D Aircraft · Hover to Orbit</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. LIVE SYSTEM STATUS BAR */}
      <div className="container">
        <div className="status-ribbon">
          <div className="status-item">
            <span style={{ color: "#3b82f6" }}>⚡</span>
            <span className="status-label">Data Pipeline:</span>
            <span className="status-value">25 / 25 Routes</span>
          </div>
          <div className="status-item">
            <span className="pulse-dot" />
            <span className="status-label">Health:</span>
            <span style={{ color: "#10b981", fontWeight: 700 }}>HEALTHY</span>
          </div>
          <div className="status-item">
            <span style={{ color: "#f9bd22" }}>⏱</span>
            <span className="status-label">Latest Sampling:</span>
            <span className="status-value">{STATISTICAL_CONSTANTS.lastUpdate}</span>
          </div>
          <div className="status-item">
            <span style={{ color: "#4cd7f6" }}>📐</span>
            <span className="status-label">Index Engine:</span>
            <span style={{ color: "#4cd7f6", fontWeight: 700 }}>ONLINE (Jevons)</span>
          </div>
        </div>
      </div>

      {/* 3. AIRFARE VOLATILITY SECTION (DEL -> BOM) */}
      <section id="volatility" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Advance-Purchase Horizon Dynamics</div>
            <h2 className="section-title">Airfares Don't Behave Like Ordinary Prices.</h2>
            <p className="section-subtitle">
              Unlike static commodities, airline revenue management adjusts seat availability dynamically. True CPI isolates inflation by indexing within homogenous booking windows.
            </p>
          </div>

          <div className="glass-card glass-card-glow" style={{ padding: 36 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20, marginBottom: 32 }}>
              <div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#f9bd22", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                  Featured Benchmark Corridor
                </span>
                <h3 style={{ fontSize: 26, fontWeight: 800, color: "#fff", marginTop: 4 }}>
                  New Delhi (DEL) ➔ Mumbai (BOM)
                </h3>
              </div>

              <div style={{ textAlign: "right" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#64748b" }}>CURRENT HORIZON PRICE</span>
                <div style={{ fontSize: 36, fontWeight: 800, color: "#4cd7f6", fontFamily: "var(--font-mono)" }}>
                  ₹{currentHorizon.price.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: "#f9bd22", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                  {currentHorizon.multiplier} vs Baseline ({currentHorizon.tag})
                </div>
              </div>
            </div>

            {/* Interactive Timeline Controls */}
            <div style={{ position: "relative", margin: "40px 0 20px" }}>
              <div
                style={{
                  height: 6,
                  background: "linear-gradient(90deg, #10b981 0%, #3b82f6 50%, #ef4444 100%)",
                  borderRadius: 10,
                  position: "relative",
                }}
              />

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(5, 1fr)",
                  gap: 12,
                  marginTop: -16,
                }}
              >
                {BOOKING_HORIZONS.map((h, i) => {
                  const isActive = volatilityIndex === i;
                  return (
                    <button
                      key={h.horizon}
                      onClick={() => setVolatilityIndex(i)}
                      style={{
                        background: isActive ? "rgba(76, 215, 246, 0.2)" : "rgba(14, 19, 32, 0.9)",
                        border: isActive ? "2px solid #00ffff" : "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: 12,
                        padding: "16px 12px",
                        textAlign: "center",
                        cursor: "pointer",
                        transition: "all 0.25s ease",
                        boxShadow: isActive ? "0 0 20px rgba(6, 182, 212, 0.4)" : "none",
                        transform: isActive ? "translateY(-6px)" : "none",
                      }}
                    >
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 800, color: isActive ? "#00ffff" : "#fff" }}>
                        {h.horizon}
                      </div>
                      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                        {h.days === 0 ? "Same-Day" : `${h.days} Days Prior`}
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#f9bd22", fontFamily: "var(--font-mono)", marginTop: 8 }}>
                        ₹{h.price.toLocaleString()}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div style={{ marginTop: 24, padding: "14px 20px", background: "rgba(255,255,255,0.03)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.06)", fontSize: 13, color: "#94a3b8" }}>
              💡 <strong>Methodology Note:</strong> {currentHorizon.desc} Comparing fares within the same horizon across time intervals prevents spurious inflation readings caused by consumer urgency.
            </div>
          </div>
        </div>
      </section>

      {/* 4. LIVE INDIA AVIATION CPI TIME SERIES */}
      <section id="index" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">National Price Movement</div>
            <h2 className="section-title">All-India Airfare Consumer Price Index</h2>
            <p className="section-subtitle">
              Aggregated across all 25 domestic corridors using DGCA passenger-volume weights.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 32 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16, marginBottom: 24 }}>
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                  <span style={{ fontSize: 48, fontWeight: 900, color: "#ffffff", fontFamily: "var(--font-mono)" }}>
                    {STATISTICAL_CONSTANTS.headlineCPI}
                  </span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: "#10b981", fontFamily: "var(--font-mono)" }}>
                    {STATISTICAL_CONSTANTS.momChange} MoM
                  </span>
                  <span style={{ fontSize: 12, color: "#64748b", fontFamily: "var(--font-mono)" }}>
                    (Base {STATISTICAL_CONSTANTS.baseYear})
                  </span>
                </div>
              </div>

              {/* Time Range Filter Pills */}
              <div style={{ display: "flex", background: "rgba(255,255,255,0.05)", padding: 4, borderRadius: 8, gap: 4 }}>
                {["7D", "30D", "90D", "1Y"].map((r) => (
                  <button
                    key={r}
                    onClick={() => setChartRange(r)}
                    style={{
                      padding: "6px 14px",
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      fontFamily: "var(--font-mono)",
                      background: chartRange === r ? "#3b82f6" : "transparent",
                      color: chartRange === r ? "#fff" : "#94a3b8",
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

            {/* Recharts Area Chart */}
            <div style={{ width: "100%", height: 360 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={TIME_SERIES_DATA[chartRange]}>
                  <defs>
                    <linearGradient id="cpiGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis domain={["auto", "auto"]} stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(8, 13, 26, 0.95)",
                      border: "1px solid rgba(76, 215, 246, 0.3)",
                      borderRadius: 8,
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpi"
                    stroke="#00ffff"
                    strokeWidth={3}
                    fill="url(#cpiGlow)"
                    name="National Airfare CPI"
                    dot={{ r: 4, fill: "#00ffff" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* 5. INDIA AVIATION ROUTE NETWORK (SVG MAP) */}
      <section id="network" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Spatial Network Topology</div>
            <h2 className="section-title">India Domestic Aviation Corridor Grid</h2>
            <p className="section-subtitle">
              Live route monitoring across top high-density metro and tier-1 airport pairs.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 24 }}>
            <IndiaNetworkMap />
          </div>
        </div>
      </section>

      {/* 6. ROUTE PRICE HEATMAP */}
      <section id="heatmap" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Cross-Sectional Intensity</div>
            <h2 className="section-title">Domestic Route Price Pressure Heatmap</h2>
            <p className="section-subtitle">
              Granular price distribution across the 25 DGCA basket routes and 5 booking horizons.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 28, overflowX: "auto" }}>
            <div className="heatmap-grid" style={{ fontWeight: 700, color: "#64748b", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: 10, marginBottom: 10 }}>
              <div>CORRIDOR</div>
              <div style={{ textAlign: "center" }}>T+0 (SAME-DAY)</div>
              <div style={{ textAlign: "center" }}>T+3</div>
              <div style={{ textAlign: "center" }}>T+7</div>
              <div style={{ textAlign: "center" }}>T+15</div>
              <div style={{ textAlign: "center" }}>T+30</div>
              <div style={{ textAlign: "right" }}>JEVONS CPI</div>
            </div>

            {ROUTE_HEATMAP_DATA.map((row) => (
              <div key={row.route} className="heatmap-grid" style={{ alignItems: "center", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                <div style={{ fontWeight: 700, color: "#ffffff" }}>
                  {row.route}
                  <span style={{ fontSize: 10, color: "#64748b", display: "block" }}>{row.pax} Pax ({row.weight}%)</span>
                </div>

                <div className="heatmap-cell" style={{ backgroundColor: "rgba(239, 68, 68, 0.25)", color: "#fca5a5" }}>
                  ₹{row.t0.toLocaleString()}
                </div>
                <div className="heatmap-cell" style={{ backgroundColor: "rgba(245, 158, 11, 0.2)", color: "#fde047" }}>
                  ₹{row.t3.toLocaleString()}
                </div>
                <div className="heatmap-cell" style={{ backgroundColor: "rgba(59, 130, 246, 0.2)", color: "#93c5fd" }}>
                  ₹{row.t7.toLocaleString()}
                </div>
                <div className="heatmap-cell" style={{ backgroundColor: "rgba(6, 182, 212, 0.15)", color: "#67e8f9" }}>
                  ₹{row.t15.toLocaleString()}
                </div>
                <div className="heatmap-cell" style={{ backgroundColor: "rgba(16, 185, 129, 0.15)", color: "#86efac" }}>
                  ₹{row.t30.toLocaleString()}
                </div>

                <div style={{ textAlign: "right", fontWeight: 700, color: "#4cd7f6" }}>
                  {row.cpi}
                  <span style={{ fontSize: 10, color: "#10b981", display: "block" }}>{row.change}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 7. DATA PIPELINE ARCHITECTURE */}
      <section id="pipeline" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Automated Ingestion Flow</div>
            <h2 className="section-title">From Web Raw Quotes to National Index</h2>
            <p className="section-subtitle">
              A 5-stage automated statistical intelligence pipeline designed for national scale.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 16,
            }}
          >
            {[
              { step: "01", name: "INGEST", desc: "Headless Playwright + XHR network interception continuously sampling airline and OTA portals." },
              { step: "02", name: "VALIDATE", desc: "Hard exclusions (₹0, corrupted tax ratios) and rolling IQR statistical anomaly fencing." },
              { step: "03", name: "STRATIFY", desc: "Clustering fare quotes into T+0, T+3, T+7, T+15, and T+30 advance-purchase buckets." },
              { step: "04", name: "COMPUTE", desc: "Jevons Geometric Mean micro-indices aggregated via DGCA passenger-volume weights." },
              { step: "05", name: "PUBLISH", desc: "Real-time API dissemination and MoSPI-format official statistical bulletins." },
            ].map((node, i) => (
              <div key={node.name} className="glass-card" style={{ position: "relative" }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 900, color: "rgba(76, 215, 246, 0.25)" }}>
                  {node.step}
                </div>
                <h4 style={{ fontSize: 18, fontWeight: 800, color: "#ffffff", margin: "8px 0" }}>
                  {node.name}
                </h4>
                <p style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6 }}>
                  {node.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 8. ECONOMETRIC ENGINE & MATHEMATICAL RIGOR */}
      <section id="methodology" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Mathematical Rigor</div>
            <h2 className="section-title">The Econometric Formulation</h2>
            <p className="section-subtitle">
              ILO/IMF CPI Manual compliant index formulas eliminating substitution bias.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {/* Jevons Micro Index Card */}
            <div className="glass-card glass-card-glow">
              <div style={{ fontSize: 11, color: "#f9bd22", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>
                1. Elementary Micro-Index (Route Level)
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 800, color: "#fff", marginTop: 4 }}>
                Jevons Geometric Price Index
              </h3>
              <div
                style={{
                  background: "rgba(8, 13, 26, 0.9)",
                  border: "1px solid rgba(76, 215, 246, 0.3)",
                  borderRadius: 8,
                  padding: "16px 20px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 18,
                  textAlign: "center",
                  color: "#00ffff",
                  margin: "18px 0",
                }}
              >
                I(r, t) = [ ∏ (p_i,t / p_i,0) ] ^ (1/n)
              </div>
              <ul style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.8, paddingLeft: 18 }}>
                <li>Computed in log-space: <code style={{ color: "#4cd7f6" }}>ln I = (1/n) ∑ ln(p_t / p_0)</code></li>
                <li>Satisfies the <strong>Time-Reversal Test</strong>: <code style={{ color: "#10b981" }}>I(0→t) × I(t→0) = 1.0</code></li>
                <li>Eliminates the Carli arithmetic upward substitution bias.</li>
              </ul>
            </div>

            {/* Upper Aggregator Card */}
            <div className="glass-card">
              <div style={{ fontSize: 11, color: "#10b981", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>
                2. Upper-Level Aggregation (National Headline)
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 800, color: "#fff", marginTop: 4 }}>
                Laspeyres / Young with DGCA Weights
              </h3>
              <div
                style={{
                  background: "rgba(8, 13, 26, 0.9)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  borderRadius: 8,
                  padding: "16px 20px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 18,
                  textAlign: "center",
                  color: "#34d399",
                  margin: "18px 0",
                }}
              >
                CPI(t) = ∑ [ w_r × I(r, t) ] × 100
              </div>
              <ul style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.8, paddingLeft: 18 }}>
                <li>Weighted by empirical DGCA city-pair monthly passenger volumes.</li>
                <li><code style={{ color: "#4cd7f6" }}>w_r = DGCA_Pax_r / ∑ DGCA_Pax</code> across 25 routes.</li>
                <li>Provides stable economic weighting unaffected by ticket volatility.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 9. LIVE SCRAPER MONITOR & SIMULATION */}
      <section style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="glass-card" style={{ padding: 32, position: "relative", overflow: "hidden" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20, marginBottom: 28 }}>
              <div>
                <div style={{ fontSize: 11, color: "#4cd7f6", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>
                  Live Sampling Pipeline Diagnostics
                </div>
                <h3 style={{ fontSize: 24, fontWeight: 800, color: "#ffffff", marginTop: 4 }}>
                  Scraper Fleet & Source Health
                </h3>
              </div>

              <button
                onClick={handleTriggerScrape}
                disabled={isScrapingRunning}
                className="btn-primary-glow"
                style={{
                  background: isScrapingRunning ? "rgba(59, 130, 246, 0.5)" : undefined,
                  cursor: isScrapingRunning ? "wait" : "pointer",
                }}
              >
                {isScrapingRunning ? `🔄 INGESTING (STAGE ${scrapeStep}/4)...` : "⚡ TRIGGER SCRAPE CYCLE"}
              </button>
            </div>

            {/* Active Sources Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
              {SCRAPER_MONITOR_SOURCES.map((src) => (
                <div key={src.name} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: "14px 18px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: 14, color: "#fff" }}>{src.name}</strong>
                    <span style={{ fontSize: 10, color: "#34d399", fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                      ● {src.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 11, color: "#64748b", fontFamily: "var(--font-mono)" }}>
                    <span>Latency: <strong style={{ color: "#94a3b8" }}>{src.latency}</strong></span>
                    <span>Quotes: <strong style={{ color: "#4cd7f6" }}>{src.observations}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 10. API EXPLORER */}
      <section id="api" style={{ padding: "60px 0" }}>
        <div className="container">
          <div className="section-header">
            <div className="section-eyebrow">Enterprise & Dissemination Architecture</div>
            <h2 className="section-title">One Index. Many Interfaces.</h2>
            <p className="section-subtitle">
              High-performance REST API endpoints providing statistical data feeds for MoSPI systems.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: 24 }}>
            {/* Endpoints List */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {API_ENDPOINTS_LIST.map((ep, i) => (
                <div
                  key={ep.path}
                  onClick={() => setSelectedApiIndex(i)}
                  style={{
                    background: selectedApiIndex === i ? "rgba(59, 130, 246, 0.2)" : "rgba(14, 19, 32, 0.7)",
                    border: selectedApiIndex === i ? "1px solid #4cd7f6" : "1px solid rgba(255,255,255,0.06)",
                    borderRadius: 10,
                    padding: "14px 18px",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      style={{
                        padding: "2px 6px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                        fontFamily: "var(--font-mono)",
                        backgroundColor: ep.method === "GET" ? "rgba(16, 185, 129, 0.2)" : "rgba(59, 130, 246, 0.2)",
                        color: ep.method === "GET" ? "#34d399" : "#60a5fa",
                      }}
                    >
                      {ep.method}
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "#fff", fontWeight: 600 }}>
                      {ep.path}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 6 }}>
                    {ep.description}
                  </p>
                </div>
              ))}
            </div>

            {/* JSON Response Terminal */}
            <div
              className="glass-card"
              style={{
                background: "rgba(5, 9, 18, 0.95)",
                border: "1px solid rgba(76, 215, 246, 0.3)",
                padding: 20,
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                overflowY: "auto",
                maxHeight: 480,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 8, marginBottom: 12, color: "#64748b", fontSize: 11 }}>
                <span>HTTP/1.1 200 OK</span>
                <span>Content-Type: application/json</span>
              </div>
              <pre style={{ color: "#4cd7f6", margin: 0 }}>
                {JSON.stringify(API_ENDPOINTS_LIST[selectedApiIndex].response, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* 11. STATISTICAL BULLETIN MODAL */}
      {showBulletinModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.85)",
            backdropFilter: "blur(16px)",
            zIndex: 99999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <div
            className="glass-card"
            style={{
              maxWidth: 760,
              width: "100%",
              maxHeight: "88vh",
              overflowY: "auto",
              background: "#0c1220",
              border: "1px solid #4cd7f6",
              padding: 36,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: 16 }}>
              <div>
                <span style={{ fontSize: 11, color: "#f9bd22", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Government of India · MoSPI</span>
                <h3 style={{ fontSize: 18, color: "#fff", fontWeight: 800, marginTop: 2 }}>Monthly Statistical Release Bulletin</h3>
              </div>
              <button
                onClick={() => setShowBulletinModal(false)}
                style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 22, cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginTop: 24, fontFamily: "serif", color: "#e2e8f0", lineHeight: 1.7, fontSize: 14 }}>
              <div style={{ textAlign: "center", margin: "16px 0", borderBottom: "1px solid #334155", paddingBottom: 12 }}>
                <strong style={{ fontSize: 16, textTransform: "uppercase" }}>PRESS RELEASE: ALL-INDIA CONSUMER PRICE INDEX FOR DOMESTIC AIR TRAVEL</strong>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Base Year: 2024 = 100 | Reference Period: August 2026</div>
              </div>

              <div style={{ background: "rgba(255,255,255,0.03)", padding: 16, borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)", margin: "16px 0" }}>
                <div>ALL-INDIA AIRFARE CPI (PROVISIONAL): <strong style={{ color: "#4cd7f6", fontSize: 20 }}>107.42</strong></div>
                <div>Month-on-Month Movement: <strong style={{ color: "#10b981" }}>+2.84%</strong></div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Based on 48,200 validated quotes across 25 high-traffic DGCA corridors.</div>
              </div>

              <p style={{ fontSize: 13 }}>
                The All-India Airfare Price Index reflects price fluctuations of scheduled domestic commercial passenger flights across 25 high-density routes weighted by Directorate General of Civil Aviation (DGCA) city-pair passenger traffic. Micro-level route indices are computed using the <strong>Jevons geometric mean formula</strong>, stratified across five advance-purchase booking horizons (T+0, T+3, T+7, T+15, and T+30).
              </p>
            </div>

            <div style={{ textAlign: "right", marginTop: 24 }}>
              <button onClick={() => setShowBulletinModal(false)} className="btn-primary-glow" style={{ padding: "8px 20px" }}>
                Close Bulletin
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 12. FINAL FOOTER & CALL TO ACTION */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.08)", padding: "40px 0 60px", marginTop: 80 }}>
        <div className="container" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 20 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#fff" }}>
              AIRFARE <span style={{ color: "#4cd7f6" }}>CPI</span>
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
              Smart India Hackathon 2026 · Problem Statement SIH26056 (MoSPI)
            </div>
          </div>

          <div style={{ fontSize: 12, color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
            Built with statistical rigor and modern aerospace telemetry.
          </div>
        </div>
      </footer>
    </div>
  );
}
