# Source Governance Review: SpiceJet Airline Portal

**Source ID:** `spicejet`  
**Operator:** SpiceJet Limited  
**Target Resource:** Booking Engine (`https://www.spicejet.com`)  
**Acquisition Method:** `WEB_SCRAPE` (Navitaire web engine / Playwright)  
**Evaluation Date:** 7 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 7 December 2026 (90-day review cycle)  
**Operator Contact:** `custrelations@spicejet.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Evaluated under research prototype exemption. | **PENDING REVIEW** | Bilateral research request submitted. |
| **2. robots.txt** | Target query paths evaluated against `spicejet.com/robots.txt`. | **PASS** | Evaluated under RFC 9309 rules with approved query path restriction. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero evasion plugins, immediate circuit breaker. | **PASS** | Aborts immediately on challenge. |
| **4. Rate Limits** | Politeness enforced: 2.0s minimum interval, max 20 requests/minute, 2,000/day. | **PASS** | Polite research rate limits. |
| **5. Data Reliability** | Real SG flight numbers, base fare, baggage allowances, timings. | **PASS** | Direct carrier data. |
| **6. Artifact Archiving** | Sanitized DOM/XHR JSON response stored with SHA-256 integrity hash. | **PASS** | Full cryptographic provenance. |
| **7. Quota Fit** | Direct airline portal search; zero API subscription costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day review horizon expiring 7 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |
