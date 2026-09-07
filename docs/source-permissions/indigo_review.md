# Source Governance Review: IndiGo Airline Portal

**Source ID:** `indigo`  
**Operator:** InterGlobe Aviation Limited  
**Target Resource:** Booking Engine (`https://www.goindigo.in/booking/flight-select.html`)  
**Acquisition Method:** `WEB_SCRAPE` (Navitaire dotrez adapter / Playwright)  
**Evaluation Date:** 7 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 7 December 2026 (90-day review cycle)  
**Operator Contact:** `corporate@goindigo.in`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Direct consumer booking engine evaluated under research prototype exemption. | **PENDING REVIEW** | Bilateral research request submitted to InterGlobe Aviation. |
| **2. robots.txt** | Path `/booking/` evaluated against `goindigo.in/robots.txt`. | **PASS** | Evaluated under RFC 9309 rules with approved query path restriction. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero evasion plugins, immediate circuit breaker on challenge. | **PASS** | Aborts immediately on challenge. |
| **4. Rate Limits** | Politeness enforced: 2.0s minimum interval, max 20 requests/minute, 2,000/day. | **PASS** | Polite research rate limits. |
| **5. Data Reliability** | Real 6E flight numbers, Saver/Flexi fare families, passenger fees, seat availability. | **PASS** | Primary airline operator source. |
| **6. Artifact Archiving** | Sanitized DOM/XHR JSON response stored with SHA-256 integrity hash. | **PASS** | Full cryptographic provenance. |
| **7. Quota Fit** | Direct airline portal search; zero API subscription costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day review horizon expiring 7 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |
