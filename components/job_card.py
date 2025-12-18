"""
Job card component for displaying individual job information.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd

from utils.formatters import (
    format_datetime,
    format_status,
    format_priority,
    format_coordinates,
    format_address,
    status_badge,
    priority_badge
)
from utils.gps_helpers import validate_coordinates


def render_job_card(job: Dict[str, Any], show_details: bool = True):
    """
    Render a job card with job information.

    Args:
        job: Dictionary containing job data
        show_details: Whether to show detailed information
    """
    if not job:
        st.warning("No job data to display")
        return

    # Main card container
    with st.container():
        # Header row with job number and status
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"Job {job.get('job_number', 'N/A')}")

        with col2:
            status = job.get('job_status', 'Unknown')
            st.markdown(status_badge(format_status(status)), unsafe_allow_html=True)

        # Title and description
        st.markdown(f"**{job.get('title', 'No title')}**")

        if show_details and job.get('description'):
            with st.expander("Description"):
                st.write(job.get('description'))

        # Customer and location info
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Customer Information**")
            st.write(f"Customer: {job.get('customer_name', 'N/A')}")

            if job.get('customer_uid'):
                st.caption(f"Customer UID: {job.get('customer_uid')}")

        with col2:
            st.markdown("**Location**")
            address = format_address(job.get('job_address'), max_length=80)
            st.write(address)

            lat = job.get('latitude')
            lon = job.get('longitude')

            if validate_coordinates(lat, lon):
                st.caption(f"Coordinates: {format_coordinates(lat, lon)}")

        # Schedule and technician info
        if show_details:
            st.divider()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Scheduled Start**")
                st.write(format_datetime(job.get('scheduled_start_time')))

            with col2:
                st.markdown("**Scheduled End**")
                st.write(format_datetime(job.get('scheduled_end_time')))

            with col3:
                st.markdown("**Priority**")
                priority = job.get('priority', 'Normal')
                st.markdown(priority_badge(format_priority(priority)), unsafe_allow_html=True)

        # Technician info
        if show_details and job.get('assigned_technician'):
            st.divider()
            st.markdown("**Assigned Technician**")
            st.write(job.get('assigned_technician', 'Not assigned'))

            if job.get('technician_uid'):
                st.caption(f"Technician UID: {job.get('technician_uid')}")

        # Parts status
        if show_details:
            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Parts Status**")
                parts_status = job.get('parts_status', 'N/A')
                st.write(parts_status)

            with col2:
                st.markdown("**Parts Delivered Date**")
                delivered_date = job.get('parts_delivered_date')
                st.write(format_datetime(delivered_date, date_only=True))

        # Additional metadata
        if show_details:
            with st.expander("Additional Information"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Created:** {format_datetime(job.get('created_time'))}")
                    st.write(f"**Modified:** {format_datetime(job.get('modified_time'))}")

                with col2:
                    st.write(f"**Category:** {job.get('job_category', 'N/A')}")
                    st.write(f"**Last Synced:** {format_datetime(job.get('last_synced'))}")

                # Tags
                if job.get('tags'):
                    st.write(f"**Tags:** {', '.join(job.get('tags', []))}")

        # Map view
        if show_details:
            lat = job.get('latitude')
            lon = job.get('longitude')

            if validate_coordinates(lat, lon):
                st.divider()

                with st.expander("View Location on Map"):
                    # Create map dataframe
                    map_df = pd.DataFrame([{
                        'lat': lat,
                        'lon': lon
                    }])

                    st.map(map_df, zoom=13)


def render_job_list(jobs_df: pd.DataFrame, max_items: int = 10):
    """
    Render a list of jobs as compact cards.

    Args:
        jobs_df: DataFrame with job data
        max_items: Maximum number of items to display
    """
    if jobs_df.empty:
        st.info("No jobs to display")
        return

    st.write(f"Showing {min(len(jobs_df), max_items)} of {len(jobs_df)} jobs")

    # Display jobs
    for idx, (_, job) in enumerate(jobs_df.head(max_items).iterrows()):
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**{job.get('job_number', 'N/A')}**")
                st.caption(job.get('title', 'No title'))

            with col2:
                st.write(job.get('customer_name', 'N/A'))
                st.caption(format_datetime(job.get('scheduled_start_time')))

            with col3:
                status = job.get('job_status', 'Unknown')
                st.markdown(status_badge(format_status(status)), unsafe_allow_html=True)

            # View details button
            if st.button("View Details", key=f"view_{idx}_{job.get('job_uid')}"):
                st.session_state['selected_job'] = job.to_dict()

            st.divider()


def render_job_summary(job: Dict[str, Any]):
    """
    Render a compact job summary (for bulk lookup results).

    Args:
        job: Dictionary containing job data
    """
    with st.container():
        col1, col2, col3, col4 = st.columns([1.5, 2, 1.5, 1])

        with col1:
            st.write(f"**{job.get('job_number', 'N/A')}**")

        with col2:
            st.write(job.get('title', 'No title'))

        with col3:
            st.write(job.get('customer_name', 'N/A'))

        with col4:
            status = job.get('job_status', 'Unknown')
            st.markdown(status_badge(format_status(status)), unsafe_allow_html=True)


def render_job_metrics(jobs_df: pd.DataFrame):
    """
    Render job statistics metrics.

    Args:
        jobs_df: DataFrame with job data
    """
    if jobs_df.empty:
        st.info("No data available for metrics")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_jobs = len(jobs_df)
        st.metric("Total Jobs", total_jobs)

    with col2:
        # Count jobs with parts delivered
        parts_delivered = len(jobs_df[
            jobs_df['parts_delivered_date'].notna()
        ])
        st.metric("Parts Delivered", parts_delivered)

    with col3:
        # Count jobs with parts pending
        parts_pending = len(jobs_df[
            jobs_df['parts_delivered_date'].isna()
        ])
        st.metric("Parts Pending", parts_pending)

    with col4:
        # Count unique statuses
        unique_statuses = jobs_df['job_status'].nunique()
        st.metric("Unique Statuses", unique_statuses)
