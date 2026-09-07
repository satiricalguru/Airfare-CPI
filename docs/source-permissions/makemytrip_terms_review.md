# Source Governance Review: MakeMyTrip Domestic Flight Portal

**Source ID:** `makemytrip`  
**Operator:** MakeMyTrip (India) Private Limited  
**Target Resource:** Flight Search (`https://www.makemytrip.com/flight/search`)  
**Acquisition Method:** `WEB_SCRAPE` (Playwright / Scrapy Interception)  
**Evaluation Date:** 7 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 7 December 2026 (90-day review cycle)  
**Operator Contact:** `legal@makemytrip.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Automated retrieval requires written consent. Evaluated under academic research prototype exemption. | **PENDING REVIEW** | MMT Terms restrict unauthorized automated harvesting. Bilateral data sharing requested for official index compilation. |
| **2. robots.txt** | Path `/flight/search` evaluated against `https://www.makemytrip.com/robots.txt`. | **PASS** | Evaluated under RFC 9309 rules with approved query path restriction. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero evasion plugins, immediate circuit breaker on bot challenge. | **PASS** | Aborts immediately on Akamai challenge. |
| **4. Rate Limits** | Politeness enforced: 2.0s minimum interval, max 20 requests/minute, 2,000/day. | **PASS** | Polite research rate limits. |
| **5. Data Reliability** | Flight listing exposes exact carrier codes, flight numbers, fare families, baggage, and seat availability. | **PASS** | High granularity empirical quotes. |
| **6. Artifact Archiving** | Sanitized DOM/XHR JSON response stored with SHA-256 integrity hash. | **PASS** | Full cryptographic provenance. |
| **7. Quota Fit** | Public flight list endpoint; zero API subscription costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day review horizon expiring 7 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |
