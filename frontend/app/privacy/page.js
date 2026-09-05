"use client";
/* eslint-disable @next/next/no-img-element */

import { useState, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  Sun, 
  Moon, 
  ShieldCheck
} from "lucide-react";
import { getAssetPath } from "../utils/assetPath";

const emptySubscribe = () => () => {};

export default function PrivacyPolicyPage() {
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
              <p className="eyebrow">Prototype privacy notice</p>
              <h2>Privacy policy &amp; data governance</h2>
              <p className="section-description">
                What this repository is designed to collect, what it does not need, and which deployment-specific controls remain the operator&apos;s responsibility.
              </p>
            </div>
            <span className="status-pill status-pill-success" style={{ height: "fit-content", padding: "6px 12px" }}>
              <ShieldCheck size={14} /> No compliance certification claimed
            </span>
          </div>

          <div className="about-hero">
            <div className="about-spotlight-card">
              <p className="eyebrow">Data minimisation</p>
              <h3>Passenger identity is outside the data model</h3>
              <p>
                The airfare observation schema does not require passenger names, contact details, payment credentials, booking accounts, or PNRs. Collection adapters should be limited to permitted fare-offer data and must never enter authenticated passenger areas.
              </p>
            </div>
            <div>
              <p className="eyebrow">Research purpose</p>
              <h3>Empirical measurement without citizen surveillance.</h3>
              <p>
                The prototype studies whether high-frequency fare quotations can support an experimental airfare price indicator. Its route weights and outputs are provisional and are not official CPI statistics.
              </p>
            </div>
          </div>

          <div className="methodology-grid">
            <article className="method-card">
              <span>01</span>
              <h3>Scope</h3>
              <p>
                This notice describes the repository&apos;s intended research data flow. It is not issued by, endorsed by, or affiliated with MoSPI, the NSO, or the Government of India.
              </p>
            </article>

            <article className="method-card">
              <span>02</span>
              <h3>Deployment responsibility</h3>
              <p>
                No legal-compliance certification is made here. A deployment operator must assess applicable privacy, security, retention, provider-contract, and data-protection obligations before operation.
              </p>
            </article>

            <article className="method-card">
              <span>03</span>
              <h3>Ethical Scraping</h3>
              <p>
                Adapters are expected to use permitted access, bounded concurrency, retry backoff, and source-specific rate controls. CAPTCHA or login-wall bypass is not part of this project.
              </p>
            </article>

            <article className="method-card">
              <span>04</span>
              <h3>Audit Provenance</h3>
              <p>
                Every stored observation carries collection time, source type/name, request ID, product key, and validation metadata. The current database is persistent, but is not claimed to be an immutable append-only ledger.
              </p>
            </article>
          </div>

          <div className="formula-grid" style={{ marginTop: 24, marginBottom: 40 }}>
            <article className="formula-panel">
              <p className="eyebrow">Data Retention &amp; Storage</p>
              <h3>Retention and infrastructure</h3>
              <p>
                This repository does not prescribe a hosting provider, encryption-at-rest product, or retention period. Those controls must be configured and documented by each operator. Avoid retaining raw data longer than the research and audit purpose requires.
              </p>
            </article>

            <article className="formula-panel formula-panel-dark">
              <p className="eyebrow">Questions and corrections</p>
              <h3>Project maintainer</h3>
              <p>
                Use the repository&apos;s maintainer or issue tracker for methodology, security, privacy, and data-correction questions. No government contact address is represented by this prototype.
              </p>
              <code style={{ background: "rgba(255,255,255,0.08)", color: "#9ac3a0" }}>
                Contact: repository maintainer / project issue tracker
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
        <span className="footer-meta">prototype · no compliance certification</span>
      </footer>
    </div>
  );
}
