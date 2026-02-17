"""Project permission endpoints."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from sre_agent.exceptions import UserFacingError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("/info")
async def get_permissions_info() -> Any:
    """Get information about permissions required by the agent.

    Returns the agent's service account and the IAM roles needed to access
    user projects for telemetry analysis.
    """
    try:
        # Get the service account the agent is running as
        import google.auth
        import google.auth.transport.requests

        _, credentials_project_id = google.auth.default()

        request = google.auth.transport.requests.Request()
        creds, _ = google.auth.default()
        creds.refresh(request)  # type: ignore[no-untyped-call]

        # Service account email is what users need to grant roles to
        service_account = getattr(creds, "service_account_email", "unknown")

        return {
            "service_account": service_account,
            "roles": [
                "roles/cloudtrace.user",
                "roles/logging.viewer",
                "roles/monitoring.viewer",
                "roles/compute.viewer",
            ],
            "project_id": credentials_project_id,
        }
    except Exception as e:
        logger.error(f"Error getting permissions info: {e}")
        return {
            "service_account": "sre-agent@PROJECT_ID.iam.gserviceaccount.com",
            "roles": [
                "roles/cloudtrace.user",
                "roles/logging.viewer",
                "roles/monitoring.viewer",
                "roles/compute.viewer",
            ],
            "error": f"Failed to retrieve permission info: {e}",
        }


@router.get("/gcloud")
async def get_gcloud_commands(project_id: str) -> Any:
    """Generate gcloud commands for granting permissions to a specific project.

    Args:
        project_id: The user's GCP project ID to grant access to

    Returns:
        Ready-to-use gcloud commands for granting permissions.
    """
    try:
        info = await get_permissions_info()
        sa = info["service_account"]
        roles = info["roles"]

        commands = []
        for role in roles:
            commands.append(
                f"gcloud projects add-iam-policy-binding {project_id} "
                f"--member='serviceAccount:{sa}' --role='{role}'"
            )

        return {
            "project_id": project_id,
            "service_account": sa,
            "commands": commands,
            "one_liner": " && ".join(commands),
        }
    except Exception as e:
        logger.exception("Error generating gcloud commands")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.get("/check/{project_id}")
async def check_permissions(project_id: str) -> Any:
    """Check if the agent has the required permissions on a project.

    This performs lightweight API calls to verify access.

    Args:
        project_id: The user's GCP project ID to check

    Returns:
        Status of each required permission.
    """
    results = {
        "cloudtrace.user": {"status": "unknown", "message": None},
        "logging.viewer": {"status": "unknown", "message": None},
        "monitoring.viewer": {"status": "unknown", "message": None},
    }

    # Test trace access
    async def _test_trace_access() -> tuple[str, str | None]:
        try:
            from google.cloud import trace_v2

            client = trace_v2.TraceServiceClient()
            list(
                client.list_traces(  # type: ignore[attr-defined]
                    request={"parent": f"projects/{project_id}", "page_size": 1}
                )
            )
            return "ok", None
        except Exception as e:
            msg = str(e)
            if "PermissionDenied" in msg or "403" in msg:
                return "missing", "Permission Denied (403)"
            return "error", msg

    # Test logging access
    async def _test_logging_access() -> tuple[str, str | None]:
        try:
            from google.cloud import logging as cloud_logging

            client = cloud_logging.Client(project=project_id)  # type: ignore[no-untyped-call]
            # Try to list logs
            list(client.list_logs(page_size=1))  # type: ignore[attr-defined]
            return "ok", None
        except Exception as e:
            msg = str(e)
            if "PermissionDenied" in msg or "403" in msg:
                return "missing", "Permission Denied (403)"
            return "error", msg

    # Test monitoring access
    async def _test_monitoring_access() -> tuple[str, str | None]:
        try:
            from google.cloud import monitoring_v3

            client = monitoring_v3.MetricServiceClient()
            # Try to list metric descriptors
            list(
                client.list_metric_descriptors(
                    request={"name": f"projects/{project_id}", "page_size": 1}
                )
            )
            return "ok", None
        except Exception as e:
            msg = str(e)
            if "PermissionDenied" in msg or "403" in msg:
                return "missing", "Permission Denied (403)"
            return "error", msg

    # Run checks
    trace_status, trace_msg = await _test_trace_access()
    log_status, log_msg = await _test_logging_access()
    mon_status, mon_msg = await _test_monitoring_access()

    results["cloudtrace.user"] = {"status": trace_status, "message": trace_msg}
    results["logging.viewer"] = {"status": log_status, "message": log_msg}
    results["monitoring.viewer"] = {"status": mon_status, "message": mon_msg}

    # Overall status
    all_ok = all(r["status"] == "ok" for r in results.values())

    return {
        "project_id": project_id,
        "results": results,
        "all_ok": all_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
