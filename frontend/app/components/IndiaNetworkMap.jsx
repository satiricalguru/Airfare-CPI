"use client";
/* eslint-disable @next/next/no-img-element */

import { useState, useEffect, useMemo, useRef, useCallback, useSyncExternalStore } from "react";
import { Compass, Layers } from "lucide-react";
import { getAssetPath } from "../utils/assetPath";
import { NOT_AVAILABLE } from "../lib/api";
import { fmtCount, fmtIndex, fmtPctFromFraction } from "../lib/format";

// ── Exact Calibrated Coordinates for High-Definition Space View with Marked Borders (1024 × 935) ──
const HUBS_CONFIG = [
  { code: "DEL", city: "New Delhi", state: "Delhi", x: 356, y: 262, labelOffset: { x: 14, y: -8 } },
  { code: "BOM", city: "Mumbai", state: "Maharashtra", x: 224, y: 512, labelOffset: { x: -38, y: 4 } },
  { code: "PNQ", city: "Pune", state: "Maharashtra", x: 248, y: 534, labelOffset: { x: 14, y: 8 } },
  { code: "BLR", city: "Bengaluru", state: "Karnataka", x: 352, y: 692, labelOffset: { x: -38, y: 4 } },
  { code: "HYD", city: "Hyderabad", state: "Telangana", x: 405, y: 562, labelOffset: { x: 14, y: 4 } },
  { code: "CCU", city: "Kolkata", state: "West Bengal", x: 645, y: 428, labelOffset: { x: 14, y: 4 } },
  { code: "MAA", city: "Chennai", state: "Tamil Nadu", x: 432, y: 678, labelOffset: { x: 14, y: 4 } },
  { code: "AMD", city: "Ahmedabad", state: "Gujarat", x: 232, y: 412, labelOffset: { x: -38, y: 0 } },
  { code: "GOI", city: "Goa", state: "Goa", x: 242, y: 622, labelOffset: { x: -34, y: 4 } },
  { code: "COK", city: "Kochi", state: "Kerala", x: 316, y: 768, labelOffset: { x: -34, y: 4 } },
  { code: "JAI", city: "Jaipur", state: "Rajasthan", x: 324, y: 308, labelOffset: { x: -34, y: 4 } },
  { code: "LKO", city: "Lucknow", state: "Uttar Pradesh", x: 465, y: 318, labelOffset: { x: 12, y: -8 } },
  { code: "PAT", city: "Patna", state: "Bihar", x: 580, y: 345, labelOffset: { x: 12, y: -8 } },
  { code: "GAU", city: "Guwahati", state: "Assam", x: 725, y: 342, labelOffset: { x: 12, y: -8 } },
  { code: "SXR", city: "Srinagar", state: "Jammu & Kashmir", x: 320, y: 135, labelOffset: { x: -34, y: -8 } },
  { code: "IXZ", city: "Port Blair", state: "Andaman & Nicobar", x: 750, y: 742, labelOffset: { x: 14, y: 4 } },
];

const HUB_MAP = Object.fromEntries(HUBS_CONFIG.map((h) => [h.code, h]));

// ── Clearly Marked State Name Badges on Space View ──
const STATE_LABELS = [
  { name: "JAMMU & KASHMIR", x: 330, y: 110 },
  { name: "LADAKH", x: 385, y: 85 },
  { name: "PUNJAB", x: 305, y: 195 },
  { name: "HARYANA", x: 338, y: 235 },
  { name: "RAJASTHAN", x: 270, y: 305 },
  { name: "UTTAR PRADESH", x: 470, y: 295 },
  { name: "GUJARAT", x: 195, y: 410 },
  { name: "MADHYA PRADESH", x: 390, y: 415 },
  { name: "BIHAR", x: 585, y: 325 },
  { name: "WEST BENGAL", x: 650, y: 405 },
  { name: "MAHARASHTRA", x: 315, y: 505 },
  { name: "CHHATTISGARH", x: 485, y: 465 },
  { name: "ODISHA", x: 545, y: 480 },
  { name: "TELANGANA", x: 410, y: 540 },
  { name: "ANDHRA PRADESH", x: 445, y: 635 },
  { name: "KARNATAKA", x: 315, y: 640 },
  { name: "TAMIL NADU", x: 380, y: 745 },
  { name: "KERALA", x: 310, y: 750 },
  { name: "ASSAM", x: 750, y: 325 },
];

// ── Complete 25 Domestic Aviation Corridors in MoSPI Representative Basket ──
const ALL_NETWORK_ROUTES = [
  { from: "DEL", to: "BOM", name: "Delhi ⇄ Mumbai", desc: "Golden Trunk Corridor", weightPct: 10.02 },
  { from: "DEL", to: "BLR", name: "Delhi ⇄ Bengaluru", desc: "Tech Expressway", weightPct: 7.93 },
  { from: "BOM", to: "BLR", name: "Mumbai ⇄ Bengaluru", desc: "Commercial Shuttle", weightPct: 7.26 },
  { from: "DEL", to: "HYD", name: "Delhi ⇄ Hyderabad", desc: "Deccan Trunk", weightPct: 6.51 },
  { from: "DEL", to: "CCU", name: "Delhi ⇄ Kolkata", desc: "Eastern Express", weightPct: 6.18 },
  { from: "BOM", to: "HYD", name: "Mumbai ⇄ Hyderabad", desc: "Western Gateway", weightPct: 5.43 },
  { from: "DEL", to: "MAA", name: "Delhi ⇄ Chennai", desc: "Southern Trunk", weightPct: 5.01 },
  { from: "BOM", to: "CCU", name: "Mumbai ⇄ Kolkata", desc: "Trans-India Heavy", weightPct: 4.34 },
  { from: "BLR", to: "HYD", name: "Bengaluru ⇄ Hyderabad", desc: "Cyber Corridor", weightPct: 4.01 },
  { from: "DEL", to: "GOI", name: "Delhi ⇄ Goa", desc: "Leisure Flagship", weightPct: 3.76 },
  { from: "BOM", to: "MAA", name: "Mumbai ⇄ Chennai", desc: "Coastal Trunk", weightPct: 3.59 },
  { from: "BLR", to: "CCU", name: "Bengaluru ⇄ Kolkata", desc: "East-South Link", weightPct: 3.34 },
  { from: "DEL", to: "PNQ", name: "Delhi ⇄ Pune", desc: "Auto-IT Corridor", weightPct: 3.26 },
  { from: "BOM", to: "GOI", name: "Mumbai ⇄ Goa", desc: "Konkan Shuttle", weightPct: 3.17 },
  { from: "DEL", to: "AMD", name: "Delhi ⇄ Ahmedabad", desc: "Business Corridor", weightPct: 3.09 },
  { from: "BLR", to: "MAA", name: "Bengaluru ⇄ Chennai", desc: "Short-Haul Shuttle", weightPct: 2.84 },
  { from: "DEL", to: "JAI", name: "Delhi ⇄ Jaipur", desc: "Heritage Commuter", weightPct: 2.67 },
  { from: "BOM", to: "AMD", name: "Mumbai ⇄ Ahmedabad", desc: "Industrial Shuttle", weightPct: 2.59 },
  { from: "DEL", to: "LKO", name: "Delhi ⇄ Lucknow", desc: "Awadh Express", weightPct: 2.50 },
  { from: "BLR", to: "GOI", name: "Bengaluru ⇄ Goa", desc: "Southern Holiday Link", weightPct: 2.34 },
  { from: "HYD", to: "CCU", name: "Hyderabad ⇄ Kolkata", desc: "East-Coast Trunk", weightPct: 2.25 },
  { from: "DEL", to: "PAT", name: "Delhi ⇄ Patna", desc: "Ganga Trunk", weightPct: 2.17 },
  { from: "BOM", to: "JAI", name: "Mumbai ⇄ Jaipur", desc: "Royal Route", weightPct: 2.00 },
  { from: "DEL", to: "COK", name: "Delhi ⇄ Kochi", desc: "Kerala Long-Haul", weightPct: 1.92 },
  { from: "BOM", to: "PNQ", name: "Mumbai ⇄ Pune", desc: "Sahyadri Feeder", weightPct: 1.84 },
];

function subscribeToDocumentDark(callback) {
  if (typeof MutationObserver === "undefined") return () => {};
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getDocumentDarkSnapshot() {
  return typeof document !== "undefined" ? document.documentElement.classList.contains("dark") : false;
}

function getDocumentDarkServerSnapshot() {
  return false;
}

export default function IndiaNetworkMap({ isDarkMode: propDarkMode, routes = [] }) {
  const [selectedRoute, setSelectedRoute] = useState(ALL_NETWORK_ROUTES[0]);
  const [filterMode, setFilterMode] = useState("all"); // "all" | "top5" | "trunk"
  const [hoveredHub, setHoveredHub] = useState(null);
  const [utcTime, setUtcTime] = useState(() => new Date().toUTCString().slice(17, 25) + " UTC");

  const domDarkMode = useSyncExternalStore(subscribeToDocumentDark, getDocumentDarkSnapshot, getDocumentDarkServerSnapshot);
  const isDarkMode = propDarkMode !== undefined ? propDarkMode : domDarkMode;

  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  // Real-time UTC clock
  useEffect(() => {
    const timer = setInterval(() => {
      setUtcTime(new Date().toUTCString().slice(17, 25) + " UTC");
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  /**
   * Active selected route data derived from the API payload.
   */
  const activeRouteData = useMemo(() => {
    const from = selectedRoute?.from;
    const to = selectedRoute?.to;
    if (!from || !to) return undefined;
    return routes.find(
      (r) =>
        (r.origin_code === from && r.destination_code === to) ||
        (r.origin_code === to && r.destination_code === from),
    );
  }, [routes, selectedRoute]);

  const activeFrom = selectedRoute?.from || "DEL";
  const activeTo = selectedRoute?.to || "BOM";

  // Geodesic Corridor Curvature
  const getControlPoint = useCallback((h1, h2) => {
    const dx = h2.x - h1.x;
    const dy = h2.y - h1.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const curvature = Math.min(dist * 0.11, 36);
    const nx = -dy / dist;
    const ny = dx / dist;
    return {
      x: (h1.x + h2.x) / 2 + nx * curvature,
      y: (h1.y + h2.y) / 2 + ny * curvature,
    };
  }, []);

  const getBezierPoint = useCallback((p0, p1, p2, t) => {
    const invT = 1 - t;
    const x = invT * invT * p0.x + 2 * invT * t * p1.x + t * t * p2.x;
    const y = invT * invT * p0.y + 2 * invT * t * p1.y + t * t * p2.y;
    return { x, y };
  }, []);

  const isDarkRef = useRef(isDarkMode);
  useEffect(() => {
    isDarkRef.current = isDarkMode;
  }, [isDarkMode]);

  // Filtered routes list for quick switcher chips
  const displayedRoutes = useMemo(() => {
    if (filterMode === "top5") return ALL_NETWORK_ROUTES.slice(0, 5);
    if (filterMode === "trunk") return ALL_NETWORK_ROUTES.filter((r) => r.weightPct >= 4.0);
    return ALL_NETWORK_ROUTES;
  }, [filterMode]);

  // 60FPS Flight Animation — Renders ALL 25 Corridors on 896 × 1200 Space View
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let animId;
    const VB_W = 1024;
    const VB_H = 935;

    const setupCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    };

    setupCanvas();
    window.addEventListener("resize", setupCanvas);

    let mainProgress = 0;
    let time = 0;

    // Pre-calculate control points for all 25 corridors
    const corridorCurves = ALL_NETWORK_ROUTES.map((r, i) => {
      const h1 = HUB_MAP[r.from];
      const h2 = HUB_MAP[r.to];
      if (!h1 || !h2) return null;
      const cp = getControlPoint(h1, h2);
      return {
        from: r.from,
        to: r.to,
        h1,
        h2,
        cp,
        weight: r.weightPct,
        speed: 0.003 + (i % 5) * 0.0008,
        offset: (i * 0.17) % 1,
      };
    }).filter(Boolean);

    const render = () => {
      time += 0.016;
      mainProgress = (mainProgress + 0.005) % 1;

      const rect = canvas.getBoundingClientRect();
      const scaleX = rect.width / VB_W;
      const scaleY = rect.height / VB_H;

      ctx.clearRect(0, 0, rect.width, rect.height);

      const isDark = isDarkRef.current;
      const bgRouteColor = isDark ? "rgba(101, 201, 138, 0.28)" : "rgba(46, 125, 50, 0.35)";
      const greenColor = isDark ? "#65C98A" : "#2e7d32";
      const glowColor = isDark ? "rgba(101, 201, 138, 0.95)" : "rgba(46, 125, 50, 0.85)";
      const softGlowColor = isDark ? "rgba(101, 201, 138, 0.3)" : "rgba(46, 125, 50, 0.25)";

      // ── 1. Draw ALL 25 Background Network Corridors ──
      corridorCurves.forEach((item) => {
        const isSelected =
          (item.from === activeFrom && item.to === activeTo) ||
          (item.from === activeTo && item.to === activeFrom);

        if (isSelected) return; // Drawn prominently in layer 2

        ctx.beginPath();
        ctx.moveTo(item.h1.x * scaleX, item.h1.y * scaleY);
        ctx.quadraticCurveTo(item.cp.x * scaleX, item.cp.y * scaleY, item.h2.x * scaleX, item.h2.y * scaleY);
        ctx.strokeStyle = bgRouteColor;
        ctx.lineWidth = 1.4;
        ctx.stroke();

        // Ambient moving pulse on major non-selected routes
        if (item.weight >= 4.0) {
          const ambProg = (time * item.speed * 20 + item.offset) % 1;
          const ambPt = getBezierPoint(item.h1, item.cp, item.h2, ambProg);
          ctx.beginPath();
          ctx.arc(ambPt.x * scaleX, ambPt.y * scaleY, 2.8, 0, Math.PI * 2);
          ctx.fillStyle = isDark ? "rgba(255, 255, 255, 0.75)" : "rgba(46, 125, 50, 0.75)";
          ctx.fill();
        }
      });

      // ── 2. Draw Prominent Selected Corridor ──
      const h1 = HUB_MAP[activeFrom];
      const h2 = HUB_MAP[activeTo];

      if (h1 && h2) {
        const cp = getControlPoint(h1, h2);

        // Outer soft glow
        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
        ctx.strokeStyle = softGlowColor;
        ctx.lineWidth = 12;
        ctx.stroke();

        // Sharp vibrant laser arc
        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
        ctx.strokeStyle = greenColor;
        ctx.lineWidth = 3.8;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 18;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // ── 3. Traveling Flight Beacon Pulse with Tail ──
        const pt = getBezierPoint(h1, cp, h2, mainProgress);

        // Core airplane beacon
        ctx.beginPath();
        ctx.arc(pt.x * scaleX, pt.y * scaleY, 6, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = greenColor;
        ctx.shadowBlur = 16;
        ctx.fill();
        ctx.shadowBlur = 0;

        // ── 4. Radar Expanding Rings on Selected Hubs ──
        [h1, h2].forEach((hub, idx) => {
          const phase = (time * 1.5 + idx * 0.6) % 1;
          const radius = (6 + phase * 28) * ((scaleX + scaleY) / 2);
          const opacity = (1 - phase) * 0.8;

          ctx.beginPath();
          ctx.arc(hub.x * scaleX, hub.y * scaleY, radius, 0, Math.PI * 2);
          ctx.strokeStyle = isDark ? `rgba(101, 201, 138, ${opacity})` : `rgba(46, 125, 50, ${opacity})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        });
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", setupCanvas);
    };
  }, [activeFrom, activeTo, getControlPoint, getBezierPoint]);

  const nodeColor = isDarkMode ? "#65C98A" : "#2e7d32";
  const badgeBg = isDarkMode ? "rgba(10, 18, 28, 0.88)" : "rgba(255, 255, 255, 0.95)";
  const badgeTextColor = isDarkMode ? "#f3f1e9" : "#191917";

  return (
    <div
      ref={containerRef}
      className="stitch-card network-map-card aerospace-space-map-root"
      data-testid="india-network-map"
    >
      {/* ── Top Mission Control Telemetry Strip ── */}
      <div className="aerospace-telemetry-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div className="aerospace-pill">
            <span className="aerospace-live-dot" />
            <strong>BHARAT-SAT · SPACE VIEW · STATES &amp; BORDERS DEMARCATED</strong>
          </div>
          <span className="aerospace-coords">
            20.59° N, 78.96° E · ORBIT: 480 KM
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span className="aerospace-utc-clock">
            {utcTime}
          </span>
          <span className="aerospace-engine-tag">
            <Layers size={11} style={{ display: "inline", marginRight: "4px" }} />
            25 MONITORED CORRIDORS
          </span>
        </div>
      </div>

      {/* ── Main Clean Space Map Viewport (896 × 1200) ── */}
      <div className="aerospace-map-viewport">
        {/* Layer 0: High-Resolution Satellite Space View with Glowing National & State Borders */}
        <div style={{ position: "absolute", inset: 0 }}>
          <img
            src={getAssetPath("/india_space_satellite_borders.jpg")}
            alt="Photorealistic Satellite Space View of India with Demarcated State Borders"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "fill",
              objectPosition: "center center",
              filter: isDarkMode
                ? "contrast(1.08) brightness(0.96) saturate(1.04)"
                : "contrast(1.02) brightness(1.02) saturate(1.05)",
              pointerEvents: "none",
            }}
          />

          {/* Atmospheric Edge Vignette */}
          <div className="aerospace-vignette" />
        </div>

        {/* Layer 1: Flight Arc Canvas (Renders 25 arcs & flight pulses) */}
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            zIndex: 1,
          }}
        />

        {/* Layer 2: Demarcated State Labels & All 16 Airport Hub Markers */}
        <svg
          viewBox="0 0 1024 935"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            zIndex: 2,
          }}
        >
          {/* Subtle Demarcated State Labels Across the Subcontinent */}
          <g id="demarcated-state-names" style={{ pointerEvents: "none" }}>
            {STATE_LABELS.map((st) => (
              <text
                key={st.name}
                x={st.x}
                y={st.y}
                textAnchor="middle"
                fill={isDarkMode ? "rgba(255, 255, 255, 0.42)" : "rgba(25, 25, 23, 0.55)"}
                fontSize={8.5}
                fontWeight={700}
                letterSpacing="0.14em"
                fontFamily="var(--mono)"
                style={{
                  textShadow: isDarkMode ? "0 1px 4px rgba(0,0,0,0.9)" : "0 1px 3px rgba(255,255,255,0.9)",
                }}
              >
                {st.name}
              </text>
            ))}
          </g>

          {/* All 16 Airport Hub Markers (Interactive & Hoverable) */}
          <g id="aerospace-airport-nodes">
            {HUBS_CONFIG.map((hub) => {
              const isOrigin = hub.code === activeFrom;
              const isDest = hub.code === activeTo;
              const isActive = isOrigin || isDest;
              const offset = hub.labelOffset || { x: 14, y: 4 };

              return (
                <g
                  key={hub.code}
                  transform={`translate(${hub.x}, ${hub.y})`}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHoveredHub(hub)}
                  onMouseLeave={() => setHoveredHub(null)}
                  onClick={() => {
                    // Quick select a route connected to this hub
                    const match = ALL_NETWORK_ROUTES.find(
                      (r) => r.from === hub.code || r.to === hub.code
                    );
                    if (match) setSelectedRoute(match);
                  }}
                  data-testid={`india-map-hub-${hub.code.toLowerCase()}`}
                >
                  {/* Active Selected Target Ring */}
                  {isActive && (
                    <circle
                      r={18}
                      fill={isDarkMode ? "rgba(101, 201, 138, 0.25)" : "rgba(46, 125, 50, 0.2)"}
                      stroke={nodeColor}
                      strokeWidth={1.8}
                      strokeDasharray="4 3"
                    />
                  )}

                  {/* Airport Pin Outer Ring */}
                  <circle
                    r={isActive ? 8 : 5}
                    fill={isActive ? nodeColor : isDarkMode ? "rgba(101, 201, 138, 0.65)" : "rgba(46, 125, 50, 0.7)"}
                    stroke="#ffffff"
                    strokeWidth={isActive ? 2.4 : 1.5}
                    style={{
                      filter: isActive ? `drop-shadow(0 0 10px ${nodeColor})` : "none",
                      transition: "all 0.2s ease",
                    }}
                  />

                  {/* Small Inner Core */}
                  <circle r={isActive ? 2.8 : 1.8} fill={isDarkMode ? "#050B14" : "#ffffff"} />

                  {/* Clean IATA Airport Badge */}
                  <g transform={`translate(${offset.x}, ${offset.y})`}>
                    <rect
                      x={-4}
                      y={-11}
                      width={32}
                      height={16}
                      rx={4}
                      fill={isActive ? (isDarkMode ? "#65C98A" : "var(--ink, #191917)") : badgeBg}
                      stroke={isActive ? "#ffffff" : isDarkMode ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.25)"}
                      strokeWidth={isActive ? 1.4 : 0.8}
                      style={{
                        filter: "drop-shadow(0 3px 6px rgba(0,0,0,0.5))",
                        transition: "all 0.2s ease",
                      }}
                    />
                    <text
                      x={12}
                      y={1}
                      textAnchor="middle"
                      fill={isActive ? (isDarkMode ? "#050B14" : "#ffffff") : badgeTextColor}
                      fontSize={9.5}
                      fontWeight={isActive ? 800 : 700}
                      fontFamily="var(--mono)"
                    >
                      {hub.code}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Hover Hub Tooltip Overlay */}
        {hoveredHub && (
          <div
            style={{
              position: "absolute",
              left: `${(hoveredHub.x / 1024) * 100}%`,
              top: `${(hoveredHub.y / 935) * 100}%`,
              transform: "translate(-50%, -130%)",
              background: "var(--paper-bright)",
              color: "var(--ink)",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "var(--mono)",
              boxShadow: "var(--shadow)",
              pointerEvents: "none",
              zIndex: 10,
              whiteSpace: "nowrap",
            }}
          >
            <strong>{hoveredHub.city} ({hoveredHub.code})</strong>
            <div style={{ color: "var(--muted)", fontSize: "10px" }}>State: {hoveredHub.state}</div>
          </div>
        )}
      </div>

      {/* ── Analytics Console ── */}
      <div className="aerospace-analytics-console">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          {/* Active Corridor Selector & Indicator */}
          <div>
            <div className="aerospace-corridor-eyebrow">
              <Compass size={12} />
              <span>Selected Corridor ({ALL_NETWORK_ROUTES.findIndex((r) => r.from === activeFrom && r.to === activeTo) + 1} of 25)</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="aerospace-corridor-title">
                {activeFrom} ⇄ {activeTo}
              </span>
              <span className={`aerospace-status-pill ${activeRouteData ? "" : "is-missing"}`}>
                {activeRouteData ? "Index Available" : "Basket Corridor"}
              </span>
              <span className="aerospace-corridor-desc">
                {selectedRoute?.desc}
              </span>
            </div>
          </div>

          {/* Metric Stats Readouts */}
          <div style={{ display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
            <div>
              <div className="aerospace-stat-label">
                Jevons Index
              </div>
              <div className="aerospace-stat-value is-green">
                {activeRouteData ? fmtIndex(activeRouteData.value) : NOT_AVAILABLE}
              </div>
            </div>

            <div>
              <div className="aerospace-stat-label">
                Matched Products
              </div>
              <div className="aerospace-stat-value">
                {activeRouteData ? fmtCount(activeRouteData.matched_products) : NOT_AVAILABLE}
              </div>
            </div>

            <div>
              <div className="aerospace-stat-label">
                Basket Weight
              </div>
              <div className="aerospace-stat-value">
                {activeRouteData ? fmtPctFromFraction(activeRouteData.weight, 2) : `${selectedRoute?.weightPct}%`}
              </div>
            </div>
          </div>
        </div>

        {/* Route Filter Controls & All 25 Corridor Switcher Chips */}
        <div style={{ marginTop: 14, borderTop: "1px solid var(--line-light)", paddingTop: 10 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <button
                onClick={() => setFilterMode("all")}
                style={{
                  fontSize: "10.5px",
                  fontFamily: "var(--mono)",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line)",
                  background: filterMode === "all" ? "var(--ink)" : "var(--surface-subtle)",
                  color: filterMode === "all" ? "var(--paper)" : "var(--muted)",
                  cursor: "pointer",
                }}
              >
                All 25 Corridors
              </button>
              <button
                onClick={() => setFilterMode("top5")}
                style={{
                  fontSize: "10.5px",
                  fontFamily: "var(--mono)",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line)",
                  background: filterMode === "top5" ? "var(--ink)" : "var(--surface-subtle)",
                  color: filterMode === "top5" ? "var(--paper)" : "var(--muted)",
                  cursor: "pointer",
                }}
              >
                Top 5 Heavyweight
              </button>
              <button
                onClick={() => setFilterMode("trunk")}
                style={{
                  fontSize: "10.5px",
                  fontFamily: "var(--mono)",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line)",
                  background: filterMode === "trunk" ? "var(--ink)" : "var(--surface-subtle)",
                  color: filterMode === "trunk" ? "var(--paper)" : "var(--muted)",
                  cursor: "pointer",
                }}
              >
                Major Trunks (&gt;4%)
              </button>
            </div>
            <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--mono)" }}>
              Click corridor chip or map hub to inspect
            </span>
          </div>

          <div
            style={{
              display: "flex",
              gap: 6,
              overflowX: "auto",
              paddingBottom: 6,
              scrollbarWidth: "thin",
            }}
          >
            {displayedRoutes.map((r) => {
              const isCurrent = r.from === activeFrom && r.to === activeTo;
              return (
                <button
                  key={`${r.from}-${r.to}`}
                  onClick={() => setSelectedRoute(r)}
                  data-testid={`india-map-route-${r.from.toLowerCase()}-${r.to.toLowerCase()}-button`}
                  className={`aerospace-chip-btn ${isCurrent ? "is-active" : ""}`}
                  style={{ whiteSpace: "nowrap" }}
                >
                  {r.from} ⇄ {r.to} <span style={{ opacity: 0.65, fontSize: "10px" }}>({r.weightPct}%)</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
