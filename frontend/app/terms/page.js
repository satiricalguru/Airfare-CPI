"use client";
/* eslint-disable @next/next/no-img-element */

import { useState, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  Scale
} from "lucide-react";
import { getAssetPath } from "../utils/assetPath";

const emptySubscribe = () => () => {};

export default function TermsOfServicePage() {
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const saved = window.localStorage.getItem("airfare_cpi_theme");
      if (saved) return saved === "dark";
      return document.documentElement.classList.contains("dark");
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (!mounted) return;
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("light", !dark);
    try {
      window.localStorage.setItem("airfare_cpi_theme", dark ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }, [dark, mounted]);

  return (
    <div className="app-shell">
      {/* Site Header matching application design */}
      <header className="site-header">
        <div className="header-inner">
          <Link href="/" className="brand-lockup" style={{ textDecoration: "none" }}>
            <img
              src={getAssetPath(mounted && dark ? "/logo_dark.png" : "/logo.png")}
              alt="Airfare CPI Logo"
              className="brand-logo-img"
              suppressHydrationWarning
            />
            <span>
              <strong>Airfare CPI</strong>
              <small>SIH26056 research prototype</small>
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
              <p className="eyebrow">Prototype use notice</p>
              <h2>Use and limitations</h2>
              <p className="section-description">
                Research-use guidance, provenance requirements, provider constraints, and limitations of the experimental API and index.
              </p>
            </div>
            <span className="status-pill status-pill-success" style={{ height: "fit-content", padding: "6px 12px" }}>
              <Scale size={14} /> Experimental output
            </span>
          </div>

          <div className="about-hero">
            <div className="about-spotlight-card">
              <p className="eyebrow">Provisional Status Disclaimer</p>
              <h3>High-Frequency Experimental Price Indicator</h3>
              <p>
                All daily and high-frequency values shown here are provisional research indicators. They are not official statistics and must not be presented as issued, endorsed, or validated by any government body.
              </p>
            </div>
            <div>
              <p className="eyebrow">Research access</p>
              <h3>Use only with provenance and limitations attached.</h3>
              <p>
                Repository source code is governed by its included software license. Fare observations and provider-derived fields can be subject to separate source terms; this page does not grant rights that the project does not own.
              </p>
            </div>
          </div>

          <div className="methodology-grid">
            <article className="method-card">
              <span>01</span>
              <h3>Permitted Usage</h3>
              <p>
                The API may be used for testing, education, and research where applicable law and source terms permit. Consumers must preserve the data-provenance label and experimental-status disclaimer.
              </p>
            </article>

            <article className="method-card">
              <span>02</span>
              <h3>Attribution</h3>
              <p>
                Do not attribute this project to MoSPI, the NSO, or the Government of India. Cite the SIH26056 Airfare CPI research prototype and identify whether the data was live, simulated, or offline.
              </p>
            </article>

            <article className="method-card">
              <span>03</span>
              <h3>API availability</h3>
              <p>
                No public uptime, retention, or request-quota guarantee is offered. Read endpoints are public in the reference app; mutation endpoints require the configured administrator token and fail closed when it is absent.
              </p>
            </article>

            <article className="method-card">
              <span>04</span>
              <h3>Prohibited Misuse</h3>
              <p>
                Do not use the project to bypass access controls, CAPTCHAs, robots restrictions, provider rate limits, or contractual terms; access passenger accounts; interfere with source systems; or misrepresent simulated data as observed data.
              </p>
            </article>
          </div>

          <div className="formula-grid" style={{ marginTop: 24, marginBottom: 40 }}>
            <article className="formula-panel">
              <p className="eyebrow">Integrity &amp; No Warranty</p>
              <h3>As-is statistical indicator</h3>
              <p>
                Data and indices are provided on an &ldquo;as-is&rdquo; experimental basis. Coverage gaps, quote changes, product churn, provider outages, provisional weights, and methodology revisions can materially affect results.
              </p>
            </article>

            <article className="formula-panel formula-panel-dark">
              <p className="eyebrow">No institutional affiliation</p>
              <h3>Research prototype</h3>
              <p>
                This page is a factual project-use notice, not a government-issued statutory license or a substitute for legal advice. Deployment operators must provide their own legally reviewed terms where required.
              </p>
              <code style={{ background: "rgba(255,255,255,0.08)", color: "#9ac3a0" }}>
                Status: independent SIH26056 research prototype
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
            <span><strong>Airfare CPI</strong> <span>SIH26056 prototype</span></span>
          </Link>
          <p>Research prototype for transparent, real-time aviation price intelligence.</p>
        </div>
        <div className="footer-links">
          <Link href="/?tab=methodology">Methodology</Link>
          <Link href="/?tab=monitoring">API access</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
        </div>
        <span className="footer-meta">prototype · as-is research output</span>
      </footer>
    </div>
  );
}
