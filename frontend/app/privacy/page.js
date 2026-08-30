"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  ShieldCheck
} from "lucide-react";
import { getAssetPath } from "../utils/assetPath";

export default function PrivacyPolicyPage() {
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
              <p className="eyebrow">Legal &amp; Regulatory Framework · DPDPA 2023</p>
              <h2>Privacy policy &amp; data governance</h2>
              <p className="section-description">
                Official data handling practices, zero-PII guarantees, and ethical web scraping protocols under the Ministry of Statistics &amp; Programme Implementation.
              </p>
            </div>
            <span className="status-pill status-pill-success" style={{ height: "fit-content", padding: "6px 12px" }}>
              <ShieldCheck size={14} /> DPDPA 2023 Compliant
            </span>
          </div>

          <div className="about-hero">
            <div className="about-spotlight-card">
              <p className="eyebrow">Statutory Data Policy</p>
              <h3>Zero Personally Identifiable Information (PII) Guarantee</h3>
              <p>
                The platform operates strictly as a statistical research engine. It neither collects, processes, nor retains passenger names, contact details, payment credentials, or booking PNRs. All ingestion is confined to public carrier quotations.
              </p>
            </div>
            <div>
              <p className="eyebrow">Institutional Mandate</p>
              <h3>Empirical measurement without citizen surveillance.</h3>
              <p>
                Price statistics measure the market, not the traveler. High-frequency price signals are derived from public airfare offers across 25 DGCA corridors to calculate unbiased Laspeyres-Jevons inflation indexes.
              </p>
            </div>
          </div>

          <div className="methodology-grid">
            <article className="method-card">
              <span>01</span>
              <h3>Mandate &amp; Scope</h3>
              <p>
                Governs data practices for the Real-Time Airfare CPI Augmentation Platform in support of MoSPI, Government of India, strictly for macroeconomic research and inflation measurement.
              </p>
            </article>

            <article className="method-card">
              <span>02</span>
              <h3>DPDPA Compliance</h3>
              <p>
                Full compliance with India’s Digital Personal Data Protection Act, 2023. No individual identity vectors are stored, queried, or processed at any stage of the data lifecycle.
              </p>
            </article>

            <article className="method-card">
              <span>03</span>
              <h3>Ethical Scraping</h3>
              <p>
                Polite crawl intervals, rate-limiting, and exponential backoff protect airline servers. No login walls, CAPTCHAs, or authenticated passenger portals are ever accessed.
              </p>
            </article>

            <article className="method-card">
              <span>04</span>
              <h3>Audit Provenance</h3>
              <p>
                Every observation carries an immutable cryptographic timestamp, carrier attribution, and horizon classification in an append-only audit ledger for statistical reproducibility.
              </p>
            </article>
          </div>

          <div className="formula-grid" style={{ marginTop: 24, marginBottom: 40 }}>
            <article className="formula-panel">
              <p className="eyebrow">Data Retention &amp; Storage</p>
              <h3>Encrypted ledger architecture</h3>
              <p>
                Raw observation tables are encrypted using TLS 1.3 in transit and AES-256 at rest within sovereign Indian cloud infrastructure. Elementary Jevons relatives and aggregated national index time-series are retained indefinitely for longitudinal research.
              </p>
            </article>

            <article className="formula-panel formula-panel-dark">
              <p className="eyebrow">Institutional Redressal</p>
              <h3>Price Statistics Division</h3>
              <p>
                For statistical inquiries, methodology clarifications, or data governance queries, contact the Price Statistics Division, National Statistical Office (NSO), MoSPI, New Delhi:
              </p>
              <code style={{ background: "rgba(255,255,255,0.08)", color: "#9ac3a0" }}>
                Email: price-statistics@mospi.gov.in · New Delhi, India
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
        <span className="footer-meta">v1.0 / provisional · DPDPA 2023</span>
      </footer>
    </div>
  );
}
