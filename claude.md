# EU Parts Job Dashboard - Development Documentation

## Project Overview

This is a **VIEW-ONLY** Streamlit dashboard for displaying EU parts jobs from Zuper. The dashboard synchronizes data from the Zuper API into a local PostgreSQL database and provides various views for job management.

## Critical Requirements

### 1. Job Category Filter
**MUST use "Field Requires Parts" with capital R**
- The exact string is: `"Field Requires Parts"`
- This is hardcoded in `config/settings.py`
- All queries filter by this exact category

### 2. Geographic Bounds
Jobs are filtered to European coordinates:
- **Latitude**: 35°N to 72°N
- **Longitude**: -11°E to 40°E
- Defined in `config/settings.py` and `utils/gps_helpers.py`

### 3. Status Field Usage
**Use `job_status` NOT `current_stage`**
- The dashboard uses the actual Zuper `job_status` field
- Do NOT use `current_stage` field
- All queries use `job_status` column

### 4. Status Naming Convention
**"Parts delivered" uses lowercase 'd'**
- Correct: `"Parts delivered"`
- Incorrect: `"Parts Delivered"`
- Implemented in `utils/formatters.py`

### 5. No Update Functionality
**This is a READ-ONLY dashboard**
- No PUT/PATCH/DELETE API calls
- No database updates from UI
- Only SELECT queries for data retrieval
- Sync operations only INSERT/UPDATE from API to database

## Architecture

### Main Entry Point
- **File**: `streamlit_app.py` (NOT app.py)
- This is the file that Streamlit runs
- Contains all page routing and main UI logic

### Module Structure

```
├── streamlit_app.py           # Main application
├── components/                # UI components
│   ├── job_card.py           # Job display
│   ├── bulk_lookup.py        # Bulk search
│   └── parts_inventory.py    # Parts views
├── database/                  # Data layer
│   ├── connection.py         # DB connection pool
│   ├── queries.py            # SQL queries (SELECT only)
│   └── schema.sql            # Database schema
├── src/
│   ├── zuper_api/            # API client
│   │   ├── client.py         # READ-ONLY client
│   │   └── exceptions.py     # Error handling
│   └── sync/                 # Synchronization
│       └── sync_manager.py   # API to DB sync
├── utils/                     # Utilities
│   ├── language.py           # i18n (EN/NL)
│   ├── formatters.py         # Display formatting
│   └── gps_helpers.py        # GPS utilities
└── config/
    └── settings.py           # Configuration
```

## Key Components

### Database Layer

**Connection Management** (`database/connection.py`)
- Uses psycopg2 connection pooling
- Cached with `@st.cache_resource`
- Helper functions: `execute_query()`, `execute_many()`

**Queries** (`database/queries.py`)
- All queries are SELECT only
- Geographic filtering built into queries
- Job category filtering built into queries
- Key methods:
  - `get_all_eu_parts_jobs()`: All EU jobs
  - `get_jobs_by_status()`: Filter by status
  - `get_job_by_number()`: Single job lookup
  - `get_jobs_by_numbers()`: Bulk lookup
  - `search_jobs()`: Text search

**Schema** (`database/schema.sql`)
- Main table: `jobs`
- Views: `eu_parts_jobs`, `active_parts_jobs`
- Sync tracking: `sync_log`
- Geographic constraints enforced at DB level

### API Client

**Zuper API Client** (`src/zuper_api/client.py`)
- **READ-ONLY**: Only GET requests
- Rate limiting: 100 requests/minute
- Automatic retry with exponential backoff
- Geographic filtering after fetch
- Key methods:
  - `get_jobs()`: Paginated job fetch
  - `get_all_parts_jobs()`: All "Field Requires Parts" jobs
  - `get_eu_parts_jobs()`: Filtered to EU bounds

**Exceptions** (`src/zuper_api/exceptions.py`)
- Custom exception hierarchy
- Specific errors for auth, rate limit, network issues

### Sync Manager

**Sync Manager** (`src/sync/sync_manager.py`)
- Fetches jobs from API
- Upserts into database
- Tracks sync statistics
- Logs all sync operations
- **No deletion**: Only insert/update

### UI Components

**Job Card** (`components/job_card.py`)
- Display individual jobs
- Status badges with colors
- Map integration
- Expandable details

**Bulk Lookup** (`components/bulk_lookup.py`)
- Multi-job search
- Table and card views
- Export to CSV/JSON

**Parts Inventory** (`components/parts_inventory.py`)
- Parts statistics
- Delivery timeline
- Jobs waiting for parts

### Utilities

**Language** (`utils/language.py`)
- English and Dutch translations
- Translation keys for all UI text

**Formatters** (`utils/formatters.py`)
- Date/time formatting
- Status formatting (lowercase 'd' in "Parts delivered")
- Currency, coordinates, etc.
- Status and priority badges (HTML)

**GPS Helpers** (`utils/gps_helpers.py`)
- EU bounds checking
- Coordinate validation
- Distance calculations (Haversine)
- Map data formatting

### Configuration

**Settings** (`config/settings.py`)
- `AppSettings`: All configuration constants
- `FeatureFlags`: Enable/disable features
- EU bounds, job category, pagination, etc.

## Data Flow

### Synchronization Flow
```
Zuper API
    ↓
API Client (client.py)
    ↓ (filters by category)
Sync Manager (sync_manager.py)
    ↓ (filters by EU bounds)
Database (PostgreSQL)
    ↓
Queries (queries.py)
    ↓
UI (streamlit_app.py)
```

### Display Flow
```
User Action
    ↓
Streamlit App (streamlit_app.py)
    ↓
Queries (queries.py)
    ↓
Database (PostgreSQL)
    ↓
Formatters (formatters.py)
    ↓
Components (job_card.py, etc.)
    ↓
Display
```

## Important Implementation Details

### Job Category Filtering

**In API Client** (`src/zuper_api/client.py`):
```python
filters = {
    "jobCategory": "Field Requires Parts"  # Capital R
}
```

**In Database Queries** (`database/queries.py`):
```python
WHERE job_category = 'Field Requires Parts'
```

**In Settings** (`config/settings.py`):
```python
JOB_CATEGORY = "Field Requires Parts"
```

### Geographic Filtering

**In GPS Helpers** (`utils/gps_helpers.py`):
```python
EU_BOUNDS = {
    "min_lat": 35.0,
    "max_lat": 72.0,
    "min_lon": -11.0,
    "max_lon": 40.0
}
```

**In Database Schema** (`database/schema.sql`):
```sql
WHERE
    latitude BETWEEN 35 AND 72
    AND longitude BETWEEN -11 AND 40
```

**In API Client** (`src/zuper_api/client.py`):
```python
# Filter after fetching
if 35 <= lat <= 72 and -11 <= lon <= 40:
    eu_jobs.append(job)
```

### Status Field Usage

**Always use `job_status`**:
```python
job_data.get("jobStatus")  # From API
job['job_status']           # In database
```

**NEVER use**:
```python
job_data.get("currentStage")  # WRONG
```

### Status Formatting

**In Formatters** (`utils/formatters.py`):
```python
def format_status(status: Optional[str]) -> str:
    if status.lower() == "parts delivered":
        return "Parts delivered"  # lowercase 'd'
    return status
```

## Configuration Files

### Secrets (.streamlit/secrets.toml)

```toml
[zuper]
api_key = "your_key"
org_uid = "your_org"
base_url = "https://api.zuper.com/v1"

[database]
host = "localhost"
port = 5432
database = "eu_parts_jobs"
user = "postgres"
password = "password"

[app]
refresh_interval_minutes = 15
max_jobs_per_page = 50
```

### Streamlit Config (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"

[server]
headless = true
port = 8501
```

## Feature Flags

Enable/disable features in `config/settings.py`:

```python
class FeatureFlags:
    ENABLE_MAP_VIEW = True
    ENABLE_BULK_LOOKUP = True
    ENABLE_PARTS_INVENTORY = True
    ENABLE_EXPORT = True
    ENABLE_MANUAL_SYNC = True
    ENABLE_AUTO_SYNC = False
```

## Database Schema

### Jobs Table
Primary table storing all job data:
- Job identification (job_uid, job_number)
- Job details (title, description, status)
- Customer info (customer_name, customer_uid)
- Location (latitude, longitude, job_address)
- Technician (assigned_technician, technician_uid)
- Timestamps (scheduled_start_time, etc.)
- Parts info (parts_status, parts_delivered_date)

### Views
- `eu_parts_jobs`: All EU jobs with parts
- `active_parts_jobs`: Active jobs only

### Sync Log
Tracks all synchronization operations with statistics.

## Common Tasks

### Adding a New Filter

1. Add filter UI in `streamlit_app.py`
2. Create query in `database/queries.py`
3. Add translation keys in `utils/language.py`

### Adding a New Status

1. Add to `JOB_STATUSES` in `config/settings.py`
2. Add badge color in `utils/formatters.py`
3. Add translations in `utils/language.py`

### Modifying Geographic Bounds

1. Update `EU_BOUNDS` in `config/settings.py`
2. Update `EU_BOUNDS` in `utils/gps_helpers.py`
3. Update views in `database/schema.sql`

## Testing Checklist

### Data Sync
- [ ] Sync fetches only "Field Requires Parts" jobs
- [ ] Geographic filtering to EU bounds works
- [ ] Sync log records all operations
- [ ] Error handling works for API failures

### Display
- [ ] Jobs display with correct status (lowercase 'd')
- [ ] Map shows only jobs with valid coordinates
- [ ] Filters work correctly
- [ ] Search finds jobs by number/title/customer

### Features
- [ ] Single job lookup works
- [ ] Bulk lookup handles multiple jobs
- [ ] Parts inventory shows correct stats
- [ ] Export generates valid CSV/JSON

### Language
- [ ] English translations work
- [ ] Dutch translations work
- [ ] Language switching preserves state

## Deployment

### Requirements
- Python 3.8+
- PostgreSQL 12+
- Zuper API access

### Steps
1. Set up PostgreSQL database
2. Run schema initialization
3. Configure secrets.toml
4. Install dependencies
5. Run streamlit app

### Environment Variables
All configuration via `.streamlit/secrets.toml` - no environment variables needed.

## Troubleshooting

### No Jobs Displayed
- Check job category is exactly "Field Requires Parts"
- Verify jobs are within EU bounds
- Run a data sync
- Check database connection

### Sync Fails
- Verify API credentials
- Check API rate limits
- Review sync log table

### Wrong Status Shown
- Ensure using `job_status` not `current_stage`
- Check Zuper API response format

## Security Notes

### API Key Storage
- NEVER commit `.streamlit/secrets.toml`
- Add to .gitignore
- Use environment-specific secrets

### Database Access
- Use connection pooling
- No SQL injection (parameterized queries)
- Read-only queries from UI

### Rate Limiting
- Respect Zuper API limits
- Implement backoff strategy
- Log all API calls

## Performance Optimization

### Caching
- API client cached with `@st.cache_resource`
- Database connection pool cached
- Query results NOT cached (data changes frequently)

### Database
- Indexes on common query fields
- Views for complex queries
- Batch inserts during sync

### API
- Pagination for large datasets
- Rate limiting built-in
- Retry with exponential backoff

## Future Enhancements

Potential additions (not implemented):
- Real-time data refresh
- Advanced analytics
- Email notifications
- Custom reporting
- Mobile responsive design
- Dark mode support

## Version History

- **v1.0**: Initial implementation
  - View-only dashboard
  - EU geographic filtering
  - "Field Requires Parts" category filter
  - Multi-language support
  - Parts inventory views
  - Manual sync functionality

## Contact

For questions or issues, refer to this documentation first. All critical requirements are documented here.
