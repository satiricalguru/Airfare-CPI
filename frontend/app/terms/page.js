"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  Scale
} from "lucide-react";
import { getAssetPath } from "../utils/assetPath";

export default function TermsOfServicePage() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("light", !dark);
  }, [dark]);

  return (
    <div className="app-shell">
      {/* Site Header matching application design */}
      <header className="site-header">
        <div className="header-inner">
          <Link href="/" className="brand-lockup" style={{ textDecoration: "none" }}>
            <img
              src={getAssetPath(dark ? "/logo_dark.png" : "/logo.png")}
              alt="Airfare CPI Logo"
              className="brand-logo-img"
            />
            <span>
              <strong>Airfare CPI</strong>
              <small>India / MoSPI</small>
            </span>
          </Link>

          <div className="header-actions">
            <button
              className="icon-button"
              onClick={() => setDark((prev) => !prev)}
              aria-label="Toggle theme"
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            <Link href="/" className="button button-dark" style={{ textDecoration: "none" }}>
              <ArrowLeft size={15} /> Back to dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content matching Methodology & About reading layouts */}
      <main className="main-content">
        <div className="page-wrap page-wrap-reading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Terms of Service &amp; Usage Policy · NDSAP 2026</p>
              <h2>Terms of service</h2>
              <p className="section-description">
                Statutory open data usage license, academic citation requirements, API rate governance, and provisional status disclaimers.
              </p>
            </div>
            <span className="status-pill status-pill-success" style={{ height: "fit-content", padding: "6px 12px" }}>
              <Scale size={14} /> Open Data License
            </span>
          </div>

          <div className="about-hero">
            <div className="about-spotlight-card">
              <p className="eyebrow">Provisional Status Disclaimer</p>
              <h3>High-Frequency Experimental Price Indicator</h3>
              <p>
                All daily and high-frequency indices published on this dashboard are provisional research indicators designed to study big data augmentation of transport inflation. Official national macroeconomic statistics remain those released by the National Statistical Office (NSO) on the 12th of each month.
              </p>
            </div>
            <div>
              <p className="eyebrow">National Data Sharing Policy</p>
              <h3>Open data for researchers, policy desks, and the public.</h3>
              <p>
                Under the National Data Sharing and Accessibility Policy (NDSAP), index time series are accessible for open non-commercial research, econometric modeling, and economic analysis with statutory attribution.
              </p>
            </div>
          </div>

          <div className="methodology-grid">
            <article className="method-card">
              <span>01</span>
              <h3>Permitted Usage</h3>
              <p>
                Academic researchers, financial institutions, media desks, and the general public may query, compute, and republish index statistics for analytical, educational, and research purposes.
              </p>
            </article>

            <article className="method-card">
              <span>02</span>
              <h3>Required Attribution</h3>
              <p>
                Any published analysis or citation must reference: <em>&ldquo;Source: Ministry of Statistics &amp; Programme Implementation (MoSPI) — Airfare CPI Prototype, 2026.&rdquo;</em>
              </p>
            </article>

            <article className="method-card">
              <span>03</span>
              <h3>API Fair Use Limits</h3>
              <p>
                REST API queries via <code>/api/v1/</code> are governed by fair-use thresholds (10,000 requests/day). Automated polling scripts must respect HTTP 429 throttling headers.
              </p>
            </article>

            <article className="method-card">
              <span>04</span>
              <h3>Prohibited Misuse</h3>
              <p>
                Users are strictly prohibited from attempting to reverse-engineer commercial airline revenue management engines, scraping passenger portals, or engaging in ticket scalping.
              </p>
            </article>
          </div>

          <div className="formula-grid" style={{ marginTop: 24, marginBottom: 40 }}>
            <article className="formula-panel">
              <p className="eyebrow">Integrity &amp; No Warranty</p>
              <h3>As-is statistical indicator</h3>
              <p>
                While the engine enforces IQR outlier filtering, zero-fare validation, and Jevons geometric index chaining, the data is provided on an &ldquo;as-is&rdquo; basis for macroeconomic research without commercial travel guarantees.
              </p>
            </article>

            <article className="formula-panel formula-panel-dark">
              <p className="eyebrow">Statutory Jurisdiction</p>
              <h3>Governing Law</h3>
              <p>
                These Terms are governed by and construed in accordance with the laws of the Republic of India. Any disputes shall be subject to the exclusive jurisdiction of the competent courts of New Delhi, India.
              </p>
              <code style={{ background: "rgba(255,255,255,0.08)", color: "#9ac3a0" }}>
                Jurisdiction: New Delhi · Government of India (MoSPI)
              </code>
            </article>
          </div>
        </div>
      </main>

      {/* Site Footer matching application design */}
      <footer className="site-footer">
        <div>
          <Link href="/" className="footer-brand" style={{ textDecoration: "none" }}>
            <img src={getAssetPath(dark ? "/logo_dark.png" : "/logo.png")} alt="Airfare CPI Logo" className="brand-logo-img" />
            <span><strong>Airfare CPI</strong> <span>India / MoSPI</span></span>
          </Link>
          <p>Research prototype for transparent, real-time aviation price intelligence.</p>
        </div>
        <div className="footer-links">
          <Link href="/?tab=methodology">Methodology</Link>
          <Link href="/?tab=monitoring">API access</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
        </div>
        <span className="footer-meta">v1.0 / provisional · NDSAP 2026</span>
      </footer>
    </div>
  );
}
