"use client";

import { useState } from "react";
import { AIRPORTS_LIST, ROUTE_HEATMAP_DATA } from "../data/mockData";

export default function PriceAlertEngine({ isDarkMode, onTriggerToast }) {
  const [origin, setOrigin] = useState("DEL");
  const [destination, setDestination] = useState("BOM");
  const [targetPrice, setTargetPrice] = useState("4500");
  const [alertType, setAlertType] = useState("price_drop"); // price_drop | index_surge
  const [surgeThreshold, setSurgeThreshold] = useState("5");
  const [horizon, setHorizon] = useState("T+15");

  const [activeWatches, setActiveWatches] = useState([
    {
      id: "watch-1",
      from: "DEL",
      to: "BOM",
      type: "price_drop",
      target: 4800,
      currentFare: 5240,
      horizon: "T+15",
      status: "watching",
      created: "2 hours ago",
    },
    {
      id: "watch-2",
      from: "BLR",
      to: "DEL",
      type: "price_drop",
      target: 4400,
      currentFare: 4350,
      horizon: "T+30",
      status: "triggered",
      created: "1 day ago",
    },
    {
      id: "watch-3",
      from: "BOM",
      to: "GOI",
      type: "index_surge",
      target: 6.0,
      currentFare: 6890,
      horizon: "T+7",
      status: "watching",
      created: "3 days ago",
    },
  ]);

  const handleCreateWatch = (e) => {
    e.preventDefault();
    if (origin === destination) {
      if (onTriggerToast) onTriggerToast("Origin and Destination cannot be identical.", "warning");
      return;
    }

    const currentRoute = ROUTE_HEATMAP_DATA.find((r) => r.from === origin && r.to === destination);
    const baseFare = currentRoute ? currentRoute.avgFare : 5500;

    const newWatch = {
      id: `watch-${Date.now()}`,
      from: origin,
      to: destination,
      type: alertType,
      target: alertType === "price_drop" ? parseInt(targetPrice, 10) || 5000 : parseFloat(surgeThreshold) || 5,
      currentFare: baseFare,
      horizon,
      status: "watching",
      created: "Just now",
    };

    setActiveWatches((prev) => [newWatch, ...prev]);
    if (onTriggerToast) {
      onTriggerToast(`Price Watch created for ${origin} → ${destination} (${alertType === "price_drop" ? `Target: ₹${targetPrice}` : `Surge > ${surgeThreshold}%`})`, "success");
    }
  };

  const handleDeleteWatch = (id) => {
    setActiveWatches((prev) => prev.filter((w) => w.id !== id));
    if (onTriggerToast) onTriggerToast("Price Watch removed.", "info");
  };

  return (
    <div style={{ width: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
        {/* Left Column: Create Alert Watch Form */}
        <div
          className="stitch-card"
          style={{
            padding: "24px 28px",
            borderRadius: 20,
            backgroundColor: isDarkMode ? "#080d1a" : "#ffffff",
            border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.2)" : "rgba(0, 101, 145, 0.12)"}`,
            boxShadow: isDarkMode ? "0 12px 36px rgba(0,0,0,0.5)" : "0 8px 24px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                backgroundColor: isDarkMode ? "rgba(56, 189, 248, 0.15)" : "rgba(0, 101, 145, 0.1)",
                color: isDarkMode ? "#38bdf8" : "#006591",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                add_alert
              </span>
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                Create Automated Price Watch
              </h3>
              <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                Trigger notifications on price dips or extreme surge anomalies
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateWatch} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Origin & Destination Selectors */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: isDarkMode ? "#94a3b8" : "#64748b", marginBottom: 6, display: "block" }}>
                  Origin City
                </label>
                <select
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.8)" : "#f8fafc",
                    border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.1)"}`,
                    color: isDarkMode ? "#ffffff" : "#0f172a",
                    fontSize: 13,
                    fontWeight: 600,
                    outline: "none",
                  }}
                >
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code} style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>
                      {a.code} — {a.city}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: isDarkMode ? "#94a3b8" : "#64748b", marginBottom: 6, display: "block" }}>
                  Destination City
                </label>
                <select
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.8)" : "#f8fafc",
                    border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.1)"}`,
                    color: isDarkMode ? "#ffffff" : "#0f172a",
                    fontSize: 13,
                    fontWeight: 600,
                    outline: "none",
                  }}
                >
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code} style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>
                      {a.code} — {a.city}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Alert Trigger Type Toggle */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: isDarkMode ? "#94a3b8" : "#64748b", marginBottom: 6, display: "block" }}>
                Trigger Condition
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setAlertType("price_drop")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 10,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    backgroundColor: alertType === "price_drop" ? (isDarkMode ? "#0284c7" : "#006591") : (isDarkMode ? "rgba(255,255,255,0.04)" : "#f1f5f9"),
                    color: alertType === "price_drop" ? "#ffffff" : (isDarkMode ? "#94a3b8" : "#64748b"),
                    border: `1px solid ${alertType === "price_drop" ? (isDarkMode ? "#38bdf8" : "#006591") : "transparent"}`,
                    transition: "all 0.15s ease",
                  }}
                >
                  📉 Price Drops Below (₹)
                </button>
                <button
                  type="button"
                  onClick={() => setAlertType("index_surge")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 10,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    backgroundColor: alertType === "index_surge" ? (isDarkMode ? "#0284c7" : "#006591") : (isDarkMode ? "rgba(255,255,255,0.04)" : "#f1f5f9"),
                    color: alertType === "index_surge" ? "#ffffff" : (isDarkMode ? "#94a3b8" : "#64748b"),
                    border: `1px solid ${alertType === "index_surge" ? (isDarkMode ? "#38bdf8" : "#006591") : "transparent"}`,
                    transition: "all 0.15s ease",
                  }}
                >
                  ⚡ Index Surge Exceeds (%)
                </button>
              </div>
            </div>

            {/* Threshold Input & Horizon */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: isDarkMode ? "#94a3b8" : "#64748b", marginBottom: 6, display: "block" }}>
                  {alertType === "price_drop" ? "Target Fare (₹)" : "Surge Threshold (%)"}
                </label>
                <input
                  type="number"
                  value={alertType === "price_drop" ? targetPrice : surgeThreshold}
                  onChange={(e) => alertType === "price_drop" ? setTargetPrice(e.target.value) : setSurgeThreshold(e.target.value)}
                  placeholder={alertType === "price_drop" ? "e.g. 4500" : "e.g. 5.0"}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: 10,
                    backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.8)" : "#f8fafc",
                    border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.1)"}`,
                    color: isDarkMode ? "#ffffff" : "#0f172a",
                    fontSize: 14,
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: isDarkMode ? "#94a3b8" : "#64748b", marginBottom: 6, display: "block" }}>
                  Advance Horizon
                </label>
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.8)" : "#f8fafc",
                    border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.1)"}`,
                    color: isDarkMode ? "#ffffff" : "#0f172a",
                    fontSize: 13,
                    fontWeight: 600,
                    outline: "none",
                  }}
                >
                  <option value="T+0" style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>T+0 (Same Day)</option>
                  <option value="T+3" style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>T+3 Days</option>
                  <option value="T+7" style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>T+7 Days</option>
                  <option value="T+15" style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>T+15 Days</option>
                  <option value="T+30" style={{ background: isDarkMode ? "#0f172a" : "#ffffff", color: isDarkMode ? "#ffffff" : "#000000" }}>T+30 Days</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              style={{
                marginTop: 8,
                padding: "12px 20px",
                borderRadius: 12,
                backgroundColor: isDarkMode ? "#0284c7" : "#006591",
                color: "#ffffff",
                fontSize: 14,
                fontWeight: 800,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: "0 4px 14px rgba(2, 132, 199, 0.35)",
                transition: "all 0.15s ease",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                notification_add
              </span>
              <span>Activate Price Watch</span>
            </button>
          </form>
        </div>

        {/* Right Column: Active Watches List */}
        <div
          className="stitch-card"
          style={{
            padding: "24px 28px",
            borderRadius: 20,
            backgroundColor: isDarkMode ? "#080d1a" : "#ffffff",
            border: `1px solid ${isDarkMode ? "rgba(56, 189, 248, 0.2)" : "rgba(0, 101, 145, 0.12)"}`,
            boxShadow: isDarkMode ? "0 12px 36px rgba(0,0,0,0.5)" : "0 8px 24px rgba(0,0,0,0.04)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: isDarkMode ? "#ffffff" : "#0f172a", margin: 0 }}>
                Active Monitored Watches ({activeWatches.length})
              </h3>
              <p style={{ fontSize: 12, color: isDarkMode ? "#94a3b8" : "#64748b", margin: 0 }}>
                Continuous scraping telemetry comparing against target thresholds
              </p>
            </div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 800,
                padding: "3px 8px",
                borderRadius: 6,
                backgroundColor: "rgba(34, 197, 94, 0.15)",
                color: "#22c55e",
                border: "1px solid rgba(34, 197, 94, 0.3)",
              }}
            >
              DAEMON ACTIVE
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flex: 1 }}>
            {activeWatches.map((w) => {
              const isTriggered = w.status === "triggered";
              const isPriceDrop = w.type === "price_drop";

              return (
                <div
                  key={w.id}
                  style={{
                    padding: "14px 18px",
                    borderRadius: 14,
                    backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.85)" : "#f8fafc",
                    border: `1px solid ${isTriggered ? (isDarkMode ? "rgba(34, 197, 94, 0.4)" : "rgba(34, 197, 94, 0.3)") : (isDarkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)")}`,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    boxShadow: isTriggered ? "0 4px 16px rgba(34, 197, 94, 0.15)" : "none",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 15, fontWeight: 900, fontFamily: "var(--font-mono)", color: isDarkMode ? "#ffffff" : "#0f172a" }}>
                        {w.from} → {w.to}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          padding: "2px 6px",
                          borderRadius: 4,
                          backgroundColor: isDarkMode ? "rgba(56, 189, 248, 0.15)" : "rgba(0, 101, 145, 0.1)",
                          color: isDarkMode ? "#38bdf8" : "#006591",
                        }}
                      >
                        {w.horizon}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          padding: "2px 6px",
                          borderRadius: 4,
                          backgroundColor: isTriggered ? "rgba(34, 197, 94, 0.15)" : "rgba(148, 163, 184, 0.15)",
                          color: isTriggered ? "#22c55e" : (isDarkMode ? "#94a3b8" : "#64748b"),
                        }}
                      >
                        {isTriggered ? "TARGET REACHED" : "WATCHING"}
                      </span>
                    </div>

                    <div style={{ display: "flex", gap: 14, marginTop: 6, fontSize: 12 }}>
                      <div>
                        <span style={{ color: isDarkMode ? "#64748b" : "#94a3b8" }}>Current: </span>
                        <strong style={{ color: isDarkMode ? "#ffffff" : "#0f172a", fontFamily: "var(--font-mono)" }}>
                          ₹{w.currentFare.toLocaleString()}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: isDarkMode ? "#64748b" : "#94a3b8" }}>Target: </span>
                        <strong style={{ color: "#22c55e", fontFamily: "var(--font-mono)" }}>
                          {isPriceDrop ? `≤ ₹${w.target.toLocaleString()}` : `≥ +${w.target}%`}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: isDarkMode ? "#64748b" : "#94a3b8" }}>Created: </span>
                        <span style={{ color: isDarkMode ? "#94a3b8" : "#64748b" }}>{w.created}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button
                      onClick={() => handleDeleteWatch(w.id)}
                      title="Delete Watch"
                      style={{
                        padding: 6,
                        borderRadius: 8,
                        background: "rgba(239, 68, 68, 0.1)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        color: "#ef4444",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                        delete
                      </span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
