# EU Parts Job Dashboard

A Streamlit-based dashboard for viewing and managing EU parts jobs from Zuper. This is a **VIEW-ONLY** dashboard that displays job data synchronized from the Zuper API.

## Features

- **Dashboard View**: Overview of all EU parts jobs with filtering and search
- **Job Lookup**: Search for individual jobs by job number
- **Bulk Lookup**: Search for multiple jobs at once
- **Parts Inventory**: View parts status and delivery timeline
- **Data Sync**: Manual synchronization from Zuper API
- **Multi-language**: Support for English and Dutch
- **Map View**: Geographic visualization of job locations
- **Export**: Download job data as CSV or JSON

## Geographic Scope

The dashboard filters jobs to the European region:
- **Latitude**: 35°N to 72°N
- **Longitude**: -11°E to 40°E
- **Job Category**: "Field Requires Parts" (capital R)

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Zuper API credentials

### Setup Steps

1. **Clone the repository**
   ```bash
   cd /Users/samfoster/Zuper-EU-Parts-Job/Jacco_part_dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database**
   - Create PostgreSQL database
   - Run schema initialization:
     ```bash
     psql -U your_user -d eu_parts_jobs -f database/schema.sql
     ```

5. **Configure secrets**
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
   - Fill in your Zuper API credentials and database connection details:
     ```toml
     [zuper]
     api_key = "your_zuper_api_key"
     org_uid = "your_organization_uid"
     base_url = "https://api.zuper.com/v1"

     [database]
     host = "your_database_host"
     port = 5432
     database = "eu_parts_jobs"
     user = "your_db_user"
     password = "your_db_password"
     ```

6. **Run the application**
   ```bash
   streamlit run streamlit_app.py
   ```

## Project Structure

```
Jacco_part_dashboard/
├── streamlit_app.py          # Main application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── claude.md                  # Development documentation
│
├── .streamlit/
│   ├── config.toml           # Streamlit configuration
│   └── secrets.toml.example  # Example secrets file
│
├── components/
│   ├── job_card.py           # Job display components
│   ├── bulk_lookup.py        # Bulk search functionality
│   └── parts_inventory.py    # Parts inventory view
│
├── database/
│   ├── connection.py         # Database connection management
│   ├── queries.py            # SQL queries
│   └── schema.sql            # Database schema
│
├── src/
│   ├── zuper_api/
│   │   ├── client.py         # Zuper API client
│   │   └── exceptions.py     # API exceptions
│   │
│   └── sync/
│       └── sync_manager.py   # Data synchronization
│
├── utils/
│   ├── language.py           # Internationalization
│   ├── formatters.py         # Display formatters
│   └── gps_helpers.py        # GPS utilities
│
└── config/
    └── settings.py           # Application settings
```

## Usage

### Initial Data Sync

Before using the dashboard, you need to sync data from Zuper:

1. Navigate to the "Sync Data" page in the sidebar
2. Click "Sync Now" button
3. Wait for the sync to complete

### Viewing Jobs

- **Dashboard**: View all jobs with filters for status, priority, and search
- **Job Lookup**: Enter a job number to view detailed information
- **Bulk Lookup**: Enter multiple job numbers (one per line) for batch searching

### Parts Management

The "Parts Inventory" page shows:
- Parts delivery statistics
- Jobs waiting for parts
- Parts delivery timeline

### Exporting Data

Use the export buttons on the Dashboard or Bulk Lookup pages to download data as CSV or JSON.

## Important Notes

### View-Only Dashboard

This dashboard is **READ-ONLY**. It does not allow updating jobs in Zuper. All data modifications must be done through the Zuper interface.

### Job Status Field

The dashboard uses the actual `job_status` field from Zuper, NOT `current_stage`. Ensure your Zuper instance populates this field correctly.

### Status Naming Convention

**Important**: The status "Parts delivered" uses a lowercase 'd', not "Parts Delivered".

### Geographic Filtering

Jobs are automatically filtered to EU bounds:
- Latitude: 35°N to 72°N
- Longitude: -11°E to 40°E

Jobs outside these bounds will not appear in the dashboard.

### Job Category Filter

Only jobs with category "Field Requires Parts" (capital R) are displayed.

## Configuration

### Application Settings

Edit `config/settings.py` to modify:
- Geographic bounds
- Pagination settings
- Sync intervals
- Display options
- Feature flags

### Feature Flags

Enable/disable features in `config/settings.py`:
- Map view
- Bulk lookup
- Parts inventory
- Export functionality
- Manual sync

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check database credentials in `.streamlit/secrets.toml`
- Ensure database schema is initialized

### API Connection Issues

- Verify Zuper API credentials
- Check API endpoint URL
- Review API rate limits

### No Data Displayed

- Run a data sync from the Sync page
- Check that jobs exist in Zuper with category "Field Requires Parts"
- Verify jobs are within EU geographic bounds

## Development

### Adding New Features

1. Create feature flag in `config/settings.py`
2. Implement feature in appropriate module
3. Add UI in `streamlit_app.py` or create new component
4. Update this README

### Database Modifications

1. Update `database/schema.sql`
2. Modify queries in `database/queries.py`
3. Update sync logic in `src/sync/sync_manager.py`

## Support

For issues or questions, refer to the `claude.md` file for detailed development documentation.

## License

Internal use only - EU Parts Job Management
