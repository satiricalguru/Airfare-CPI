"use client";

import { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from "recharts";
import { getAssetPath } from "../utils/assetPath";
import { HOMEPAGE_AIRLINE_FLEET_DATA } from "../data/mockData";

export default function RouteDetailModal({ route, isOpen, onClose, isDarkMode, onSetWatch }) {
  const [activeSubTab, setActiveSubTab] = useState("trend"); // trend | horizon | carriers | iqr

  if (!isOpen || !route) return null;

  const originCode = route.from || route.origin || "DEL";
  const destCode = route.to || route.destination || "BOM";
  const basePrice = route.avgFare || (typeof route.fare === "number" ? route.fare : 5240);

  // Generate deterministic 30-day historical trend data for this route
  const trendData = Array.from({ length: 30 }, (_, i) => {
    const day = i + 1;
    const variation = Math.sin(i * 0.45) * 450 + (i % 7 === 0 ? 600 : 0);
    const fare = Math.round(basePrice + variation);
    const ma7 = Math.round(basePrice + Math.sin((i - 3) * 0.3) * 280);
    return {
      date: `Aug ${day < 10 ? "0" + day : day}`,
      fare,
      ma7,
      median: basePrice,
    };
  });

  // Advance Purchase Horizon Curve Data
  const horizonData = [
    { horizon: "T+30 Days", fare: Math.round(basePrice * 0.86), index: 92.4, color: "#22c55e", label: "Optimal Window" },
    { horizon: "T+15 Days", fare: Math.round(basePrice * 0.98), index: 98.6, color: "#38bdf8", label: "Standard Rate" },
    { horizon: "T+7 Days", fare: Math.round(basePrice * 1.18), index: 114.2, color: "#f59e0b", label: "Urgency Premium" },
    { horizon: "T+3 Days", fare: Math.round(basePrice * 1.45), index: 139.5, color: "#f97316", label: "Yield Peak" },
    { horizon: "T+0 (Same Day)", fare: Math.round(basePrice * 1.88), index: 184.0, color: "#ef4444", label: "Scarcity Spike" },
  ];

  // Carrier spread data
  const carrierFares = [
    { code: "6E", name: "IndiGo", fare: Math.round(basePrice * 0.94), share: "62.8%", logoUrl: "/airlines/indigo.svg" },
    { code: "AI", name: "Air India", fare: Math.round(basePrice * 1.05), share: "14.2%", logoUrl: "/airlines/airindia.svg" },
    { code: "UK", name: "Vistara", fare: Math.round(basePrice * 1.12), share: "9.6%", logoUrl: "/airlines/vistara.svg" },
    { code: "QP", name: "Akasa Air", fare: Math.round(basePrice * 0.91), share: "4.8%", logoUrl: "/airlines/akasa.svg" },
    { code: "SG", name: "SpiceJet", fare: Math.round(basePrice * 0.96), share: "5.4%", logoUrl: "/airlines/spicejet.svg" },
  ];

  // Statistical IQR anomaly fences
  const q1 = Math.round(basePrice * 0.92);
  const median = basePrice;
  const q3 = Math.round(basePrice * 1.15);
  const iqr = q3 - q1;
  const lowerFence = Math.max(1500, Math.round(q1 - 1.5 * iqr));
  const upperFence = Math.round(q3 + 1.5 * iqr);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        backgroundColor: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 880,
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          borderRadius: 24,
          overflow: "hidden",
          backgroundColor: isDarkMode ? "#0d121f" : "#ffffff",
          border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.3)" : "rgba(0, 101, 145, 0.15)"}`,
          boxShadow: isDarkMode ? "0 25px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(56, 189, 248, 0.12)" : "0 20px 50px rgba(0, 0, 0, 0.15)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "20px 28px",
            borderBottom: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: isDarkMode ? "linear-gradient(90deg, #0f172a, #080d1a)" : "linear-gradient(90deg, #f8fafc, #ffffff)",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 22, fontWeight: 900, fontFamily: "var(--font-mono)", color: isDarkMode ? "#ffffff" : "#0f172a" }}>
                {originCode} ⇄ {destCode}
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  padding: "3px 8px",
                  borderRadius: 6,
                  backgroundColor: isDarkMode ? "rgba(56, 189, 248, 0.15)" : "rgba(0, 101, 145, 0.1)",
                  color: isDarkMode ? "#38bdf8" : "#006591",
                }}
              >
                DGCA HIGH DENSITY TRUNK
              </span>
            </div>
            <div style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", marginTop: 4 }}>
              Current Jevons Relative Index: <strong style={{ color: isDarkMode ? "#38bdf8" : "#006591" }}>{route.cpi || "106.4"}</strong> · Average Fare: <strong style={{ color: "#22c55e" }}>₹{basePrice.toLocaleString()}</strong> · Movement: <strong style={{ color: "#22c55e" }}>{route.change || "+2.8%"}</strong>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {onSetWatch && (
              <button
                onClick={() => {
                  onSetWatch(originCode, destCode, basePrice);
                  onClose();
                }}
                style={{
                  padding: "8px 16px",
                  borderRadius: 10,
                  backgroundColor: isDarkMode ? "#0284c7" : "#006591",
                  color: "#ffffff",
                  fontSize: 12,
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  boxShadow: "0 2px 10px rgba(2, 132, 199, 0.3)",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                  add_alert
                </span>
                <span>Set Price Watch</span>
              </button>
            )}

            <button
              onClick={onClose}
              style={{
                background: isDarkMode ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.05)",
                border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)"}`,
                borderRadius: "50%",
                width: 34,
                height: 34,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: isDarkMode ? "#94a3b8" : "#64748b",
                cursor: "pointer",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                close
              </span>
            </button>
          </div>
        </div>

        {/* Sub-Navigation Tabs */}
        <div
          style={{
            padding: "10px 28px",
            borderBottom: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.06)"}`,
            display: "flex",
            gap: 8,
            backgroundColor: isDarkMode ? "#080d1a" : "#f8fafc",
          }}
        >
          {[
            { id: "trend", label: "30-Day Historical Trend", icon: "trending_up" },
            { id: "horizon", label: "Advance Horizon Curve (T+0 to T+30)", icon: "schedule" },
            { id: "carriers", label: "Carrier Price Spread", icon: "airlines" },
            { id: "iqr", label: "IQR Anomaly Fencing", icon: "analytics" },
          ].map((tab) => {
            const isActive = activeSubTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 14px",
                  borderRadius: 10,
                  fontSize: 12.5,
                  fontWeight: isActive ? 800 : 600,
                  cursor: "pointer",
                  backgroundColor: isActive ? (isDarkMode ? "#0284c7" : "#006591") : "transparent",
                  color: isActive ? "#ffffff" : (isDarkMode ? "#94a3b8" : "#64748b"),
                  border: isActive ? `1px solid ${isDarkMode ? "#38bdf8" : "#006591"}` : "1px solid transparent",
                  transition: "all 0.15s ease",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                  {tab.icon}
                </span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Body */}
        <div style={{ padding: "24px 28px", overflowY: "auto", flex: 1, minHeight: 360 }}>
          {/* 1. 30-Day Trend Chart */}
          {activeSubTab === "trend" && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div>
                  <h4 style={{ fontSize: 15, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                    Trailing 30-Day Airfare Movement vs 7-Day Moving Average
                  </h4>
                  <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                    Daily sampled geometric mean fare compared against trailing rolling average
                  </p>
                </div>
                <div style={{ display: "flex", gap: 16, fontSize: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 12, height: 3, backgroundColor: "#38bdf8", borderRadius: 2 }} />
                    <span style={{ color: isDarkMode ? "#cbd5e1" : "#475569" }}>Daily Sampled Fare</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 12, height: 3, backgroundColor: "#22c55e", borderRadius: 2 }} />
                    <span style={{ color: isDarkMode ? "#cbd5e1" : "#475569" }}>7D Moving Average</span>
                  </div>
                </div>
              </div>

              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"} />
                    <XAxis dataKey="date" stroke={isDarkMode ? "#64748b" : "#94a3b8"} fontSize={11} />
                    <YAxis domain={["auto", "auto"]} stroke={isDarkMode ? "#64748b" : "#94a3b8"} fontSize={11} tickFormatter={(v) => `₹${v}`} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.95)" : "rgba(255, 255, 255, 0.95)",
                        border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.3)" : "rgba(0, 101, 145, 0.2)"}`,
                        borderRadius: 12,
                        boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
                        color: isDarkMode ? "#ffffff" : "#0f172a",
                      }}
                      formatter={(val) => [`₹${val.toLocaleString()}`, ""]}
                    />
                    <ReferenceLine y={basePrice} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: `Median: ₹${basePrice}`, fill: "#f59e0b", fontSize: 10, position: "right" }} />
                    <Line type="monotone" dataKey="fare" stroke="#38bdf8" strokeWidth={2.5} dot={false} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="ma7" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 2. Advance Booking Horizon Curve */}
          {activeSubTab === "horizon" && (
            <div>
              <div style={{ marginBottom: 14 }}>
                <h4 style={{ fontSize: 15, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                  Advance Purchase Yield Decay Profile ($T+0 \to T+30$)
                </h4>
                <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                  Airlines apply algorithmic dynamic yield discrimination as departure date approaches
                </p>
              </div>

              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={horizonData} margin={{ top: 20, right: 20, left: 10, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"} />
                    <XAxis dataKey="horizon" stroke={isDarkMode ? "#64748b" : "#94a3b8"} fontSize={11} />
                    <YAxis stroke={isDarkMode ? "#64748b" : "#94a3b8"} fontSize={11} tickFormatter={(v) => `₹${v}`} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.95)" : "rgba(255, 255, 255, 0.95)",
                        border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.3)" : "rgba(0, 101, 145, 0.2)"}`,
                        borderRadius: 12,
                        color: isDarkMode ? "#ffffff" : "#0f172a",
                      }}
                      formatter={(val) => [`₹${val.toLocaleString()}`, "Average Fare"]}
                    />
                    <Bar dataKey="fare" radius={[8, 8, 0, 0]}>
                      {horizonData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 3. Carrier Price Spread */}
          {activeSubTab === "carriers" && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 15, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                  Carrier Price Spread on {originCode} ⇄ {destCode}
                </h4>
                <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                  Real-time baseline economy fares across certified scheduled operators
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                {carrierFares.map((c) => (
                  <div
                    key={c.code}
                    style={{
                      padding: "16px 18px",
                      borderRadius: 16,
                      backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.7)" : "#f8fafc",
                      border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)"}`,
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                    }}
                  >
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 12,
                        backgroundColor: "#ffffff",
                        padding: 6,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                        overflow: "hidden",
                        flexShrink: 0,
                      }}
                    >
                      <img src={getAssetPath(c.logoUrl)} alt={c.name} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a" }}>{c.name}</div>
                      <div style={{ fontSize: 18, fontWeight: 900, fontFamily: "var(--font-mono)", color: isDarkMode ? "#38bdf8" : "#006591", marginTop: 2 }}>
                        ₹{c.fare.toLocaleString()}
                      </div>
                      <div style={{ fontSize: 11, color: isDarkMode ? "#64748b" : "#94a3b8", marginTop: 2 }}>
                        Market Share: {c.share}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. IQR Anomaly Fencing */}
          {activeSubTab === "iqr" && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 15, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                  Statistical Interquartile Range (IQR) Quality Gate
                </h4>
                <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                  Observations outside $[Q_1 - 1.5 \\times \\text{IQR},\\; Q_3 + 1.5 \\times \\text{IQR}]$ are flagged to protect CPI from algorithmic scrap errors
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
                <div style={{ padding: "14px 16px", borderRadius: 14, backgroundColor: isDarkMode ? "rgba(239, 68, 68, 0.1)" : "rgba(239, 68, 68, 0.06)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                  <div style={{ fontSize: 11, color: "#ef4444", fontWeight: 700 }}>Lower Anomaly Cutoff</div>
                  <div style={{ fontSize: 17, fontWeight: 900, fontFamily: "var(--font-mono)", color: "#ef4444", marginTop: 4 }}>
                    ₹{lowerFence.toLocaleString()}
                  </div>
                </div>

                <div style={{ padding: "14px 16px", borderRadius: 14, backgroundColor: isDarkMode ? "rgba(56, 189, 248, 0.1)" : "rgba(0, 101, 145, 0.06)", border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.25)" : "rgba(0, 101, 145, 0.15)"}` }}>
                  <div style={{ fontSize: 11, color: isDarkMode ? "#38bdf8" : "#006591", fontWeight: 700 }}>25th Percentile ($Q_1$)</div>
                  <div style={{ fontSize: 17, fontWeight: 900, fontFamily: "var(--font-mono)", color: isDarkMode ? "#38bdf8" : "#006591", marginTop: 4 }}>
                    ₹{q1.toLocaleString()}
                  </div>
                </div>

                <div style={{ padding: "14px 16px", borderRadius: 14, backgroundColor: isDarkMode ? "rgba(34, 197, 94, 0.1)" : "rgba(34, 197, 94, 0.06)", border: "1px solid rgba(34, 197, 94, 0.25)" }}>
                  <div style={{ fontSize: 11, color: "#22c55e", fontWeight: 700 }}>Route Median ($Q_2$)</div>
                  <div style={{ fontSize: 17, fontWeight: 900, fontFamily: "var(--font-mono)", color: "#22c55e", marginTop: 4 }}>
                    ₹{median.toLocaleString()}
                  </div>
                </div>

                <div style={{ padding: "14px 16px", borderRadius: 14, backgroundColor: isDarkMode ? "rgba(56, 189, 248, 0.1)" : "rgba(0, 101, 145, 0.06)", border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.25)" : "rgba(0, 101, 145, 0.15)"}` }}>
                  <div style={{ fontSize: 11, color: isDarkMode ? "#38bdf8" : "#006591", fontWeight: 700 }}>75th Percentile ($Q_3$)</div>
                  <div style={{ fontSize: 17, fontWeight: 900, fontFamily: "var(--font-mono)", color: isDarkMode ? "#38bdf8" : "#006591", marginTop: 4 }}>
                    ₹{q3.toLocaleString()}
                  </div>
                </div>

                <div style={{ padding: "14px 16px", borderRadius: 14, backgroundColor: isDarkMode ? "rgba(239, 68, 68, 0.1)" : "rgba(239, 68, 68, 0.06)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                  <div style={{ fontSize: 11, color: "#ef4444", fontWeight: 700 }}>Upper Surge Cutoff</div>
                  <div style={{ fontSize: 17, fontWeight: 900, fontFamily: "var(--font-mono)", color: "#ef4444", marginTop: 4 }}>
                    ₹{upperFence.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
