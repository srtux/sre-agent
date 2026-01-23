import logging

from .services import get_session_service

logger = logging.getLogger(__name__)

DEFAULT_SUGGESTIONS = [
    "Analyze recent errors",
    "Check Cloud Run latency",
    "Summarize logs",
]


async def generate_contextual_suggestions(
    project_id: str | None = None,
    session_id: str | None = None,
    user_id: str = "default",
) -> list[str]:
    """Generate 3 contextual suggestions for the user."""
    # If we have a session, try to get suggestions based on history
    if session_id:
        try:
            session_service = get_session_service()
            session = await session_service.get_session(session_id, user_id=user_id)
            if session and session.events:
                # Extract the last user message text for context
                last_user_msg = ""
                for event in reversed(session.events):
                    if event.author == "user" and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                last_user_msg = part.text
                                break
                    if last_user_msg:
                        break

                if not last_user_msg:
                    return DEFAULT_SUGGESTIONS

                # TODO: Integrate with model for dynamic suggestions
                # For now, fallback to pattern matching below

                # Alternatively, just return some smart defaults based on common patterns
                # if the last message was about logs, suggest pattern analysis
                last_msg = last_user_msg.lower()
                if "log" in last_msg:
                    return [
                        "Analyze log patterns",
                        "Filter for ERROR logs",
                        "Check log anomalies",
                    ]
                if "trace" in last_msg or "latency" in last_msg:
                    return [
                        "Find bottleneck services",
                        "Compare with baseline",
                        "Analyze critical path",
                    ]
                if "metric" in last_msg or "promql" in last_msg:
                    return [
                        "Detect metric anomalies",
                        "List related time series",
                        "Check SLO status",
                    ]
        except Exception as e:
            logger.warning(f"Error generating contextual suggestions: {e}")

    # For empty state or if history analysis ignored
    if project_id:
        try:
            # Proactively check for active alerts to provide truly contextual suggestions
            from .tools.clients.alerts import list_alerts

            alerts_data = await list_alerts(
                project_id=project_id, filter_str='state="OPEN"'
            )

            # Standardized tool returns direct dict/list
            if isinstance(alerts_data, dict) and "alerts" in alerts_data:
                alerts = alerts_data["alerts"]
            elif isinstance(alerts_data, list):
                alerts = alerts_data
            else:
                alerts = []

            if alerts:
                # Suggest analyzing the most recent alert
                alert = alerts[0]

                alert_name = alert.get("display_name", "active alert")
                return [
                    f"Analyze alert: {alert_name}",
                    "List all firing alerts",
                    "Check system health",
                ]
        except Exception as e:
            logger.warning(f"Could not fetch alerts for suggestions: {e}")

        # Fallback project-aware defaults
        return [
            f"Analyze recent errors in {project_id[:15]}",
            "Summarize GKE cluster health",
            "Check for high latency traces",
        ]

    return DEFAULT_SUGGESTIONS
