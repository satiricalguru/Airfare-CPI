"use client";

import { useEffect, useState } from "react";
import { AIRPORTS_LIST, ROUTE_HEATMAP_DATA } from "../data/mockData";

const WATCHLIST_STORAGE_KEY = "airfare-cpi-watchlist-v1";
const DEFAULT_WATCHES = [
  { id: "watch-1", from: "DEL", to: "BOM", type: "price_drop", target: 4800, currentFare: 5240, horizon: "T+15", status: "watching", created: "2 hours ago" },
  { id: "watch-2", from: "BLR", to: "DEL", type: "price_drop", target: 4400, currentFare: 4350, horizon: "T+30", status: "triggered", created: "1 day ago" },
  { id: "watch-3", from: "BOM", to: "GOI", type: "index_surge", target: 6.0, currentFare: 6890, horizon: "T+7", status: "watching", created: "3 days ago" },
];

export default function PriceAlertEngine({ isDarkMode, onTriggerToast }) {
  const [origin, setOrigin] = useState("DEL");
  const [destination, setDestination] = useState("BOM");
  const [targetPrice, setTargetPrice] = useState("4500");
  const [alertType, setAlertType] = useState("price_drop"); // price_drop | index_surge
  const [surgeThreshold, setSurgeThreshold] = useState("5");
  const [horizon, setHorizon] = useState("T+15");

  const [activeWatches, setActiveWatches] = useState(DEFAULT_WATCHES);
  const [storageReady, setStorageReady] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
      if (stored) setActiveWatches(JSON.parse(stored));
    } catch {
      // Keep the benchmark watchlist when browser storage is unavailable.
    } finally {
      setStorageReady(true);
    }
  }, []);

  useEffect(() => {
    if (storageReady) window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(activeWatches));
  }, [activeWatches, storageReady]);

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
    <div className="alert-engine" data-testid="price-alert-engine">
      <div className="alert-engine-grid">
        {/* Left Column: Create Alert Watch Form */}
        <section className="alert-builder-panel">
          <div className="alert-engine-heading">
            <div className="alert-engine-icon" aria-hidden="true">
              <span className="material-symbols-outlined">add_alert</span>
            </div>
            <div>
              <h3 className="alert-engine-title">Create automated price watch</h3>
              <p className="alert-engine-subtitle">
                Trigger notifications on price dips or extreme surge anomalies
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateWatch} className="alert-builder-form" data-testid="price-alert-builder-form">
            {/* Origin & Destination Selectors */}
            <div className="alert-form-grid">
              <label className="alert-field">
                <span>Origin city</span>
                <select
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  className="alert-control"
                  data-testid="price-alert-origin-select"
                >
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code}>
                      {a.code} — {a.city}
                    </option>
                  ))}
                </select>
              </label>

              <label className="alert-field">
                <span>Destination city</span>
                <select
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="alert-control"
                  data-testid="price-alert-destination-select"
                >
                  {AIRPORTS_LIST.map((a) => (
                    <option key={a.code} value={a.code}>
                      {a.code} — {a.city}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {/* Alert Trigger Type Toggle */}
            <fieldset className="alert-field alert-trigger-fieldset">
              <legend>Trigger condition</legend>
              <div className="alert-trigger-options">
                <button
                  type="button"
                  onClick={() => setAlertType("price_drop")}
                  className={`alert-trigger-option ${alertType === "price_drop" ? "is-selected" : ""}`}
                  aria-pressed={alertType === "price_drop"}
                  data-testid="price-alert-drop-trigger-button"
                >
                  <span aria-hidden="true">↘</span> Price drops below (₹)
                </button>
                <button
                  type="button"
                  onClick={() => setAlertType("index_surge")}
                  className={`alert-trigger-option ${alertType === "index_surge" ? "is-selected" : ""}`}
                  aria-pressed={alertType === "index_surge"}
                  data-testid="price-alert-surge-trigger-button"
                >
                  <span aria-hidden="true">↗</span> Index surge exceeds (%)
                </button>
              </div>
            </fieldset>

            {/* Threshold Input & Horizon */}
            <div className="alert-form-grid">
              <label className="alert-field">
                <span>{alertType === "price_drop" ? "Target fare (₹)" : "Surge threshold (%)"}</span>
                <input
                  type="number"
                  value={alertType === "price_drop" ? targetPrice : surgeThreshold}
                  onChange={(e) => alertType === "price_drop" ? setTargetPrice(e.target.value) : setSurgeThreshold(e.target.value)}
                  placeholder={alertType === "price_drop" ? "e.g. 4500" : "e.g. 5.0"}
                  className="alert-control alert-number-control"
                  data-testid="price-alert-threshold-input"
                />
              </label>

              <label className="alert-field">
                <span>Advance horizon</span>
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  className="alert-control"
                  data-testid="price-alert-horizon-select"
                >
                  <option value="T+0">T+0 (Same day)</option>
                  <option value="T+3">T+3 days</option>
                  <option value="T+7">T+7 days</option>
                  <option value="T+15">T+15 days</option>
                  <option value="T+30">T+30 days</option>
                </select>
              </label>
            </div>

            <button
              type="submit"
              className="alert-submit-button"
              data-testid="price-alert-submit-button"
            >
              <span className="material-symbols-outlined" aria-hidden="true">
                notification_add
              </span>
              <span>Activate price watch</span>
            </button>
          </form>
        </section>

        {/* Right Column: Active Watches List */}
        <section className="alert-watches-panel">
          <div className="alert-watches-heading">
            <div>
              <h3 className="alert-engine-title">Active monitored watches <span>({activeWatches.length})</span></h3>
              <p className="alert-engine-subtitle">
                Continuous scraping telemetry comparing against target thresholds
              </p>
            </div>
            <span className="alert-daemon-status"><i /> daemon active</span>
          </div>

          <div className="alert-watch-list" data-testid="price-alert-watch-list">
            {activeWatches.map((w) => {
              const isTriggered = w.status === "triggered";
              const isPriceDrop = w.type === "price_drop";

              return (
                <article
                  key={w.id}
                  className={`alert-watch ${isTriggered ? "is-triggered" : ""}`}
                  data-testid={`price-alert-watch-${w.id}`}
                >
                  <div className="alert-watch-copy">
                    <div className="alert-watch-route-row">
                      <span className="alert-watch-route">
                        {w.from} → {w.to}
                      </span>
                      <span className="alert-watch-chip alert-watch-horizon">
                        {w.horizon}
                      </span>
                      <span className={`alert-watch-chip ${isTriggered ? "alert-watch-chip-triggered" : "alert-watch-chip-watching"}`}>
                        {isTriggered ? "TARGET REACHED" : "WATCHING"}
                      </span>
                    </div>

                    <div className="alert-watch-metrics">
                      <div>
                        <span>Current </span>
                        <strong>
                          ₹{w.currentFare.toLocaleString()}
                        </strong>
                      </div>
                      <div>
                        <span>Target </span>
                        <strong className="alert-watch-target">
                          {isPriceDrop ? `≤ ₹${w.target.toLocaleString()}` : `≥ +${w.target}%`}
                        </strong>
                      </div>
                      <div>
                        <span>Created </span>
                        <span>{w.created}</span>
                      </div>
                    </div>
                  </div>

                  <div className="alert-watch-actions">
                    <button
                      onClick={() => handleDeleteWatch(w.id)}
                      title="Delete watch"
                      aria-label={`Delete watch for ${w.from} to ${w.to}`}
                      className="alert-delete-button"
                      data-testid={`price-alert-delete-${w.id}-button`}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">
                        delete
                      </span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
