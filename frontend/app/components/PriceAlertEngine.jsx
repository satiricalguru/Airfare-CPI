"use client";

/**
 * SIH26056 — Price watch builder (browser-local).
 *
 * Honesty note, stated on screen and not only here
 * ------------------------------------------------
 * There is NO server-side alert monitor and NO delivery mechanism. Nothing evaluates
 * these watches when the browser is closed, and no email or webhook is ever sent. The
 * backend reports this at `/api/v1/alerts` as NOT IMPLEMENTED.
 *
 * The audit found this component shipping three seeded watches with invented
 * "triggered" states and relative timestamps ("1 day ago"), which made it look like a
 * working monitor with a history. Those are gone: the list starts empty, and a watch is
 * only ever created by the user.
 *
 * Current fares shown against a watch come from the route index data passed in as
 * `routes`. When that is unavailable, the watch simply has no current value rather than
 * a fabricated one.
 */

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bell, Plus, Trash2 } from "lucide-react";
import { AIRPORTS_LIST } from "../data/referenceData";
import { NOT_AVAILABLE } from "../lib/api";
import { fmtDateTime, fmtIndex, fmtInr } from "../lib/format";

const WATCHLIST_STORAGE_KEY = "airfare-cpi-watchlist-v2";
const HORIZONS = ["T+0", "T+3", "T+7", "T+15", "T+30"];

/** Restore saved watches. Guarded for the static-export prerender. */
function readStoredWatches() {
  if (typeof window === "undefined") return [];
  try {
    const stored = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function PriceAlertEngine({ onTriggerToast, routes = [] }) {
  const [origin, setOrigin] = useState("DEL");
  const [destination, setDestination] = useState("BOM");
  const [alertType, setAlertType] = useState("price_drop");
  const [targetPrice, setTargetPrice] = useState("4500");
  const [surgeThreshold, setSurgeThreshold] = useState("5");
  const [horizon, setHorizon] = useState("T+15");

  // Starts EMPTY. No seeded watches, because a seeded "triggered" watch implies a
  // monitor that evaluated it. Restored lazily rather than in an effect, so mount does
  // not trigger a synchronous state update.
  const [watches, setWatches] = useState(readStoredWatches);

  useEffect(() => {
    try {
      window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watches));
    } catch {
      /* storage unavailable; watches live for this session only */
    }
  }, [watches]);

  /** Route index lookup, so a watch can display a real current index. */
  const routeByCode = useMemo(() => {
    const map = new Map();
    for (const r of routes) {
      if (r.route_code) map.set(r.route_code, r);
    }
    return map;
  }, [routes]);

  const createWatch = (event) => {
    event.preventDefault();

    if (origin === destination) {
      onTriggerToast?.("Origin and destination cannot be the same.");
      return;
    }

    const routeCode = `${origin}-${destination}`;
    const parsedTarget =
      alertType === "price_drop"
        ? Number.parseInt(targetPrice, 10)
        : Number.parseFloat(surgeThreshold);

    if (!Number.isFinite(parsedTarget) || parsedTarget <= 0) {
      onTriggerToast?.("Enter a valid threshold.");
      return;
    }

    setWatches((current) => [
      {
        id: `watch-${Date.now()}`,
        routeCode,
        origin,
        destination,
        type: alertType,
        target: parsedTarget,
        horizon,
        createdAt: new Date().toISOString(),
      },
      ...current,
    ]);

    onTriggerToast?.(
      `Watch saved in this browser for ${routeCode}. Nothing monitors it server-side.`,
    );
  };

  const removeWatch = (id) => setWatches((current) => current.filter((w) => w.id !== id));

  return (
    <div className="alert-engine">
      <form className="alert-builder" onSubmit={createWatch}>
        <div className="filter-grid">
          <label>
            Origin
            <select value={origin} onChange={(e) => setOrigin(e.target.value)} data-testid="alert-origin-select">
              {AIRPORTS_LIST.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} — {a.city}
                </option>
              ))}
            </select>
          </label>
          <label>
            Destination
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
            Trigger
            <select value={alertType} onChange={(e) => setAlertType(e.target.value)} data-testid="alert-type-select">
              <option value="price_drop">Fare drops below</option>
              <option value="index_surge">Index rises by more than</option>
            </select>
          </label>
          {alertType === "price_drop" ? (
            <label>
              Target fare (INR)
              <input
                type="number"
                min="500"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                data-testid="alert-target-price-input"
              />
            </label>
          ) : (
            <label>
              Threshold (%)
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={surgeThreshold}
                onChange={(e) => setSurgeThreshold(e.target.value)}
                data-testid="alert-surge-input"
              />
            </label>
          )}
          <label>
            Booking horizon
            <select value={horizon} onChange={(e) => setHorizon(e.target.value)} data-testid="alert-horizon-select">
              {HORIZONS.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button className="button button-dark" type="submit" data-testid="alert-create-button">
          <Plus size={15} /> Save watch in this browser
        </button>
      </form>

      <div className="table-panel">
        <div className="table-panel-header">
          <div>
            <p className="eyebrow">{watches.length} saved watch(es)</p>
            <h3>Browser watchlist</h3>
          </div>
          <span className="status-pill status-pill-muted">
            <Bell size={12} /> Not monitored
          </span>
        </div>

        {watches.length === 0 ? (
          <div className="table-panel-empty">
            <p className="muted-note" data-testid="alert-empty-note">
              No watches saved. Creating one stores it in this browser; it will not be
              evaluated anywhere.
            </p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Trigger</th>
                  <th>Horizon</th>
                  <th>Current route index</th>
                  <th>Saved</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {watches.map((watch) => {
                  const routeRow = routeByCode.get(watch.routeCode);
                  return (
                    <tr key={watch.id} data-testid={`alert-row-${watch.id}`}>
                      <td>
                        <strong>{watch.routeCode}</strong>
                      </td>
                      <td>
                        {watch.type === "price_drop"
                          ? `below ${fmtInr(watch.target)}`
                          : `index up more than ${watch.target}%`}
                      </td>
                      <td>{watch.horizon}</td>
                      <td className="mono">
                        {/* Real index when available; otherwise N/A, never a stand-in. */}
                        {routeRow ? fmtIndex(routeRow.value) : NOT_AVAILABLE}
                      </td>
                      <td>
                        <small className="mono">{fmtDateTime(watch.createdAt)}</small>
                      </td>
                      <td>
                        <span className="status-pill status-pill-muted">Not evaluated</span>
                      </td>
                      <td>
                        <button
                          className="row-action"
                          onClick={() => removeWatch(watch.id)}
                          aria-label={`Delete watch for ${watch.routeCode}`}
                          data-testid={`alert-delete-${watch.id}`}
                        >
                          <Trash2 size={13} /> Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="table-panel-footer">
          <p className="muted-note">
            Every watch shows <strong>Not evaluated</strong> because that is the truth:
            there is no monitor. A status of &ldquo;triggered&rdquo; would imply an
            evaluation that never happened.
          </p>
        </div>
      </div>

    </div>
  );
}
