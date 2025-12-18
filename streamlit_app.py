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
from database.connection import is_database_configured, DatabaseNotConfiguredError
from components.job_card import render_job_card, render_job_list
from components.bulk_lookup import render_bulk_lookup
from components.parts_inventory import render_parts_inventory
from src.zuper_api.client import get_zuper_client, is_zuper_configured, ZuperAPINotConfiguredError
from src.sync.sync_manager import SyncManager
from utils.language import Language
from utils.formatters import format_datetime, format_status, status_badge
from utils.gps_helpers import format_map_data, get_center_point
from config.settings import AppSettings, FeatureFlags


# Page configuration
st.set_page_config(
    page_title="EU Parts Jobs Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for status tiles
st.markdown("""
<style>
.status-tile {
    padding: 15px 10px;
    border-radius: 10px;
    text-align: center;
    margin: 5px;
    cursor: pointer;
    transition: transform 0.2s;
}
.status-tile:hover {
    transform: scale(1.05);
}
.status-tile h3 {
    margin: 0;
    font-size: 14px;
    color: white;
}
.status-tile p {
    margin: 5px 0 0 0;
    font-size: 24px;
    font-weight: bold;
    color: white;
}
.tile-all { background-color: #607D8B; }
.tile-new-ticket { background-color: #3498db; }
.tile-received-request { background-color: #9b59b6; }
.tile-parts-on-order { background-color: #f39c12; }
.tile-shop-pick-up { background-color: #27ae60; }
.tile-shipped { background-color: #16a085; }
.tile-parts-delivered { background-color: #2ecc71; }
.tile-done { background-color: #2ecc71; }
.tile-canceled { background-color: #95a5a6; }
.tile-selected {
    box-shadow: 0 0 0 3px #fff, 0 0 0 5px #333;
    transform: scale(1.05);
}
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'language' not in st.session_state:
        st.session_state.language = AppSettings.DEFAULT_LANGUAGE
    if 'selected_job' not in st.session_state:
        st.session_state.selected_job = None
    if 'last_sync' not in st.session_state:
        st.session_state.last_sync = None
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = "All"


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
    """Render sync information in sidebar."""
    st.subheader(lang.get("last_sync"))

    if not is_zuper_configured():
        st.info("API not configured")
        return

    try:
        api_client = get_zuper_client()
        sync_manager = SyncManager(api_client)
        last_sync = sync_manager.get_last_sync_info()

        if last_sync:
            sync_time = last_sync.get('sync_completed') or last_sync.get('sync_started')
            status = last_sync.get('status', 'unknown')

            st.write(f"**Time:** {format_datetime(sync_time)}")
            st.write(f"**Status:** {status}")

            if status == 'completed':
                jobs_created = last_sync.get('jobs_created', 0) or 0
                jobs_updated = last_sync.get('jobs_updated', 0) or 0
                st.write(f"Created: {jobs_created}")
                st.write(f"Updated: {jobs_updated}")
        else:
            st.info("No sync yet - click Sync to fetch data")

    except ZuperAPINotConfiguredError:
        st.info("API not configured")
    except Exception as e:
        logger.debug(f"Sync info not available: {e}")
        st.info("No sync data")


def render_status_tiles(jobs_df: pd.DataFrame):
    """
    Render clickable status tiles for filtering.
    Returns the selected status.
    """
    # Get status counts
    status_counts = jobs_df['job_status'].value_counts().to_dict()
    total_jobs = len(jobs_df)

    # Status configuration with colors
    statuses = [
        ("All", total_jobs, "tile-all"),
        ("New Ticket", status_counts.get("New Ticket", 0), "tile-new-ticket"),
        ("Received Request", status_counts.get("Received Request", 0), "tile-received-request"),
        ("Parts On Order", status_counts.get("Parts On Order", 0), "tile-parts-on-order"),
        ("Shop Pick UP", status_counts.get("Shop Pick UP", 0), "tile-shop-pick-up"),
        ("Shipped", status_counts.get("Shipped", 0), "tile-shipped"),
        ("Parts delivered", status_counts.get("Parts delivered", 0), "tile-parts-delivered"),
        ("Done", status_counts.get("Done", 0), "tile-done"),
        ("Canceled", status_counts.get("Canceled", 0), "tile-canceled"),
    ]

    # Create columns for tiles
    cols = st.columns(len(statuses))

    for idx, (status_name, count, css_class) in enumerate(statuses):
        with cols[idx]:
            # Check if this status is selected
            is_selected = st.session_state.status_filter == status_name
            selected_class = "tile-selected" if is_selected else ""

            # Render tile as HTML
            st.markdown(f"""
                <div class="status-tile {css_class} {selected_class}">
                    <h3>{status_name}</h3>
                    <p>{count}</p>
                </div>
            """, unsafe_allow_html=True)

            # Button to select this status (hidden label)
            if st.button("Select", key=f"tile_{status_name}", use_container_width=True):
                st.session_state.status_filter = status_name
                st.rerun()


def render_dashboard_page(lang: Language):
    """Render main dashboard page."""
    st.title(lang.get("eu_parts_jobs"))

    # Load data
    try:
        jobs_df = JobQueries.get_all_eu_parts_jobs()
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        st.error(f"Failed to load data: {str(e)}")
        st.info("Please run a data sync to populate the database.")
        return

    if jobs_df.empty:
        st.warning(lang.get("no_jobs_found"))
        st.info("Please run a data sync to populate the database.")
        return

    # Display status tiles
    render_status_tiles(jobs_df)

    st.divider()

    # Apply status filter
    filtered_df = jobs_df.copy()
    if st.session_state.status_filter != "All":
        filtered_df = filtered_df[filtered_df['job_status'] == st.session_state.status_filter]

    # Search box
    search_term = st.text_input(
        lang.get("search"),
        placeholder=lang.get("enter_job_number")
    )

    if search_term:
        search_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df['job_number'].str.lower().str.contains(search_lower, na=False) |
            filtered_df['title'].str.lower().str.contains(search_lower, na=False) |
            filtered_df['customer_name'].str.lower().str.contains(search_lower, na=False)
        ]

    st.divider()

    # Results header
    st.subheader(f"Jobs ({len(filtered_df)} found)")

    if filtered_df.empty:
        st.info(lang.get("no_jobs_found"))
        return

    # View mode toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        view_mode = st.radio("View Mode", ["Cards", "Table"], horizontal=True)
    with col2:
        if FeatureFlags.ENABLE_MAP_VIEW:
            show_map = st.checkbox(lang.get("show_map"))

    # Map view
    if FeatureFlags.ENABLE_MAP_VIEW and show_map:
        render_map_view(filtered_df, lang)

    st.divider()

    # Display jobs
    if view_mode == "Table":
        render_jobs_table(filtered_df, lang)
    else:
        render_job_list(filtered_df, max_items=20)

    # Export
    if FeatureFlags.ENABLE_EXPORT:
        st.divider()
        render_export_options(filtered_df, lang)


def render_jobs_table(jobs_df: pd.DataFrame, lang: Language):
    """Render jobs as a table."""
    display_columns = [
        'job_number', 'title', 'job_status', 'customer_name',
        'scheduled_start_time', 'priority', 'parts_status'
    ]

    display_df = jobs_df[display_columns].copy()

    display_df['scheduled_start_time'] = display_df['scheduled_start_time'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
    )
    display_df['job_status'] = display_df['job_status'].apply(
        lambda x: format_status(x) if pd.notna(x) else 'Unknown'
    )

    display_df.columns = [
        lang.get("job_number"), lang.get("title"), lang.get("status"),
        lang.get("customer"), lang.get("scheduled_start"),
        lang.get("priority"), lang.get("parts_status")
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_map_view(jobs_df: pd.DataFrame, lang: Language):
    """Render map view of jobs."""
    st.subheader(lang.get("location"))

    valid_coords = jobs_df[
        jobs_df['latitude'].notna() & jobs_df['longitude'].notna()
    ].copy()

    if valid_coords.empty:
        st.info("No location data available")
        return

    map_df = valid_coords[['latitude', 'longitude']].copy()
    map_df.columns = ['lat', 'lon']
    st.map(map_df, zoom=4)
    st.caption(f"Showing {len(map_df)} jobs with location data")


def render_job_lookup_page(lang: Language):
    """Render single job lookup page."""
    st.title(lang.get("job_lookup"))
    st.markdown("Search for a specific job by job number.")

    job_number = st.text_input(lang.get("enter_job_number"), placeholder="JOB-001")

    if st.button(lang.get("search"), type="primary"):
        if job_number:
            job = JobQueries.get_job_by_number(job_number.strip())
            if job:
                st.success(f"Job found: {job_number}")
                st.divider()
                render_job_card(job, show_details=True)
            else:
                st.error(lang.get("job_not_found"))
        else:
            st.warning("Please enter a job number")


def render_sync_page(lang: Language):
    """Render data sync page."""
    st.title(lang.get("sync"))

    if not is_zuper_configured():
        st.error("Zuper API not configured. Please add API credentials to secrets.")
        st.markdown("""
        ### Setup Required
        Add the following to your `.streamlit/secrets.toml`:
        ```toml
        [zuper]
        api_key = "your_zuper_api_key"
        base_url = "https://us-east-1.zuperpro.com/api"
        ```
        """)
        return

    st.markdown("Synchronize job data from Zuper API to the local database.")
    st.warning("**Note:** Sync may take several minutes depending on the number of jobs.")

    if st.button(lang.get("sync_now"), type="primary"):
        try:
            with st.spinner("Synchronizing data..."):
                api_client = get_zuper_client()
                sync_manager = SyncManager(api_client)
                stats = sync_manager.sync_all_jobs()

                if stats['status'] == 'completed':
                    st.success(lang.get("sync_success"))
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Jobs Fetched", stats['jobs_fetched'])
                    col2.metric("Jobs Created", stats['jobs_created'])
                    col3.metric("Jobs Updated", stats['jobs_updated'])

                    if stats.get('errors'):
                        st.warning(f"{len(stats['errors'])} errors occurred")
                        with st.expander("View Errors"):
                            for error in stats['errors']:
                                st.write(f"- {error}")
                else:
                    st.error(lang.get("sync_failed"))
                    if stats.get('errors'):
                        for error in stats['errors']:
                            st.write(f"- {error}")

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            st.error(f"Sync failed: {str(e)}")


def render_export_options(jobs_df: pd.DataFrame, lang: Language):
    """Render export options."""
    st.subheader(lang.get("export"))
    col1, col2 = st.columns(2)

    with col1:
        csv = jobs_df.to_csv(index=False)
        st.download_button(
            "Download as CSV", csv,
            f"eu_parts_jobs_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

    with col2:
        json_str = jobs_df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            "Download as JSON", json_str,
            f"eu_parts_jobs_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json"
        )


def main():
    """Main application entry point."""
    initialize_session_state()
    selected_page, lang = render_sidebar()

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

    st.divider()
    st.caption(f"EU Parts Job Dashboard | Last updated: {format_datetime(datetime.now())}")


if __name__ == "__main__":
    main()
