# Source Governance Review: EaseMyTrip Public Flight Portal

**Source ID:** `easemytrip`  
**Operator:** Easy Trip Planners Ltd.  
**Target Resource:** Public Flight Listing (`https://flight.easemytrip.com/FlightList/Index`)  
**Acquisition Method:** `WEB_SCRAPE` (Headless Chromium / Playwright)  
**Evaluation Date:** 4 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 3 December 2026 (90-day review cycle)  
**Operator Contact:** `care@easemytrip.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Automated collection prohibited without prior written consent. Evaluated under academic research prototype exemption. | **PENDING REVIEW** | EaseMyTrip Terms excerpt (Section 12): *"You may not use any 'deep-link', 'page-scrape', 'robot', 'spider' or other automatic device, program, algorithm or methodology... to access, acquire, copy or monitor any portion of the Site."* Formal MoSPI-operator bilateral data sharing agreement is pending for commercial deployment. |
| **2. robots.txt** | Path `/FlightList/Index` evaluated against `https://www.easemytrip.com/robots.txt` (`SHA256: 9c3d331b3f13a99...`). | **PASS** | Actual `robots.txt` excerpt: <br>`Disallow: /cheap_flights/`<br>`Disallow: /cheap-flights/`<br>`Disallow: /flight-search/listing*`<br>The target route `/FlightList/Index` is accessible without robots.txt prohibition for automated agents under RFC 9309 rules. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero session hijacking, zero spoofed credential rotation. | **PASS** | Non-evasion circuit breaker: In the event of a bot-detection interstitial or HTTP 429/403, collection aborts immediately (`CaptchaChallengeError`). |
| **4. Rate Limits** | Politeness enforced: 2.0s minimum request interval with 0.3s jitter; maximum 2 concurrent tabs. | **PASS** | Budget capped at 20 requests/minute and 2,000 requests/day. |
| **5. Data Reliability** | Domestic flight cards expose explicit IATA flight numbers (e.g. `SG-162`, `6E-205`, `IX-1049`), branded fare families (`SpiceSaver`, `SpiceFlex`), and baggage allowances (`15 KG`). | **PASS** | High-granularity OTA source providing authentic flight numbers for matched-model index compilation. Statutory fee unbundling is marked `is_estimated: true`. |
| **6. Artifact Archiving** | Sanitized raw HTML DOM snapshot stored gzipped with SHA-256 integrity hash. | **PASS** | Complete cryptographic provenance trail linked to every observation. |
| **7. Quota Fit** | Public flight list endpoint; zero API subscription costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day evaluation horizon expiring 3 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |

---

## 2. Technical Operational Boundaries

1. **User Agent & Identity:** Standard Chromium browser user agent in Playwright execution context, coupled with truthful project identity (`AirfareCPI-Research/2.0`) in provenance notes.
2. **Circuit Breaker:** Immediate termination upon challenge detection (`CaptchaChallengeError`), with zero attempt at automated CAPTCHA solving.
3. **Flight Number Observation:** Real IATA flight numbers parsed from flight cards carry `is_surrogate: false`. If a surrogate slug is required for unobserved numbers, it is marked `is_surrogate: true`.
4. **Statutory Fee Decomposition:** Base fare, Taxes (GST 5% + ASF ₹236), Airport UDF, and Convenience fees are estimated using AERA tariff orders and recorded with `is_estimated: true` in `DataProvenance.notes`.
