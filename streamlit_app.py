"""
EU Parts Job Dashboard - Main Application
A Streamlit dashboard for viewing EU parts jobs from Zuper.

This is a VIEW-ONLY dashboard that displays job data synchronized from Zuper API.
NO update functionality - data is read-only.
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components and utilities
from database.queries import JobQueries
from database.connection import is_database_configured, DatabaseNotConfiguredError, init_database
from components.job_card import render_job_card, render_job_list, render_job_metrics
from components.bulk_lookup import render_bulk_lookup
from components.parts_inventory import render_parts_inventory
from src.zuper_api.client import get_zuper_client, is_zuper_configured, ZuperAPINotConfiguredError
from src.sync.sync_manager import SyncManager
from utils.language import Language
from utils.formatters import format_datetime, format_status, status_badge
from utils.gps_helpers import format_map_data, get_center_point
from config.settings import AppSettings, FeatureFlags

# Initialize database on startup
try:
    init_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.warning(f"Database initialization skipped: {e}")


# Page configuration
st.set_page_config(
    page_title="EU Parts Jobs Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize session state variables."""
    if 'language' not in st.session_state:
        st.session_state.language = AppSettings.DEFAULT_LANGUAGE

    if 'selected_job' not in st.session_state:
        st.session_state.selected_job = None

    if 'last_sync' not in st.session_state:
        st.session_state.last_sync = None


def render_sidebar():
    """Render sidebar with navigation and settings."""
    with st.sidebar:
        st.title("EU Parts Jobs")

        # Language selection
        lang = Language(st.session_state.language)
        languages = lang.get_available_languages()

        selected_lang = st.selectbox(
            "Language / Taal",
            options=list(languages.keys()),
            format_func=lambda x: languages[x],
            index=list(languages.keys()).index(st.session_state.language)
        )

        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()

        st.divider()

        # Navigation
        st.subheader(lang.get("dashboard"))

        pages = {
            "Dashboard": "dashboard",
            lang.get("job_lookup"): "job_lookup",
            lang.get("bulk_lookup"): "bulk_lookup",
            lang.get("parts_inventory"): "parts_inventory",
        }

        if FeatureFlags.ENABLE_MANUAL_SYNC:
            pages[lang.get("sync")] = "sync"

        selected_page = st.radio(
            "Navigation",
            options=list(pages.keys()),
            label_visibility="collapsed"
        )

        st.divider()

        # Sync information
        render_sync_info(lang)

        return pages[selected_page], lang


def render_sync_info(lang: Language):
    """
    Render sync information in sidebar.

    Args:
        lang: Language instance for translations
    """
    st.subheader(lang.get("last_sync"))

    try:
        # Try to get last sync info from database
        from src.sync.sync_manager import SyncManager

        class DummyClient:
            pass

        # Create a minimal sync manager just to read sync log
        sync_manager = SyncManager(DummyClient())
        last_sync = sync_manager.get_last_sync_info()

        if last_sync:
            sync_time = last_sync.get('sync_completed') or last_sync.get('sync_started')
            status = last_sync.get('status', 'unknown')

            st.write(f"**Time:** {format_datetime(sync_time)}")
            st.write(f"**Status:** {status}")

            if status == 'completed':
                jobs_created = last_sync.get('jobs_created', 0)
                jobs_updated = last_sync.get('jobs_updated', 0)
                st.write(f"Created: {jobs_created}")
                st.write(f"Updated: {jobs_updated}")
        else:
            st.info("No sync data yet")

    except Exception as e:
        logger.debug(f"Could not fetch sync info: {e}")
        st.info("No sync data yet")


def render_configuration_error():
    """Render configuration error message with setup instructions."""
    st.error("⚠️ Zuper API Not Configured")

    st.markdown("""
    ### Setup Required

    This application requires the Zuper API to be configured:

    **Zuper API Configuration:**
    ```toml
    [zuper]
    api_key = "your-api-key"
    org_uid = "your-organization-uid"
    base_url = "https://us-east-1.zuperpro.com"
    ```

    For Streamlit Cloud, add these in the app settings under "Secrets".
    For local development, create a `.streamlit/secrets.toml` file.

    **Note:** The database uses SQLite and is created automatically.
    """)


def render_dashboard_page(lang: Language):
    """
    Render main dashboard page.

    Args:
        lang: Language instance for translations
    """
    st.title(lang.get("eu_parts_jobs"))

    # Load data
    try:
        with st.spinner(lang.get("loading")):
            jobs_df = JobQueries.get_all_eu_parts_jobs()
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        st.error(f"Failed to load data: {str(e)}")
        st.info("Please check database connection and try again.")
        return

    if jobs_df.empty:
        st.warning(lang.get("no_jobs_found"))
        if is_zuper_configured():
            st.info("Please run a data sync to populate the database.")
        else:
            render_configuration_error()
        return

    # Display metrics
    render_job_metrics(jobs_df)

    st.divider()

    # Filters
    st.subheader(lang.get("filter"))

    col1, col2, col3 = st.columns(3)

    with col1:
        # Status filter
        all_statuses = sorted(jobs_df['job_status'].dropna().unique().tolist())
        selected_statuses = st.multiselect(
            lang.get("status"),
            options=all_statuses,
            default=all_statuses
        )

    with col2:
        # Priority filter
        all_priorities = sorted(jobs_df['priority'].dropna().unique().tolist())
        selected_priorities = st.multiselect(
            lang.get("priority"),
            options=all_priorities,
            default=all_priorities
        )

    with col3:
        # Search
        search_term = st.text_input(
            lang.get("search"),
            placeholder=lang.get("enter_job_number")
        )

    # Apply filters
    filtered_df = jobs_df.copy()

    if selected_statuses:
        filtered_df = filtered_df[filtered_df['job_status'].isin(selected_statuses)]

    if selected_priorities:
        filtered_df = filtered_df[filtered_df['priority'].isin(selected_priorities)]

    if search_term:
        search_term_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df['job_number'].str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['title'].str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['customer_name'].str.lower().str.contains(search_term_lower, na=False)
        ]

    st.divider()

    # Display results
    st.subheader(f"Jobs ({len(filtered_df)} found)")

    if filtered_df.empty:
        st.info(lang.get("no_jobs_found"))
        return

    # Display options
    col1, col2 = st.columns([3, 1])

    with col1:
        view_mode = st.radio(
            "View Mode",
            ["Table", "Cards"],
            horizontal=True
        )

    with col2:
        if FeatureFlags.ENABLE_MAP_VIEW:
            show_map = st.checkbox(lang.get("show_map"))

    # Map view
    if FeatureFlags.ENABLE_MAP_VIEW and show_map:
        render_map_view(filtered_df, lang)

    st.divider()

    # Data display
    if view_mode == "Table":
        render_jobs_table(filtered_df, lang)
    else:
        render_job_list(filtered_df, max_items=20)

    # Export option
    if FeatureFlags.ENABLE_EXPORT:
        st.divider()
        render_export_options(filtered_df, lang)


def render_jobs_table(jobs_df: pd.DataFrame, lang: Language):
    """
    Render jobs as a table.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    display_columns = [
        'job_number',
        'title',
        'job_status',
        'customer_name',
        'scheduled_start_time',
        'priority',
        'parts_status'
    ]

    display_df = jobs_df[display_columns].copy()

    # Format datetime
    display_df['scheduled_start_time'] = display_df['scheduled_start_time'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
    )

    # Format status
    display_df['job_status'] = display_df['job_status'].apply(
        lambda x: format_status(x) if pd.notna(x) else 'Unknown'
    )

    # Rename columns
    display_df.columns = [
        lang.get("job_number"),
        lang.get("title"),
        lang.get("status"),
        lang.get("customer"),
        lang.get("scheduled_start"),
        lang.get("priority"),
        lang.get("parts_status")
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


def render_map_view(jobs_df: pd.DataFrame, lang: Language):
    """
    Render map view of jobs.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader(lang.get("location"))

    # Filter jobs with valid coordinates
    valid_coords = jobs_df[
        jobs_df['latitude'].notna() &
        jobs_df['longitude'].notna()
    ].copy()

    if valid_coords.empty:
        st.info("No location data available for selected jobs")
        return

    # Create map dataframe
    map_df = valid_coords[['latitude', 'longitude']].copy()
    map_df.columns = ['lat', 'lon']

    # Display map
    st.map(map_df, zoom=4)

    st.caption(f"Showing {len(map_df)} jobs with location data")


def render_job_lookup_page(lang: Language):
    """
    Render single job lookup page.

    Args:
        lang: Language instance for translations
    """
    st.title(lang.get("job_lookup"))

    st.markdown("""
    Search for a specific job by job number.
    """)

    # Job number input
    job_number = st.text_input(
        lang.get("enter_job_number"),
        placeholder="JOB-001"
    )

    if st.button(lang.get("search"), type="primary"):
        if job_number:
            search_single_job(job_number.strip(), lang)
        else:
            st.warning("Please enter a job number")


def search_single_job(job_number: str, lang: Language):
    """
    Search for a single job and display results.

    Args:
        job_number: Job number to search for
        lang: Language instance for translations
    """
    with st.spinner(lang.get("loading")):
        job = JobQueries.get_job_by_number(job_number)

        if job:
            st.success(f"Job found: {job_number}")
            st.divider()
            render_job_card(job, show_details=True)
        else:
            st.error(lang.get("job_not_found"))


def render_sync_page(lang: Language):
    """
    Render data sync page.

    Args:
        lang: Language instance for translations
    """
    st.title(lang.get("sync"))

    # Check Zuper API configuration
    if not is_zuper_configured():
        render_configuration_error()
        return

    st.markdown("""
    Synchronize job data from Zuper API to the local database.
    This will fetch all EU parts jobs and update the database.
    """)

    st.warning("""
    **Note:** Sync operations may take several minutes depending on the number of jobs.
    """)

    if st.button(lang.get("sync_now"), type="primary"):
        run_sync(lang)


def run_sync(lang: Language):
    """
    Run data synchronization.

    Args:
        lang: Language instance for translations
    """
    try:
        with st.spinner("Synchronizing data..."):
            # Initialize sync manager
            api_client = get_zuper_client()
            sync_manager = SyncManager(api_client)

            # Run sync
            stats = sync_manager.sync_all_jobs()

            # Display results
            if stats['status'] == 'completed':
                st.success(lang.get("sync_success"))

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Jobs Fetched", stats['jobs_fetched'])

                with col2:
                    st.metric("Jobs Created", stats['jobs_created'])

                with col3:
                    st.metric("Jobs Updated", stats['jobs_updated'])

                if stats.get('errors'):
                    st.warning(f"{len(stats['errors'])} errors occurred during sync")
                    with st.expander("View Errors"):
                        for error in stats['errors']:
                            st.write(f"- {error}")

                # Update session state
                st.session_state.last_sync = stats['completed']

            else:
                st.error(lang.get("sync_failed"))

                if stats.get('errors'):
                    st.error("Errors:")
                    for error in stats['errors']:
                        st.write(f"- {error}")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        st.error(f"Sync failed: {str(e)}")


def render_export_options(jobs_df: pd.DataFrame, lang: Language):
    """
    Render export options.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader(lang.get("export"))

    col1, col2 = st.columns(2)

    with col1:
        csv = jobs_df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"eu_parts_jobs_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col2:
        json_str = jobs_df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="Download as JSON",
            data=json_str,
            file_name=f"eu_parts_jobs_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar and get selected page
    selected_page, lang = render_sidebar()

    # Render selected page
    if selected_page == "dashboard":
        render_dashboard_page(lang)

    elif selected_page == "job_lookup":
        render_job_lookup_page(lang)

    elif selected_page == "bulk_lookup":
        if FeatureFlags.ENABLE_BULK_LOOKUP:
            render_bulk_lookup(lang)
        else:
            st.warning("Bulk lookup is currently disabled")

    elif selected_page == "parts_inventory":
        if FeatureFlags.ENABLE_PARTS_INVENTORY:
            render_parts_inventory(lang)
        else:
            st.warning("Parts inventory is currently disabled")

    elif selected_page == "sync":
        if FeatureFlags.ENABLE_MANUAL_SYNC:
            render_sync_page(lang)
        else:
            st.warning("Manual sync is currently disabled")

    # Footer
    st.divider()
    st.caption(f"EU Parts Job Dashboard | Last updated: {format_datetime(datetime.now())}")


if __name__ == "__main__":
    main()
