-- ============================================================
-- SIH26056 — Real-Time Airfare CPI — Database Schema
-- PostgreSQL 16
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. ROUTES — The basket of monitored city-pair routes
-- ============================================================
CREATE TABLE routes (
    route_id        SERIAL PRIMARY KEY,
    origin_code     CHAR(3)         NOT NULL,   -- IATA airport code
    destination_code CHAR(3)        NOT NULL,
    origin_city     VARCHAR(100)    NOT NULL,
    destination_city VARCHAR(100)   NOT NULL,
    dgca_monthly_pax INTEGER       NOT NULL DEFAULT 0,  -- DGCA passenger volume
    weight          DECIMAL(8,6)    NOT NULL DEFAULT 0,  -- Normalized weight
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    effective_from  DATE            NOT NULL DEFAULT CURRENT_DATE,
    effective_to    DATE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_route_pair UNIQUE (origin_code, destination_code),
    CONSTRAINT chk_route_different CHECK (origin_code <> destination_code),
    CONSTRAINT chk_weight_range CHECK (weight >= 0 AND weight <= 1)
);

CREATE INDEX idx_routes_active ON routes(is_active) WHERE is_active = TRUE;

-- ============================================================
-- 2. AIRLINES — Reference table for tracked airlines
-- ============================================================
CREATE TABLE airlines (
    airline_id      SERIAL PRIMARY KEY,
    iata_code       VARCHAR(3)      NOT NULL UNIQUE,
    airline_name    VARCHAR(100)    NOT NULL,
    website_url     VARCHAR(500),
    scraping_status VARCHAR(20)     NOT NULL DEFAULT 'planned',  -- active/planned/blocked/mock
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. FARE_OBSERVATIONS — The core data: every scraped fare
-- ============================================================
CREATE TABLE fare_observations (
    observation_id      BIGSERIAL PRIMARY KEY,
    scrape_timestamp    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    route_id            INTEGER         NOT NULL REFERENCES routes(route_id),
    airline_code        VARCHAR(6)      NOT NULL,
    airline_name        VARCHAR(100),
    flight_number       VARCHAR(15),
    departure_date      DATE            NOT NULL,
    booking_horizon_days INTEGER        NOT NULL,  -- 0, 3, 7, 15, 30
    cabin_class         VARCHAR(20)     NOT NULL DEFAULT 'Economy',
    fare_base           DECIMAL(10,2),             -- Base fare excl. taxes
    fare_taxes          DECIMAL(10,2),             -- Taxes + mandatory fees
    fare_total          DECIMAL(10,2)   NOT NULL,  -- All-in consumer price
    is_direct           BOOLEAN         NOT NULL DEFAULT TRUE,
    stops               INTEGER         NOT NULL DEFAULT 0,
    baggage_kg          INTEGER,
    is_refundable       BOOLEAN         NOT NULL DEFAULT FALSE,
    fare_family         VARCHAR(50),
    source_platform     VARCHAR(50)     NOT NULL,  -- 'indigo.com', 'makemytrip', 'mock'
    scraper_version     VARCHAR(20),
    is_valid            BOOLEAN         NOT NULL DEFAULT TRUE,
    validation_flags    JSONB           DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_fare_positive CHECK (fare_total > 0),
    CONSTRAINT chk_horizon CHECK (booking_horizon_days >= 0),
    CONSTRAINT chk_stops CHECK (stops >= 0)
);

-- Performance indexes for common queries
CREATE INDEX idx_fares_route_date ON fare_observations(route_id, departure_date);
CREATE INDEX idx_fares_scrape_ts ON fare_observations(scrape_timestamp);
CREATE INDEX idx_fares_horizon ON fare_observations(booking_horizon_days);
CREATE INDEX idx_fares_airline ON fare_observations(airline_code);
CREATE INDEX idx_fares_valid ON fare_observations(is_valid) WHERE is_valid = TRUE;
CREATE INDEX idx_fares_route_horizon ON fare_observations(route_id, booking_horizon_days, scrape_timestamp);

-- ============================================================
-- 4. ROUTE_INDICES — Computed Jevons index per route per day
-- ============================================================
CREATE TABLE route_indices (
    id                  BIGSERIAL PRIMARY KEY,
    route_id            INTEGER         NOT NULL REFERENCES routes(route_id),
    index_date          DATE            NOT NULL,
    booking_horizon     INTEGER,         -- NULL = combined across all horizons
    jevons_index        DECIMAL(12,6)   NOT NULL,
    observation_count   INTEGER         NOT NULL,
    geometric_mean_price DECIMAL(10,2),  -- Geometric mean fare for reference
    base_period_start   DATE            NOT NULL,
    base_period_end     DATE            NOT NULL,
    computed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_route_index UNIQUE (route_id, index_date, booking_horizon),
    CONSTRAINT chk_jevons_positive CHECK (jevons_index > 0)
);

CREATE INDEX idx_route_indices_date ON route_indices(index_date);
CREATE INDEX idx_route_indices_route ON route_indices(route_id, index_date);

-- ============================================================
-- 5. NATIONAL_INDEX — Weighted national Airfare CPI
-- ============================================================
CREATE TABLE national_index (
    id                  BIGSERIAL PRIMARY KEY,
    index_date          DATE            NOT NULL,
    booking_horizon     INTEGER,         -- NULL = combined
    airfare_cpi         DECIMAL(12,6)   NOT NULL,
    mom_change_pct      DECIMAL(8,4),    -- Month-on-month % change
    yoy_change_pct      DECIMAL(8,4),    -- Year-on-year % change
    routes_included     INTEGER         NOT NULL,
    total_observations  INTEGER         NOT NULL,
    base_period         VARCHAR(50)     NOT NULL,
    computed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_national_index UNIQUE (index_date, booking_horizon),
    CONSTRAINT chk_cpi_positive CHECK (airfare_cpi > 0)
);

CREATE INDEX idx_national_date ON national_index(index_date);

-- ============================================================
-- 6. SCRAPER_HEALTH — Monitoring & observability
-- ============================================================
CREATE TABLE scraper_health (
    id                  BIGSERIAL PRIMARY KEY,
    source_platform     VARCHAR(50)     NOT NULL,
    scrape_timestamp    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    status              VARCHAR(20)     NOT NULL,  -- success/failure/partial
    routes_attempted    INTEGER         NOT NULL DEFAULT 0,
    routes_succeeded    INTEGER         NOT NULL DEFAULT 0,
    fares_collected     INTEGER         NOT NULL DEFAULT 0,
    error_type          VARCHAR(100),
    error_message       TEXT,
    selector_version    VARCHAR(20),
    response_time_ms    INTEGER,
    retry_count         INTEGER         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_health_source ON scraper_health(source_platform, scrape_timestamp);
CREATE INDEX idx_health_status ON scraper_health(status);

-- ============================================================
-- 7. ANOMALY_LOG — Flagged price anomalies
-- ============================================================
CREATE TABLE anomaly_log (
    id                  BIGSERIAL PRIMARY KEY,
    observation_id      BIGINT          REFERENCES fare_observations(observation_id),
    route_id            INTEGER         REFERENCES routes(route_id),
    anomaly_type        VARCHAR(50)     NOT NULL,  -- spike/crash/outlier/scrape_error
    severity            VARCHAR(20)     NOT NULL,  -- low/medium/high/critical
    description         TEXT,
    fare_observed       DECIMAL(10,2),
    fare_expected_low   DECIMAL(10,2),
    fare_expected_high  DECIMAL(10,2),
    action_taken        VARCHAR(50)     NOT NULL DEFAULT 'flagged',  -- flagged/excluded/preserved
    is_genuine          BOOLEAN,         -- NULL = unclassified, TRUE = real market, FALSE = error
    detected_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_anomaly_route ON anomaly_log(route_id, detected_at);
CREATE INDEX idx_anomaly_type ON anomaly_log(anomaly_type);

-- ============================================================
-- Helper: Updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_routes_updated_at
    BEFORE UPDATE ON routes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
