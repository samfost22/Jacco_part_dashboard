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
from components.ai_assistant import (
    is_ai_available,
    render_ai_search_bar,
    render_ai_chat,
    render_ai_sidebar_status,
    render_summary_generator
)
from src.zuper_api.client import get_zuper_client, is_zuper_configured, ZuperAPINotConfiguredError
from src.sync.sync_manager import SyncManager
from utils.language import Language
from utils.formatters import format_datetime, format_status, status_badge
from utils.gps_helpers import format_map_data, get_center_point
from config.settings import AppSettings, FeatureFlags

# Database is automatically initialized when first connection is made
# via get_db_connection() in database/connection.py


# Page configuration
st.set_page_config(
    page_title="EU Parts Jobs Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for improved dashboard styling
st.markdown("""
<style>
/* Status tiles - centered content */
.status-tile {
    padding: 20px 16px;
    border-radius: 14px;
    text-align: center;
    margin: 6px 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 3px 6px rgba(0,0,0,0.12);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 140px;
}
.status-tile:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.18);
}
.status-tile .icon {
    font-size: 28px;
    margin-bottom: 10px;
    line-height: 1;
    display: block;
}
.status-tile h3 {
    margin: 0;
    padding: 0;
    font-size: 15px;
    font-weight: 700;
    color: white;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    line-height: 1;
    display: block;
}
.status-tile p {
    margin: 12px 0 0 0;
    padding: 0;
    font-size: 42px;
    font-weight: 800;
    color: white;
    line-height: 1;
    display: block;
}

/* Status tile colors - clearer progression */
.tile-all { background: linear-gradient(135deg, #546E7A, #607D8B); }
.tile-new { background: linear-gradient(135deg, #1976D2, #2196F3); }
.tile-received { background: linear-gradient(135deg, #7B1FA2, #9C27B0); }
.tile-ordered { background: linear-gradient(135deg, #F57C00, #FF9800); }
.tile-pickup { background: linear-gradient(135deg, #00838F, #00ACC1); }
.tile-shipped { background: linear-gradient(135deg, #00796B, #009688); }
.tile-delivered { background: linear-gradient(135deg, #388E3C, #4CAF50); }
.tile-done { background: linear-gradient(135deg, #2E7D32, #43A047); }
.tile-canceled { background: linear-gradient(135deg, #757575, #9E9E9E); }

.tile-selected {
    box-shadow: 0 0 0 3px #fff, 0 0 0 5px #1a1a1a !important;
    transform: translateY(-2px) scale(1.02);
}

/* Hide the Select button text and make it overlay the tile */
.tile-button button {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
}
.tile-button {
    position: relative;
}
.tile-button > div:first-child {
    position: relative;
}
.tile-button > div:last-child button {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 160px;
    margin-top: -160px;
    opacity: 0;
    cursor: pointer;
}

/* Job cards - cleaner look */
.job-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    border-left: 4px solid #2196F3;
}

/* Better table styling */
.dataframe {
    font-size: 14px !important;
}

/* Sidebar improvements */
section[data-testid="stSidebar"] {
    background-color: #f5f5f5;
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
        }

        # Add AI Assistant page if available
        if FeatureFlags.ENABLE_AI_ASSISTANT and is_ai_available():
            pages["AI Assistant"] = "ai_assistant"

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

        # AI status indicator
        if FeatureFlags.ENABLE_AI_ASSISTANT:
            st.divider()
            render_ai_sidebar_status()

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
    Uses icons and simple labels for better UX.
    """
    # Get status counts
    status_counts = jobs_df['job_status'].value_counts().to_dict()
    total_jobs = len(jobs_df)

    # Status configuration: (display_label, api_status, icon, css_class)
    # Using simple labels with icons for clarity
    statuses = [
        ("All", "All", "📋", "tile-all", total_jobs),
        ("New", "New Ticket", "🆕", "tile-new", status_counts.get("New Ticket", 0)),
        ("Received Request", "Received Request", "📥", "tile-received", status_counts.get("Received Request", 0)),
        ("Ordered", "Parts On Order", "🛒", "tile-ordered", status_counts.get("Parts On Order", 0)),
        ("Pickup", "Shop Pick UP", "🏪", "tile-pickup", status_counts.get("Shop Pick UP", 0)),
        ("Shipped", "Shipped", "📦", "tile-shipped", status_counts.get("Shipped", 0)),
        ("Delivered", "Parts delivered", "✅", "tile-delivered", status_counts.get("Parts delivered", 0)),
        ("Done", "Done", "🎉", "tile-done", status_counts.get("Done", 0)),
        ("Canceled", "Canceled", "⊘", "tile-canceled", status_counts.get("Canceled", 0)),
    ]

    # Display in 2 rows for better readability
    # Row 1: All, New, Received, Ordered, Pickup
    row1 = statuses[:5]
    cols1 = st.columns(5)
    for idx, (label, api_status, icon, css_class, count) in enumerate(row1):
        with cols1[idx]:
            is_selected = st.session_state.status_filter == api_status
            selected_class = "tile-selected" if is_selected else ""
            # Clickable tile - button overlays the tile
            if st.button(f"{icon}\n{label}\n{count}", key=f"tile_{api_status}", use_container_width=True, type="secondary"):
                st.session_state.status_filter = api_status
                st.rerun()
            # Visual tile overlay
            st.markdown(f"""
                <style>
                div[data-testid="stButton"]:has(button[key="tile_{api_status}"]) button {{
                    background: {'linear-gradient(135deg, #546E7A, #607D8B)' if css_class == 'tile-all' else
                                'linear-gradient(135deg, #1976D2, #2196F3)' if css_class == 'tile-new' else
                                'linear-gradient(135deg, #7B1FA2, #9C27B0)' if css_class == 'tile-received' else
                                'linear-gradient(135deg, #F57C00, #FF9800)' if css_class == 'tile-ordered' else
                                'linear-gradient(135deg, #00838F, #00ACC1)' if css_class == 'tile-pickup' else
                                'linear-gradient(135deg, #00796B, #009688)' if css_class == 'tile-shipped' else
                                'linear-gradient(135deg, #388E3C, #4CAF50)' if css_class == 'tile-delivered' else
                                'linear-gradient(135deg, #2E7D32, #43A047)' if css_class == 'tile-done' else
                                'linear-gradient(135deg, #757575, #9E9E9E)'} !important;
                    color: white !important;
                    border: none !important;
                    min-height: 140px !important;
                    font-size: 14px !important;
                    font-weight: 700 !important;
                    white-space: pre-line !important;
                    {'box-shadow: 0 0 0 3px #fff, 0 0 0 5px #1a1a1a !important; transform: scale(1.02);' if is_selected else ''}
                }}
                </style>
            """, unsafe_allow_html=True)

    # Row 2: Shipped, Delivered, Done, Canceled
    row2 = statuses[5:]
    cols2 = st.columns([1, 1, 1, 1, 1])
    for idx, (label, api_status, icon, css_class, count) in enumerate(row2):
        with cols2[idx]:
            is_selected = st.session_state.status_filter == api_status
            selected_class = "tile-selected" if is_selected else ""
            # Clickable tile - button overlays the tile
            if st.button(f"{icon}\n{label}\n{count}", key=f"tile_{api_status}", use_container_width=True, type="secondary"):
                st.session_state.status_filter = api_status
                st.rerun()
            # Visual tile overlay
            st.markdown(f"""
                <style>
                div[data-testid="stButton"]:has(button[key="tile_{api_status}"]) button {{
                    background: {'linear-gradient(135deg, #00796B, #009688)' if css_class == 'tile-shipped' else
                                'linear-gradient(135deg, #388E3C, #4CAF50)' if css_class == 'tile-delivered' else
                                'linear-gradient(135deg, #2E7D32, #43A047)' if css_class == 'tile-done' else
                                'linear-gradient(135deg, #757575, #9E9E9E)'} !important;
                    color: white !important;
                    border: none !important;
                    min-height: 140px !important;
                    font-size: 14px !important;
                    font-weight: 700 !important;
                    white-space: pre-line !important;
                    {'box-shadow: 0 0 0 3px #fff, 0 0 0 5px #1a1a1a !important; transform: scale(1.02);' if is_selected else ''}
                }}
                </style>
            """, unsafe_allow_html=True)


def render_configuration_error():
    """Render configuration error message."""
    st.error("Configuration required")
    st.markdown("""
    ### Setup Required
    Please configure the Zuper API credentials in `.streamlit/secrets.toml`:
    ```toml
    [zuper]
    api_key = "your_zuper_api_key"
    base_url = "https://us-east-1.zuperpro.com/api"
    ```
    """)


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
        if is_zuper_configured():
            st.info("Please run a data sync to populate the database.")
        else:
            render_configuration_error()
        return

    # Display status tiles
    render_status_tiles(jobs_df)

    st.divider()

    # Apply status filter
    filtered_df = jobs_df.copy()
    if st.session_state.status_filter != "All":
        filtered_df = filtered_df[filtered_df['job_status'] == st.session_state.status_filter]

    # AI Search (if available)
    ai_filters = None
    if FeatureFlags.ENABLE_AI_SEARCH and is_ai_available():
        customers = jobs_df['customer_name'].dropna().unique().tolist()
        ai_filters = render_ai_search_bar(
            available_statuses=AppSettings.JOB_STATUSES,
            available_priorities=AppSettings.PRIORITY_LEVELS,
            available_customers=customers
        )

        if ai_filters:
            # Apply AI-parsed filters
            if ai_filters.get("status"):
                filtered_df = filtered_df[filtered_df['job_status'].isin(ai_filters["status"])]
            if ai_filters.get("priority"):
                filtered_df = filtered_df[filtered_df['priority'].isin(ai_filters["priority"])]
            if ai_filters.get("customer"):
                customer_filter = ai_filters["customer"].lower()
                filtered_df = filtered_df[
                    filtered_df['customer_name'].str.lower().str.contains(customer_filter, na=False)
                ]
            if ai_filters.get("search_text"):
                search_text = ai_filters["search_text"].lower()
                filtered_df = filtered_df[
                    filtered_df['title'].str.lower().str.contains(search_text, na=False) |
                    filtered_df['description'].str.lower().str.contains(search_text, na=False)
                ]

        st.divider()

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
        show_map = False
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


def render_ai_assistant_page(lang: Language):
    """Render AI assistant page with chat and summary generation."""
    st.title("AI Assistant")
    st.markdown("Chat with AI to get insights about your parts jobs, generate reports, or ask questions.")

    # Load job data for context
    try:
        jobs_df = JobQueries.get_all_eu_parts_jobs()
        jobs_list = jobs_df.to_dict('records') if not jobs_df.empty else []

        # Build context for AI
        status_counts = jobs_df['job_status'].value_counts().to_dict() if not jobs_df.empty else {}
        context = {
            "total_jobs": len(jobs_df),
            "status_counts": status_counts,
            "current_filters": None
        }

    except Exception as e:
        logger.error(f"Error loading jobs for AI: {e}")
        jobs_list = []
        context = {"total_jobs": 0, "status_counts": {}}

    # Two-column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        render_ai_chat(context=context)

    with col2:
        st.markdown("### Quick Actions")

        # Summary generator
        if jobs_list:
            render_summary_generator(jobs_list)

        st.divider()

        # Quick stats
        st.markdown("### Current Stats")
        if context.get("total_jobs"):
            st.metric("Total Jobs", context["total_jobs"])

            if context.get("status_counts"):
                st.markdown("**By Status:**")
                for status, count in sorted(context["status_counts"].items(), key=lambda x: -x[1])[:5]:
                    st.write(f"- {status}: {count}")


def main():
    """Main application entry point."""
    initialize_session_state()
    selected_page, lang = render_sidebar()

    if selected_page == "dashboard":
        render_dashboard_page(lang)
    elif selected_page == "job_lookup":
        render_job_lookup_page(lang)
    elif selected_page == "ai_assistant":
        if FeatureFlags.ENABLE_AI_ASSISTANT and is_ai_available():
            render_ai_assistant_page(lang)
        else:
            st.warning("AI Assistant is not available. Please configure your Anthropic API key.")
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
