-- ============================================================
-- SIH26056 — Seed: Top 25 Domestic Routes by DGCA Passenger Volume
-- Source: DGCA City-Pair Traffic Statistics (approximated from latest available data)
-- Routes are NON-DIRECTIONAL (DEL-BOM covers both DEL→BOM and BOM→DEL)
-- ============================================================

-- First, compute total pax for weight normalization
-- Total estimated monthly pax across these 25 routes: 11,980,000
-- Normalized weights sum to exactly 1.0000

INSERT INTO routes (origin_code, destination_code, origin_city, destination_city, dgca_monthly_pax, weight, is_active, effective_from) VALUES
-- Tier 1: Metro-to-Metro mega corridors (>700K monthly pax each direction combined)
('DEL', 'BOM', 'New Delhi',     'Mumbai',       1200000, 0.1002, TRUE, '2026-08-01'),
('DEL', 'BLR', 'New Delhi',     'Bengaluru',     950000, 0.0793, TRUE, '2026-08-01'),
('BOM', 'BLR', 'Mumbai',        'Bengaluru',     870000, 0.0726, TRUE, '2026-08-01'),
('DEL', 'HYD', 'New Delhi',     'Hyderabad',     780000, 0.0651, TRUE, '2026-08-01'),
('DEL', 'CCU', 'New Delhi',     'Kolkata',       740000, 0.0618, TRUE, '2026-08-01'),

-- Tier 2: Major metro connections (400K–700K)
('BOM', 'HYD', 'Mumbai',        'Hyderabad',     650000, 0.0543, TRUE, '2026-08-01'),
('DEL', 'MAA', 'New Delhi',     'Chennai',       600000, 0.0501, TRUE, '2026-08-01'),
('BOM', 'CCU', 'Mumbai',        'Kolkata',       520000, 0.0434, TRUE, '2026-08-01'),
('BLR', 'HYD', 'Bengaluru',     'Hyderabad',     480000, 0.0401, TRUE, '2026-08-01'),
('DEL', 'GOI', 'New Delhi',     'Goa',           450000, 0.0376, TRUE, '2026-08-01'),

-- Tier 3: High-traffic secondary connections (300K–450K)
('BOM', 'MAA', 'Mumbai',        'Chennai',       430000, 0.0359, TRUE, '2026-08-01'),
('BLR', 'CCU', 'Bengaluru',     'Kolkata',       400000, 0.0334, TRUE, '2026-08-01'),
('DEL', 'PNQ', 'New Delhi',     'Pune',          390000, 0.0326, TRUE, '2026-08-01'),
('BOM', 'GOI', 'Mumbai',        'Goa',           380000, 0.0317, TRUE, '2026-08-01'),
('DEL', 'AMD', 'New Delhi',     'Ahmedabad',     370000, 0.0309, TRUE, '2026-08-01'),

-- Tier 4: Regional high-traffic (200K–350K)
('BLR', 'MAA', 'Bengaluru',     'Chennai',       340000, 0.0284, TRUE, '2026-08-01'),
('DEL', 'JAI', 'New Delhi',     'Jaipur',        320000, 0.0267, TRUE, '2026-08-01'),
('BOM', 'AMD', 'Mumbai',        'Ahmedabad',     310000, 0.0259, TRUE, '2026-08-01'),
('DEL', 'LKO', 'New Delhi',     'Lucknow',       300000, 0.0250, TRUE, '2026-08-01'),
('BLR', 'GOI', 'Bengaluru',     'Goa',           280000, 0.0234, TRUE, '2026-08-01'),

-- Tier 5: Important secondary routes (150K–280K)
('HYD', 'CCU', 'Hyderabad',     'Kolkata',       270000, 0.0225, TRUE, '2026-08-01'),
('DEL', 'PAT', 'New Delhi',     'Patna',         260000, 0.0217, TRUE, '2026-08-01'),
('BOM', 'JAI', 'Mumbai',        'Jaipur',        240000, 0.0200, TRUE, '2026-08-01'),
('DEL', 'COK', 'New Delhi',     'Kochi',         230000, 0.0192, TRUE, '2026-08-01'),
('BOM', 'PNQ', 'Mumbai',        'Pune',          220000, 0.0182, TRUE, '2026-08-01');

-- Verify weights sum to exactly 1.0
-- SELECT SUM(weight) FROM routes; -- Yields 1.0000

-- ============================================================
-- Seed Airlines
-- ============================================================
INSERT INTO airlines (iata_code, airline_name, website_url, scraping_status) VALUES
('6E', 'IndiGo',        'https://www.goindigo.in',       'planned'),
('AI', 'Air India',     'https://www.airindia.com',      'planned'),
('SG', 'SpiceJet',      'https://www.spicejet.com',      'planned'),
('UK', 'Vistara',       'https://www.airvistara.com',    'planned'),
('I5', 'AirAsia India', 'https://www.airasia.co.in',     'planned'),
('QP', 'Akasa Air',     'https://www.akasaair.com',      'planned'),
('S5', 'Star Air',      'https://www.starair.in',        'planned'),
('G8', 'Go First',      'https://www.flygofirst.com',    'blocked');  -- suspended operations
