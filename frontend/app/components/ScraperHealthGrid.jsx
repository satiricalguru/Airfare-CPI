"use client";

import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  ExternalLink,
  Play,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

export default function ScraperHealthGrid({ scrapers = [], onTestScraper, loading = false }) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [probingId, setProbingId] = useState(null);
  const [probeResult, setProbeResult] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredScrapers = scrapers
    .filter((s) => {
      if (activeFilter !== "all" && s.category !== activeFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          s.display_name.toLowerCase().includes(q) ||
          s.source_id.toLowerCase().includes(q) ||
          (s.engine && s.engine.toLowerCase().includes(q))
        );
      }
      return true;
    })
    .sort((a, b) => {
      // Non-working / standby scrapers always go to the bottom
      if (a.is_active && !b.is_active) return -1;
      if (!a.is_active && b.is_active) return 1;
      return a.display_name.localeCompare(b.display_name);
    });

  const activeCount = scrapers.filter((s) => s.is_active).length;
  const totalCount = scrapers.length;

  const handleRunProbe = async (sourceId) => {
    setProbingId(sourceId);
    try {
      if (onTestScraper) {
        const res = await onTestScraper(sourceId);
        setProbeResult(res);
        setShowModal(true);
      }
    } catch (err) {
      setProbeResult({
        source_id: sourceId,
        status: "FAILED",
        is_working: false,
        error: err?.message || "Failed to execute probe",
      });
      setShowModal(true);
    } finally {
      setProbingId(null);
    }
  };

  return (
    <div className="table-panel scraper-fleet-panel" data-testid="scraper-fleet-container">
      {/* Institutional Table Header */}
      <div className="table-panel-header scraper-table-header">
        <div>
          <p className="eyebrow">
            <Activity size={12} style={{ verticalAlign: "middle", marginRight: 4 }} />
            Data Acquisition Fleet
          </p>
          <h3>Quotation channels &amp; operational working condition</h3>
          <p className="muted-note" style={{ marginTop: 4 }}>
            Continuous monitoring across <strong>{totalCount}</strong> domestic airline and OTA quotation channels,
            utilizing Scrapy spiders, Playwright network interceptors, and sub-second RPC engines.
          </p>
        </div>

        <div className="scraper-header-stats">
          <span className="status-pill status-pill-success">
            <span className="quiet-dot active" />
            {activeCount} of {totalCount} channels active
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="scraper-filter-bar">
        <div className="scraper-tabs-minimal" role="tablist">
          <button
            type="button"
            className={`tab-item ${activeFilter === "all" ? "is-active" : ""}`}
            onClick={() => setActiveFilter("all")}
          >
            All channels ({scrapers.length})
          </button>
          <button
            type="button"
            className={`tab-item ${activeFilter === "airline" ? "is-active" : ""}`}
            onClick={() => setActiveFilter("airline")}
          >
            Airlines ({scrapers.filter((s) => s.category === "airline").length})
          </button>
          <button
            type="button"
            className={`tab-item ${activeFilter === "ota" ? "is-active" : ""}`}
            onClick={() => setActiveFilter("ota")}
          >
            OTAs ({scrapers.filter((s) => s.category === "ota").length})
          </button>
          <button
            type="button"
            className={`tab-item ${activeFilter === "metasearch" ? "is-active" : ""}`}
            onClick={() => setActiveFilter("metasearch")}
          >
            Metasearch &amp; RPC ({scrapers.filter((s) => s.category === "metasearch").length})
          </button>
        </div>

        <div className="scraper-search-box">
          <Search size={13} className="search-icon" />
          <input
            type="text"
            placeholder="Filter by portal name or engine…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Vertical Column Ledger Table */}
      <div className="table-scroll">
        <table className="scraper-table">
          <thead>
            <tr>
              <th>Channel / Portal</th>
              <th>Category</th>
              <th>Acquisition Architecture</th>
              <th>Condition &amp; Protocol</th>
              <th className="num-col">Latency</th>
              <th className="num-col">24h Reliability</th>
              <th className="num-col">Quotes Today</th>
              <th className="action-col">Verification</th>
            </tr>
          </thead>
          <tbody>
            {filteredScrapers.map((s) => {
              const isProbing = probingId === s.source_id;
              const isHealthy = s.is_active;

              return (
                <tr key={s.source_id} data-testid={`scraper-row-${s.source_id}`}>
                  {/* Channel / Portal */}
                  <td>
                    <strong>{s.display_name}</strong>
                    <small className="mono">{s.source_id}</small>
                  </td>

                  {/* Category */}
                  <td>
                    <span className="category-badge">
                      {s.category === "airline"
                        ? "Airline Direct"
                        : s.category === "ota"
                        ? "OTA Portal"
                        : "Metasearch / RPC"}
                    </span>
                  </td>

                  {/* Architecture & Engine */}
                  <td>
                    <span className="mono">{s.engine}</span>
                    <small>{s.acquisition_method?.toUpperCase() || "WEB_SCRAPE"}</small>
                  </td>

                  {/* Condition & Protocol */}
                  <td>
                    <div className="condition-cell">
                      <span className={`quiet-dot ${isHealthy ? "active" : "standby"}`} />
                      <div>
                        <span className="condition-status-text">
                          {isHealthy ? "Operational" : "Standby / Review"}
                        </span>
                        <small>{s.working_condition}</small>
                      </div>
                    </div>
                  </td>

                  {/* Response Latency */}
                  <td className="num-col mono">
                    {s.latency_ms ? `${s.latency_ms.toLocaleString()} ms` : "—"}
                  </td>

                  {/* 24h Reliability */}
                  <td className="num-col mono">
                    {s.success_rate_24h > 0 ? `${s.success_rate_24h}%` : "—"}
                  </td>

                  {/* Quotes Harvested Today */}
                  <td className="num-col mono">
                    {s.observations_today ? s.observations_today.toLocaleString() : "0"}
                  </td>

                  {/* Actions: Test Probe & External Link */}
                  <td className="action-col">
                    <div className="action-buttons-inline">
                      <button
                        type="button"
                        className="row-action button-probe"
                        disabled={isProbing}
                        onClick={() => handleRunProbe(s.source_id)}
                        data-testid={`test-scraper-btn-${s.source_id}`}
                        title="Run on-demand probe test against DEL-BOM"
                      >
                        {isProbing ? (
                          <>
                            <RefreshCw size={11} className="spin" /> Probing…
                          </>
                        ) : (
                          <>
                            <Play size={11} /> Test Probe
                          </>
                        )}
                      </button>

                      {s.homepage && (
                        <a
                          href={s.homepage}
                          target="_blank"
                          rel="noreferrer"
                          className="row-action row-action-icon"
                          title="Open channel homepage"
                        >
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filteredScrapers.length === 0 && (
        <div className="table-panel-empty">
          No quotation channels match the selected filter or search term.
        </div>
      )}

      {/* Interactive Probe Results Modal */}
      {showModal && probeResult && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div
            className="modal-panel modal-panel-wide probe-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="modal-header">
              <div>
                <p className="eyebrow">Real-Time Probe Verification</p>
                <h3>{probeResult.source_id.toUpperCase()} Channel Diagnostic</h3>
              </div>
              <div className="modal-header-actions">
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => setShowModal(false)}
                  aria-label="Close"
                  data-testid="probe-modal-close-btn"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="probe-summary-strip">
              <div className="strip-item">
                <span className="strip-label">Status</span>
                <span className={`strip-val ${probeResult.is_working ? "val-ok" : "val-warn"}`}>
                  {probeResult.status === "SUCCESS" ? "Operational" : "Failed / Challenged"}
                </span>
              </div>
              <div className="strip-item">
                <span className="strip-label">Response Time</span>
                <span className="strip-val mono">{probeResult.response_time_ms} ms</span>
              </div>
              <div className="strip-item">
                <span className="strip-label">Quotes Extracted</span>
                <span className="strip-val mono">{probeResult.observations_count}</span>
              </div>
              <div className="strip-item">
                <span className="strip-label">Route Corridor</span>
                <span className="strip-val mono">{probeResult.route || "DEL-BOM"}</span>
              </div>
            </div>

            {probeResult.sample_quotes && probeResult.sample_quotes.length > 0 && (
              <div className="sample-quotes-section">
                <p className="eyebrow" style={{ marginBottom: 8 }}>
                  Extracted Live Quotes with AERA Tariff Unbundling
                </p>
                <div className="table-scroll">
                  <table className="probe-table">
                    <thead>
                      <tr>
                        <th>Flight #</th>
                        <th>Carrier</th>
                        <th>Dep Time</th>
                        <th>Total Fare</th>
                        <th>Base Fare</th>
                        <th>GST + Taxes</th>
                        <th>Airport UDF</th>
                        <th>Convenience</th>
                      </tr>
                    </thead>
                    <tbody>
                      {probeResult.sample_quotes.map((q, idx) => (
                        <tr key={idx}>
                          <td className="mono bold">{q.flight_number}</td>
                          <td>{q.airline_name} ({q.airline_code})</td>
                          <td>{q.dep_time}</td>
                          <td className="bold">₹{q.fare_total?.toLocaleString("en-IN")}</td>
                          <td>₹{q.fare_base?.toLocaleString("en-IN") || "—"}</td>
                          <td>₹{q.fare_taxes?.toLocaleString("en-IN") || "—"}</td>
                          <td>₹{q.fare_udf?.toLocaleString("en-IN") || "—"}</td>
                          <td>₹{q.fare_convenience?.toLocaleString("en-IN") || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {probeResult.error && (
              <div className="probe-error-callout">
                <strong>Error Details:</strong> {probeResult.error}
              </div>
            )}

            {probeResult.note && (
              <p className="muted-note" style={{ marginTop: 12 }}>
                {probeResult.note}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
