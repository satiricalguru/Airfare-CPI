"use client";

import { useState, useEffect, useRef, useSyncExternalStore } from "react";
import { INDIA_MAP_DATA } from "../data/indiaMapData";
import { ROUTE_HEATMAP_DATA, NETWORK_ROUTES } from "../data/mockData";

const rawRoutes = NETWORK_ROUTES || ROUTE_HEATMAP_DATA || [];
const routesList = rawRoutes.map((r) => ({
  ...r,
  from: r.from || r.origin || "DEL",
  to: r.to || r.destination || "BOM",
  status: r.status || (r.cpi > 107 ? "Surging" : "Stable"),
  fare: r.fare || (r.avgFare ? `₹${r.avgFare.toLocaleString()}` : "₹6,240"),
  change: r.change || "+2.5%",
  cpi: r.cpi ? (typeof r.cpi === "number" ? r.cpi.toFixed(1) : r.cpi) : "106.0",
}));

// Geographically exact coordinates mapped inside viewBox="0 0 612 696" strictly on Indian land
const HUBS_CONFIG = [
  { code: "DEL", city: "New Delhi", state: "Delhi", x: 186.5, y: 210.0, pax: "1.2M", cpi: 106.0, labelPos: "top" },
  { code: "BOM", city: "Mumbai", state: "Maharashtra", x: 140.0, y: 434.0, pax: "870K", cpi: 107.4, labelPos: "left" },
  { code: "PNQ", city: "Pune", state: "Maharashtra", x: 156.0, y: 448.0, pax: "390K", cpi: 105.4, labelPos: "right" },
  { code: "AMD", city: "Ahmedabad", state: "Gujarat", x: 82.0, y: 342.0, pax: "370K", cpi: 106.2, labelPos: "left" },
  { code: "BLR", city: "Bengaluru", state: "Karnataka", x: 198.0, y: 562.0, pax: "950K", cpi: 107.5, labelPos: "bottom" },
  { code: "MAA", city: "Chennai", state: "Tamil Nadu", x: 246.0, y: 560.0, pax: "600K", cpi: 106.8, labelPos: "right" },
  { code: "CCU", city: "Kolkata", state: "West Bengal", x: 416.0, y: 348.0, pax: "740K", cpi: 108.2, labelPos: "right" },
  { code: "HYD", city: "Hyderabad", state: "Telangana", x: 236.0, y: 456.0, pax: "780K", cpi: 105.8, labelPos: "right" },
  { code: "GOI", city: "Goa", state: "Goa", x: 122.0, y: 512.0, pax: "450K", cpi: 109.1, labelPos: "left" },
  { code: "COK", city: "Kochi", state: "Kerala", x: 175.0, y: 615.0, pax: "230K", cpi: 104.5, labelPos: "bottom" },
  { code: "GAU", city: "Guwahati", state: "Assam", x: 486.0, y: 268.0, pax: "310K", cpi: 107.8, labelPos: "top" },
  { code: "SXR", city: "Srinagar", state: "Jammu and Kashmir", x: 168.0, y: 65.0, pax: "190K", cpi: 105.1, labelPos: "top" },
];

const HUB_MAP = Object.fromEntries(HUBS_CONFIG.map((h) => [h.code, h]));

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

export default function IndiaNetworkMap({ isDarkMode: propDarkMode }) {
  const [selectedRoute, setSelectedRoute] = useState(routesList[0] || null);
  const [hoveredHub, setHoveredHub] = useState(null);
  const [hoveredState, setHoveredState] = useState(null);
  const domDarkMode = useSyncExternalStore(subscribeToDocumentDark, getDocumentDarkSnapshot, getDocumentDarkServerSnapshot);
  const isDarkMode = propDarkMode !== undefined ? propDarkMode : domDarkMode;
  const canvasRef = useRef(null);

  const activeFrom = selectedRoute?.from || "DEL";
  const activeTo = selectedRoute?.to || "BOM";
  const fromHub = HUB_MAP[activeFrom] || HUBS_CONFIG[0];
  const toHub = HUB_MAP[activeTo] || HUBS_CONFIG[1];

  // 60FPS Particle Stream Animation on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let animId;
    const VB_WIDTH = 612;
    const VB_HEIGHT = 696;

    const setupCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    setupCanvas();
    window.addEventListener("resize", setupCanvas);

    // Dynamic flight particles across all interconnected corridors
    const particles = routesList.map((route, i) => ({
      route,
      progress: (i * 0.12) % 1,
      speed: 0.0035 + (i % 4) * 0.0008,
      size: (i % 3 === 0 ? 3.5 : 2.5),
    }));

    // Quadratic Bezier Helper
    const getBezierPoint = (p0, p1, p2, t) => {
      const invT = 1 - t;
      const x = invT * invT * p0.x + 2 * invT * t * p1.x + t * t * p2.x;
      const y = invT * invT * p0.y + 2 * invT * t * p1.y + t * t * p2.y;
      return { x, y };
    };

    const getControlPoint = (h1, h2) => {
      const dx = h2.x - h1.x;
      const dy = h2.y - h1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const curvature = Math.min(dist * 0.22, 45);
      const nx = -dy / dist;
      const ny = dx / dist;
      return {
        x: (h1.x + h2.x) / 2 + nx * curvature,
        y: (h1.y + h2.y) / 2 + ny * curvature,
      };
    };

    let time = 0;

    const render = () => {
      time += 0.016;
      const rect = canvas.getBoundingClientRect();
      const scaleX = rect.width / VB_WIDTH;
      const scaleY = rect.height / VB_HEIGHT;

      ctx.clearRect(0, 0, rect.width, rect.height);

      // 1. Draw Flight Stream Arcs
      routesList.forEach((r) => {
        const h1 = HUB_MAP[r.from];
        const h2 = HUB_MAP[r.to];
        if (!h1 || !h2) return;

        const isSelected =
          (r.from === activeFrom && r.to === activeTo) ||
          (r.from === activeTo && r.to === activeFrom);

        const cp = getControlPoint(h1, h2);

        ctx.beginPath();
        ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
        ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);

        if (isSelected) {
          // Luminous glowing active corridor
          ctx.strokeStyle = isDarkMode ? "#9ac3a0" : "#3b6d4d";
          ctx.lineWidth = 3.5;
          ctx.shadowColor = isDarkMode ? "rgba(154, 195, 160, 0.9)" : "rgba(59, 109, 77, 0.6)";
          ctx.shadowBlur = 12;
          ctx.stroke();

          // Outer secondary glow
          ctx.beginPath();
          ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
          ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
          ctx.strokeStyle = isDarkMode ? "rgba(154, 195, 160, 0.3)" : "rgba(59, 109, 77, 0.2)";
          ctx.lineWidth = 8;
          ctx.shadowBlur = 0;
          ctx.stroke();
        } else {
          // Subtle background route mesh
          ctx.strokeStyle = isDarkMode ? "rgba(185, 200, 186, 0.22)" : "rgba(104, 119, 101, 0.27)";
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.shadowBlur = 0;
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });

      // 2. Animate Photon Flight Particles along Arcs
      particles.forEach((p) => {
        const h1 = HUB_MAP[p.route.from];
        const h2 = HUB_MAP[p.route.to];
        if (!h1 || !h2) return;

        const isSelected =
          (p.route.from === activeFrom && p.route.to === activeTo) ||
          (p.route.from === activeTo && p.route.to === activeFrom);

        p.progress += p.speed * (isSelected ? 1.5 : 1.0);
        if (p.progress > 1) p.progress = 0;

        const cp = getControlPoint(h1, h2);
        const pt = getBezierPoint(h1, cp, h2, p.progress);

        const screenX = pt.x * scaleX;
        const screenY = pt.y * scaleY;

        // Draw particle trail
        ctx.beginPath();
        ctx.arc(screenX, screenY, isSelected ? 4.5 : p.size, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? (isDarkMode ? "#f3f1e9" : "#3b6d4d") : (isDarkMode ? "#9ac3a0" : "#6f9974");
        ctx.shadowColor = isDarkMode ? "#9ac3a0" : "#3b6d4d";
        ctx.shadowBlur = isSelected ? 16 : 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // 3. Expanding Radar Pulse on Selected Hubs
      [fromHub, toHub].forEach((hub, idx) => {
        if (!hub) return;
        const phase = (time * 1.8 + idx * 0.8) % 1;
        const radius = (10 + phase * 32) * ((scaleX + scaleY) / 2);
        const opacity = (1 - phase) * 0.7;

        ctx.beginPath();
        ctx.arc(hub.x * scaleX, hub.y * scaleY, radius, 0, Math.PI * 2);
        ctx.strokeStyle = isDarkMode ? `rgba(154, 195, 160, ${opacity})` : `rgba(59, 109, 77, ${opacity})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      });

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", setupCanvas);
    };
  }, [selectedRoute, activeFrom, activeTo, isDarkMode, fromHub, toHub]);

  return (
    <div
      className="stitch-card network-map-card"
      data-testid="india-network-map"
      style={{
        position: "relative",
        width: "100%",
        borderRadius: 20,
        overflow: "hidden",
        backgroundColor: isDarkMode ? "#151b18" : "#fffdf8",
        border: `1px solid ${isDarkMode ? "rgba(154, 195, 160, 0.2)" : "rgba(59, 109, 77, 0.16)"}`,
        boxShadow: isDarkMode ? "0 20px 50px rgba(0,0,0,0.35)" : "0 18px 50px rgba(31, 31, 24, 0.08)",
      }}
    >
      {/* Background Radar Grid Pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: isDarkMode
            ? "radial-gradient(circle at 50% 50%, rgba(154, 195, 160, 0.08) 1px, transparent 1px)"
            : "radial-gradient(circle at 50% 50%, rgba(59, 109, 77, 0.08) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          pointerEvents: "none",
        }}
      />

      {/* Main Centered Map Stage with Locked Aspect Ratio */}
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 520,
          aspectRatio: "612 / 696",
          margin: "16px auto 12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Unified Single SVG Map (States + Nodes perfectly locked) */}
        <svg
          viewBox={INDIA_MAP_DATA.viewBox}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            filter: isDarkMode ? "drop-shadow(0 4px 24px rgba(154, 195, 160, 0.12))" : "drop-shadow(0 4px 16px rgba(59, 109, 77, 0.1))",
          }}
        >
          <defs>
            <filter id="india-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <linearGradient id="state-gradient-dark" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0f172a" />
              <stop offset="100%" stopColor="#1e293b" />
            </linearGradient>
            <linearGradient id="state-gradient-light" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f4f1e8" />
              <stop offset="100%" stopColor="#e4e9df" />
            </linearGradient>
          </defs>

          {/* Layer 1: 36 Indian State Polygons */}
          <g id="india-states">
            {INDIA_MAP_DATA.locations.map((loc) => {
              const isHovered = hoveredState === loc.id;
              const hasActiveHub = (fromHub?.state === loc.name) || (toHub?.state === loc.name);

              let fillColor = isDarkMode ? "#1b241e" : "#f4f1e8";
              if (hasActiveHub) {
                fillColor = isDarkMode ? "rgba(154, 195, 160, 0.18)" : "rgba(59, 109, 77, 0.13)";
              } else if (isHovered) {
                fillColor = isDarkMode ? "rgba(154, 195, 160, 0.1)" : "rgba(59, 109, 77, 0.08)";
              }

              let strokeColor = isDarkMode ? "rgba(154, 195, 160, 0.28)" : "rgba(104, 119, 101, 0.62)";
              if (hasActiveHub) {
                strokeColor = isDarkMode ? "#9ac3a0" : "#3b6d4d";
              }

              return (
                <path
                  key={loc.id}
                  id={`state-${loc.id}`}
                  d={loc.path}
                  fill={fillColor}
                  stroke={strokeColor}
                  strokeWidth={hasActiveHub ? 1.6 : 0.8}
                  strokeLinejoin="round"
                  style={{
                    transition: "fill 0.25s ease, stroke 0.25s ease",
                    cursor: "pointer",
                  }}
                  data-testid={`india-map-state-${loc.id}`}
                  onMouseEnter={() => setHoveredState(loc.id)}
                  onMouseLeave={() => setHoveredState(null)}
                >
                  <title>{loc.name}</title>
                </path>
              );
            })}
          </g>

          {/* Layer 2: Airport Hub Interactive Nodes (inside same SVG!) */}
          <g id="airport-hubs">
            {HUBS_CONFIG.map((hub) => {
              const isOrigin = hub.code === activeFrom;
              const isDest = hub.code === activeTo;
              const isSelected = isOrigin || isDest;
              const isHovered = hoveredHub === hub.code;

              return (
                <g
                  key={hub.code}
                  transform={`translate(${hub.x}, ${hub.y})`}
                  style={{ cursor: "pointer" }}
                  data-testid={`india-map-hub-${hub.code.toLowerCase()}`}
                  onMouseEnter={() => setHoveredHub(hub.code)}
                  onMouseLeave={() => setHoveredHub(null)}
                  onClick={() => {
                    const matchingRoute = routesList.find((r) => r.from === hub.code || r.to === hub.code);
                    if (matchingRoute) setSelectedRoute(matchingRoute);
                  }}
                >
                  {/* Active Hub Radar Ring */}
                  {isSelected && (
                    <circle
                      r={14}
                      fill={isDarkMode ? "rgba(56, 189, 248, 0.15)" : "rgba(0, 101, 145, 0.12)"}
                      stroke={isDarkMode ? "#38bdf8" : "#006591"}
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Hub Beacon Pin */}
                  <circle
                    r={isSelected ? 6 : (isHovered ? 5 : 3.5)}
                    fill={isSelected ? (isDarkMode ? "#ffffff" : "#006591") : (isDarkMode ? "#38bdf8" : "#0284c7")}
                    stroke={isSelected ? (isDarkMode ? "#38bdf8" : "#ffffff") : (isDarkMode ? "#0f172a" : "#ffffff")}
                    strokeWidth={2}
                    filter={isSelected ? "url(#india-glow)" : undefined}
                  />

                  {/* Hub IATA Label Pill */}
                  <g transform={`translate(${hub.labelPos === "left" ? -28 : (hub.labelPos === "right" ? 10 : -10)}, ${hub.labelPos === "top" ? -12 : 16})`}>
                    <rect
                      x={-2}
                      y={-10}
                      width={24}
                      height={14}
                      rx={3}
                      fill={isSelected ? (isDarkMode ? "#0284c7" : "#006591") : (isDarkMode ? "rgba(15,23,42,0.88)" : "rgba(255,255,255,0.9)")}
                      stroke={isSelected ? "#ffffff" : (isDarkMode ? "rgba(56, 189, 248, 0.4)" : "rgba(0, 101, 145, 0.25)")}
                      strokeWidth={0.8}
                    />
                    <text
                      x={10}
                      y={0}
                      textAnchor="middle"
                      fill={isSelected ? "#ffffff" : (isDarkMode ? "#e2e8f0" : "#1e293b")}
                      fontSize={8.5}
                      fontWeight={900}
                      fontFamily="var(--font-mono)"
                    >
                      {hub.code}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Layer 3: 60FPS Flight Stream Canvas (exact same frame) */}
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

        {/* Layer 4: Hover Hub Telemetry Tooltip */}
        {hoveredHub && HUB_MAP[hoveredHub] && (
          <div
            style={{
              position: "absolute",
              top: 24,
              right: 24,
              backgroundColor: isDarkMode ? "rgba(21, 27, 24, 0.95)" : "rgba(255, 253, 248, 0.95)",
              border: `1px solid ${isDarkMode ? "rgba(154, 195, 160, 0.3)" : "rgba(59, 109, 77, 0.2)"}`,
              borderRadius: 12,
              padding: "12px 16px",
              boxShadow: "0 10px 25px rgba(0,0,0,0.15)",
              pointerEvents: "none",
              zIndex: 10,
              backdropFilter: "blur(8px)",
              minWidth: 160,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13, color: isDarkMode ? "#f3f1e9" : "#172019", marginBottom: 2 }}>
              {HUB_MAP[hoveredHub].city} ({HUB_MAP[hoveredHub].code})
            </div>
            <div style={{ fontSize: 11, color: isDarkMode ? "#9ca3af" : "#6b7280", marginBottom: 8 }}>
              State: {HUB_MAP[hoveredHub].state}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
              <span style={{ color: isDarkMode ? "#9ca3af" : "#6b7280" }}>Mo. Traffic:</span>
              <strong style={{ color: isDarkMode ? "#9ac3a0" : "#3b6d4d" }}>{HUB_MAP[hoveredHub].pax}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginTop: 2 }}>
              <span style={{ color: isDarkMode ? "#9ca3af" : "#6b7280" }}>Sub-Index:</span>
              <strong style={{ color: "#22c55e" }}>{HUB_MAP[hoveredHub].cpi}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Bottom HUD Control Card */}
      <div
        style={{
          margin: "0 16px 16px",
          padding: "16px 20px",
          borderRadius: 12,
          backgroundColor: isDarkMode ? "rgba(28, 33, 29, 0.94)" : "rgba(255, 253, 248, 0.96)",
          backdropFilter: "blur(16px)",
          border: `1px solid ${isDarkMode ? "rgba(154, 195, 160, 0.2)" : "rgba(59, 109, 77, 0.16)"}`,
          boxShadow: isDarkMode ? "0 8px 30px rgba(0,0,0,0.5)" : "0 4px 16px rgba(31, 31, 24, 0.06)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          {/* Active Corridor Details */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: isDarkMode ? "#9ac3a0" : "#3b6d4d", marginBottom: 2 }}>
              Active Aviation Corridor
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 900, color: isDarkMode ? "#f3f1e9" : "#191917", fontFamily: "var(--font-mono)" }}>
                {activeFrom} → {activeTo}
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  padding: "3px 8px",
                  borderRadius: 6,
                  backgroundColor: selectedRoute?.status === "Surging" ? "rgba(239, 68, 68, 0.15)" : "rgba(34, 197, 94, 0.15)",
                  color: selectedRoute?.status === "Surging" ? "#ef4444" : "#22c55e",
                  border: `1px solid ${selectedRoute?.status === "Surging" ? "rgba(239, 68, 68, 0.3)" : "rgba(34, 197, 94, 0.3)"}`,
                }}
              >
                {(selectedRoute?.status || "Stable").toUpperCase()}
              </span>
            </div>
          </div>

          {/* Metric Stats */}
          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <div>
              <div style={{ fontSize: 10, color: isDarkMode ? "#aaa9a0" : "#77746d", textTransform: "uppercase" }}>Jevons Index</div>
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-mono)", color: isDarkMode ? "#9ac3a0" : "#3b6d4d" }}>
                {selectedRoute?.cpi || "106.0"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: isDarkMode ? "#aaa9a0" : "#77746d", textTransform: "uppercase" }}>Average Fare</div>
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-mono)", color: isDarkMode ? "#f3f1e9" : "#191917" }}>
                {selectedRoute?.fare || "₹6,240"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: isDarkMode ? "#aaa9a0" : "#77746d", textTransform: "uppercase" }}>MoM Movement</div>
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-mono)", color: "#22c55e" }}>
                {selectedRoute?.change || "+3.2%"}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Corridor Selector Pills */}
        <div style={{ display: "flex", gap: 8, marginTop: 14, overflowX: "auto", paddingBottom: 2 }}>
          {routesList.slice(0, 6).map((r) => {
            const isCurrent = r.from === activeFrom && r.to === activeTo;
            return (
              <button
                key={`${r.from}-${r.to}`}
                onClick={() => setSelectedRoute(r)}
                data-testid={`india-map-route-${r.from.toLowerCase()}-${r.to.toLowerCase()}-button`}
                style={{
                  padding: "6px 12px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  backgroundColor: isCurrent ? "#3b6d4d" : (isDarkMode ? "rgba(154, 195, 160, 0.08)" : "rgba(59,109,77,0.06)"),
                  color: isCurrent ? "#ffffff" : (isDarkMode ? "#f3f1e9" : "#191917"),
                  border: isCurrent ? `1px solid ${isDarkMode ? "#9ac3a0" : "#3b6d4d"}` : `1px solid ${isDarkMode ? "rgba(154, 195, 160, 0.15)" : "rgba(59,109,77,0.12)"}`,
                  transition: "all 0.2s ease",
                }}
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
