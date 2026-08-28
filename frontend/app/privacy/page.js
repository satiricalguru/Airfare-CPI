"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getAssetPath } from "../utils/assetPath";

export default function PrivacyPolicyPage() {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.remove("dark");
      root.classList.add("light");
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode((prev) => !prev);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", backgroundColor: isDarkMode ? "#0d121f" : "#f7f9fb", color: isDarkMode ? "#dae2fd" : "#131b2e", transition: "background-color 0.3s ease, color 0.3s ease" }}>
      {/* Navigation Header */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          height: 64,
          zIndex: 50,
          backgroundColor: isDarkMode ? "rgba(19, 27, 46, 0.94)" : "rgba(255, 255, 255, 0.94)",
          backdropFilter: "blur(12px)",
          borderBottom: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.08)"}`,
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 12, textDecoration: "none", color: "inherit" }}>
          <img
            src={getAssetPath(isDarkMode ? "/logo_dark.png" : "/logo.png")}
            alt="Airfare CPI Logo"
            className="logo-animated-glow"
            style={{
              width: 36,
              height: 36,
              objectFit: "contain",
            }}
          />
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, fontFamily: "var(--font-heading)", letterSpacing: "-0.02em" }}>Airfare CPI</div>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: isDarkMode ? "#bec6e0" : "#76777d" }}>
              India · MoSPI Prototype
            </div>
          </div>
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={toggleTheme}
            style={{
              background: isDarkMode ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.04)",
              border: `1px solid ${isDarkMode ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.08)"}`,
              borderRadius: "50%",
              width: 36,
              height: 36,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: isDarkMode ? "#ffddb8" : "#131b2e",
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              {isDarkMode ? "light_mode" : "dark_mode"}
            </span>
          </button>

          <Link
            href="/"
            style={{
              backgroundColor: isDarkMode ? "#39b8fd" : "#131b2e",
              color: isDarkMode ? "#001e2f" : "#ffffff",
              padding: "7px 16px",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
            Back to Dashboard
          </Link>
        </div>
      </nav>

      {/* Main Privacy Document Content */}
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px 80px", flexGrow: 1 }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isDarkMode ? "#39b8fd" : "#006591", marginBottom: 6 }}>
            Legal &amp; Regulatory Framework
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.03em", color: isDarkMode ? "#ffffff" : "#131b2e", margin: 0 }}>
            Privacy Policy &amp; Data Governance
          </h1>
          <p style={{ fontSize: 13, color: isDarkMode ? "#bec6e0" : "#76777d", marginTop: 8 }}>
            Effective Date: August 28, 2026 · Ministry of Statistics &amp; Programme Implementation (MoSPI)
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Section 1 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              1. Institutional Mandate &amp; Scope
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              This policy governs data handling practices for the <strong>Real-Time Airfare Consumer Price Index (CPI) Augmentation Platform</strong>, developed in support of the Ministry of Statistics and Programme Implementation (MoSPI), Government of India. The platform is designed strictly for statistical research, macro-economic price measurement, and transport inflation monitoring.
            </p>
          </div>

          {/* Section 2 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              2. Zero Personally Identifiable Information (PII) Guarantee
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d", marginBottom: 12 }}>
              In full compliance with India’s <strong>Digital Personal Data Protection Act (DPDPA), 2023</strong>:
            </p>
            <ul style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d", paddingLeft: 20 }}>
              <li><strong>No Passenger Data:</strong> The platform neither collects, processes, nor stores any passenger names, contact numbers, email addresses, payment credentials, or booking PNRs.</li>
              <li><strong>Public Market Quotes Only:</strong> Data ingestion is strictly confined to publicly visible, unauthenticated airline fare quotations published across carrier websites and online travel aggregators (OTAs).</li>
              <li><strong>Anonymous Price Relatives:</strong> All calculations operate exclusively on aggregated price levels, route codes, departure horizons, and statistical weight vectors.</li>
            </ul>
          </div>

          {/* Section 3 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              3. Ethical Web Scraping &amp; Data Collection Standards
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              Automated data extraction protocols adhere to strict fair-use and ethical scraping guidelines:
            </p>
            <ul style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d", paddingLeft: 20 }}>
              <li><strong>Rate-Limiting &amp; Backoff:</strong> Ingestion cycles employ polite crawl intervals and exponential backoff to ensure zero impact on airline booking engine performance.</li>
              <li><strong>Respect for Authentication:</strong> Scraping adapters only access unauthenticated, public fare query endpoints. No access controls, CAPTCHAs, or login gates are bypassed.</li>
              <li><strong>Provenance &amp; Audit Logs:</strong> Every collected quote is timestamped with source provenance and stored in an immutable audit ledger for statistical reproducibility.</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              4. Data Retention &amp; Security
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              Raw observations are stored in encrypted PostgreSQL database instances with TLS 1.3 encryption in transit and AES-256 encryption at rest. Aggregated elementary Jevons indices and national time series are retained indefinitely to enable longitudinal econometric studies.
            </p>
          </div>

          {/* Section 5 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              5. Contact &amp; Grievance Redressal
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              For statistical inquiries, methodology clarifications, or data policy queries, contact the Price Statistics Division, National Statistical Office (NSO), MoSPI, New Delhi at <a href="mailto:price-statistics@mospi.gov.in" style={{ color: isDarkMode ? "#39b8fd" : "#006591", textDecoration: "none", fontWeight: 600 }}>price-statistics@mospi.gov.in</a>.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{ backgroundColor: "#131b2e", color: "#ffffff", padding: "24px", textAlign: "center", fontSize: 12, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div>Government of India · Ministry of Statistics &amp; Programme Implementation</div>
        <div style={{ color: "rgba(255,255,255,0.6)", marginTop: 4 }}>Airfare Consumer Price Index Research Prototype v1.0</div>
      </footer>
    </div>
  );
}
