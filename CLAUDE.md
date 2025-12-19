# CLAUDE.md - AI Assistant Guide for EU Parts Job Dashboard

## Quick Reference

```bash
# Run the application
streamlit run streamlit_app.py

# Install dependencies
pip install -r requirements.txt

# Run with specific port
streamlit run streamlit_app.py --server.port 8501
```

## Critical Requirements - READ FIRST

### 1. This is a VIEW-ONLY Dashboard
- **NO** PUT/PATCH/DELETE API calls to Zuper
- **NO** database updates from UI (only sync operations)
- **Only** SELECT queries for data retrieval
- Sync operations only INSERT/UPDATE from API to database

### 2. Job Category Filter - EXACT String Required
```python
# MUST use capital 'R' in "Requires"
JOB_CATEGORY = "Field Requires Parts"  # CORRECT
JOB_CATEGORY = "Field requires Parts"  # WRONG
```
- Defined in `config/settings.py:21`
- Used in all API and database queries

### 3. Status Field - Use `job_status` NOT `current_stage`
```python
# CORRECT
job_data.get("job_status")
job['job_status']

# WRONG - Never use this
job_data.get("current_stage")
```

### 4. Status Naming - Lowercase 'd' in "Parts delivered"
```python
# CORRECT
"Parts delivered"

# WRONG
"Parts Delivered"
```
- Implemented in `utils/formatters.py:33-51`

### 5. Geographic Bounds - EU Filtering
```python
EU_BOUNDS = {
    "min_lat": 35.0,   # Southern Europe
    "max_lat": 72.0,   # Northern Scandinavia
    "min_lon": -11.0,  # Western Ireland/Portugal
    "max_lon": 40.0    # Eastern Europe
}
```
- Defined in `config/settings.py:13-18`
- Applied in database queries and API filtering

## Project Structure

```
Jacco_part_dashboard/
├── streamlit_app.py           # Main entry point - run this file
├── requirements.txt           # Python dependencies (streamlit, pandas, requests)
├── CLAUDE.md                  # This file
├── README.md                  # User documentation
│
├── .streamlit/
│   ├── config.toml           # Streamlit theme and server config
│   └── secrets.toml.example  # Template for API credentials
│
├── .devcontainer/
│   └── devcontainer.json     # GitHub Codespaces/VS Code dev container
│
├── data/
│   └── eu_parts_jobs.db      # SQLite database (auto-created)
│
├── components/                # Streamlit UI components
│   ├── job_card.py           # Job display cards and lists
│   ├── bulk_lookup.py        # Multi-job search interface
│   └── parts_inventory.py    # Parts status views
│
├── database/                  # Data layer (SQLite)
│   ├── connection.py         # Connection management, auto-init
│   ├── queries.py            # SELECT-only query methods
│   └── schema.sql            # Table definitions
│
├── src/
│   ├── zuper_api/            # Zuper API integration
│   │   ├── client.py         # READ-ONLY API client
│   │   └── exceptions.py     # Custom exception classes
│   │
│   └── sync/
│       └── sync_manager.py   # API to database sync logic
│
├── utils/
│   ├── language.py           # i18n (English/Dutch)
│   ├── formatters.py         # Display formatting, badges
│   └── gps_helpers.py        # Coordinate validation
│
└── config/
    └── settings.py           # AppSettings and FeatureFlags classes
```

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Streamlit | >=1.45.0 |
| Database | SQLite | Built-in |
| Data Processing | Pandas | >=2.2.0 |
| HTTP Client | Requests | >=2.31.0 |
| Python | Python | 3.8+ |

## Database

### SQLite - No Configuration Required
- Database file: `data/eu_parts_jobs.db`
- Auto-created on first run
- Schema auto-initialized from `database/schema.sql`

### Main Tables

**`jobs`** - Primary job data
```sql
job_uid TEXT PRIMARY KEY,
job_number TEXT UNIQUE,
title TEXT,
description TEXT,
job_status TEXT,           -- Use this, NOT current_stage
job_category TEXT,         -- "Field Requires Parts"
priority TEXT,
customer_name TEXT,
latitude REAL,
longitude REAL,
-- ... (see schema.sql for full definition)
```

**`sync_log`** - Tracks sync operations
```sql
sync_id INTEGER PRIMARY KEY,
sync_started TEXT,
sync_completed TEXT,
status TEXT,               -- 'running', 'completed', 'failed'
jobs_fetched INTEGER,
jobs_created INTEGER,
jobs_updated INTEGER
```

### Query Patterns
All queries in `database/queries.py` follow this pattern:
```python
# Always filter by category and EU bounds
WHERE
    job_category = 'Field Requires Parts'
    AND latitude BETWEEN 35 AND 72
    AND longitude BETWEEN -11 AND 40
```

## API Integration

### Zuper API Client (`src/zuper_api/client.py`)

**Configuration** (`.streamlit/secrets.toml`):
```toml
[zuper]
api_key = "your_api_key"
base_url = "https://us-east-1.zuperpro.com/api"
```

**Key Methods**:
- `get_jobs()` - Paginated job fetch
- `get_all_parts_jobs()` - All "Field Requires Parts" jobs
- `get_eu_parts_jobs()` - Filtered to EU bounds

**Rate Limiting**:
- 100 requests/minute (built-in)
- Automatic retry with exponential backoff
- 30 second timeout

**Zuper API Response Format**:
```python
# Jobs are in 'data' array
response = {
    "data": [...],
    "total_records": 100,
    "total_pages": 2,
    "current_page": 1
}

# Job category is nested object
job_category = job.get("job_category", {}).get("category_name")

# Status is nested object
status = job.get("current_job_status", {}).get("status_name")

# Coordinates are in customer_address.geo_cordinates array
geo = job.get("customer_address", {}).get("geo_cordinates", [])
lat, lon = geo[0], geo[1]  # [latitude, longitude]
```

## Available Job Statuses

From `config/settings.py:41-50`:
```python
JOB_STATUSES = [
    "New Ticket",
    "Received Request",
    "Parts On Order",
    "Shop Pick UP",
    "Shipped",
    "Parts delivered",    # Note: lowercase 'd'
    "Done",
    "Canceled"
]
```

## Feature Flags

From `config/settings.py:161-177`:
```python
class FeatureFlags:
    ENABLE_MAP_VIEW = True
    ENABLE_BULK_LOOKUP = True
    ENABLE_PARTS_INVENTORY = True
    ENABLE_EXPORT = True
    ENABLE_MANUAL_SYNC = True
    ENABLE_AUTO_SYNC = False
    ENABLE_ADVANCED_FILTERS = True
    ENABLE_CUSTOM_FIELDS = True
    ENABLE_DARK_MODE = False
```

## Multi-Language Support

The app supports English (`en`) and Dutch (`nl`).

**Translation file**: `utils/language.py`

**Usage**:
```python
from utils.language import Language
lang = Language(st.session_state.language)
text = lang.get("job_lookup")  # Returns translated string
```

## Common Development Tasks

### Adding a New Status

1. Add to `config/settings.py`:
   ```python
   JOB_STATUSES = [..., "New Status"]
   ```

2. Add badge color in `utils/formatters.py`:
   ```python
   status_colors = {
       ...,
       "new status": "#hexcolor"
   }
   ```

3. Add icon in `streamlit_app.py` status tiles and `components/job_card.py`:
   ```python
   status_icons = {
       ...,
       'New Status': 'emoji'
   }
   ```

4. Add translations in `utils/language.py` for both `en` and `nl`

### Adding a New Filter

1. Add UI in `streamlit_app.py` render functions
2. Create/modify query in `database/queries.py`
3. Add translation keys in `utils/language.py`

### Modifying Geographic Bounds

Update in THREE places:
1. `config/settings.py` - `EU_BOUNDS` dict
2. `utils/gps_helpers.py` - validation functions
3. `database/queries.py` - SQL WHERE clauses

## Data Flow

### Sync Flow (API -> Database)
```
Zuper API
    ↓ GET /jobs (paginated)
ZuperAPIClient.get_eu_parts_jobs()
    ↓ filter by category + EU bounds
SyncManager.sync_all_jobs()
    ↓ INSERT OR REPLACE
SQLite Database
```

### Display Flow (Database -> UI)
```
User Action (click/filter)
    ↓
Streamlit App
    ↓
JobQueries.get_all_eu_parts_jobs()
    ↓ SELECT with filters
SQLite Database
    ↓
format_* functions
    ↓
UI Components (job_card, etc.)
```

## Important Files by Function

### Entry Points
- `streamlit_app.py` - Main app, page routing, UI

### Configuration
- `config/settings.py` - All app settings
- `.streamlit/secrets.toml` - API credentials (DO NOT COMMIT)
- `.streamlit/config.toml` - Streamlit theme/server

### Database
- `database/connection.py` - `get_db_connection()`, `execute_query()`
- `database/queries.py` - `JobQueries` class with all SELECT queries
- `database/schema.sql` - Table definitions

### API
- `src/zuper_api/client.py` - `ZuperAPIClient`, `get_zuper_client()`
- `src/sync/sync_manager.py` - `SyncManager.sync_all_jobs()`

### UI Components
- `components/job_card.py` - `render_job_card()`, `render_job_list()`
- `components/bulk_lookup.py` - Bulk search functionality
- `components/parts_inventory.py` - Parts statistics

### Utilities
- `utils/formatters.py` - `format_status()`, `status_badge()`
- `utils/language.py` - `Language` class for i18n
- `utils/gps_helpers.py` - Coordinate validation

## Troubleshooting

### No Jobs Displayed
1. Check sync has been run (Sync Data page)
2. Verify job category is exactly "Field Requires Parts"
3. Check jobs are within EU bounds (lat: 35-72, lon: -11 to 40)
4. Check database file exists: `data/eu_parts_jobs.db`

### Sync Fails
1. Verify API credentials in `.streamlit/secrets.toml`
2. Check network connectivity
3. Review Streamlit logs for API errors
4. Check rate limiting (100 req/min)

### Status Display Issues
1. Ensure using `job_status` field, not `current_stage`
2. Check "Parts delivered" uses lowercase 'd'
3. Verify status exists in `JOB_STATUSES` list

## Security Notes

- **NEVER** commit `.streamlit/secrets.toml`
- API key stored only in secrets file
- All database queries use parameterized statements
- UI is read-only (no data modification)

## Development Environment

### GitHub Codespaces / VS Code Dev Container
- Configuration in `.devcontainer/devcontainer.json`
- Python 3.11 environment
- Auto-installs requirements
- Auto-starts Streamlit on port 8501

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure API (copy and edit)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Run app
streamlit run streamlit_app.py
```

## Code Style Guidelines

- Python 3.8+ compatible
- Type hints encouraged but not required
- Docstrings for all public functions
- Logging via `logging` module
- Error handling with custom exceptions in `src/zuper_api/exceptions.py`
