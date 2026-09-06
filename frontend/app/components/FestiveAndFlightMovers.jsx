"use client";

import { useMemo, useState } from "react";
import {
  Calendar,
  Plane,
  TrendingDown,
  TrendingUp,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
} from "lucide-react";
import { CopilotSymbol } from "./AviationCopilotModal";

export default function FestiveAndFlightMovers({ data, onSelectRoute }) {
  const [activeTab, setActiveTab] = useState("festivals"); // "festivals" | "surging" | "dropping" | "brands"
  const [selectedRouteCode, setSelectedRouteCode] = useState("DEL-BOM");

  const festiveSpikes = data?.festive_spikes || {};
  const flightMovers = data?.flight_movers || {};

  const festivals = festiveSpikes.calendar_events || [];
  const surgingFlights = flightMovers.top_surging_flights || [];
  const droppingFlights = flightMovers.top_dropping_flights || [];
  const brandComparisons = useMemo(
    () => flightMovers.brand_comparison || [],
    [flightMovers.brand_comparison]
  );

  const activeBrandCorridor = useMemo(() => {
    if (!brandComparisons.length) return null;
    return (
      brandComparisons.find((c) => c.route_code === selectedRouteCode) ||
      brandComparisons[0]
    );
  }, [brandComparisons, selectedRouteCode]);

  return (
    <div className="fm-wrapper" data-testid="festive-and-flight-movers">
      {/* Section Heading matching the Web App Design System */}
      <div className="section-heading">
        <div>
          <p className="eyebrow">Market Volatility &amp; Pricing Dynamics</p>
          <h2>Indian Festive Spikes &amp; Flight Movers</h2>
          <p className="section-description">
            Real-time volatility across major festival surges, top flight price swings, and carrier brand benchmarks.
          </p>
        </div>

        {/* Tab Controls matching Web App Segmented Navigation */}
        <div className="segmented-control fm-nav-segmented">
          <button
            onClick={() => setActiveTab("festivals")}
            className={activeTab === "festivals" ? "is-active" : ""}
            data-testid="fm-tab-festivals"
          >
            Festive Spikes ({festivals.length})
          </button>
          <button
            onClick={() => setActiveTab("surging")}
            className={activeTab === "surging" ? "is-active" : ""}
            data-testid="fm-tab-surging"
          >
            Highest Surges ({surgingFlights.length})
          </button>
          <button
            onClick={() => setActiveTab("dropping")}
            className={activeTab === "dropping" ? "is-active" : ""}
            data-testid="fm-tab-dropping"
          >
            Lowest Fares ({droppingFlights.length})
          </button>
          <button
            onClick={() => setActiveTab("brands")}
            className={activeTab === "brands" ? "is-active" : ""}
            data-testid="fm-tab-brands"
          >
            Brand Benchmark
          </button>
        </div>
      </div>

      {/* Tab 1: Festive Spikes */}
      {activeTab === "festivals" && (
        <div className="fm-events-grid">
          {festivals.map((evt) => {
            const surgePct = Math.min(100, Math.round((evt.typical_surge_pct / 70) * 100));
            const datesDisplay = evt.dates_2026 || evt.dates_2025 || evt.dates || "Peak travel window";
            return (
              <div className="fm-event-card" key={evt.id}>
                <div className="fm-event-card-top">
                  <div>
                    <h3 className="fm-event-name">{evt.name}</h3>
                    <div className="fm-event-dates">
                      <Clock size={12} />
                      <span>{datesDisplay}</span>
                    </div>
                  </div>
                  <span className={`fm-surge-pill severity-${evt.severity}`}>
                    <TrendingUp size={12} /> +{evt.typical_surge_pct}%
                  </span>
                </div>

                <div className="fm-event-meter">
                  <div className="fm-meter-bar-bg">
                    <div
                      className="fm-meter-bar-fill"
                      style={{ width: `${surgePct}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="fm-corridors-label">Impacted Corridors:</div>
                  <div className="fm-corridors-wrap">
                    {(evt.impacted_corridors || []).map((code) => (
                      <span
                        key={code}
                        className="fm-corridor-tag"
                        onClick={() => onSelectRoute?.(code)}
                        title={`View ${code} corridor detail`}
                      >
                        {code}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="fm-advice-box">
                  <CopilotSymbol size={13} className="fm-advice-copilot-icon" />
                  <div className="fm-advice-text">
                    <strong>Booking Advice:</strong> {evt.booking_advice}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 2: Highest Surges */}
      {activeTab === "surging" && (
        <div className="fm-flights-grid">
          {surgingFlights.map((f, idx) => (
            <div className="fm-flight-card is-surge" key={`${f.flight_number}-${idx}`}>
              <div className="fm-flight-header">
                <div className="fm-flight-num-badge">
                  <Plane size={14} />
                  <span className="fm-flight-num">{f.flight_number}</span>
                  <span className="fm-airline-tag">{f.airline_name}</span>
                </div>
                <span className="fm-badge-surge">
                  <ArrowUpRight size={13} style={{ display: "inline" }} /> +{f.percent_change}%
                </span>
              </div>

              <div className="fm-flight-route-row">
                <span>{f.origin_city} → {f.destination_city}</span>
                <span
                  className="fm-corridor-tag"
                  onClick={() => onSelectRoute?.(f.route_code)}
                  title="View corridor details"
                >
                  {f.route_code}
                </span>
              </div>

              <div className="fm-flight-meta-row">
                <span>Horizon: T+{f.booking_horizon_days}d ({f.departure_date})</span>
                <span>{f.stops === 0 ? "Non-stop" : `${f.stops} stop(s)`} • {f.cabin}</span>
              </div>

              <div className="fm-flight-fare-row">
                <div>
                  <span className="fm-current-fare">₹{f.current_fare?.toLocaleString("en-IN")}</span>
                </div>
                <div className="fm-baseline-fare">
                  Route Median: ₹{f.baseline_fare?.toLocaleString("en-IN")}
                </div>
              </div>
            </div>
          ))}
          {surgingFlights.length === 0 && (
            <div className="fm-empty-state">
              No flight surges currently detected above corridor median.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Lowest Fares */}
      {activeTab === "dropping" && (
        <div className="fm-flights-grid">
          {droppingFlights.map((f, idx) => (
            <div className="fm-flight-card is-deal" key={`${f.flight_number}-${idx}`}>
              <div className="fm-flight-header">
                <div className="fm-flight-num-badge">
                  <Plane size={14} />
                  <span className="fm-flight-num">{f.flight_number}</span>
                  <span className="fm-airline-tag">{f.airline_name}</span>
                </div>
                <span className="fm-badge-deal">
                  <ArrowDownRight size={13} style={{ display: "inline" }} /> {f.percent_change}%
                </span>
              </div>

              <div className="fm-flight-route-row">
                <span>{f.origin_city} → {f.destination_city}</span>
                <span
                  className="fm-corridor-tag"
                  onClick={() => onSelectRoute?.(f.route_code)}
                  title="View corridor details"
                >
                  {f.route_code}
                </span>
              </div>

              <div className="fm-flight-meta-row">
                <span>Horizon: T+{f.booking_horizon_days}d ({f.departure_date})</span>
                <span>{f.stops === 0 ? "Non-stop" : `${f.stops} stop(s)`} • {f.cabin}</span>
              </div>

              <div className="fm-flight-fare-row">
                <div>
                  <span className="fm-current-fare is-deal-fare">
                    ₹{f.current_fare?.toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="fm-baseline-fare">
                  Route Median: ₹{f.baseline_fare?.toLocaleString("en-IN")}
                </div>
              </div>
            </div>
          ))}
          {droppingFlights.length === 0 && (
            <div className="fm-empty-state">
              No discounted flights currently detected below corridor median.
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Brand Benchmark */}
      {activeTab === "brands" && (
        <div>
          {/* Corridor Selection Chips */}
          <div className="fm-corridor-selector-wrap">
            <span className="eyebrow" style={{ alignSelf: "center", marginRight: "6px" }}>
              Select Corridor:
            </span>
            <div className="fm-corridor-selector">
              {brandComparisons.map((c) => (
                <button
                  key={c.route_code}
                  onClick={() => setSelectedRouteCode(c.route_code)}
                  className={`fm-corridor-chip ${
                    selectedRouteCode === c.route_code ? "is-active" : ""
                  }`}
                >
                  {c.route_code}
                </button>
              ))}
            </div>
          </div>

          {activeBrandCorridor && (
            <div>
              <div className="fm-corridor-info-banner">
                <div>
                  <p className="eyebrow" style={{ margin: "0 0 3px" }}>
                    {activeBrandCorridor.route_code} Trunk Corridor
                  </p>
                  <h3 className="fm-corridor-title">{activeBrandCorridor.route_name}</h3>
                </div>
                <div className="fm-corridor-median">
                  <span className="eyebrow">Corridor Median</span>
                  <strong>₹{activeBrandCorridor.corridor_median_fare?.toLocaleString("en-IN")}</strong>
                </div>
              </div>

              <div className="fm-brands-grid">
                {(activeBrandCorridor.brands || []).map((b) => {
                  const isCheapest = b.position === "LOWEST PRICED BRAND";
                  const isPremium = b.position === "HIGHEST / PREMIUM BRAND";
                  return (
                    <div
                      key={b.brand_name}
                      className={`fm-brand-card ${isCheapest ? "is-cheapest" : isPremium ? "is-premium" : ""}`}
                    >
                      <div className="fm-brand-top">
                        <h4 className="fm-brand-name">{b.brand_name}</h4>
                        {b.position && (
                          <span
                            className={`fm-brand-position ${
                              isCheapest ? "cheapest" : isPremium ? "premium" : ""
                            }`}
                          >
                            {b.position}
                          </span>
                        )}
                      </div>

                      <div className="fm-brand-fare-block">
                        <span className="eyebrow">Average Fare</span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "2px" }}>
                          <span className="fm-brand-avg-fare">₹{b.average_fare?.toLocaleString("en-IN")}</span>
                          <span
                            className={`fm-brand-diff-tag ${
                              b.percent_vs_median <= 0 ? "cheaper" : "higher"
                            }`}
                          >
                            {b.percent_vs_median > 0 ? `+${b.percent_vs_median}%` : `${b.percent_vs_median}%`} vs median
                          </span>
                        </div>
                      </div>

                      <div className="fm-brand-stats-row">
                        <div>
                          <div className="fm-brand-stat-label">Lowest ({b.cheapest_flight})</div>
                          <div className="fm-brand-stat-value">₹{b.min_fare?.toLocaleString("en-IN")}</div>
                        </div>
                        <div>
                          <div className="fm-brand-stat-label">Peak ({b.peak_flight})</div>
                          <div className="fm-brand-stat-value">₹{b.max_fare?.toLocaleString("en-IN")}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
