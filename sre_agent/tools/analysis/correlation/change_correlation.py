"""Change Correlation tool for linking incidents to recent deployments and config changes.

One of the most common root causes for production incidents is a recent change:
- Code deployments
- Configuration updates
- Infrastructure changes (scaling, migration)
- Feature flag toggles

This tool queries GCP Audit Logs and Cloud Deploy to find changes that
correlate temporally with the incident window.

SRE Principle: "Most outages are caused by changes" - Google SRE Book
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)

# GCP Audit Log method names indicating significant changes
CHANGE_INDICATORS: dict[str, dict[str, Any]] = {
    "deployment": {
        "methods": [
            "google.cloud.run.v2.Services.UpdateService",
            "google.cloud.run.v1.Services.ReplaceService",
            "google.appengine.v1.Versions.CreateVersion",
            "google.container.v1.ClusterManager.UpdateCluster",
            "google.container.v1beta1.ClusterManager.UpdateNodePool",
            "io.k8s.apps.v1.deployments.create",
            "io.k8s.apps.v1.deployments.update",
            "io.k8s.apps.v1.deployments.patch",
        ],
        "category": "deployment",
        "risk": "high",
    },
    "configuration": {
        "methods": [
            "SetIamPolicy",
            "google.cloud.secretmanager.v1.SecretManagerService.AddSecretVersion",
            "google.cloud.sql.v1beta4.SqlInstancesService.Patch",
            "google.cloud.redis.v1.CloudRedis.UpdateInstance",
        ],
        "category": "configuration",
        "risk": "medium",
    },
    "infrastructure": {
        "methods": [
            "google.container.v1.ClusterManager.SetNodePoolSize",
            "google.container.v1.ClusterManager.SetNodePoolAutoscaling",
            "google.compute.instances.insert",
            "google.compute.instances.delete",
            "google.compute.instanceGroupManagers.resize",
            "google.cloud.sql.v1beta4.SqlInstancesService.RestartReplica",
            "google.cloud.sql.v1beta4.SqlInstancesService.Restart",
        ],
        "category": "infrastructure",
        "risk": "medium",
    },
    "networking": {
        "methods": [
            "google.compute.firewalls.insert",
            "google.compute.firewalls.update",
            "google.compute.firewalls.patch",
            "google.compute.networks.insert",
            "google.compute.subnetworks.insert",
            "google.cloud.networkservices.v1.NetworkServices.UpdateEndpointPolicy",
        ],
        "category": "networking",
        "risk": "high",
    },
    "feature_flag": {
        "methods": [
            "google.firebase.remoteconfig.v1.RemoteConfig.UpdateRemoteConfig",
            "google.cloud.runtimeconfig.v1beta1.RuntimeConfig.Update",
        ],
        "category": "feature_flag",
        "risk": "medium",
    },
}

# Build a flat lookup: method_name -> (indicator_name, category, risk)
_METHOD_LOOKUP: dict[str, tuple[str, str, str]] = {}
for indicator_name, indicator_data in CHANGE_INDICATORS.items():
    for method in indicator_data["methods"]:
        _METHOD_LOOKUP[method] = (
            indicator_name,
            indicator_data["category"],
            indicator_data["risk"],
        )


def _build_audit_log_filter(
    project_id: str,
    start_time: str,
    end_time: str,
    service_name: str | None = None,
) -> str:
    """Build a Cloud Logging filter for audit log entries about changes.

    Args:
        project_id: GCP project ID.
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time.
        service_name: Optional service name to filter by.

    Returns:
        Cloud Logging filter string.
    """
    parts = [
        'logName="projects/{}/logs/cloudaudit.googleapis.com%2Factivity"'.format(
            project_id
        ),
        f'timestamp>="{start_time}"',
        f'timestamp<="{end_time}"',
    ]

    if service_name:
        parts.append(
            f'(resource.labels.service_name="{service_name}" OR '
            f'protoPayload.resourceName:"{service_name}")'
        )

    return " AND ".join(parts)


def _classify_change(method_name: str) -> dict[str, str]:
    """Classify an audit log method as a change type.

    Args:
        method_name: The protoPayload.methodName from audit log.

    Returns:
        Classification with category and risk level.
    """
    lookup = _METHOD_LOOKUP.get(method_name)
    if lookup:
        return {
            "indicator": lookup[0],
            "category": lookup[1],
            "risk": lookup[2],
        }

    # Heuristic classification for unknown methods
    method_lower = method_name.lower()
    if any(w in method_lower for w in ["create", "insert", "deploy"]):
        return {"indicator": "unknown", "category": "deployment", "risk": "medium"}
    if any(w in method_lower for w in ["update", "patch", "set"]):
        return {"indicator": "unknown", "category": "configuration", "risk": "low"}
    if any(w in method_lower for w in ["delete", "remove", "destroy"]):
        return {"indicator": "unknown", "category": "infrastructure", "risk": "high"}
    return {"indicator": "unknown", "category": "other", "risk": "low"}


def _calculate_temporal_correlation(
    change_time: str,
    incident_start: str,
    lookback_hours: float,
) -> dict[str, Any]:
    """Calculate how strongly a change correlates with an incident.

    Args:
        change_time: ISO 8601 timestamp of the change.
        incident_start: ISO 8601 timestamp of incident start.
        lookback_hours: How far back to consider changes.

    Returns:
        Correlation assessment with score and explanation.
    """
    try:
        change_dt = datetime.fromisoformat(change_time.replace("Z", "+00:00"))
        incident_dt = datetime.fromisoformat(incident_start.replace("Z", "+00:00"))

        delta_minutes = (incident_dt - change_dt).total_seconds() / 60.0

        if delta_minutes < 0:
            # Change happened AFTER incident started
            return {
                "correlation_score": 0.1,
                "minutes_before_incident": round(delta_minutes, 1),
                "assessment": "Change occurred after incident start (unlikely cause)",
            }

        if delta_minutes <= 15:
            return {
                "correlation_score": 0.95,
                "minutes_before_incident": round(delta_minutes, 1),
                "assessment": "Very strong correlation: change within 15 minutes of incident",
            }
        if delta_minutes <= 60:
            return {
                "correlation_score": 0.8,
                "minutes_before_incident": round(delta_minutes, 1),
                "assessment": "Strong correlation: change within 1 hour of incident",
            }
        if delta_minutes < 360:
            return {
                "correlation_score": 0.5,
                "minutes_before_incident": round(delta_minutes, 1),
                "assessment": "Moderate correlation: change within 6 hours of incident",
            }
        max_minutes = lookback_hours * 60
        if delta_minutes <= max_minutes:
            score = max(0.1, 1.0 - (delta_minutes / max_minutes))
            return {
                "correlation_score": round(score, 2),
                "minutes_before_incident": round(delta_minutes, 1),
                "assessment": f"Weak correlation: change {delta_minutes / 60:.1f} hours before incident",
            }

        return {
            "correlation_score": 0.0,
            "minutes_before_incident": round(delta_minutes, 1),
            "assessment": "Outside lookback window",
        }
    except (ValueError, TypeError) as e:
        return {
            "correlation_score": 0.0,
            "minutes_before_incident": None,
            "assessment": f"Could not calculate correlation: {e}",
        }


@adk_tool
async def correlate_changes_with_incident(
    project_id: str,
    incident_start: str,
    lookback_hours: float = 6.0,
    service_name: str | None = None,
    incident_end: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Find recent changes that may have caused an incident.

    Queries GCP Audit Logs to find deployments, configuration changes, and
    infrastructure modifications that occurred before the incident. Changes
    are ranked by temporal correlation and risk level.

    This is the first thing a senior SRE checks: "What changed?"

    Args:
        project_id: The Google Cloud Project ID.
        incident_start: Incident start time (ISO 8601 format).
        lookback_hours: How many hours before the incident to search (default 6).
        service_name: Optional service name to filter changes.
        incident_end: Optional incident end time (ISO 8601 format).
        tool_context: Context object for tool execution.

    Returns:
        Ranked list of changes with correlation scores and risk assessments.

    Example:
        correlate_changes_with_incident(
            "my-project",
            "2024-06-15T14:00:00Z",
            lookback_hours=6,
            service_name="checkout-service"
        )
    """
    try:
        # Calculate lookback window
        incident_dt = datetime.fromisoformat(
            incident_start.replace("Z", "+00:00")
        )
        from datetime import timedelta

        lookback_start = incident_dt - timedelta(hours=lookback_hours)
        lookback_end = incident_dt + timedelta(hours=1)  # Include some post-incident

        log_filter = _build_audit_log_filter(
            project_id,
            lookback_start.isoformat(),
            lookback_end.isoformat(),
            service_name,
        )

        # Try to query actual audit logs using the logging client
        changes: list[dict[str, Any]] = []
        try:
            from sre_agent.auth import (
                get_credentials_from_tool_context,
                get_current_credentials,
            )
            from google.cloud import logging as cloud_logging

            credentials = get_credentials_from_tool_context(tool_context)
            if not credentials:
                auth_obj: Any = get_current_credentials()
                credentials, _ = auth_obj

            client = cloud_logging.Client(
                project=project_id, credentials=credentials
            )

            entries = list(client.list_entries(
                filter_=log_filter,
                order_by=cloud_logging.DESCENDING,
                max_results=100,
            ))

            for entry in entries:
                payload = entry.payload if hasattr(entry, "payload") else {}
                if isinstance(payload, dict):
                    method_name = payload.get("methodName", "")
                    resource_name = payload.get("resourceName", "")
                    actor = payload.get("authenticationInfo", {}).get(
                        "principalEmail", "unknown"
                    )
                else:
                    method_name = str(getattr(entry, "method_name", ""))
                    resource_name = str(getattr(entry, "resource_name", ""))
                    actor = "unknown"

                if not method_name:
                    continue

                classification = _classify_change(method_name)
                timestamp = (
                    entry.timestamp.isoformat()
                    if hasattr(entry, "timestamp") and entry.timestamp
                    else lookback_start.isoformat()
                )

                correlation = _calculate_temporal_correlation(
                    timestamp, incident_start, lookback_hours
                )

                changes.append(
                    {
                        "timestamp": timestamp,
                        "method": method_name,
                        "resource": resource_name,
                        "actor": actor,
                        "classification": classification,
                        "correlation": correlation,
                    }
                )

        except ImportError:
            logger.warning(
                "google-cloud-logging not available; providing static analysis"
            )
        except Exception as e:
            logger.warning(f"Could not query audit logs: {e}")

        # If no live data, provide guidance on what to check
        if not changes:
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result={
                    "project_id": project_id,
                    "incident_start": incident_start,
                    "lookback_hours": lookback_hours,
                    "service_filter": service_name,
                    "changes_found": 0,
                    "audit_log_filter": log_filter,
                    "guidance": {
                        "message": (
                            "No changes found in audit logs (or logs unavailable). "
                            "You can manually run this filter in Cloud Logging, or check:"
                        ),
                        "manual_checks": [
                            "Cloud Run revision history for recent deployments",
                            "GKE workload revision history",
                            "Cloud Deploy delivery pipeline status",
                            "Secret Manager recent version additions",
                            "Cloud SQL instance modification history",
                            "Feature flag service (Firebase Remote Config, LaunchDarkly)",
                            "Git commit history for the service",
                        ],
                        "gcloud_command": (
                            f'gcloud logging read \'{log_filter}\' '
                            f"--project={project_id} --limit=50 --format=json"
                        ),
                    },
                },
                metadata={"tool_category": "change_correlation"},
            )

        # Sort by correlation score (highest first)
        changes.sort(
            key=lambda c: c.get("correlation", {}).get("correlation_score", 0),
            reverse=True,
        )

        # Identify most likely culprit
        top_change = changes[0] if changes else None
        high_risk_changes = [
            c for c in changes
            if c.get("classification", {}).get("risk") == "high"
            and c.get("correlation", {}).get("correlation_score", 0) >= 0.5
        ]

        result: dict[str, Any] = {
            "project_id": project_id,
            "incident_start": incident_start,
            "lookback_hours": lookback_hours,
            "service_filter": service_name,
            "changes_found": len(changes),
            "high_risk_changes": len(high_risk_changes),
            "changes": changes[:20],  # Top 20
        }

        if top_change:
            correlation = top_change.get("correlation", {})
            result["most_likely_cause"] = {
                "change": top_change,
                "correlation_score": correlation.get("correlation_score", 0),
                "assessment": correlation.get("assessment", ""),
                "recommendation": (
                    f"Investigate the {top_change.get('classification', {}).get('category', 'unknown')} "
                    f"change at {top_change.get('timestamp', 'unknown')} by "
                    f"{top_change.get('actor', 'unknown')}. "
                    "Consider rolling back if this is the root cause."
                ),
            }

        if high_risk_changes:
            result["high_risk_summary"] = [
                {
                    "timestamp": c["timestamp"],
                    "method": c["method"],
                    "actor": c.get("actor", "unknown"),
                    "score": c.get("correlation", {}).get("correlation_score", 0),
                }
                for c in high_risk_changes[:5]
            ]

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"tool_category": "change_correlation"},
        )

    except Exception as e:
        error_msg = f"Failed to correlate changes with incident: {e!s}"
        logger.error(error_msg, exc_info=True)
        return BaseToolResponse(status=ToolStatus.ERROR, error=error_msg)
