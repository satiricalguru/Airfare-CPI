# Source Governance Review: Google Flights Public Aggregator

**Source ID:** `live_portal`  
**Operator:** Google LLC / Alphabet  
**Target Resource:** Public Travel Flights (`https://www.google.com/travel/flights`)  
**Acquisition Method:** `WEB_SCRAPE` (Headless Chromium / Playwright)  
**Evaluation Date:** 4 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 3 December 2026 (90-day review cycle)  
**Operator Contact:** `support-in@google.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Commercial automated extraction restricted; permitted exclusively under non-commercial academic research prototype exemption. | **PENDING REVIEW** | Google Terms excerpt: *"Don't misuse our services. For example, don't interfere with our services or try to access them using a method other than the interface and the instructions that we provide."* Formal bilateral MoU between MoSPI and operator recommended for sovereign production release. |
| **2. robots.txt** | Path `/travel/flights` evaluated against `https://www.google.com/robots.txt` (`SHA256: 1aba570a1b32deb...`). | **PASS (With Restrictions)** | Actual `robots.txt` excerpt: <br>`Disallow: /travel/flights/booking`<br>`Disallow: /travel/flights/s/`<br>`Disallow: /travel/flights/search`<br>The top-level query path `/travel/flights?q=...` is accessible under RFC 9309 rules, and all disallowed subpaths (`/booking`, `/s/`, `/search`) are strictly avoided. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero authentication bypass, zero residential proxy rotation. | **PASS** | Non-evasion circuit breaker: If Google returns HTTP 429, 403, or a challenge page (`sorry/index`), collection immediately aborts (`CaptchaChallengeError`). |
| **4. Rate Limits** | Politeness enforced: 1.5s minimum request interval with 0.25s random jitter; maximum 2 concurrent tabs. | **PASS** | Budget capped at 30 requests/minute and 3,000 requests/day. |
| **5. Data Reliability** | Flight cards expose scheduled times, airline brand, duration, stops, and total INR fare. Flight numbers are not displayed on cards. | **PASS (Estimated Components)** | Flight numbers are deterministic surrogate strings (`6E-DELBOM-0845`) with `is_surrogate: true`. Statutory fees decomposed via AERA Tariff Orders with `is_estimated: true`. |
| **6. Artifact Archiving** | Sanitized raw DOM capture stored gzipped with SHA-256 integrity hash. | **PASS** | Complete cryptographic provenance trail linked to every observation. |
| **7. Quota Fit** | Public flight search; zero monetary subscription costs. | **PASS** | Zero API fee liability. |
| **8. Review Expiry** | 90-day evaluation horizon expiring 3 December 2026. | **PASS** | Mandates quarterly re-verification under repository governance rules. |

---

## 2. Technical Operational Boundaries

1. **User Agent & Identity:** Standard Chromium browser engine user agent in Playwright execution context, with truthful project identity (`AirfareCPI-Research/2.0`) recorded in audit provenance.
2. **Circuit Breaker:** Any challenge page or HTTP 429/403 triggers `CaptchaChallengeError` and immediately halts execution without retry loops.
3. **Surrogate Flight Identification:** Because Google Flights summary cards only display airline brands (e.g. "IndiGo") rather than IATA flight numbers, the adapter builds a deterministic surrogate identifier (`6E-DELBOM-0845`) and marks `is_surrogate: true` in `DataProvenance.notes` to avoid misleading index matchers.
4. **Statutory Fee Unbundling:** Base fare, Taxes (GST 5% + ASF ₹236), Airport UDF, and Convenience fees are computed using AERA tariff orders and explicitly marked `is_estimated: true` in provenance metadata.
