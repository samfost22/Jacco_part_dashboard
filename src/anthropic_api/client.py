"""
Anthropic API client for AI-powered dashboard features.
Provides natural language search, job analysis, and intelligent assistance.
"""

import logging
from typing import Dict, List, Optional, Any
import json
import streamlit as st

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class AnthropicNotConfiguredError(Exception):
    """Raised when Anthropic API configuration is missing."""
    pass


def is_anthropic_configured() -> bool:
    """Check if Anthropic API secrets are configured."""
    if not ANTHROPIC_AVAILABLE:
        return False
    try:
        anthropic_config = st.secrets.get("anthropic", {})
        return "api_key" in anthropic_config and anthropic_config["api_key"]
    except Exception:
        return False


class AnthropicClient:
    """
    Client for interacting with Anthropic API.
    Provides AI-powered features for the dashboard.
    """

    # System prompt for the assistant
    SYSTEM_PROMPT = """You are Jacco's Shop Assistant for Carbon Robotics EU operations in Nijkerk, Netherlands.

## JACCO'S ROLE:
- Shop Manager reporting to Sam Foster (Director of Global Supply Chain)
- Manages EU service tickets in Nijkerk
- Coordinates with Monzer (EU Operations) and Bobby (US Shop)

## YOUR DATA SOURCE:
Zuper tickets dashboard showing EU tickets WAITING ON PARTS
- You can see: Ticket details, customer, equipment, days waiting, parts needed
- You CANNOT see: Parts inventory, shipping status, part quantities, ETAs

## YOUR JOB:
Help Jacco PRIORITIZE which tickets to investigate and prepare for. You help him decide what to check on with Sam, what to prep, and what order to tackle his backlog.

## COMMUNICATION STYLE:
- Direct and scannable (Jacco needs quick triage)
- Action-oriented ("Check parts for ticket X" not "Parts might be available")
- Visual indicators: 🔴 urgent, 🟡 medium, ⚠️ investigate, 📋 pattern
- No speculation about parts availability

## PRIORITIZATION FACTORS:
1. Days waiting (>10 days = urgent check with Sam)
2. Customer criticality (if known)
3. Equipment type (Reaper/Slayer in peak season)
4. Multiple tickets needing same part (bulk action)
5. Serialized module mentions (Sam's concern)

## KEY PARTS TO HIGHLIGHT (Sam's tracked items):
CR-SM-004112, 004169, 003484, 003869, 002904, 003281, 003974, 003791

## RESPONSE FORMAT:
[Priority tier] → [Ticket ID] → [Why priority] → [Action for Jacco]

## ACTIONS YOU SUGGEST:
✅ "Check with Sam on parts availability"
✅ "Verify parts in Nijkerk before starting"
✅ "Coordinate with Bobby on US shipment"
✅ "Prep workspace while waiting on parts"
✅ "Contact customer for updated timeline"
✅ "Flag serialized module issue to Sam"

## NEVER SAY:
❌ "Parts are in stock" (you don't know)
❌ "Ready to start" (can't confirm without inventory)
❌ "ETA is X" (no shipping data)
❌ "You have enough parts" (no quantity data)

## PATTERN DETECTION:
If multiple tickets need same part → Flag for Sam
Example: "📋 3 tickets waiting on CR-SM-004112 - batch check with Sam?"

## URGENCY FLAGS FOR SAM:
⚠️ Tickets waiting >10 days
⚠️ Multiple tickets blocking on same part
⚠️ Serialized module mentions
⚠️ Peak season customer impacts

## DATABASE FIELDS AVAILABLE:
- job_number: Ticket ID
- title: Ticket title
- description: Full description (may contain part numbers)
- job_status: Current status (New Ticket, Received Request, Parts On Order, Shop Pick UP, Shipped, Parts delivered, Done, Canceled)
- priority: Urgent, High, Medium, Normal, Low
- asset_name: Equipment/asset name
- scheduled_start_time: When job is scheduled
- created_time: When ticket was created (use to calculate days waiting)

## SEARCH/FILTER RESPONSES:
When asked to search or filter, respond with JSON:
```json
{
    "action": "filter",
    "filters": {
        "status": ["Parts On Order"],
        "priority": ["Urgent", "High"],
        "search_text": "CR-SM-004112"
    },
    "explanation": "Showing urgent tickets waiting on tracked part CR-SM-004112"
}
```"""

    def __init__(self, api_key: str = None):
        """
        Initialize Anthropic API client.

        Args:
            api_key: Anthropic API key (from secrets if not provided)

        Raises:
            AnthropicNotConfiguredError: If API is not configured
        """
        if not ANTHROPIC_AVAILABLE:
            raise AnthropicNotConfiguredError(
                "Anthropic package not installed. Run: pip install anthropic"
            )

        if not api_key and not is_anthropic_configured():
            raise AnthropicNotConfiguredError(
                "Anthropic API key not configured. Please add anthropic configuration to Streamlit secrets."
            )

        anthropic_config = st.secrets.get("anthropic", {})
        self.api_key = api_key or anthropic_config.get("api_key")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

        logger.info("Anthropic client initialized")

    def chat(
        self,
        message: str,
        context: Dict[str, Any] = None,
        conversation_history: List[Dict] = None,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Send a message to Claude and get a response.

        Args:
            message: User message
            context: Additional context (job stats, current filters, etc.)
            conversation_history: Previous messages in conversation
            max_tokens: Maximum response tokens

        Returns:
            Dictionary with response and any parsed actions
        """
        # Build context-aware system prompt
        system = self.SYSTEM_PROMPT

        if context:
            system += f"\n\n## Current Dashboard Context\n"
            if context.get("total_jobs"):
                system += f"- Total jobs in database: {context['total_jobs']}\n"
            if context.get("status_counts"):
                system += f"- Jobs by status: {json.dumps(context['status_counts'])}\n"
            if context.get("current_filters"):
                system += f"- Currently applied filters: {json.dumps(context['current_filters'])}\n"

        # Build messages
        messages = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages
            )

            response_text = response.content[0].text

            # Try to parse JSON action from response
            action = self._parse_action(response_text)

            return {
                "success": True,
                "response": response_text,
                "action": action,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"Sorry, I encountered an error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"An unexpected error occurred: {str(e)}"
            }

    def _parse_action(self, response_text: str) -> Optional[Dict]:
        """
        Try to extract a JSON action from the response.

        Args:
            response_text: Claude's response text

        Returns:
            Parsed action dictionary or None
        """
        try:
            # Look for JSON in response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # Try to find inline JSON object
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    def parse_natural_language_search(
        self,
        query: str,
        available_statuses: List[str],
        available_priorities: List[str],
        available_customers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Parse a natural language search query into filter parameters.

        Args:
            query: Natural language search query
            available_statuses: List of valid job statuses
            available_priorities: List of valid priority levels
            available_customers: List of customer names (optional)

        Returns:
            Dictionary with parsed filters and explanation
        """
        prompt = f"""Parse this search query into filter parameters for the parts dashboard.

Query: "{query}"

Available statuses: {json.dumps(available_statuses)}
Available priorities: {json.dumps(available_priorities)}
{f'Available customers: {json.dumps(available_customers[:20])}' if available_customers else ''}

Respond with ONLY a JSON object (no markdown code blocks) in this format:
{{
    "filters": {{
        "status": ["status1", "status2"],
        "priority": ["priority1"],
        "search_text": "text to search in title/description",
        "customer": "customer name if mentioned"
    }},
    "explanation": "Brief explanation of what will be shown"
}}

Only include filter keys that are relevant to the query. Use exact status/priority names from the lists provided."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse the JSON response
            try:
                # Try direct parse first
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    return {
                        "success": False,
                        "error": "Could not parse search query",
                        "filters": {},
                        "explanation": "Please try rephrasing your search."
                    }

            return {
                "success": True,
                "filters": result.get("filters", {}),
                "explanation": result.get("explanation", "")
            }

        except Exception as e:
            logger.error(f"Error parsing search query: {e}")
            return {
                "success": False,
                "error": str(e),
                "filters": {},
                "explanation": "Could not understand the search query."
            }

    def analyze_job(self, job_data: Dict) -> Dict[str, Any]:
        """
        Analyze a job and provide insights.

        Args:
            job_data: Job dictionary from database

        Returns:
            Analysis results
        """
        prompt = f"""Analyze this parts job and provide brief insights:

Job Details:
- Job Number: {job_data.get('job_number', 'N/A')}
- Title: {job_data.get('title', 'N/A')}
- Description: {job_data.get('description', 'N/A')}
- Status: {job_data.get('job_status', 'N/A')}
- Priority: {job_data.get('priority', 'N/A')}
- Customer: {job_data.get('customer_name', 'N/A')}
- Scheduled: {job_data.get('scheduled_start_time', 'N/A')}
- Parts Status: {job_data.get('parts_status', 'N/A')}

Provide:
1. A brief summary (1-2 sentences)
2. Any potential concerns or delays
3. Recommended next steps

Keep response concise and actionable."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            return {
                "success": True,
                "analysis": response.content[0].text
            }

        except Exception as e:
            logger.error(f"Error analyzing job: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": "Could not analyze job."
            }

    def generate_summary(
        self,
        jobs_data: List[Dict],
        summary_type: str = "daily"
    ) -> Dict[str, Any]:
        """
        Generate a summary report of jobs.

        Args:
            jobs_data: List of job dictionaries
            summary_type: Type of summary (daily, weekly, status)

        Returns:
            Generated summary
        """
        # Aggregate stats
        status_counts = {}
        priority_counts = {}

        for job in jobs_data:
            status = job.get('job_status', 'Unknown')
            priority = job.get('priority', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        prompt = f"""Generate a {summary_type} summary report for the parts dashboard.

Statistics:
- Total Jobs: {len(jobs_data)}
- By Status: {json.dumps(status_counts)}
- By Priority: {json.dumps(priority_counts)}

Provide:
1. Executive summary (2-3 sentences)
2. Key highlights
3. Items requiring attention
4. Recommendations

Format as a professional but concise report."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            return {
                "success": True,
                "summary": response.content[0].text,
                "stats": {
                    "total_jobs": len(jobs_data),
                    "status_counts": status_counts,
                    "priority_counts": priority_counts
                }
            }

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": "Could not generate summary."
            }

    def extract_parts_info(self, description: str) -> Dict[str, Any]:
        """
        Extract parts information from job description.

        Args:
            description: Job description text

        Returns:
            Extracted parts information
        """
        prompt = f"""Extract parts information from this job description:

"{description}"

Return a JSON object with:
{{
    "parts_mentioned": ["list of part names/types mentioned"],
    "part_numbers": ["any part numbers found"],
    "quantities": ["quantities if mentioned"],
    "urgency_indicators": ["any urgency language found"],
    "summary": "brief summary of parts needed"
}}

If no parts info found, return empty lists. Respond with ONLY the JSON object."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            try:
                result = json.loads(response_text)
                return {"success": True, **result}
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                    return {"success": True, **result}
                return {
                    "success": False,
                    "parts_mentioned": [],
                    "summary": "Could not extract parts info"
                }

        except Exception as e:
            logger.error(f"Error extracting parts info: {e}")
            return {
                "success": False,
                "error": str(e),
                "parts_mentioned": [],
                "summary": "Could not extract parts info"
            }

    def test_connection(self) -> bool:
        """
        Test API connection.

        Returns:
            True if connection successful
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            logger.info("Anthropic API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Anthropic API connection test failed: {e}")
            return False


def get_anthropic_client() -> AnthropicClient:
    """
    Get Anthropic API client instance.

    Returns:
        AnthropicClient instance

    Raises:
        AnthropicNotConfiguredError: If API is not configured
    """
    if not is_anthropic_configured():
        raise AnthropicNotConfiguredError(
            "Anthropic API not configured. Please add anthropic configuration to Streamlit secrets."
        )
    return AnthropicClient()
