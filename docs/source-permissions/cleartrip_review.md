# Source Governance Review: Cleartrip Flight Portal

**Source ID:** `cleartrip`  
**Operator:** Cleartrip Private Limited (Flipkart Group)  
**Target Resource:** Flight Results (`https://www.cleartrip.com/flights/results`)  
**Acquisition Method:** `WEB_SCRAPE` (Playwright / Next.js Hydration Extractor)  
**Evaluation Date:** 7 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 7 December 2026 (90-day review cycle)  
**Operator Contact:** `support@cleartrip.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Evaluated under non-commercial academic research prototype exemption. | **PENDING REVIEW** | Cleartrip consumer terms require authorization for commercial data aggregation. Formal MoU pending. |
| **2. robots.txt** | Target query paths evaluated against `cleartrip.com/robots.txt`. | **PASS** | Evaluated under RFC 9309 rules with approved query path restriction. |
| **3. Non-Circumvention** | Zero CAPTCHA solving, zero evasion plugins, immediate circuit breaker. | **PASS** | Aborts immediately on challenge. |
| **4. Rate Limits** | Politeness enforced: 2.0s minimum interval, max 20 requests/minute, 2,000/day. | **PASS** | Polite research rate limits. |
| **5. Data Reliability** | Domestic flight cards expose exact carrier codes, flight numbers, fare families, and timings. | **PASS** | High granularity empirical quotes. |
| **6. Artifact Archiving** | Sanitized DOM/XHR JSON response stored with SHA-256 integrity hash. | **PASS** | Full cryptographic provenance. |
| **7. Quota Fit** | Public flight list endpoint; zero API subscription costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day review horizon expiring 7 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |
