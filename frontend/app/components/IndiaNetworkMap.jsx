"use client";

import { useState, useEffect, useRef } from "react";
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

export default function IndiaNetworkMap() {
  const [selectedRoute, setSelectedRoute] = useState(routesList[0] || null);
  const [hoveredHub, setHoveredHub] = useState(null);
  const [hoveredState, setHoveredState] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const canvasRef = useRef(null);

  // Sync dark mode
  useEffect(() => {
    const checkDark = () => {
      setIsDarkMode(document.documentElement.classList.contains("dark"));
    };
    checkDark();
    const observer = new MutationObserver(checkDark);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  const hubMap = {};
  HUBS_CONFIG.forEach((h) => {
    hubMap[h.code] = h;
  });

  const activeFrom = selectedRoute?.from || "DEL";
  const activeTo = selectedRoute?.to || "BOM";
  const fromHub = hubMap[activeFrom] || HUBS_CONFIG[0];
  const toHub = hubMap[activeTo] || HUBS_CONFIG[1];

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
        const h1 = hubMap[r.from];
        const h2 = hubMap[r.to];
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
          ctx.strokeStyle = isDarkMode ? "#38bdf8" : "#006591";
          ctx.lineWidth = 3.5;
          ctx.shadowColor = isDarkMode ? "rgba(56, 189, 248, 0.9)" : "rgba(0, 101, 145, 0.6)";
          ctx.shadowBlur = 12;
          ctx.stroke();

          // Outer secondary glow
          ctx.beginPath();
          ctx.moveTo(h1.x * scaleX, h1.y * scaleY);
          ctx.quadraticCurveTo(cp.x * scaleX, cp.y * scaleY, h2.x * scaleX, h2.y * scaleY);
          ctx.strokeStyle = isDarkMode ? "rgba(56, 189, 248, 0.3)" : "rgba(0, 101, 145, 0.2)";
          ctx.lineWidth = 8;
          ctx.shadowBlur = 0;
          ctx.stroke();
        } else {
          // Subtle background route mesh
          ctx.strokeStyle = isDarkMode ? "rgba(148, 163, 184, 0.22)" : "rgba(100, 116, 139, 0.25)";
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.shadowBlur = 0;
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });

      // 2. Animate Photon Flight Particles along Arcs
      particles.forEach((p) => {
        const h1 = hubMap[p.route.from];
        const h2 = hubMap[p.route.to];
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
        ctx.fillStyle = isSelected ? (isDarkMode ? "#ffffff" : "#0284c7") : (isDarkMode ? "#38bdf8" : "#0ea5e9");
        ctx.shadowColor = isDarkMode ? "#38bdf8" : "#0284c7";
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
        ctx.strokeStyle = isDarkMode ? `rgba(56, 189, 248, ${opacity})` : `rgba(0, 101, 145, ${opacity})`;
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
      className="stitch-card"
      style={{
        position: "relative",
        width: "100%",
        borderRadius: 20,
        overflow: "hidden",
        backgroundColor: isDarkMode ? "#080d1a" : "#f8fafc",
        border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.2)" : "rgba(0, 101, 145, 0.12)"}`,
        boxShadow: isDarkMode ? "0 20px 50px rgba(0,0,0,0.5)" : "0 12px 36px rgba(0, 101, 145, 0.08)",
      }}
    >
      {/* Background Radar Grid Pattern */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: isDarkMode
            ? "radial-gradient(circle at 50% 50%, rgba(56, 189, 248, 0.08) 1px, transparent 1px)"
            : "radial-gradient(circle at 50% 50%, rgba(0, 101, 145, 0.06) 1px, transparent 1px)",
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
            filter: isDarkMode ? "drop-shadow(0 4px 24px rgba(56, 189, 248, 0.12))" : "drop-shadow(0 4px 16px rgba(0, 101, 145, 0.08))",
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
              <stop offset="0%" stopColor="#f1f5f9" />
              <stop offset="100%" stopColor="#e2e8f0" />
            </linearGradient>
          </defs>

          {/* Layer 1: 36 Indian State Polygons */}
          <g id="india-states">
            {INDIA_MAP_DATA.locations.map((loc) => {
              const isHovered = hoveredState === loc.id;
              const hasActiveHub = (fromHub?.state === loc.name) || (toHub?.state === loc.name);

              let fillColor = isDarkMode ? "#0f172a" : "#f1f5f9";
              if (hasActiveHub) {
                fillColor = isDarkMode ? "rgba(56, 189, 248, 0.18)" : "rgba(0, 101, 145, 0.12)";
              } else if (isHovered) {
                fillColor = isDarkMode ? "rgba(56, 189, 248, 0.1)" : "rgba(0, 101, 145, 0.08)";
              }

              let strokeColor = isDarkMode ? "rgba(56, 189, 248, 0.28)" : "rgba(148, 163, 184, 0.65)";
              if (hasActiveHub) {
                strokeColor = isDarkMode ? "#38bdf8" : "#006591";
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
        {hoveredHub && hubMap[hoveredHub] && (
          <div
            style={{
              position: "absolute",
              top: 10,
              right: 10,
              padding: "10px 14px",
              borderRadius: 12,
              backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.95)" : "rgba(255, 255, 255, 0.95)",
              backdropFilter: "blur(16px)",
              border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.35)" : "rgba(0, 101, 145, 0.2)"}`,
              boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
              zIndex: 20,
              pointerEvents: "none",
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a" }}>
              {hubMap[hoveredHub].city} ({hubMap[hoveredHub].code})
            </div>
            <div style={{ fontSize: 11, color: isDarkMode ? "#94a3b8" : "#64748b", marginTop: 2 }}>
              State: {hubMap[hoveredHub].state}
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 6, fontSize: 11 }}>
              <div>
                <span style={{ color: isDarkMode ? "#64748b" : "#94a3b8" }}>Monthly Pax: </span>
                <strong style={{ color: isDarkMode ? "#38bdf8" : "#006591" }}>{hubMap[hoveredHub].pax}</strong>
              </div>
              <div>
                <span style={{ color: isDarkMode ? "#64748b" : "#94a3b8" }}>Hub CPI: </span>
                <strong style={{ color: "#22c55e" }}>{hubMap[hoveredHub].cpi}</strong>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Bottom HUD Control Card */}
      <div
        style={{
          margin: "0 16px 16px",
          padding: "16px 20px",
          borderRadius: 16,
          backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.9)" : "rgba(255, 255, 255, 0.95)",
          backdropFilter: "blur(16px)",
          border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.25)" : "rgba(0, 101, 145, 0.15)"}`,
          boxShadow: isDarkMode ? "0 8px 30px rgba(0,0,0,0.4)" : "0 4px 16px rgba(0,0,0,0.04)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          {/* Active Corridor Details */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: isDarkMode ? "#38bdf8" : "#006591", marginBottom: 2 }}>
              Active Aviation Corridor
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 900, color: isDarkMode ? "#ffffff" : "#0f172a", fontFamily: "var(--font-mono)" }}>
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
              <div style={{ fontSize: 10, color: isDarkMode ? "#94a3b8" : "#64748b", textTransform: "uppercase" }}>Jevons Index</div>
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-mono)", color: isDarkMode ? "#38bdf8" : "#006591" }}>
                {selectedRoute?.cpi || "106.0"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: isDarkMode ? "#94a3b8" : "#64748b", textTransform: "uppercase" }}>Average Fare</div>
              <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-mono)", color: isDarkMode ? "#ffffff" : "#0f172a" }}>
                {selectedRoute?.fare || "₹6,240"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: isDarkMode ? "#94a3b8" : "#64748b", textTransform: "uppercase" }}>MoM Movement</div>
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
                style={{
                  padding: "6px 12px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  backgroundColor: isCurrent ? (isDarkMode ? "#0284c7" : "#006591") : (isDarkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)"),
                  color: isCurrent ? "#ffffff" : (isDarkMode ? "#cbd5e1" : "#475569"),
                  border: isCurrent ? `1px solid ${isDarkMode ? "#38bdf8" : "#006591"}` : `1px solid ${isDarkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"}`,
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
