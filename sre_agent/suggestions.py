"""Contextual suggestions generation for the SRE Agent.

This module generates dynamic, LLM-based suggestions for the user based on:
1. Conversation history (extracts "Recommended Next Steps" from agent responses)
2. Active alerts in the project
3. Default suggestions when no context is available
"""

import json
import logging
import os
import re
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from .services import get_session_service

logger = logging.getLogger(__name__)

# Default suggestions when no conversation context is available
DEFAULT_SUGGESTIONS = [
    "Analyze recent errors",
    "Check Cloud Run latency",
    "List active alerts",
    "Summarize system health",
]

# Minimum and maximum number of suggestions to return
MIN_SUGGESTIONS = 3
MAX_SUGGESTIONS = 6

# System prompt for generating contextual suggestions
SUGGESTIONS_SYSTEM_PROMPT = """You are an SRE assistant helping users navigate their observability data.
Based on the conversation history provided, generate actionable next step suggestions.

Rules:
1. Generate between 3-6 short, actionable suggestions
2. Each suggestion should be a concise command/question (5-10 words max)
3. Suggestions should be specific to the context discussed
4. If the conversation mentions specific services, clusters, or alerts - reference them
5. Prioritize suggestions that help the user investigate further or take action
6. Include a mix of: investigation actions, analysis requests, and follow-up checks

Output format: Return ONLY a JSON array of strings, no other text.
Example: ["Check Cilium health in guess-game", "Analyze cluster events", "List recent deployments"]
"""


def _get_genai_client() -> genai.Client:
    """Get a configured GenAI client for suggestion generation."""
    # Use Vertex AI backend with project from environment
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if project_id:
        return genai.Client(vertexai=True, project=project_id, location=location)

    # Fallback to API key if no project (local dev)
    return genai.Client()


def _extract_conversation_context(events: list[Any]) -> str:
    """Extract relevant context from conversation events.

    Focuses on:
    - Last few user messages
    - Agent's "Recommended Next Steps" sections
    - Key findings and recommendations from agent responses
    """
    context_parts: list[str] = []
    recommended_steps: list[str] = []

    # Process events in reverse to get most recent context
    events_to_process = list(reversed(events))[:10]  # Last 10 events max

    for event in events_to_process:
        author = getattr(event, "author", None)
        content = getattr(event, "content", None)

        if not content or not hasattr(content, "parts"):
            continue

        for part in content.parts:
            if not hasattr(part, "text") or not part.text:
                continue

            text = part.text

            if author == "user":
                # Include user messages for context
                context_parts.append(f"User: {text[:500]}")  # Truncate long messages

            elif author == "model":
                # Extract "Recommended Next Steps" sections from agent responses
                next_steps_match = re.search(
                    r"(?:Recommended Next Steps|Next Steps|Suggested Actions)[:\s]*\n?((?:[-*\d.]+[^\n]+\n?)+)",
                    text,
                    re.IGNORECASE,
                )
                if next_steps_match:
                    steps_text = next_steps_match.group(1)
                    # Parse individual steps
                    steps = re.findall(r"[-*\d.]+\s*(.+?)(?:\n|$)", steps_text)
                    recommended_steps.extend(steps[:5])  # Max 5 steps per section

                # Also extract key findings/conclusions
                findings_match = re.search(
                    r"(?:Key Findings|Summary|Conclusion)[:\s]*\n?(.+?)(?:\n\n|\Z)",
                    text,
                    re.IGNORECASE | re.DOTALL,
                )
                if findings_match:
                    context_parts.append(
                        f"Agent Finding: {findings_match.group(1)[:300]}"
                    )

    # Build context string
    context = ""
    if context_parts:
        context += "Recent conversation:\n" + "\n".join(context_parts[:5])

    if recommended_steps:
        context += "\n\nAgent's recommended next steps:\n"
        for i, step in enumerate(recommended_steps[:5], 1):
            context += f"{i}. {step.strip()}\n"

    return context


async def _generate_llm_suggestions(context: str) -> list[str]:
    """Use LLM to generate contextual suggestions based on conversation."""
    try:
        client = _get_genai_client()

        prompt = f"""Based on this conversation context, generate actionable next step suggestions for the user:

{context}

Generate 3-6 short, actionable suggestions that help the user continue their investigation or take action.
Return ONLY a JSON array of strings."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=SUGGESTIONS_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=500,
            ),
        )

        if not response.text:
            logger.warning("Empty response from LLM for suggestions")
            return []

        # Parse JSON response
        # Handle potential markdown code blocks
        text = response.text.strip()
        if text.startswith("```"):
            # Remove markdown code blocks
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = text.strip("`")

        suggestions = json.loads(text)

        if isinstance(suggestions, list):
            # Filter and validate suggestions
            valid_suggestions: list[str] = [
                s.strip()
                for s in suggestions
                if isinstance(s, str) and 3 < len(s.strip()) < 100
            ]
            return valid_suggestions[:MAX_SUGGESTIONS]

        return []

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM suggestions as JSON: {e}")
        return []
    except Exception as e:
        logger.warning(f"Error generating LLM suggestions: {e}")
        return []


async def generate_contextual_suggestions(
    project_id: str | None = None,
    session_id: str | None = None,
    user_id: str = "default",
) -> list[str]:
    """Generate contextual suggestions based on conversation history and project state.

    This function attempts to generate intelligent suggestions by:
    1. Analyzing the conversation history for "Recommended Next Steps"
    2. Using LLM to generate relevant follow-up actions
    3. Falling back to project-aware defaults if no context
    4. Returning generic defaults as a last resort

    Args:
        project_id: Optional GCP project ID for project-aware suggestions
        session_id: Optional session ID to retrieve conversation history
        user_id: User ID for session lookup

    Returns:
        List of 3-6 actionable suggestion strings
    """
    # Strategy 1: Use LLM to generate suggestions from conversation history
    if session_id:
        try:
            session_service = get_session_service()
            session = await session_service.get_session(session_id, user_id=user_id)

            if session and session.events:
                context = _extract_conversation_context(session.events)

                if context:
                    # Generate LLM-based suggestions
                    llm_suggestions = await _generate_llm_suggestions(context)

                    if len(llm_suggestions) >= MIN_SUGGESTIONS:
                        return llm_suggestions

                    # If we got some suggestions but not enough, supplement with defaults
                    if llm_suggestions:
                        # Add some default suggestions to reach minimum
                        supplemental = [
                            s for s in DEFAULT_SUGGESTIONS if s not in llm_suggestions
                        ]
                        combined = llm_suggestions + supplemental
                        return combined[:MAX_SUGGESTIONS]

        except Exception as e:
            logger.warning(f"Error generating contextual suggestions from session: {e}")

    # Strategy 2: Check for active alerts to provide truly contextual suggestions
    if project_id:
        try:
            from .tools.clients.alerts import list_alerts

            alerts_data = await list_alerts(
                project_id=project_id, filter_str='state="OPEN"'
            )

            # Standardized tool returns direct dict/list
            alerts: list[dict[str, Any]] = []
            if isinstance(alerts_data, dict) and "alerts" in alerts_data:
                alerts = alerts_data["alerts"]
            elif isinstance(alerts_data, list):
                alerts = alerts_data

            if alerts:
                # Generate alert-specific suggestions
                suggestions: list[str] = []

                # Add suggestions for top alerts (up to 3)
                for alert in alerts[:3]:
                    alert_name = alert.get("display_name", "alert")
                    # Truncate long alert names
                    if len(alert_name) > 40:
                        alert_name = alert_name[:37] + "..."
                    suggestions.append(f"Investigate alert: {alert_name}")

                # Add general alert-related suggestions
                suggestions.extend(
                    [
                        "Show all firing alerts",
                        "Check recent error logs",
                        "Analyze system health",
                    ]
                )

                return suggestions[:MAX_SUGGESTIONS]

        except Exception as e:
            logger.warning(f"Could not fetch alerts for suggestions: {e}")

        # Project-aware defaults when no alerts
        return [
            "Analyze recent errors",
            "Check service latency",
            "List GKE cluster health",
            "Show recent deployments",
            "Summarize log patterns",
        ]

    # Strategy 3: Return default suggestions
    return DEFAULT_SUGGESTIONS
