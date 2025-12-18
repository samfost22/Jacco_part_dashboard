"""
Parts inventory component.
Displays parts-related information and statistics.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from database.queries import JobQueries
from database.connection import is_database_configured
from utils.formatters import format_datetime, format_status, status_badge
from utils.language import Language


def render_parts_inventory(lang: Language):
    """
    Render parts inventory and status overview.

    Args:
        lang: Language instance for translations
    """
    st.header(lang.get("parts_inventory"))

    # Check if database is configured
    if not is_database_configured():
        st.error("Database not configured. Please add database secrets.")
        return

    st.markdown("""
    Overview of parts status across all EU jobs.
    """)

    # Load data
    with st.spinner(lang.get("loading")):
        jobs_df = JobQueries.get_all_eu_parts_jobs()

        if jobs_df.empty:
            st.warning(lang.get("no_jobs_found"))
            return

        # Display parts metrics
        render_parts_metrics(jobs_df, lang)

        st.divider()

        # Parts status breakdown
        render_parts_status_breakdown(jobs_df, lang)

        st.divider()

        # Jobs by parts delivery date
        render_parts_delivery_timeline(jobs_df, lang)

        st.divider()

        # Jobs waiting for parts
        render_jobs_waiting_for_parts(jobs_df, lang)


def render_parts_metrics(jobs_df: pd.DataFrame, lang: Language):
    """
    Render parts-related metrics.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader("Parts Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_jobs = len(jobs_df)
        st.metric(lang.get("total_jobs"), total_jobs)

    with col2:
        # Jobs with parts delivered
        parts_delivered = len(jobs_df[jobs_df['parts_delivered_date'].notna()])
        st.metric(lang.get("parts_delivered_count"), parts_delivered)

    with col3:
        # Jobs waiting for parts
        parts_pending = len(jobs_df[jobs_df['parts_delivered_date'].isna()])
        st.metric(lang.get("parts_pending"), parts_pending)

    with col4:
        # Delivery rate
        if total_jobs > 0:
            delivery_rate = (parts_delivered / total_jobs) * 100
            st.metric("Delivery Rate", f"{delivery_rate:.1f}%")
        else:
            st.metric("Delivery Rate", "N/A")


def render_parts_status_breakdown(jobs_df: pd.DataFrame, lang: Language):
    """
    Render breakdown of jobs by parts status.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader("Parts Status Breakdown")

    # Count by parts status
    if 'parts_status' in jobs_df.columns:
        status_counts = jobs_df['parts_status'].value_counts()

        if not status_counts.empty:
            # Create a bar chart
            st.bar_chart(status_counts)

            # Display as table
            status_df = pd.DataFrame({
                'Parts Status': status_counts.index,
                'Count': status_counts.values
            })

            st.dataframe(status_df, use_container_width=True, hide_index=True)
        else:
            st.info("No parts status data available")
    else:
        st.info("Parts status information not available")


def render_parts_delivery_timeline(jobs_df: pd.DataFrame, lang: Language):
    """
    Render timeline of parts deliveries.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader("Parts Delivery Timeline")

    # Filter jobs with delivered parts
    delivered_jobs = jobs_df[jobs_df['parts_delivered_date'].notna()].copy()

    if delivered_jobs.empty:
        st.info("No parts delivery data available")
        return

    # Sort by delivery date
    delivered_jobs = delivered_jobs.sort_values('parts_delivered_date', ascending=False)

    # Display recent deliveries
    st.write(f"Recent parts deliveries (showing last 10)")

    recent_deliveries = delivered_jobs.head(10)

    for _, job in recent_deliveries.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

        with col1:
            st.write(f"**{job.get('job_number', 'N/A')}**")

        with col2:
            st.write(job.get('customer_name', 'N/A'))

        with col3:
            delivery_date = format_datetime(job.get('parts_delivered_date'), date_only=True)
            st.write(f"Delivered: {delivery_date}")

        with col4:
            status = job.get('job_status', 'Unknown')
            st.markdown(status_badge(format_status(status)), unsafe_allow_html=True)


def render_jobs_waiting_for_parts(jobs_df: pd.DataFrame, lang: Language):
    """
    Render list of jobs waiting for parts.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader("Jobs Waiting for Parts")

    # Filter jobs without parts delivered
    waiting_jobs = jobs_df[jobs_df['parts_delivered_date'].isna()].copy()

    if waiting_jobs.empty:
        st.success("No jobs waiting for parts!")
        return

    # Sort by scheduled start time
    waiting_jobs = waiting_jobs.sort_values('scheduled_start_time', ascending=True)

    st.write(f"**{len(waiting_jobs)} jobs waiting for parts**")

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        # Filter by status
        all_statuses = ['All'] + sorted(waiting_jobs['job_status'].unique().tolist())
        selected_status = st.selectbox(
            lang.get("status"),
            all_statuses
        )

    with col2:
        # Filter by priority
        all_priorities = ['All'] + sorted(waiting_jobs['priority'].dropna().unique().tolist())
        selected_priority = st.selectbox(
            lang.get("priority"),
            all_priorities
        )

    # Apply filters
    filtered_jobs = waiting_jobs.copy()

    if selected_status != 'All':
        filtered_jobs = filtered_jobs[filtered_jobs['job_status'] == selected_status]

    if selected_priority != 'All':
        filtered_jobs = filtered_jobs[filtered_jobs['priority'] == selected_priority]

    # Display filtered jobs
    st.write(f"Showing {len(filtered_jobs)} jobs")

    # Display as table
    display_columns = [
        'job_number',
        'title',
        'customer_name',
        'scheduled_start_time',
        'job_status',
        'priority',
        'parts_status'
    ]

    display_df = filtered_jobs[display_columns].copy()

    # Format datetime
    display_df['scheduled_start_time'] = display_df['scheduled_start_time'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
    )

    # Rename columns
    display_df.columns = [
        lang.get("job_number"),
        lang.get("title"),
        lang.get("customer"),
        lang.get("scheduled_start"),
        lang.get("status"),
        lang.get("priority"),
        lang.get("parts_status")
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # Export option
    st.divider()

    csv = filtered_jobs.to_csv(index=False)
    st.download_button(
        label="Export Waiting Jobs as CSV",
        data=csv,
        file_name="jobs_waiting_for_parts.csv",
        mime="text/csv"
    )
