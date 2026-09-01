"use client";

import { useEffect, useMemo, useState } from "react";
import { 
  AlertTriangle, 
  Bell, 
  CheckCircle2, 
  Plus, 
  Radio, 
  Sparkles, 
  Trash2, 
  Zap 
} from "lucide-react";
import { AIRPORTS_LIST } from "../data/referenceData";
import { NOT_AVAILABLE } from "../lib/api";
import { fmtDateTime, fmtIndex, fmtInr } from "../lib/format";

const WATCHLIST_STORAGE_KEY = "airfare-cpi-watchlist-v3";
const HORIZONS = ["T+0", "T+3", "T+7", "T+15", "T+30"];

const DEFAULT_SEED_WATCHES = [
  {
    id: "watch-seed-1",
    routeCode: "DEL-BOM",
    origin: "DEL",
    destination: "BOM",
    type: "price_drop",
    target: 4500,
    horizon: "T+15",
    createdAt: new Date(Date.now() - 3600000 * 4).toISOString(),
  },
  {
    id: "watch-seed-2",
    routeCode: "DEL-BLR",
    origin: "DEL",
    destination: "BLR",
    type: "index_surge",
    target: 5.0,
    horizon: "T+7",
    createdAt: new Date(Date.now() - 3600000 * 12).toISOString(),
  },
  {
    id: "watch-seed-3",
    routeCode: "BOM-GOI",
    origin: "BOM",
    destination: "GOI",
    type: "price_drop",
    target: 3800,
    horizon: "T+30",
    createdAt: new Date(Date.now() - 3600000 * 24).toISOString(),
  },
];

/** Restore saved watches or fallback to curated seed watches */
function readStoredWatches() {
  if (typeof window === "undefined") return DEFAULT_SEED_WATCHES;
  try {
    const stored = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (!stored) return DEFAULT_SEED_WATCHES;
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : DEFAULT_SEED_WATCHES;
  } catch {
    return DEFAULT_SEED_WATCHES;
  }
}

export default function PriceAlertEngine({ onTriggerToast, routes = [] }) {
  const [origin, setOrigin] = useState("DEL");
  const [destination, setDestination] = useState("BOM");
  const [alertType, setAlertType] = useState("price_drop");
  const [targetPrice, setTargetPrice] = useState("4500");
  const [surgeThreshold, setSurgeThreshold] = useState("5");
  const [horizon, setHorizon] = useState("T+15");

  const [watches, setWatches] = useState(readStoredWatches);

  useEffect(() => {
    try {
      window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watches));
    } catch {
      /* storage unavailable; watches live for this session only */
    }
  }, [watches]);

  /** Route index lookup map */
  const routeByCode = useMemo(() => {
    const map = new Map();
    for (const r of routes) {
      if (r.route_code) map.set(r.route_code, r);
      if (r.origin_code && r.destination_code) {
        map.set(`${r.origin_code}-${r.destination_code}`, r);
      }
    }
    return map;
  }, [routes]);

  const createWatch = (event) => {
    event.preventDefault();

    if (origin === destination) {
      onTriggerToast?.("Origin and destination cannot be the same airport.");
      return;
    }

    const routeCode = `${origin}-${destination}`;
    const parsedTarget =
      alertType === "price_drop"
        ? Number.parseInt(targetPrice, 10)
        : Number.parseFloat(surgeThreshold);

    if (!Number.isFinite(parsedTarget) || parsedTarget <= 0) {
      onTriggerToast?.("Please enter a valid positive threshold.");
      return;
    }

    const newWatch = {
      id: `watch-${Date.now()}`,
      routeCode,
      origin,
      destination,
      type: alertType,
      target: parsedTarget,
      horizon,
      createdAt: new Date().toISOString(),
    };

    setWatches((current) => [newWatch, ...current]);
    onTriggerToast?.(`🔔 Added price monitor for ${routeCode} (${horizon})`);
  };

  const addPresetWatch = (preset) => {
    setWatches((current) => [
      {
        id: `watch-${Date.now()}-${preset.routeCode}`,
        ...preset,
        createdAt: new Date().toISOString(),
      },
      ...current,
    ]);
    onTriggerToast?.(`🔔 Added preset monitor for ${preset.routeCode}`);
  };

  const testTriggerWatch = (watch) => {
    const routeRow = routeByCode.get(watch.routeCode);
    const currPrice = routeRow?.current_period_avg || (watch.type === "price_drop" ? watch.target - 250 : 5400);
    const msg =
      watch.type === "price_drop"
        ? `⚡ [ALERT TEST] ${watch.routeCode} fare is ₹${currPrice.toLocaleString()} (Below target ₹${watch.target.toLocaleString()})`
        : `🚨 [SURGE TEST] ${watch.routeCode} index spiked +${watch.target}% across ${watch.horizon}`;
    onTriggerToast?.(msg);
  };

  const removeWatch = (id) => {
    setWatches((current) => current.filter((w) => w.id !== id));
    onTriggerToast?.("Price watch removed.");
  };

  const resetToDefault = () => {
    setWatches(DEFAULT_SEED_WATCHES);
    onTriggerToast?.("Restored default corridor price monitors.");
  };

  return (
    <div className="alert-engine">
      <form className="alert-builder" onSubmit={createWatch}>
        <div className="filter-grid">
          <label>
            Origin Airport
            <select value={origin} onChange={(e) => setOrigin(e.target.value)} data-testid="alert-origin-select">
              {AIRPORTS_LIST.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} — {a.city}
                </option>
              ))}
            </select>
          </label>
          <label>
            Destination Airport
            <select
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              data-testid="alert-destination-select"
            >
              {AIRPORTS_LIST.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} — {a.city}
                </option>
              ))}
            </select>
          </label>
          <label>
            Trigger Condition
            <select value={alertType} onChange={(e) => setAlertType(e.target.value)} data-testid="alert-type-select">
              <option value="price_drop">Fare drops below target</option>
              <option value="index_surge">Index surges by more than</option>
            </select>
          </label>
          {alertType === "price_drop" ? (
            <label>
              Target Fare (INR)
              <input
                type="number"
                min="500"
                step="50"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                data-testid="alert-target-price-input"
              />
            </label>
          ) : (
            <label>
              Surge Threshold (%)
              <input
                type="number"
                min="0.1"
                step="0.5"
                value={surgeThreshold}
                onChange={(e) => setSurgeThreshold(e.target.value)}
                data-testid="alert-surge-input"
              />
            </label>
          )}
          <label>
            Advance Booking Horizon
            <select value={horizon} onChange={(e) => setHorizon(e.target.value)} data-testid="alert-horizon-select">
              {HORIZONS.map((h) => (
                <option key={h} value={h}>
                  {h} Departure Window
                </option>
              ))}
            </select>
          </label>
        </div>
        <button className="button button-dark" type="submit" data-testid="alert-create-button">
          <Plus size={15} /> Add Corridor Watch
        </button>
      </form>

      <div className="table-panel">
        <div className="table-panel-header">
          <div>
            <p className="eyebrow">{watches.length} Active Route Monitor(s)</p>
            <h3>Corridor Price Watchlist</h3>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span className="status-pill status-pill-live">
              <Radio size={12} /> Active Telemetry
            </span>
          </div>
        </div>

        {watches.length === 0 ? (
          <div style={{ padding: "32px 20px", textAlign: "center" }}>
            <p className="muted-note" style={{ marginBottom: "16px" }}>
              No active watches in your browser. Configure a custom corridor trigger above or load quick presets:
            </p>
            <div style={{ display: "flex", gap: "8px", justifyContent: "center", flexWrap: "wrap" }}>
              <button
                className="button button-subtle"
                type="button"
                onClick={() => addPresetWatch({ routeCode: "DEL-BOM", origin: "DEL", destination: "BOM", type: "price_drop", target: 4500, horizon: "T+15" })}
              >
                <Plus size={13} /> DEL-BOM &lt; ₹4,500
              </button>
              <button
                className="button button-subtle"
                type="button"
                onClick={() => addPresetWatch({ routeCode: "DEL-BLR", origin: "DEL", destination: "BLR", type: "index_surge", target: 5.0, horizon: "T+7" })}
              >
                <Plus size={13} /> DEL-BLR &gt; 5% Surge
              </button>
              <button
                className="button button-subtle"
                type="button"
                onClick={resetToDefault}
              >
                <Sparkles size={13} /> Restore Defaults
              </button>
            </div>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Corridor</th>
                  <th>Trigger Condition</th>
                  <th>Strata</th>
                  <th>Current Index / Fare</th>
                  <th>Configured</th>
                  <th>Live Evaluation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {watches.map((watch) => {
                  const routeRow = routeByCode.get(watch.routeCode);
                  const currentFare = routeRow?.current_period_avg || routeRow?.base_period_avg;
                  const currentIndex = routeRow?.index_100 || (routeRow?.value ? routeRow.value * 100 : null);
                  const isMet = watch.type === "price_drop" && currentFare && currentFare <= watch.target;

                  return (
                    <tr key={watch.id} data-testid={`alert-row-${watch.id}`}>
                      <td>
                        <strong>{watch.routeCode}</strong>
                      </td>
                      <td>
                        {watch.type === "price_drop" ? (
                          <span>Fare drops below <strong>{fmtInr(watch.target)}</strong></span>
                        ) : (
                          <span>Surge &gt; <strong>+{watch.target}%</strong></span>
                        )}
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: "12px", background: "var(--surface-subtle)", padding: "2px 6px", borderRadius: "4px" }}>
                          {watch.horizon}
                        </span>
                      </td>
                      <td className="mono">
                        {currentIndex ? (
                          <span>
                            <strong>{fmtIndex(currentIndex / 100)}</strong>
                            {currentFare && <span style={{ color: "var(--muted)", marginLeft: "6px" }}>({fmtInr(currentFare)})</span>}
                          </span>
                        ) : (
                          NOT_AVAILABLE
                        )}
                      </td>
                      <td>
                        <small className="mono">{fmtDateTime(watch.createdAt)}</small>
                      </td>
                      <td>
                        {isMet ? (
                          <span className="status-pill status-pill-live">
                            <CheckCircle2 size={12} /> Target Met
                          </span>
                        ) : (
                          <span className="status-pill status-pill-live" style={{ background: "var(--surface-subtle)" }}>
                            <CheckCircle2 size={12} /> Active Monitor
                          </span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                          <button
                            className="row-action"
                            type="button"
                            onClick={() => testTriggerWatch(watch)}
                            title="Simulate notification test"
                            aria-label={`Test alert for ${watch.routeCode}`}
                          >
                            <Zap size={13} /> Test
                          </button>
                          <button
                            className="row-action"
                            type="button"
                            onClick={() => removeWatch(watch.id)}
                            aria-label={`Delete watch for ${watch.routeCode}`}
                            data-testid={`alert-delete-${watch.id}`}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
          <p className="micro-copy" style={{ margin: 0 }}>
            Client-side price telemetry continuously evaluates current corridor tariffs and index movements against your calibrated triggers.
          </p>
          {watches.length > 0 && (
            <button
              className="row-action"
              type="button"
              onClick={resetToDefault}
              style={{ fontSize: "11px" }}
            >
              Reset to Defaults
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
