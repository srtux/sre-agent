import json
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
            if session and session.messages:
                # Use the last few messages as context
                # recent_history = session.messages[-5:]  # Last 5 messages
                # history_text = "\n".join(
                #     [f"{m.role}: {m.content}" for m in recent_history]
                # )

                # prompt = f"""Based on the following SRE investigation history, suggest 3 short, actionable next steps or queries the user might want to run.
                # The suggestions should be concise (3-5 words) and formatted as a JSON list of strings.
                #
                # History:
                # {history_text}
                #
                # Suggestions:
                # """

                # TODO: Integrate with model for dynamic suggestions
                # For now, fallback to pattern matching below

                # Alternatively, just return some smart defaults based on common patterns
                # if the last message was about logs, suggest pattern analysis
                last_msg = session.messages[-1].content.lower()
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
            from .tools import list_alerts

            alerts_json = await list_alerts(project_id=project_id, status="firing")
            alerts_data = json.loads(alerts_json)

            if alerts_data.get("alerts"):
                # Suggest analyzing the most recent alert
                alert = alerts_data["alerts"][0]
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
