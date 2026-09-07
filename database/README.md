# Database Storage & Schema Architecture (SIH26056)

This directory serves as the centralized storage location for all persistent SQLite database files, baseline schemas, seed fixtures, and migration provenance for the **Airfare CPI** engine.

---

## 1. Directory Contents

| File | Description | Status |
|---|---|---|
| [`airfare_cpi_managed.db`](airfare_cpi_managed.db) | **Active, version-controlled SQLite database** managed by Alembic. Contains 454,000+ raw fare observations (ranging to 2026-09-07), 9,820+ corridor elementary aggregates, 2,358 national index records, and 413 pipeline runs. | `ACTIVE (Target)` |
| [`seed_snapshot.sql`](seed_snapshot.sql) | **Compact Git-tracked SQL seed export** (~16 MB). Restores full schema, Alembic revision marker, 25 routes, 400 national CPI history rows, 2,000 corridor index rows, and 5,000 real fare observations with AERA UDF decomposition. | `TRACKED SEED SNAPSHOT` |
| [`airfare_cpi.db`](airfare_cpi.db) | Historical read-only archive (1.2 GB, 858,480 historical observations). Protected against overwrites. | `HISTORICAL ARCHIVE` |
| [`schema.sql`](schema.sql) | Complete SQL DDL defining all relational tables, indices, and constraints. | `CANONICAL DDL` |
| [`seed_routes.sql`](seed_routes.sql) | Official 25 core DGCA passenger corridors and trunk routes with distance and base passenger volume weights. | `SEED DATA` |

---

## 2. Relational Schema Architecture

The database is built on **SQLAlchemy 2.0 (Async Engine)** and migrations are strictly tracked via **Alembic**:

```
┌─────────────────────────────────┐
│       routes (Master Table)     │
│  - id, origin_iata, dest_iata   │
│  - distance_km, base_weight_pax │
└────────────────┬────────────────┘
                 │ 1:N
                 ▼
┌─────────────────────────────────┐
│        fare_observations        │
│  - product_key (Composite)      │
│  - departure_time_band (4 bands)│
│  - base_fare_inr, gst_inr       │
│  - udf_inr, convenience_fee_inr │
│  - total_fare_inr, is_valid     │
└────────────────┬────────────────┘
                 │ Aggregation
                 ▼
┌─────────────────────────────────┐
│     national_index_history      │
│  - index_date, value, base_year │
│  - formula (Matched Jevons)     │
│  - sample_size, standard_error  │
└─────────────────────────────────┘
```

### Core Relational Tables:
1. `routes`: 83 monitored flight corridors (25 Core DGCA trunk routes + 58 interstate routes connecting all 28 States and 8 Union Territories).
2. `fare_observations`: Live quotes scraped by the automated browser engine across 4 statutory departure time bands (`EARLY_MORNING`, `MORNING`, `AFTERNOON`, `EVENING_NIGHT`) with fee decomposition.
3. `route_indices`: Daily elementary geometric aggregates for each individual corridor.
4. `horizon_indices`: Stratified booking horizon relatives ($T+1, T+7, T+15, T+30, T+45$).
5. `national_index_history`: Published daily All-India Airfare CPI series (Rebased 2024=100).
6. `source_registry`: Compliance registry for monitored airline portals, quotas, and crawl policies.
7. `anomalies`: Flagged extreme price swings and automated quarantine audit records.
8. `alembic_version`: Current active migration revision (`20260903_0004`).

---

## 3. Configuration & Connection URLs

The active database path is configured in `backend/config.py`:
```python
DATABASE_DIR = REPO_ROOT / "database"
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DATABASE_DIR / 'airfare_cpi_managed.db'}"
```

For PostgreSQL deployments in containerized/production environments:
```bash
DATABASE_URL="postgresql+asyncpg://airfare:airfare@db:5432/airfare_cpi"
```

---

## 4. Running Migrations

To apply latest schema updates or verify the database revision:
```bash
cd backend
python3 -c 'from alembic.config import main; main()' -c alembic.ini upgrade head
```
Check migration status:
```bash
python3 -c 'from alembic.config import main; main()' -c alembic.ini current
# Output: 20260903_0004 (head)
```

---

## 5. Instant Database Restoration from Git Seed

Because the full operational database exceeds 700 MB, the repository tracks [`seed_snapshot.sql`](seed_snapshot.sql) (~16 MB). It contains the complete schema, the Alembic migration revision marker (`20260903_0004`), master trunk routes, 400-day national CPI series, 2,000 corridor elementary index rows, and 5,000 real flight observations with statutory AERA UDF decomposition.

To restore a fully operational local database from scratch in seconds:
```bash
sqlite3 database/airfare_cpi_managed.db < database/seed_snapshot.sql
```
