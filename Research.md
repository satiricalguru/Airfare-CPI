# Deep Research Prompt: SIH26056 — Real-Time Airfare Price Index for MoSPI

Conduct a **deep, technically rigorous research study** of Smart India Hackathon problem statement **SIH26056 — Real-Time Airfare Price Index (MoSPI)**.

The goal is to determine exactly how to build a statistically defensible, engineering-feasible prototype that continuously collects domestic airfare data and converts it into a **route-level and national Consumer Price Index (CPI) for air travel**.

Base the research primarily on authoritative sources such as **MoSPI, PIB, DGCA, ILO/IMF CPI manuals, Statistics Canada, UK ONS, Australian Bureau of Statistics, airline/airfare pricing literature, and relevant government datasets**. Clearly separate verified facts from assumptions, recommendations, and proposed engineering choices.

## 1. Problem Definition

Explain SIH26056 precisely:

* What MoSPI is asking the team to build.
* Why airfare is difficult to measure using conventional price-collection methods.
* Why web scraping and alternative data sources are relevant to India's CPI modernization.
* How a real-time airfare index could fit into MoSPI's new CPI framework.
* Identify the expected outputs, frequency, geography, and statistical purpose of the index.

The research briefing describes the problem as an automated system covering roughly **20–30 high-traffic domestic routes**, multiple airlines/OTAs, and standardized booking horizons, producing a route-level micro-index that is aggregated into a national airfare CPI using DGCA passenger volumes.

## 2. MoSPI CPI Modernization Context

Research and verify:

* India's current CPI data-collection methodology.
* MoSPI's new CPI series and its base year.
* MoSPI's planned use of alternative data sources.
* The role of web scraping, scanner data, e-commerce data, ticketing data, rail fares and OTT prices.
* Whether airfare data is actually intended to be incorporated into the new CPI system.
* Expected implementation/publication timelines.
* Existing government initiatives or pilots involving automated price collection.

The provided research states that MoSPI has been exploring web scraping and scanner data for airfare, rail and OTT prices and describes SIH26056 as closely aligned with this modernization effort. Verify these claims against primary government sources rather than assuming the briefing is correct.

## 3. Airfare Data Acquisition Architecture

Design a complete data-ingestion architecture.

### Routes

Research how to select the **20–30 most representative domestic city-pair routes**.

Investigate:

* DGCA city-pair passenger-volume statistics.
* Directional versus non-directional routes.
* Route ranking by passenger traffic.
* Whether routes should be selected nationally, regionally, or by passenger volume.
* How frequently the route basket should be reviewed.
* How to handle new routes and discontinued routes.

The source briefing identifies high-volume corridors such as **DEL–BOM, BLR–DEL and MAA–CCU** and proposes using DGCA passenger traffic to identify representative routes.

### Sellers

Research collection from:

* Airline websites.
* Online travel agencies.
* Other legally accessible airfare sources.

Evaluate examples including:

* IndiGo
* Air India
* SpiceJet
* Major OTAs

For each source determine:

* Availability of public fare information.
* URL/search architecture.
* Dynamic JavaScript requirements.
* DOM instability.
* Session requirements.
* CAPTCHA/bot protection.
* Rate limits.
* Robots.txt.
* Terms of service.
* Legal/ethical scraping limitations.
* Whether API access exists.
* Whether scraping can be performed sustainably.

Do not recommend bypassing security systems or violating access controls.

## 4. Booking-Window Methodology

Research the statistical importance of the **advance-purchase window**.

Analyze these proposed horizons:

* T+0
* T+3
* T+7
* T+15
* T+30

Determine whether these horizons are statistically justified.

Study airline dynamic-pricing research concerning advance-purchase thresholds such as:

* 3 days
* 7 days
* 14 days
* 21 days

Explain how booking-window stratification captures airline revenue-management effects and prevents the CPI from confusing advance-purchase prices with last-minute fares.

The source briefing specifically argues that booking-window stratification is the statistically novel component and that the proposed grid brackets important advance-purchase pricing thresholds.

## 5. Fare Observation Definition

Define exactly what constitutes one airfare observation.

Research and recommend treatment of:

* Departure date
* Search date/time
* Booking horizon
* Origin
* Destination
* Airline
* Flight number
* Cabin class
* Fare family
* Refundability
* Baggage allowance
* Taxes
* Fees
* Seat selection charges
* Ancillary charges
* Currency
* Round-trip versus one-way
* Direct versus connecting flights

Determine whether the CPI should use:

* Advertised base fare
* Fare including taxes
* All-in mandatory consumer price
* Fare plus standardized ancillary basket

Explain the statistical and practical implications of each.

## 6. Dynamic Pricing and Data Normalization

Research how to make airfare observations comparable when airlines sell heterogeneous products.

Address:

* Different departure times.
* Different flight durations.
* Direct versus connecting flights.
* Different aircraft.
* Fare classes.
* Fare families.
* Baggage differences.
* Refund restrictions.
* Seat availability.
* Promotional fares.
* Temporary discounts.
* Dynamic price changes within a day.

Develop a normalization framework that minimizes changes in product quality being mistaken for inflation.

## 7. Scraping / Automation Engineering

Design the scraping system using tools such as:

* Playwright
* Scrapy
* Headless browsers
* Proxy infrastructure where legally permissible
* User-agent management
* Scheduler/orchestrator
* Retry mechanisms
* Selector versioning
* Failure detection
* Logging
* Monitoring

Research how to make the scraper resilient to:

* DOM changes
* JavaScript rendering changes
* Temporary outages
* CAPTCHA
* Rate limits
* Session expiration
* Anti-bot mechanisms
* Schema changes

The briefing emphasizes that the main engineering challenge is not simply writing a scraper but maintaining it over time through selector versioning and failure alerting.

## 8. Route-Level CPI — Jevons Index

Deeply research **Jevons price indices**.

Explain:

* Formula.
* Mathematical intuition.
* Why the geometric mean is useful.
* Why it is appropriate for elementary CPI aggregates.
* How it differs from Carli.
* How it differs from Dutot.
* Treatment of missing observations.
* Treatment of replacements.
* Treatment of zero prices.
* Treatment of extreme price changes.
* Whether the index should be computed across airlines, flights, or matched observations.

The briefing proposes a route-level Jevons index using price relatives:

I(r,t) = [Πᵢ (pᵢ,t / pᵢ,0)]^(1/n)

and argues that Jevons is less sensitive to extreme airfare observations than arithmetic alternatives.

Use the ILO/IMF CPI Manual and national statistical agencies to independently verify this methodology.

## 9. National Aggregation — Laspeyres / Young / Lowe

Research how route-level elementary indices should be aggregated.

Investigate:

* Laspeyres index.
* Young index.
* Lowe index.
* Fixed versus updated weights.
* Base-period weights.
* Expenditure weights versus passenger-volume weights.
* Passenger count as a proxy for expenditure share.
* Whether DGCA passenger volumes are sufficient.
* Whether average fares should be used to construct expenditure weights.
* Directional versus route-level weights.

The briefing proposes using DGCA city-pair passenger volumes as route weights and a Laspeyres/Young-type upper-level aggregation.

Critically evaluate whether **passenger volume is statistically equivalent to CPI expenditure weight**, and identify any methodological limitations.

## 10. DGCA Dataset Research

Research DGCA's city-pair traffic data in depth.

Determine:

* Exact datasets available.
* Historical coverage.
* Update frequency.
* Passenger-volume fields.
* Directionality.
* Airline-level fields.
* Route-level fields.
* Missing-value patterns.
* Download/API availability.
* Licensing/usage constraints.

Explain how to convert DGCA passenger counts into normalized weights:

wᵣ = passenger volume for route r / total passenger volume across selected routes

and how those weights would feed into the national index.

## 11. Base Period

Determine the appropriate base period.

Research:

* How CPI base years are selected.
* What base month should be used for an airfare micro-index.
* Whether the system should maintain a monthly or daily base.
* How rebasing should work.
* How to prevent a new base from destroying historical comparability.

Design an explicit base-period strategy for a hackathon prototype.

## 12. Sampling Frequency

Determine whether the index should collect fares:

* Daily
* Multiple times daily
* Hourly
* At fixed times
* At randomized times

Analyze the trade-off between:

* Statistical representativeness
* Scraping cost
* Website load
* Volatility
* Infrastructure complexity

Recommend the most defensible collection frequency for a SIH prototype.

## 13. Missing Data and Route Entry/Exit

Develop methodology for:

* Missing fares.
* Temporarily unavailable flights.
* Sold-out fares.
* Airline disappearance.
* New airlines.
* New routes.
* Cancelled routes.
* Seasonal routes.
* Route substitutions.
* Flight number changes.
* Structural breaks.

The briefing identifies **route entry/exit and weighting** as two of the actual difficult parts of SIH26056, even though the formulas themselves are textbook.

## 14. Outlier and Anomaly Handling

Research statistical treatment of:

* Extreme fare spikes.
* Festival pricing.
* Disruption pricing.
* Flash sales.
* Data-entry errors.
* Scraping errors.
* Unusually cheap promotional fares.
* Sudden route-wide price changes.

Determine when a price change should be:

1. Preserved as genuine market movement.
2. Flagged as an anomaly.
3. Excluded as bad data.

Do not automatically remove genuine airfare volatility merely because it looks extreme.

## 15. Real-Time Index Architecture

Design the complete backend architecture:

Input:

Airline/OTA fare sources
↓
Scraping engine
↓
Raw fare store
↓
Validation / normalization
↓
Booking-window classification
↓
Route-level aggregation
↓
Jevons calculation
↓
DGCA weighting
↓
National Airfare CPI
↓
Database
↓
API
↓
Dashboard / reports

Specify suitable technologies for:

* Scraping
* Scheduling
* Backend API
* Database
* Statistical computation
* Monitoring
* Visualization
* Report generation

The briefing recommends a stack around **Playwright/Scrapy + FastAPI + PostgreSQL + Next.js/Streamlit**, with PostgreSQL particularly suited to structured time-series fare records at prototype scale.

## 16. Database Schema

Design a normalized database schema for:

### Routes

* route_id
* origin
* destination
* airport codes
* weight
* effective dates

### Fare observations

* observation_id
* timestamp
* airline
* route
* flight
* departure date
* booking horizon
* fare
* taxes
* total price
* cabin
* fare family
* availability

### Index tables

* route index
* route weight
* national index
* base period
* index version

### Scraper monitoring

* source
* timestamp
* status
* selector version
* error type
* retry count

## 17. Dashboard

Design a professional dashboard containing:

* Current national Airfare CPI.
* Route-level indices.
* Route heatmap.
* Fare trends.
* Booking-window comparison.
* Airline comparison.
* Inflation versus base period.
* Daily/weekly/monthly movement.
* Anomaly alerts.
* Data-collection health.
* Scraper success/failure rates.

The briefing specifically identifies **real-time route heatmaps, base-year inflation comparisons, surge-anomaly detection, and automated MoSPI-format monthly reports** as useful dashboard outputs.

## 18. Automated Reporting

Design a monthly report containing:

* National airfare CPI.
* Month-on-month change.
* Year-on-year change.
* Route contributions.
* Major fare increases.
* Major fare decreases.
* Booking-window effects.
* Data-quality statistics.
* Missing observations.
* Scraper health.
* Methodological notes.

Explain how this could be exported into a format suitable for a statistical organization such as MoSPI.

## 19. Statistical Validation

Develop a validation framework.

Compare the prototype index against:

* Historical airfare trends.
* Alternative public airfare indicators.
* Airline fare movements.
* Known festival/holiday periods.
* Major disruptions.
* Major fuel-price events if relevant.

Test:

* Stability.
* Sensitivity.
* Reproducibility.
* Robustness to missing data.
* Robustness to outliers.
* Route-basket changes.
* Weight changes.
* Booking-window changes.

Create synthetic-data tests for the index before using live scraped data.

## 20. Legal, Ethical and Operational Risks

Research:

* Terms of service.
* Robots.txt.
* Copyright.
* Database rights.
* Personal-data considerations.
* Rate limiting.
* Automated access restrictions.
* Responsible scraping practices.

Do not propose methods for bypassing authentication, CAPTCHA, access controls, or technical protections.

Explain how a hackathon prototype can remain compliant while demonstrating the concept.

## 21. Real-Time Data Challenge

Explicitly investigate:

**How can we obtain real-time airfare data reliably and legally?**

Compare:

* Airline websites.
* OTA websites.
* Public APIs.
* Commercial airfare APIs.
* Government datasets.
* Synthetic/mock data.
* Browser automation.
* Partner feeds.

For each source provide:

* Cost
* Freshness
* Reliability
* Coverage
* Legal considerations
* Ease of integration
* Suitability for a hackathon prototype

Identify a **fallback architecture** in case live scraping becomes unreliable.

## 22. Prototype Strategy for SIH

Separate the system into:

### MVP

What can realistically be demonstrated during SIH?

### Strong Prototype

What should be added to make the system statistically credible?

### Production-Ready Version

What would be required for actual government deployment?

Prioritize engineering effort according to impact.

## 23. Demo Strategy

Design a compelling SIH final-round demonstration.

The demo should show:

1. Live fare collection.
2. Raw observation entering the pipeline.
3. Data validation.
4. Booking-window classification.
5. Route-level Jevons calculation.
6. DGCA weighting.
7. National CPI update.
8. Heatmap visualization.
9. Anomaly detection.
10. Automated report generation.

Demonstrate both **technical depth and statistical correctness**.

## 24. Difficult Questions the Jury May Ask

Prepare strong answers to questions such as:

* Why Jevons?
* Why not Laspeyres directly at the fare level?
* Why use DGCA passenger volume as weights?
* Why these five booking horizons?
* How do you handle dynamic pricing?
* How do you ensure the same product is being compared?
* What happens when a fare disappears?
* How do you handle new routes?
* What happens when the scraper fails?
* How do you prevent scraping errors from becoming CPI movements?
* How do you distinguish a genuine fare spike from an anomaly?
* What happens during Diwali or other peak travel periods?
* How do you make the index reproducible?
* How would MoSPI audit the index?
* How would you scale from 30 routes to nationwide coverage?
* How would you comply with website terms and robots.txt?
* What happens when airline websites redesign themselves?

## 25. Final Research Deliverables

Produce the following:

### A. Executive Summary

A concise explanation of the complete SIH26056 solution.

### B. Statistical Methodology

A mathematically precise description of:

* Fare sampling
* Booking horizons
* Jevons route index
* DGCA weighting
* National index
* Base period
* Missing-data treatment
* Outlier treatment

### C. System Architecture

A production-quality architecture diagram described in text.

### D. Data Model

Complete database schema.

### E. Scraping Strategy

Detailed source-by-source architecture and resilience strategy.

### F. Real-Time Data Strategy

Best live-data approach plus fallback approach.

### G. Dashboard Specification

Every page, chart, KPI and interaction.

### H. Validation Framework

Statistical and engineering tests.

### I. SIH Demo Plan

A step-by-step final-round demo.

### J. Risk Register

Technical, statistical, legal and operational risks with mitigations.

### K. Implementation Roadmap

Break development into:

* Day 1–2
* Day 3–5
* Week 2
* Week 3
* Final polishing

### L. Source Verification

For every important statistical or governmental claim, provide the authoritative source and distinguish:

* Verified fact
* Research finding
* Design recommendation
* Assumption

## Important Research Standard

Do not blindly accept the supplied briefing.

Verify its claims against primary sources wherever possible.

In particular, independently validate:

* MoSPI's new CPI plans.
* DGCA datasets.
* Jevons methodology.
* Laspeyres/Young/Lowe aggregation.
* Airfare dynamic-pricing research.
* Booking-window thresholds.
* Availability of APIs.
* Legal scraping constraints.

Finally, produce a **recommended end-to-end SIH26056 architecture** that balances:

**statistical validity + real-time capability + scraping resilience + legal compliance + implementation speed + SIH demo impact.**

The final recommendation must clearly identify which components are essential, which are optional, and which should be mocked or simplified for the hackathon.
