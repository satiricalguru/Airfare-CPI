"use client";
/* eslint-disable @next/next/no-img-element */

import { useState, useEffect, useMemo, useRef, useCallback, useSyncExternalStore } from "react";
import { Compass } from "lucide-react";
import { getAssetPath } from "../utils/assetPath";
import { NOT_AVAILABLE } from "../lib/api";
import { fmtCount, fmtIndex, fmtPctFromFraction } from "../lib/format";

// ── Exact Ground-Truth Coordinates (1200 × 896 Centered Satellite Basemap) ──
const HUBS_CONFIG = [
  { code: "DEL", city: "New Delhi", state: "Delhi", x: 475, y: 310, labelOffset: { x: 14, y: -10 } },
  { code: "BOM", city: "Mumbai", state: "Maharashtra", x: 380, y: 550, labelOffset: { x: -36, y: 4 } },
  { code: "BLR", city: "Bengaluru", state: "Karnataka", x: 485, y: 730, labelOffset: { x: -36, y: 4 } },
  { code: "HYD", city: "Hyderabad", state: "Telangana", x: 520, y: 610, labelOffset: { x: 14, y: 4 } },
  { code: "CCU", city: "Kolkata", state: "West Bengal", x: 745, y: 460, labelOffset: { x: 14, y: 4 } },
  { code: "MAA", city: "Chennai", state: "Tamil Nadu", x: 540, y: 735, labelOffset: { x: 14, y: 4 } },
  { code: "AMD", city: "Ahmedabad", state: "Gujarat", x: 370, y: 445, labelOffset: { x: -36, y: 0 } },
  { code: "GOI", city: "Goa", state: "Goa", x: 415, y: 650, labelOffset: { x: -34, y: 4 } },
  { code: "COK", city: "Kochi", state: "Kerala", x: 470, y: 800, labelOffset: { x: -34, y: 4 } },
  { code: "JAI", city: "Jaipur", state: "Rajasthan", x: 420, y: 365, labelOffset: { x: -32, y: 4 } },
  { code: "LKO", city: "Lucknow", state: "Uttar Pradesh", x: 560, y: 345, labelOffset: { x: 12, y: -8 } },
  { code: "PAT", city: "Patna", state: "Bihar", x: 660, y: 375, labelOffset: { x: 12, y: -8 } },
  { code: "GAU", city: "Guwahati", state: "Assam", x: 855, y: 360, labelOffset: { x: 12, y: -8 } },
  { code: "SXR", city: "Srinagar", state: "Jammu & Kashmir", x: 385, y: 155, labelOffset: { x: -34, y: -6 } },
  { code: "IXZ", city: "Port Blair", state: "Andaman & Nicobar", x: 885, y: 805, labelOffset: { x: 12, y: 4 } },
];

const HUB_MAP = Object.fromEntries(HUBS_CONFIG.map((h) => [h.code, h]));

// ── Golden Trunk Corridors ──
const ALL_NETWORK_ROUTES = [
  { from: "DEL", to: "BOM", name: "Delhi ⇄ Mumbai", desc: "Golden Trunk Corridor" },
  { from: "DEL", to: "BLR", name: "Delhi ⇄ Bengaluru", desc: "Tech Expressway" },
  { from: "BOM", to: "BLR", name: "Mumbai ⇄ Bengaluru", desc: "Commercial Shuttle" },
  { from: "DEL", to: "HYD", name: "Delhi ⇄ Hyderabad", desc: "Deccan Trunk" },
  { from: "BOM", to: "HYD", name: "Mumbai ⇄ Hyderabad", desc: "Western Gateway" },
  { from: "DEL", to: "CCU", name: "Delhi ⇄ Kolkata", desc: "Eastern Express" },
  { from: "DEL", to: "MAA", name: "Delhi ⇄ Chennai", desc: "Southern Trunk" },
  { from: "BLR", to: "MAA", name: "Bengaluru ⇄ Chennai", desc: "Short-Haul Shuttle" },
  { from: "BOM", to: "GOI", name: "Mumbai ⇄ Goa", desc: "Leisure Heavyweight" },
  { from: "BOM", to: "AMD", name: "Mumbai ⇄ Ahmedabad", desc: "Industrial Corridor" },
  { from: "BLR", to: "COK", name: "Bengaluru ⇄ Kochi", desc: "Southern Connector" },
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
  const fromHub = HUB_MAP[activeFrom] || HUBS_CONFIG[0];
  const toHub = HUB_MAP[activeTo] || HUBS_CONFIG[1];

  // Geodesic Corridor Curvature
  const getControlPoint = useCallback((h1, h2) => {
    const dx = h2.x - h1.x;
    const dy = h2.y - h1.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const curvature = Math.min(dist * 0.08, 24);
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

  // 60FPS Flight Animation (Selected Corridor Only)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let animId;
    const VB_W = 1200;
    const VB_H = 896;

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

    let progress = 0;
    let time = 0;

    const render = () => {
      time += 0.016;
      progress = (progress + 0.0055) % 1;

      const rect = canvas.getBoundingClientRect();
      const scaleX = rect.width / VB_W;
      const scaleY = rect.height / VB_H;

      ctx.clearRect(0, 0, rect.width, rect.height);

      const h1 = HUB_MAP[activeFrom];
      const h2 = HUB_MAP[activeTo];

      const isDark = isDarkRef.current;
      const greenColor = isDark ? "#65C98A" : "#2e7d32";
      const glowColor = isDark ? "rgba(101, 201, 138, 0.9)" : "rgba(46, 125, 50, 0.7)";
      const softGlowColor = isDark ? "rgba(101, 201, 138, 0.25)" : "rgba(46, 125, 50, 0.2)";

      if (h1 && h2) {
        const cp = getControlPoint(h1, h2);

        // 1. Prominent Selected Corridor Arc
        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
        ctx.strokeStyle = greenColor;
        ctx.lineWidth = 3.6;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 18;
        ctx.stroke();

        // Outer soft glow
        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
        ctx.strokeStyle = softGlowColor;
        ctx.lineWidth = 8.5;
        ctx.shadowBlur = 0;
        ctx.stroke();

        // 2. Single Traveling Flight Pulse
        const pt = getBezierPoint(h1, cp, h2, progress);
        ctx.beginPath();
        ctx.arc(pt.x * scaleX, pt.y * scaleY, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = greenColor;
        ctx.shadowBlur = 16;
        ctx.fill();
        ctx.shadowBlur = 0;

        // 3. Subtle Radar Rings on Selected Hubs
        [h1, h2].forEach((hub, idx) => {
          const phase = (time * 1.4 + idx * 0.7) % 1;
          const radius = (8 + phase * 26) * ((scaleX + scaleY) / 2);
          const opacity = (1 - phase) * 0.75;

          ctx.beginPath();
          ctx.arc(hub.x * scaleX, hub.y * scaleY, radius, 0, Math.PI * 2);
          ctx.strokeStyle = isDark ? `rgba(101, 201, 138, ${opacity})` : `rgba(46, 125, 50, ${opacity})`;
          ctx.lineWidth = 1.8;
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


  const activeHubs = useMemo(() => {
    const list = [];
    if (fromHub) list.push({ ...fromHub, isOrigin: true });
    if (toHub && toHub.code !== fromHub?.code) list.push({ ...toHub, isDest: true });
    return list;
  }, [fromHub, toHub]);

  const nodeColor = isDarkMode ? "#65C98A" : "#2e7d32";
  const badgeBg = isDarkMode ? "#65C98A" : "var(--ink, #191917)";
  const badgeTextColor = isDarkMode ? "#050B14" : "#ffffff";

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
            <strong>BHARAT-SAT · LEO SPACE VIEW</strong>
          </div>
          <span className="aerospace-coords">
            20.59° N, 78.96° E · ALT: 480 KM
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span className="aerospace-utc-clock">
            {utcTime}
          </span>
          <span className="aerospace-engine-tag">
            JEVONS GEO-ENGINE
          </span>
        </div>
      </div>

      {/* ── Main Clean Space Map Viewport (1200 × 896) ── */}
      <div className="aerospace-map-viewport">
        {/* Layer 0: Centered Satellite Layer */}
        <div style={{ position: "absolute", inset: 0 }}>
          <img
            src={getAssetPath("/satellite_india_v2.jpg")}
            alt="Satellite View of India and South Asian Subcontinent from Space"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "fill",
              objectPosition: "center center",
              filter: isDarkMode ? "contrast(1.06) brightness(0.96) saturate(1.04)" : "contrast(1.02) brightness(1.02) saturate(1.05)",
              pointerEvents: "none",
            }}
          />

          {/* Atmospheric Vignette */}
          <div className="aerospace-vignette" />
        </div>

        {/* Layer 1: Airport Hub Markers (ONLY the 2 Active Route Endpoints) */}
        <svg
          viewBox="0 0 1200 896"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        >
          <g id="aerospace-airport-nodes">
            {activeHubs.map((hub) => {
              const offset = hub.labelOffset || { x: 12, y: 4 };

              return (
                <g
                  key={hub.code}
                  transform={`translate(${hub.x}, ${hub.y})`}
                  style={{ pointerEvents: "none" }}
                  data-testid={`india-map-hub-${hub.code.toLowerCase()}`}
                >
                  {/* Active Selected Target Ring */}
                  <circle
                    r={18}
                    fill={isDarkMode ? "rgba(101, 201, 138, 0.22)" : "rgba(46, 125, 50, 0.2)"}
                    stroke={nodeColor}
                    strokeWidth={1.8}
                    strokeDasharray="4 3"
                  />

                  {/* Airport Pin Dot */}
                  <circle
                    r={8}
                    fill={nodeColor}
                    stroke="#ffffff"
                    strokeWidth={2.4}
                    style={{
                      filter: `drop-shadow(0 0 10px ${nodeColor})`,
                    }}
                  />

                  {/* Small Inner Core */}
                  <circle r={2.8} fill={isDarkMode ? "#050B14" : "#ffffff"} />

                  {/* Clean IATA Badge */}
                  <g transform={`translate(${offset.x}, ${offset.y})`}>
                    <rect
                      x={-4}
                      y={-11}
                      width={32}
                      height={16}
                      rx={4}
                      fill={badgeBg}
                      stroke="#ffffff"
                      strokeWidth={1.2}
                      style={{ filter: "drop-shadow(0 3px 8px rgba(0,0,0,0.35))" }}
                    />
                    <text
                      x={12}
                      y={1}
                      textAnchor="middle"
                      fill={badgeTextColor}
                      fontSize={10}
                      fontWeight={800}
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

        {/* Layer 2: 60FPS Flight Arc Canvas */}
        <canvas
          ref={canvasRef}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        />
      </div>

      {/* ── Analytics Console ── */}
      <div className="aerospace-analytics-console">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          {/* Active Corridor Selector & Indicator */}
          <div>
            <div className="aerospace-corridor-eyebrow">
              <Compass size={12} />
              <span>Active Aviation Corridor</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="aerospace-corridor-title">
                {activeFrom} ⇄ {activeTo}
              </span>
              <span className={`aerospace-status-pill ${activeRouteData ? "" : "is-missing"}`}>
                {activeRouteData ? "Index Available" : "No Basket Index"}
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
                {activeRouteData ? fmtPctFromFraction(activeRouteData.weight, 2) : NOT_AVAILABLE}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Golden Trunk Corridor Switcher Chips */}
        <div
          style={{
            display: "flex",
            gap: 6,
            marginTop: 14,
            overflowX: "auto",
            paddingBottom: 4,
          }}
        >
          {ALL_NETWORK_ROUTES.map((r) => {
            const isCurrent = r.from === activeFrom && r.to === activeTo;
            return (
              <button
                key={`${r.from}-${r.to}`}
                onClick={() => setSelectedRoute(r)}
                data-testid={`india-map-route-${r.from.toLowerCase()}-${r.to.toLowerCase()}-button`}
                className={`aerospace-chip-btn ${isCurrent ? "is-active" : ""}`}
              >
                {r.from} ⇄ {r.to}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

