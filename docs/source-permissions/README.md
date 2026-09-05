# Source Access Governance & Permissions

**Repository:** SIH26056 Real-Time Airfare CPI Prototype  
**Date:** 3 September 2026  
**Status:** Active Governance Framework  

---

## 1. Core Governance Constraint

Under the SIH26056 implementation plan:

1. **Access to a public website is NOT automatically permission to scrape it.**
2. A portal adapter (`acquisition_method: WEB_SCRAPE`) may be enabled **only** after its source record passes the access gates defined in `data/source_access_registry.yaml`.
3. Air India and MakeMyTrip published terms of use explicitly prohibit automated extraction without express prior written consent. Those candidate sources therefore remain **disabled** until written authorization is received.
4. Documented external APIs (such as Amadeus Self-Service) are categorized as `acquisition_method: API` and must never be represented as web-scraped portal data.
5. Simulated data and offline fixtures are categorized as `acquisition_method: SIMULATED` and `OFFLINE_FIXTURE` and remain excluded from any empirical index.

---

## 2. Source Access Gates

Before any automated network request is issued to an external portal, the source must pass all 8 access gates:

| Gate | Requirement |
|---|---|
| **1. Legal Terms** | The portal terms permit automated research collection, OR an express written authorization has been received and archived here. |
| **2. robots.txt** | The relevant search and quote paths are not disallowed by the domain's `robots.txt`. |
| **3. No Circumvention** | No login wall, CAPTCHA bypass, residential proxy rotation, or device fingerprint spoofing is used. |
| **4. Rate Limits** | An agreed maximum request rate (per-minute and per-day) and an honest project User-Agent with contact information are declared. |
| **5. Data Reliability** | The page exposes the required fare fields (base, taxes, total, flight identity, booking horizon) consistently. |
| **6. Fixture Verification** | A sanitized raw capture and deterministic parser test suite are committed to git. |
| **7. Free Quota Fit** | The projected daily request budget fits within zero-cost operation without overage. |
| **8. Current Review** | The registry entry has not expired and the SHA-256 hashes of the terms and robots.txt have not changed. |

---

## 3. Candidate Source Status Matrix

| Source ID | Operator | Kind | Acquisition Method | Status | Reason |
|---|---|---|---|---|---|
| `air_india` | Air India Ltd | Airline | `WEB_SCRAPE` | `PROHIBITED_WITHOUT_PERMISSION` | Terms require express written permission. Disabled. |
| `makemytrip` | MakeMyTrip India Pvt Ltd | OTA | `WEB_SCRAPE` | `PROHIBITED_WITHOUT_PERMISSION` | Terms require prior written consent. Disabled. |
| `indigo` | InterGlobe Aviation Ltd | Airline | `WEB_SCRAPE` | `PENDING_FORMAL_REVIEW` | Reviewing terms & robots.txt; request pending. Disabled. |
| `amadeus` | Amadeus IT Group | API | `API` | `AVAILABLE_AFTER_FREE_REGISTRATION` | Documented REST API. Labelled as API-COLLECTED DATA. |
| `simulator` | SIH Team | Test | `SIMULATED` | `NON_EMPIRICAL` | Calibration and pipeline testing only. |
| `offline_fixture` | SIH Team | Test | `OFFLINE_FIXTURE` | `NON_EMPIRICAL` | Deterministic offline replay. |

---

## 4. Formal Research Permission Request Template

The following letter must be dispatched to airline/OTA legal and commercial teams when requesting automated access authorization for research/academic purposes:

```text
Subject: Research Permission Request: Automated Airfare Quotation Study (SIH26056)

Dear [Airline/OTA Representative / Legal Team],

We are a student engineering team participating in the Smart India Hackathon 2026 (SIH26056: Real-Time Airfare Price Index Prototype for Academic and Statistical Research).

We are writing to request formal authorization to periodically collect public, anonymous airfare quotations from your web portal ([portal homepage URL]) strictly for statistical index research.

Details of our proposed automated collection:
1. Nature of Queries: Single adult, one-way, economy class flight availability on select domestic trunk routes (e.g., DEL-BOM, DEL-BLR, BOM-BLR).
2. Anonymous & Non-Transactional: No user accounts are created, no logins attempted, no seats booked, no personal data submitted.
3. Frequency & Rate Limits: Bounded at a maximum of 2 requests per minute and no more than 60 requests per day, scheduled during off-peak hours (10:00 and 18:00 IST).
4. Identification: Our HTTP requests will clearly declare our research user agent:
   "Mozilla/5.0 (compatible; SIH26056AirfareCPI/2.0; +https://github.com/...; contact: [team email])"
5. Data Protection: Fares collected are normalized into aggregate statistical indices (Jevons elementary aggregates). Raw captures redact all session tokens and cookies.
6. Zero Commercial Use: This project is strictly academic, non-commercial research.

Could you please confirm if your organization can grant written permission or provide an academic sandbox endpoint for this research?

Thank you for your consideration.

Sincerely,
SIH26056 Research Team
[Contact details]
```

---

## 5. Review Expiry & Change Detection

1. Source reviews expire every **90 days**.
2. Before each collection cycle or release, automated canary tests verify that the SHA-256 hash of the portal's `robots.txt` and `terms.html` match the values recorded in `data/source_access_registry.yaml`.
3. Any drift in hashes immediately transitions the source to `REVIEW_REQUIRED` and pauses collection.
