"""Health and debug endpoints."""

import logging
from typing import Any

from fastapi import APIRouter

from sre_agent.tools.common.debug import (
    get_debug_summary,
    log_auth_state,
    log_telemetry_state,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for connectivity testing."""
    return {"status": "ok"}


@router.get("/api/debug")
async def debug_info() -> Any:
    """Debug endpoint for diagnosing telemetry and authentication issues.

    Returns comprehensive information about:
    - OpenTelemetry configuration and trace context
    - Authentication state (ContextVar, Session, Default)
    - Environment variables affecting telemetry and auth

    Enable detailed logging by setting DEBUG_TELEMETRY=true and DEBUG_AUTH=true.
    """
    # Log telemetry state at this point
    telemetry_state = log_telemetry_state("debug_endpoint")
    auth_state = log_auth_state(None, "debug_endpoint")

    return {
        "telemetry": telemetry_state,
        "auth": auth_state,
        "summary": get_debug_summary(),
        "instructions": {
            "enable_debug_logging": (
                "Set DEBUG_TELEMETRY=true and DEBUG_AUTH=true environment variables"
            ),
            "enable_agent_engine_telemetry": (
                "Set GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true "
                "when deploying to Agent Engine"
            ),
            "view_traces": "Navigate to Cloud Console > Trace > Trace list",
        },
    }
