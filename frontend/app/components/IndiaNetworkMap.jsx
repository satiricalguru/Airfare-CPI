"use client";

import { useState } from "react";
import { ROUTE_NETWORK_HUBS, NETWORK_ROUTES } from "../data/mockData";

export default function IndiaNetworkMap() {
  const [selectedRoute, setSelectedRoute] = useState(NETWORK_ROUTES[0]);
  const [hoveredHub, setHoveredHub] = useState(null);

  // Map coordinate helpers
  const hubLookup = {};
  ROUTE_NETWORK_HUBS.forEach((h) => {
    hubLookup[h.code] = h;
  });

  return (
    <div className="network-map-container" style={{ position: "relative", width: "100%", height: 480, overflow: "hidden", borderRadius: 16 }}>
      {/* Background Radar Grid & Coordinates */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      >
        <defs>
          <radialGradient id="mapGlow" cx="45%" cy="55%" r="60%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.15" />
            <stop offset="60%" stopColor="#06b6d4" stopOpacity="0.05" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="50%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#f9bd22" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient Map Glow */}
        <rect width="100" height="100" fill="url(#mapGlow)" />

        {/* Radar Concentric Rings */}
        <circle cx="42" cy="58" r="18" fill="none" stroke="rgba(76, 215, 246, 0.08)" strokeDasharray="1,2" />
        <circle cx="42" cy="58" r="32" fill="none" stroke="rgba(76, 215, 246, 0.06)" strokeDasharray="2,3" />
        <circle cx="42" cy="58" r="46" fill="none" stroke="rgba(76, 215, 246, 0.04)" />

        {/* Flight Arcs */}
        {NETWORK_ROUTES.map((route, idx) => {
          const fromHub = hubLookup[route.from];
          const toHub = hubLookup[route.to];
          if (!fromHub || !toHub) return null;

          const isSelected =
            selectedRoute?.from === route.from && selectedRoute?.to === route.to;

          // Quadratic bezier midpoint arc
          const midX = (fromHub.x + toHub.x) / 2 - (fromHub.y - toHub.y) * 0.15;
          const midY = (fromHub.y + toHub.y) / 2 + (fromHub.x - toHub.x) * 0.15;
          const pathD = `M ${fromHub.x} ${fromHub.y} Q ${midX} ${midY} ${toHub.x} ${toHub.y}`;

          return (
            <g key={idx} style={{ cursor: "pointer" }} onClick={() => setSelectedRoute(route)}>
              {/* Glow Arc */}
              <path
                d={pathD}
                fill="none"
                stroke={isSelected ? "#00ffff" : "rgba(59, 130, 246, 0.35)"}
                strokeWidth={isSelected ? 1.2 : 0.6}
                filter={isSelected ? "url(#glow)" : undefined}
                strokeDasharray={isSelected ? "none" : "2,2"}
              />

              {/* Animated Airplane Pulse along path */}
              {isSelected && (
                <circle r="1.4" fill="#f9bd22" filter="url(#glow)">
                  <animateMotion path={pathD} dur="3s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}

        {/* City Hub Nodes */}
        {ROUTE_NETWORK_HUBS.map((hub) => {
          const isFrom = selectedRoute?.from === hub.code;
          const isTo = selectedRoute?.to === hub.code;
          const isConnected = isFrom || isTo;

          return (
            <g
              key={hub.code}
              transform={`translate(${hub.x}, ${hub.y})`}
              onMouseEnter={() => setHoveredHub(hub)}
              onMouseLeave={() => setHoveredHub(null)}
              style={{ cursor: "pointer", pointerEvents: "auto" }}
            >
              {/* Outer Pulse */}
              <circle
                r={isConnected ? 3.2 : 2.0}
                fill={isConnected ? "rgba(6, 182, 212, 0.25)" : "rgba(59, 130, 246, 0.1)"}
                stroke={isConnected ? "#00ffff" : "rgba(76, 215, 246, 0.4)"}
                strokeWidth="0.4"
              />

              {/* Center Core */}
              <circle
                r={isConnected ? 1.4 : 1.0}
                fill={isConnected ? "#f9bd22" : "#3b82f6"}
              />

              {/* Hub Label */}
              <text
                x="2.4"
                y="0.8"
                fill={isConnected ? "#ffffff" : "#94a3b8"}
                fontSize="2.8"
                fontFamily="var(--font-mono, monospace)"
                fontWeight={isConnected ? "700" : "500"}
              >
                {hub.code}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected Route Floating Card */}
      {selectedRoute && (
        <div
          style={{
            position: "absolute",
            bottom: 20,
            left: 24,
            right: 24,
            background: "rgba(10, 19, 36, 0.85)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(76, 215, 246, 0.3)",
            borderRadius: 12,
            padding: "16px 20px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            boxShadow: "0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(6,182,212,0.15)",
          }}
        >
          <div>
            <div style={{ fontSize: 11, color: "#64748b", fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Active Aviation Corridor
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#ffffff", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
              <span style={{ color: "#4cd7f6" }}>{selectedRoute.from}</span>
              <span style={{ fontSize: 14, color: "#64748b" }}>✈ ➔</span>
              <span style={{ color: "#4cd7f6" }}>{selectedRoute.to}</span>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 100,
                  backgroundColor: selectedRoute.status === "Surging" ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                  color: selectedRoute.status === "Surging" ? "#f87171" : "#34d399",
                  fontWeight: 600,
                  marginLeft: 6,
                }}
              >
                {selectedRoute.status}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 24 }}>
            <div>
              <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Jevons Index</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#f9bd22", fontFamily: "var(--font-mono)" }}>{selectedRoute.cpi}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>Geo-Mean Fare</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#ffffff", fontFamily: "var(--font-mono)" }}>{selectedRoute.fare}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>MoM Rate</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#10b981", fontFamily: "var(--font-mono)" }}>{selectedRoute.change}</div>
            </div>
          </div>
        </div>
      )}

      {/* Hover Tooltip for Hub */}
      {hoveredHub && (
        <div
          style={{
            position: "absolute",
            top: 16,
            right: 20,
            background: "rgba(15, 23, 42, 0.9)",
            border: "1px solid rgba(76, 215, 246, 0.4)",
            borderRadius: 8,
            padding: "8px 14px",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.6)",
          }}
        >
          <span style={{ color: "#4cd7f6", fontWeight: 700 }}>{hoveredHub.city} ({hoveredHub.code})</span>
          <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 2 }}>Monthly Traffic: {(hoveredHub.pax / 1000000).toFixed(2)}M Pax</div>
        </div>
      )}
    </div>
  );
}
