"""
Bulk job lookup component.
Allows users to search for multiple jobs at once.
"""

import streamlit as st
import pandas as pd
from typing import List

from database.queries import JobQueries
from components.job_card import render_job_summary, render_job_card
from utils.formatters import format_datetime, format_status
from utils.language import Language


def render_bulk_lookup(lang: Language):
    """
    Render bulk job lookup interface.

    Args:
        lang: Language instance for translations
    """
    st.header(lang.get("bulk_lookup"))

    st.markdown("""
    Search for multiple jobs at once by entering job numbers (one per line).
    """)

    # Text area for entering job numbers
    job_numbers_text = st.text_area(
        lang.get("enter_job_numbers"),
        height=200,
        placeholder="JOB-001\nJOB-002\nJOB-003"
    )

    # Search button
    if st.button(lang.get("search"), type="primary"):
        if job_numbers_text.strip():
            # Parse job numbers
            job_numbers = [
                line.strip()
                for line in job_numbers_text.split('\n')
                if line.strip()
            ]

            if job_numbers:
                search_jobs(job_numbers, lang)
            else:
                st.warning("Please enter at least one job number")
        else:
            st.warning("Please enter job numbers to search")


def search_jobs(job_numbers: List[str], lang: Language):
    """
    Search for jobs and display results.

    Args:
        job_numbers: List of job numbers to search for
        lang: Language instance for translations
    """
    with st.spinner(lang.get("loading")):
        # Query database
        jobs_df = JobQueries.get_jobs_by_numbers(job_numbers)

        if jobs_df.empty:
            st.warning(lang.get("no_jobs_found"))
            return

        # Display summary
        found_count = len(jobs_df)
        total_count = len(job_numbers)

        st.success(f"Found {found_count} out of {total_count} jobs")

        # Show which jobs were not found
        found_numbers = set(jobs_df['job_number'].tolist())
        searched_numbers = set(job_numbers)
        not_found = searched_numbers - found_numbers

        if not_found:
            with st.expander("Jobs not found"):
                for job_num in sorted(not_found):
                    st.write(f"- {job_num}")

        # Display results
        st.divider()

        # Option to view as table or cards
        view_mode = st.radio(
            "View Mode",
            ["Table", "Cards"],
            horizontal=True
        )

        if view_mode == "Table":
            render_results_table(jobs_df, lang)
        else:
            render_results_cards(jobs_df, lang)

        # Export option
        st.divider()
        render_export_options(jobs_df, lang)


def render_results_table(jobs_df: pd.DataFrame, lang: Language):
    """
    Render search results as a table.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    # Select columns to display
    display_columns = [
        'job_number',
        'title',
        'job_status',
        'customer_name',
        'scheduled_start_time',
        'parts_status',
        'job_address'
    ]

    # Create display dataframe
    display_df = jobs_df[display_columns].copy()

    # Format datetime columns
    display_df['scheduled_start_time'] = display_df['scheduled_start_time'].apply(
        lambda x: format_datetime(x) if pd.notna(x) else 'N/A'
    )

    # Format status
    display_df['job_status'] = display_df['job_status'].apply(
        lambda x: format_status(x) if pd.notna(x) else 'Unknown'
    )

    # Rename columns for display
    display_df.columns = [
        lang.get("job_number"),
        lang.get("title"),
        lang.get("status"),
        lang.get("customer"),
        lang.get("scheduled_start"),
        lang.get("parts_status"),
        lang.get("address")
    ]

    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


def render_results_cards(jobs_df: pd.DataFrame, lang: Language):
    """
    Render search results as cards.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    for idx, (_, job) in enumerate(jobs_df.iterrows()):
        with st.expander(f"{job.get('job_number')} - {job.get('title')}"):
            render_job_card(job.to_dict(), show_details=True)


def render_export_options(jobs_df: pd.DataFrame, lang: Language):
    """
    Render export options for search results.

    Args:
        jobs_df: DataFrame with job data
        lang: Language instance for translations
    """
    st.subheader(lang.get("export"))

    col1, col2 = st.columns(2)

    with col1:
        # Export as CSV
        csv = jobs_df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="eu_parts_jobs.csv",
            mime="text/csv"
        )

    with col2:
        # Export as JSON
        json_str = jobs_df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="Download as JSON",
            data=json_str,
            file_name="eu_parts_jobs.json",
            mime="application/json"
        )


def render_job_number_input():
    """
    Render a simple job number input for quick lookup.

    Returns:
        Job number entered by user or None
    """
    job_number = st.text_input(
        "Enter Job Number",
        placeholder="JOB-001"
    )

    if job_number:
        return job_number.strip()

    return None
