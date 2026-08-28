"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getAssetPath } from "../utils/assetPath";

export default function TermsOfServicePage() {
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

      {/* Main Terms Content */}
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px 80px", flexGrow: 1 }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: isDarkMode ? "#39b8fd" : "#006591", marginBottom: 6 }}>
            Terms &amp; Conditions
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.03em", color: isDarkMode ? "#ffffff" : "#131b2e", margin: 0 }}>
            Terms of Service &amp; Usage Policy
          </h1>
          <p style={{ fontSize: 13, color: isDarkMode ? "#bec6e0" : "#76777d", marginTop: 8 }}>
            Last Updated: August 28, 2026 · Ministry of Statistics &amp; Programme Implementation (MoSPI)
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Section 1 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              1. Acceptance &amp; Purpose of the Platform
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              By accessing or using the Airfare Price Index Dashboard and REST API, you agree to comply with and be bound by these Terms of Service. This platform provides experimental real-time statistical price indicators designed to explore Big Data augmentation of India&apos;s Consumer Price Index (CPI).
            </p>
          </div>

          {/* Section 2 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              2. Provisional Statistical Status Disclaimer
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              All daily and high-frequency indices published on this dashboard are <strong>provisional research indicators</strong>. Official national macroeconomic inflation figures remain those formally released by the National Statistical Office (NSO) on the 12th of each month in the official CPI press communique.
            </p>
          </div>

          {/* Section 3 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              3. Open Government Data License &amp; Attribution
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d", marginBottom: 12 }}>
              In accordance with the <strong>National Data Sharing and Accessibility Policy (NDSAP)</strong>:
            </p>
            <ul style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d", paddingLeft: 20 }}>
              <li><strong>Permitted Use:</strong> Academic researchers, policy analysts, financial institutions, and the general public may freely query, analyze, and cite index timeseries for non-commercial and research purposes.</li>
              <li><strong>Required Citation:</strong> Any publication using data from this platform must include the citation: <em>&ldquo;Source: Ministry of Statistics &amp; Programme Implementation (MoSPI) — Airfare CPI Prototype Engine, 2026.&rdquo;</em></li>
              <li><strong>Prohibited Actions:</strong> Users may not attempt to reverse-engineer commercial airline yield management algorithms or use API endpoints for commercial ticket scalping.</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              4. API Rate Limits &amp; Acceptable Use
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              Programmatic access via <code>/api/v1/</code> is subject to fair-use rate limits (10,000 requests/day per API key). Excessive polling or distributed denial-of-service traffic will result in automated IP throttling.
            </p>
          </div>

          {/* Section 5 */}
          <div className="stitch-card" style={{ padding: 28 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: isDarkMode ? "#ffffff" : "#131b2e", marginTop: 0, marginBottom: 12 }}>
              5. Governing Law &amp; Jurisdiction
            </h2>
            <p style={{ fontSize: 14, lineHeight: 1.7, color: isDarkMode ? "#bec6e0" : "#45464d" }}>
              These Terms shall be governed by and construed in accordance with the laws of the Republic of India. Any disputes arising in connection with the platform shall be subject to the exclusive jurisdiction of the courts of New Delhi, India.
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
