# Source Governance Review: FastFlights Engine (Google Flights RPC)

**Source ID:** `fast_flights`  
**Operator:** Public Aviation Metasearch / SIH26056 Research Team  
**Target Resource:** Flight Search RPC (`https://www.google.com/travel/flights`)  
**Acquisition Method:** `WEB_SCRAPE` (Direct Protobuf RPC Client)  
**Evaluation Date:** 7 September 2026  
**Status:** `PENDING_FORMAL_REVIEW` (Conditional Academic & Statistical Research Prototype)  
**Review Expiry:** 7 December 2026 (90-day review cycle)  
**Operator Contact:** `support-in@google.com`  

---

## 1. Governance Evaluation Summary

| Gate | Assessment | Status | Transparent Audit Evidence |
|---|---|:---:|---|
| **1. Legal Terms** | Direct RPC flight search evaluated under Academic Research Prototype Exemption. | **PENDING REVIEW** | Non-commercial research data evaluation. |
| **2. robots.txt** | Target query paths evaluated against Google Flights `robots.txt`. | **PASS** | Evaluated under RFC 9309 rules with approved query path restriction. |
| **3. Non-Circumvention** | Zero browser footprint, zero CAPTCHA solving, polite request cadence. | **PASS** | High-speed structured RPC client. |
| **4. Rate Limits** | Politeness enforced: 1.5s interval, max 30 requests/minute, 3,000/day. | **PASS** | Polite research rate limits. |
| **5. Data Reliability** | Comprehensive coverage of IndiGo, Air India, SpiceJet, Akasa Air, Air India Express. | **PASS** | Complete domestic airline coverage. |
| **6. Artifact Archiving** | Serialized response payload stored with SHA-256 integrity hash. | **PASS** | Full cryptographic provenance. |
| **7. Quota Fit** | Public endpoint; zero API costs. | **PASS** | Zero monetary cost. |
| **8. Review Expiry** | 90-day review horizon expiring 7 December 2026. | **PASS** | Enforces mandatory quarterly governance review. |
