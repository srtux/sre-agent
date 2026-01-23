"""System information and miscellaneous endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Request

from sre_agent.auth import get_current_project_id, validate_access_token
from sre_agent.suggestions import generate_contextual_suggestions
from sre_agent.tools.common.debug import (
    get_debug_summary,
    log_auth_state,
    log_telemetry_state,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/api/suggestions")
async def get_suggestions(
    project_id: str | None = None,
    session_id: str | None = None,
    user_id: str = "default",
) -> Any:
    """Get contextual suggestions for the user."""
    try:
        suggestions = await generate_contextual_suggestions(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {
            "suggestions": [
                "Analyze last hour's logs",
                "List active incidents",
                "Check for high latency",
            ]
        }


@router.get("/api/auth/info")
async def auth_info(request: Request) -> dict[str, Any]:
    """Get information about the current authentication state.

    Returns token validation status and user info if authenticated.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return {
            "authenticated": False,
            "error": "No Authorization header or invalid format",
            "project_id": get_current_project_id(),
        }

    token = auth_header.split(" ")[1]

    # Validate the token with Google
    token_info = await validate_access_token(token)

    return {
        "authenticated": token_info.valid,
        "token_info": {
            "valid": token_info.valid,
            "email": token_info.email,
            "expires_in": token_info.expires_in,
            "scopes": token_info.scopes,
            "error": token_info.error,
        },
        "project_id": get_current_project_id(),
    }


@router.get("/api/debug")
async def debug_info() -> Any:
    """Debug endpoint for diagnosing telemetry and authentication issues."""
    # Log telemetry state at this point
    telemetry_state = log_telemetry_state("debug_endpoint")
    auth_state = log_auth_state(None, "debug_endpoint")

    return {
        "telemetry": telemetry_state,
        "auth": auth_state,
        "summary": get_debug_summary(),
        "instructions": {
            "enable_debug_logging": "Set DEBUG_TELEMETRY=true and DEBUG_AUTH=true environment variables",
            "enable_agent_engine_telemetry": "Set GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true when deploying to Agent Engine",
            "view_traces": "Navigate to Cloud Console > Trace > Trace list",
        },
    }
