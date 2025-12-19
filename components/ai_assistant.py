"""
AI Assistant component for the Jacco Parts Dashboard.
Provides natural language search and intelligent assistance.
"""

import streamlit as st
import logging
from typing import Dict, List, Any, Optional

from config.settings import AppSettings, FeatureFlags

logger = logging.getLogger(__name__)


def is_ai_available() -> bool:
    """Check if AI features are available and configured."""
    if not FeatureFlags.ENABLE_AI_ASSISTANT:
        return False

    try:
        from src.anthropic_api import is_anthropic_configured
        return is_anthropic_configured()
    except ImportError:
        return False


def get_ai_client():
    """Get the Anthropic client instance."""
    try:
        from src.anthropic_api import get_anthropic_client
        return get_anthropic_client()
    except Exception as e:
        logger.error(f"Failed to get AI client: {e}")
        return None


def render_ai_search_bar(
    available_statuses: List[str],
    available_priorities: List[str],
    available_customers: List[str] = None,
    key_prefix: str = "ai_search"
) -> Optional[Dict[str, Any]]:
    """
    Render an AI-powered natural language search bar.

    Args:
        available_statuses: List of valid job statuses
        available_priorities: List of valid priority levels
        available_customers: List of customer names
        key_prefix: Unique key prefix for Streamlit widgets

    Returns:
        Parsed filter dictionary if search performed, None otherwise
    """
    if not is_ai_available():
        return None

    # Initialize session state
    if f"{key_prefix}_query" not in st.session_state:
        st.session_state[f"{key_prefix}_query"] = ""
    if f"{key_prefix}_result" not in st.session_state:
        st.session_state[f"{key_prefix}_result"] = None

    st.markdown("### AI Search")
    st.caption("Search using natural language, e.g., 'urgent jobs waiting for parts' or 'jobs for Customer ABC shipped last week'")

    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "Search",
            placeholder="What are you looking for?",
            key=f"{key_prefix}_input",
            label_visibility="collapsed"
        )

    with col2:
        search_clicked = st.button("Search", key=f"{key_prefix}_button", type="primary")

    if search_clicked and query:
        with st.spinner("Understanding your search..."):
            client = get_ai_client()
            if client:
                result = client.parse_natural_language_search(
                    query=query,
                    available_statuses=available_statuses,
                    available_priorities=available_priorities,
                    available_customers=available_customers
                )

                st.session_state[f"{key_prefix}_result"] = result

                if result.get("success"):
                    st.info(f"**{result.get('explanation', 'Filters applied')}**")
                    return result.get("filters", {})
                else:
                    st.warning(result.get("explanation", "Could not understand the search. Try different wording."))
            else:
                st.error("AI service unavailable")

    # Return cached result if exists
    if st.session_state[f"{key_prefix}_result"]:
        return st.session_state[f"{key_prefix}_result"].get("filters", {})

    return None


def render_ai_chat(
    context: Dict[str, Any] = None,
    key_prefix: str = "ai_chat"
):
    """
    Render an AI chat interface.

    Args:
        context: Dashboard context (job stats, current filters, etc.)
        key_prefix: Unique key prefix for Streamlit widgets
    """
    if not is_ai_available():
        st.info("AI Assistant is not configured. Add your Anthropic API key to enable.")
        return

    # Initialize chat history
    if f"{key_prefix}_history" not in st.session_state:
        st.session_state[f"{key_prefix}_history"] = []

    st.markdown("### AI Assistant")
    st.caption("Ask questions about your jobs, get insights, or request analysis")

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state[f"{key_prefix}_history"]:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Assistant:** {msg['content']}")
                if msg.get("action"):
                    with st.expander("View parsed action"):
                        st.json(msg["action"])

    # Chat input
    user_input = st.chat_input("Ask something...", key=f"{key_prefix}_input")

    if user_input:
        # Add user message to history
        st.session_state[f"{key_prefix}_history"].append({
            "role": "user",
            "content": user_input
        })

        with st.spinner("Thinking..."):
            client = get_ai_client()
            if client:
                # Convert history to API format
                api_history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in st.session_state[f"{key_prefix}_history"][:-1]
                ]

                response = client.chat(
                    message=user_input,
                    context=context,
                    conversation_history=api_history
                )

                if response.get("success"):
                    assistant_msg = {
                        "role": "assistant",
                        "content": response["response"],
                        "action": response.get("action")
                    }
                    st.session_state[f"{key_prefix}_history"].append(assistant_msg)
                else:
                    st.session_state[f"{key_prefix}_history"].append({
                        "role": "assistant",
                        "content": response.get("response", "Sorry, I encountered an error.")
                    })

        st.rerun()

    # Clear chat button
    if st.session_state[f"{key_prefix}_history"]:
        if st.button("Clear Chat", key=f"{key_prefix}_clear"):
            st.session_state[f"{key_prefix}_history"] = []
            st.rerun()


def render_job_analysis(job_data: Dict, key_prefix: str = "job_analysis"):
    """
    Render AI analysis of a specific job.

    Args:
        job_data: Job dictionary from database
        key_prefix: Unique key prefix for Streamlit widgets
    """
    if not is_ai_available():
        return

    if st.button("Analyze with AI", key=f"{key_prefix}_btn"):
        with st.spinner("Analyzing job..."):
            client = get_ai_client()
            if client:
                result = client.analyze_job(job_data)

                if result.get("success"):
                    st.markdown("#### AI Analysis")
                    st.markdown(result["analysis"])
                else:
                    st.error("Could not analyze job")


def render_parts_extraction(description: str, key_prefix: str = "parts_extract"):
    """
    Render parts information extraction from job description.

    Args:
        description: Job description text
        key_prefix: Unique key prefix for Streamlit widgets
    """
    if not is_ai_available() or not description:
        return None

    if st.button("Extract Parts Info", key=f"{key_prefix}_btn"):
        with st.spinner("Extracting parts information..."):
            client = get_ai_client()
            if client:
                result = client.extract_parts_info(description)

                if result.get("success"):
                    st.markdown("#### Extracted Parts Information")

                    if result.get("parts_mentioned"):
                        st.markdown(f"**Parts:** {', '.join(result['parts_mentioned'])}")

                    if result.get("part_numbers"):
                        st.markdown(f"**Part Numbers:** {', '.join(result['part_numbers'])}")

                    if result.get("quantities"):
                        st.markdown(f"**Quantities:** {', '.join(result['quantities'])}")

                    if result.get("urgency_indicators"):
                        st.warning(f"**Urgency:** {', '.join(result['urgency_indicators'])}")

                    if result.get("summary"):
                        st.info(result["summary"])

                    return result

    return None


def render_summary_generator(
    jobs_data: List[Dict],
    key_prefix: str = "summary"
):
    """
    Render a summary report generator.

    Args:
        jobs_data: List of job dictionaries
        key_prefix: Unique key prefix for Streamlit widgets
    """
    if not is_ai_available():
        return

    st.markdown("### Generate Summary Report")

    col1, col2 = st.columns([3, 1])

    with col1:
        summary_type = st.selectbox(
            "Report Type",
            options=["daily", "weekly", "status"],
            format_func=lambda x: x.title() + " Summary",
            key=f"{key_prefix}_type"
        )

    with col2:
        generate_clicked = st.button(
            "Generate",
            key=f"{key_prefix}_btn",
            type="primary"
        )

    if generate_clicked:
        with st.spinner("Generating summary..."):
            client = get_ai_client()
            if client:
                result = client.generate_summary(
                    jobs_data=jobs_data,
                    summary_type=summary_type
                )

                if result.get("success"):
                    st.markdown("---")
                    st.markdown(result["summary"])

                    with st.expander("View Statistics"):
                        st.json(result.get("stats", {}))
                else:
                    st.error("Could not generate summary")


def render_ai_sidebar_status():
    """Render AI status indicator in sidebar."""
    if is_ai_available():
        st.sidebar.success("AI Assistant: Connected")
    elif FeatureFlags.ENABLE_AI_ASSISTANT:
        st.sidebar.warning("AI Assistant: Not configured")
