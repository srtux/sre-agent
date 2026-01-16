import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import tools
try:
    from sre_agent.tools.clients.alerts import list_alerts
    from sre_agent.tools.clients.logging import list_log_entries
except ImportError:
    # Handle running from root
    import sys

    sys.path.append(os.getcwd())
    from sre_agent.tools.clients.alerts import list_alerts
    from sre_agent.tools.clients.logging import list_log_entries


async def main() -> None:
    """Run the health analysis script."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
    if not project_id:
        print("Error: GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID not set.")
        return

    print(f"Analyzing health for project: {project_id}")

    from sre_agent.tools.analysis.remediation.suggestions import (
        generate_remediation_suggestions,
    )

    # 1. Check for Active Alerts
    print("\n--- Active Alerts ---")
    try:
        alerts_json = await list_alerts(project_id, filter_str='state="OPEN"')
        alerts = json.loads(alerts_json)
        if isinstance(alerts, list):
            if not alerts:
                print("No open alerts found.")
            else:
                # Debug dump
                print(f"DEBUG: Alerts found: {len(alerts)}")
                print(json.dumps(alerts[0], indent=2))

                for alert in alerts:
                    print(
                        f"- [At {alert.get('create_time')}] {alert.get('payload', {}).get('summary') or 'Alert'}"
                    )
                    print(
                        f"  Resource: {alert.get('resource_type')} {alert.get('resource_name')}"
                    )
        else:
            print(f"Error fetching alerts: {alerts}")
    except Exception as e:
        print(f"Failed to list alerts: {e}")

    # 2. Check for Recent Errors (Last 1 Hour)
    found_issue = False
    issue_summary = ""

    print("\n--- Recent Errors (Last 1 Hour) ---")
    try:
        # ISO format for Cloud Logging
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        filter_str = f'severity="ERROR" AND timestamp >= "{one_hour_ago}"'

        logs_json = await list_log_entries(project_id, filter_str=filter_str, limit=10)
        logs = json.loads(logs_json)

        if isinstance(logs, dict) and "entries" in logs:
            entries = logs["entries"]
            if not entries:
                print("No recent errors found.")
            else:
                print(f"Found {len(entries)} recent errors (showing last 5):")
                # Debug: print first entry full details
                if entries:
                    print("DEBUG: First Log Entry Content:")
                    print(json.dumps(entries[0], indent=2, default=str))

                    # Construct summary from first error
                    first_log = entries[0]
                    payload = first_log.get("payload", {})
                    if isinstance(payload, dict):
                        status = payload.get("status", {})
                        msg = (
                            status.get("message")
                            or payload.get("message")
                            or "Unknown Error"
                        )
                        if "No such object" in msg:
                            issue_summary = f"Dataproc/GCS Error: {msg}"
                            found_issue = True
                        else:
                            issue_summary = f"Application Error: {msg}"
                            found_issue = True

                for log in entries[:5]:
                    ts = log.get("timestamp", "N/A")
                    severity = log.get("severity", "N/A")
                    # ... (rest of print logic)
                    payload = (
                        log.get("protoPayload")
                        or log.get("jsonPayload")
                        or log.get("textPayload")
                        or {}
                    )
                    if isinstance(payload, dict):
                        # Try standard audit log fields
                        msg = (
                            payload.get("methodName")
                            or payload.get("message")
                            or payload.get("status", {}).get("message")
                            or str(payload)
                        )
                    else:
                        msg = str(payload)

                    resource = log.get("resource", {}).get("labels", {})
                    print(f"- [{ts}] [{severity}] {msg[:200]}...")  # Increased length
                    print(f"  Resource: {resource}")
        else:
            print(f"Error fetching logs: {logs}")

    except Exception as e:
        print(f"Failed to list logs: {e}")

    # 3. Generate Suggestions
    if found_issue:
        print("\n--- Remediation Suggestions ---")
        print(f"Generating suggestions for: {issue_summary}")
        suggestions_json = generate_remediation_suggestions(
            issue_summary, finding_details={"project_id": project_id}
        )
        try:
            suggestions = json.loads(suggestions_json)
            print(json.dumps(suggestions, indent=2))
        except Exception:
            print(suggestions_json)


if __name__ == "__main__":
    asyncio.run(main())
