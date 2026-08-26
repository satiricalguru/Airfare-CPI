"use client";

import { useState, useEffect, useRef } from "react";
import { NETWORK_ROUTES } from "../data/mockData";

// Geographically Proportional Coordinates scaled to leave bottom 140px clear for card
// Map bounds: X: 160 -> 660 (Width 800), Y: 50 -> 380 (Height 560)
const HUBS_CONFIG = [
  { code: "DEL", city: "New Delhi", x: 380, y: 65, pax: 1200000, cpi: 106.0, labelPos: "top" },
  { code: "AMD", city: "Ahmedabad", x: 230, y: 165, pax: 370000, cpi: 106.2, labelPos: "left" },
  { code: "CCU", city: "Kolkata", x: 650, y: 175, pax: 740000, cpi: 108.2, labelPos: "right" },
  { code: "BOM", city: "Mumbai", x: 245, y: 235, pax: 870000, cpi: 107.4, labelPos: "left" },
  { code: "PNQ", city: "Pune", x: 300, y: 260, pax: 390000, cpi: 105.4, labelPos: "right" },
  { code: "HYD", city: "Hyderabad", x: 425, y: 250, pax: 780000, cpi: 105.8, labelPos: "right" },
  { code: "GOI", city: "Goa", x: 265, y: 315, pax: 450000, cpi: 109.1, labelPos: "left" },
  { code: "BLR", city: "Bengaluru", x: 370, y: 335, pax: 950000, cpi: 107.5, labelPos: "bottom" },
  { code: "MAA", city: "Chennai", x: 475, y: 340, pax: 600000, cpi: 106.8, labelPos: "right" },
  { code: "COK", city: "Kochi", x: 340, y: 385, pax: 230000, cpi: 104.5, labelPos: "bottom" },
];

export default function IndiaNetworkMap() {
  const [selectedRoute, setSelectedRoute] = useState(NETWORK_ROUTES[0]);
  const [hoveredHub, setHoveredHub] = useState(null);
  const [hoveredRoute, setHoveredRoute] = useState(null);
  const canvasRef = useRef(null);

  const hubMap = {};
  HUBS_CONFIG.forEach((h) => {
    hubMap[h.code] = h;
  });

  // 60FPS High-Performance Canvas Particle & Flight Stream Animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let animId;
    const VB_WIDTH = 800;
    const VB_HEIGHT = 560;

    const setupCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    setupCanvas();
    window.addEventListener("resize", setupCanvas);

    // Flight particles for each corridor
    const particles = NETWORK_ROUTES.map((route, i) => ({
      route,
      progress: (i * 0.14) % 1,
      speed: 0.003 + (i % 3) * 0.0006,
    }));

    // Quadratic Bezier interpolation helper
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
      const curvature = Math.min(dist * 0.2, 50);
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

      // 1. Draw Flight Paths
      NETWORK_ROUTES.forEach((route) => {
        const from = hubMap[route.from];
        const to = hubMap[route.to];
        if (!from || !to) return;

        const isSelected =
          (selectedRoute?.from === route.from && selectedRoute?.to === route.to) ||
          (selectedRoute?.from === route.to && selectedRoute?.to === route.from);
        const isHovered = hoveredRoute === route;

        const h1 = { x: from.x * scaleX, y: from.y * scaleY };
        const h2 = { x: to.x * scaleX, y: to.y * scaleY };
        const cp = getControlPoint(h1, h2);

        // Draw Flight Path Arc
        ctx.beginPath();
        ctx.moveTo(h1.x, h1.y);
        ctx.quadraticCurveTo(cp.x, cp.y, h2.x, h2.y);

        if (isSelected) {
          // Luminous Outer Beam Glow
          ctx.strokeStyle = "rgba(0, 113, 227, 0.22)";
          ctx.lineWidth = 8;
          ctx.setLineDash([]);
          ctx.stroke();

          // Solid Core Beam
          ctx.strokeStyle = "#0071e3";
          ctx.lineWidth = 3;
          ctx.stroke();
        } else if (isHovered) {
          ctx.strokeStyle = "rgba(0, 113, 227, 0.6)";
          ctx.lineWidth = 2.2;
          ctx.setLineDash([]);
          ctx.stroke();
        } else {
          ctx.strokeStyle = "rgba(142, 142, 147, 0.22)";
          ctx.lineWidth = 1.2;
          ctx.setLineDash([4, 4]);
          ctx.stroke();
        }
      });

      // 2. Animate Cruising Aircraft Beacons & Vapor Trails (60 FPS Smooth)
      particles.forEach((p) => {
        p.progress += p.speed;
        if (p.progress > 1) p.progress -= 1;

        const from = hubMap[p.route.from];
        const to = hubMap[p.route.to];
        if (!from || !to) return;

        const isSelected =
          (selectedRoute?.from === p.route.from && selectedRoute?.to === p.route.to) ||
          (selectedRoute?.from === p.route.to && selectedRoute?.to === p.route.from);

        const h1 = { x: from.x * scaleX, y: from.y * scaleY };
        const h2 = { x: to.x * scaleX, y: to.y * scaleY };
        const cp = getControlPoint(h1, h2);

        const pt = getBezierPoint(h1, cp, h2, p.progress);
        const trailPt = getBezierPoint(h1, cp, h2, Math.max(0, p.progress - 0.05));

        // Vapor Trail
        ctx.beginPath();
        ctx.moveTo(trailPt.x, trailPt.y);
        ctx.lineTo(pt.x, pt.y);
        ctx.strokeStyle = isSelected ? "rgba(0, 113, 227, 0.45)" : "rgba(0, 113, 227, 0.25)";
        ctx.lineWidth = isSelected ? 3.5 : 1.8;
        ctx.setLineDash([]);
        ctx.stroke();

        // Cruising Aircraft Beacon Dot
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, isSelected ? 5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = "#0071e3";
        ctx.shadowColor = "#0071e3";
        ctx.shadowBlur = isSelected ? 12 : 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // 3. Draw Radar Pulses on Active Hubs
      HUBS_CONFIG.forEach((hub) => {
        const isFrom = selectedRoute?.from === hub.code;
        const isTo = selectedRoute?.to === hub.code;
        const isConnected = isFrom || isTo;

        if (isConnected) {
          const hx = hub.x * scaleX;
          const hy = hub.y * scaleY;
          const pulseR = 8 + (Math.sin(time * 3) + 1) * 7;

          ctx.beginPath();
          ctx.arc(hx, hy, pulseR, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(0, 113, 227, 0.35)";
          ctx.lineWidth = 1.5;
          ctx.setLineDash([]);
          ctx.stroke();
        }
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", setupCanvas);
    };
  }, [selectedRoute, hoveredRoute]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: 560,
        backgroundColor: "#ffffff",
        borderRadius: 20,
        overflow: "hidden",
        border: "1px solid rgba(0, 0, 0, 0.06)",
        boxShadow: "0 10px 30px rgba(0, 0, 0, 0.03)",
      }}
    >
      {/* Background Decorative Spatial Radar Grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          pointerEvents: "none",
        }}
      />

      {/* 60FPS Ultra-Smooth Canvas Animation Layer */}
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

      {/* SVG Interactive Hub Overlay & Visible Labels */}
      <svg
        viewBox="0 0 800 560"
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
        }}
      >
        {/* Invisible Clickable Corridor Hitboxes */}
        {NETWORK_ROUTES.map((route, idx) => {
          const from = hubMap[route.from];
          const to = hubMap[route.to];
          if (!from || !to) return null;

          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const curvature = Math.min(dist * 0.2, 50);
          const nx = -dy / dist;
          const ny = dx / dist;
          const cpx = (from.x + to.x) / 2 + nx * curvature;
          const cpy = (from.y + to.y) / 2 + ny * curvature;

          const pathD = `M ${from.x} ${from.y} Q ${cpx} ${cpy} ${to.x} ${to.y}`;

          return (
            <path
              key={idx}
              d={pathD}
              fill="none"
              stroke="transparent"
              strokeWidth={28}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHoveredRoute(route)}
              onMouseLeave={() => setHoveredRoute(null)}
              onClick={() => setSelectedRoute(route)}
            />
          );
        })}

        {/* Airport Hub Nodes & Labels - Fully Visible with Clear Spacing */}
        {HUBS_CONFIG.map((hub) => {
          const isFrom = selectedRoute?.from === hub.code;
          const isTo = selectedRoute?.to === hub.code;
          const isConnected = isFrom || isTo;
          const isHovered = hoveredHub?.code === hub.code;

          // Label offsets
          let labelX = hub.x;
          let labelY = hub.y;
          let textAnchor = "middle";

          if (hub.labelPos === "top") {
            labelY -= 14;
          } else if (hub.labelPos === "bottom") {
            labelY += 18;
          } else if (hub.labelPos === "left") {
            labelX -= 16;
            labelY += 4;
            textAnchor = "end";
          } else if (hub.labelPos === "right") {
            labelX += 16;
            labelY += 4;
            textAnchor = "start";
          }

          return (
            <g
              key={hub.code}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHoveredHub(hub)}
              onMouseLeave={() => setHoveredHub(null)}
              onClick={() => {
                const connectedRoute = NETWORK_ROUTES.find((r) => r.from === hub.code || r.to === hub.code);
                if (connectedRoute) setSelectedRoute(connectedRoute);
              }}
            >
              {/* Outer Glow Ring */}
              <circle
                cx={hub.x}
                cy={hub.y}
                r={isConnected || isHovered ? 12 : 7}
                fill={isConnected ? "rgba(0, 113, 227, 0.15)" : "#ffffff"}
                stroke={isConnected ? "#0071e3" : "rgba(0, 0, 0, 0.18)"}
                strokeWidth={isConnected ? 2 : 1}
                style={{ transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }}
              />

              {/* Center Core Dot */}
              <circle
                cx={hub.x}
                cy={hub.y}
                r={isConnected ? 5 : 3}
                fill={isConnected ? "#0071e3" : "#1d1d1f"}
                style={{ transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }}
              />

              {/* Hub Code Label */}
              <text
                x={labelX}
                y={labelY}
                textAnchor={textAnchor}
                fill={isConnected ? "#0071e3" : "#1d1d1f"}
                fontSize={isConnected ? "13" : "11"}
                fontFamily="var(--font-sans, -apple-system, BlinkMacSystemFont, sans-serif)"
                fontWeight={isConnected ? "800" : "600"}
                letterSpacing="0.04em"
                style={{
                  transition: "all 0.25s ease",
                  userSelect: "none",
                }}
              >
                {hub.code}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected Corridor Floating Glass Pill Card */}
      {selectedRoute && (
        <div
          style={{
            position: "absolute",
            bottom: 16,
            left: 16,
            right: 16,
            background: "rgba(255, 255, 255, 0.94)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            border: "1px solid rgba(0, 0, 0, 0.08)",
            borderRadius: 16,
            padding: "14px 22px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            boxShadow: "0 10px 32px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04)",
            transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
            zIndex: 10,
          }}
        >
          <div>
            <div style={{ fontSize: 10, color: "#86868b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Active Aviation Corridor
            </div>
            <div style={{ fontSize: 19, fontWeight: 800, color: "#1d1d1f", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
              <span>{selectedRoute.from}</span>
              <span style={{ fontSize: 13, color: "#0071e3" }}>➔</span>
              <span>{selectedRoute.to}</span>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 7px",
                  borderRadius: 100,
                  backgroundColor: selectedRoute.status === "Surging" ? "rgba(255, 59, 48, 0.1)" : "rgba(52, 199, 89, 0.1)",
                  color: selectedRoute.status === "Surging" ? "#ff3b30" : "#34c759",
                  fontWeight: 700,
                  marginLeft: 6,
                  fontFamily: "var(--font-mono)",
                }}
              >
                {selectedRoute.status.toUpperCase()}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 28 }}>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>Jevons Index</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "#0071e3", fontFamily: "var(--font-mono)" }}>{selectedRoute.cpi}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>Average Fare</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "#1d1d1f", fontFamily: "var(--font-mono)" }}>{selectedRoute.fare}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>MoM Movement</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: "#34c759", fontFamily: "var(--font-mono)" }}>{selectedRoute.change}</div>
            </div>
          </div>
        </div>
      )}

      {/* Hub Hover Popover Tooltip */}
      {hoveredHub && (
        <div
          style={{
            position: "absolute",
            top: 16,
            right: 16,
            background: "#ffffff",
            border: "1px solid rgba(0, 0, 0, 0.08)",
            borderRadius: 12,
            padding: "8px 14px",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.08)",
            zIndex: 30,
            pointerEvents: "none",
          }}
        >
          <div style={{ color: "#0071e3", fontWeight: 800, fontSize: 12 }}>
            {hoveredHub.city} ({hoveredHub.code})
          </div>
          <div style={{ color: "#86868b", fontSize: 11, marginTop: 2, fontFamily: "var(--font-mono)" }}>
            Monthly Traffic: <strong>{(hoveredHub.pax / 1000000).toFixed(2)}M Pax</strong> · CPI: <strong style={{ color: "#0071e3" }}>{hoveredHub.cpi}</strong>
          </div>
        </div>
      )}
    </div>
  );
}
