"use client";

import { useState } from "react";
import { ROUTE_NETWORK_HUBS, NETWORK_ROUTES } from "../data/mockData";

export default function IndiaNetworkMap() {
  const [selectedRoute, setSelectedRoute] = useState(NETWORK_ROUTES[0]);
  const [hoveredHub, setHoveredHub] = useState(null);

  const hubLookup = {};
  ROUTE_NETWORK_HUBS.forEach((h) => {
    hubLookup[h.code] = h;
  });

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: 500,
        backgroundColor: "#fbfbfd",
        border: "1px solid rgba(0, 0, 0, 0.06)",
        borderRadius: 20,
        overflow: "hidden",
      }}
    >
      {/* Background SVG Grid & Indian Aviation Corridors */}
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
          <filter id="appleGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="0.8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Minimalist Radar Rings */}
        <circle cx="42" cy="58" r="18" fill="none" stroke="rgba(0, 0, 0, 0.04)" strokeDasharray="1,2" />
        <circle cx="42" cy="58" r="32" fill="none" stroke="rgba(0, 0, 0, 0.03)" strokeDasharray="2,3" />

        {/* Flight Path Arcs */}
        {NETWORK_ROUTES.map((route, idx) => {
          const fromHub = hubLookup[route.from];
          const toHub = hubLookup[route.to];
          if (!fromHub || !toHub) return null;

          const isSelected =
            selectedRoute?.from === route.from && selectedRoute?.to === route.to;

          // Curved bezier arc
          const midX = (fromHub.x + toHub.x) / 2 - (fromHub.y - toHub.y) * 0.15;
          const midY = (fromHub.y + toHub.y) / 2 + (fromHub.x - toHub.x) * 0.15;
          const pathD = `M ${fromHub.x} ${fromHub.y} Q ${midX} ${midY} ${toHub.x} ${toHub.y}`;

          return (
            <g key={idx} style={{ cursor: "pointer", pointerEvents: "auto" }} onClick={() => setSelectedRoute(route)}>
              <path
                d={pathD}
                fill="none"
                stroke={isSelected ? "#0071e3" : "rgba(0, 0, 0, 0.15)"}
                strokeWidth={isSelected ? 1.6 : 0.8}
                filter={isSelected ? "url(#appleGlow)" : undefined}
                strokeDasharray={isSelected ? "none" : "2,2"}
              />

              {/* Animated Cruising Aircraft */}
              {isSelected && (
                <circle r="1.4" fill="#0071e3">
                  <animateMotion path={pathD} dur="2.8s" repeatCount="indefinite" />
                </circle>
              )}
            </g>
          );
        })}

        {/* City Nodes */}
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
              <circle
                r={isConnected ? 3.0 : 1.8}
                fill={isConnected ? "rgba(0, 113, 227, 0.15)" : "#ffffff"}
                stroke={isConnected ? "#0071e3" : "rgba(0, 0, 0, 0.2)"}
                strokeWidth="0.6"
              />
              <circle
                r={isConnected ? 1.4 : 0.9}
                fill={isConnected ? "#0071e3" : "#1d1d1f"}
              />
              <text
                x="2.4"
                y="0.8"
                fill={isConnected ? "#0071e3" : "#1d1d1f"}
                fontSize="2.8"
                fontFamily="var(--font-sans, sans-serif)"
                fontWeight={isConnected ? "700" : "500"}
              >
                {hub.code}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected Corridor Apple Floating Pill */}
      {selectedRoute && (
        <div
          style={{
            position: "absolute",
            bottom: 24,
            left: 24,
            right: 24,
            background: "rgba(255, 255, 255, 0.92)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(0, 0, 0, 0.08)",
            borderRadius: 16,
            padding: "16px 24px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            boxShadow: "0 8px 30px rgba(0, 0, 0, 0.06)",
          }}
        >
          <div>
            <div style={{ fontSize: 11, color: "#86868b", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Active Aviation Corridor
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#1d1d1f", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
              <span>{selectedRoute.from}</span>
              <span style={{ fontSize: 14, color: "#86868b" }}>➔</span>
              <span>{selectedRoute.to}</span>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 100,
                  backgroundColor: selectedRoute.status === "Surging" ? "rgba(255, 59, 48, 0.1)" : "rgba(52, 199, 89, 0.1)",
                  color: selectedRoute.status === "Surging" ? "#ff3b30" : "#34c759",
                  fontWeight: 600,
                  marginLeft: 6,
                }}
              >
                {selectedRoute.status}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 28 }}>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>Jevons Index</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#0071e3", fontFamily: "var(--font-mono)" }}>{selectedRoute.cpi}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>Average Fare</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#1d1d1f", fontFamily: "var(--font-mono)" }}>{selectedRoute.fare}</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#86868b", textTransform: "uppercase", fontWeight: 600 }}>MoM Movement</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#34c759", fontFamily: "var(--font-mono)" }}>{selectedRoute.change}</div>
            </div>
          </div>
        </div>
      )}

      {hoveredHub && (
        <div
          style={{
            position: "absolute",
            top: 20,
            right: 24,
            background: "#ffffff",
            border: "1px solid rgba(0, 0, 0, 0.08)",
            borderRadius: 10,
            padding: "8px 14px",
            fontSize: 12,
            boxShadow: "0 4px 16px rgba(0,0,0,0.06)",
          }}
        >
          <span style={{ color: "#0071e3", fontWeight: 700 }}>{hoveredHub.city} ({hoveredHub.code})</span>
          <div style={{ color: "#86868b", fontSize: 11, marginTop: 2 }}>Monthly Traffic: {(hoveredHub.pax / 1000000).toFixed(2)}M Passengers</div>
        </div>
      )}
    </div>
  );
}
