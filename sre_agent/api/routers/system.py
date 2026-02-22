"""System information and miscellaneous endpoints."""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    encrypt_token,
    get_current_project_id,
    validate_access_token,
    validate_id_token,
)
from sre_agent.services import get_session_service
from sre_agent.suggestions import generate_contextual_suggestions
from sre_agent.tools.common.debug import (
    get_debug_summary,
    log_auth_state,
    log_telemetry_state,
)
from sre_agent.version import get_version_info

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Get public configuration for the frontend."""
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "auth_enabled": os.getenv("ENABLE_AUTH", "true").lower() == "true",
        "guest_mode_enabled": os.getenv("ENABLE_GUEST_MODE", "true").lower() == "true",
    }


@router.get("/api/version")
async def get_version() -> dict[str, str]:
    """Return build version metadata (version, git SHA, build timestamp)."""
    return get_version_info()


@router.get("/api/system/tools")
async def get_system_tools() -> dict[str, Any]:
    """Get the dynamic registry of all available agent tools.

    This endpoint allows AI agents and clients to discover exactly
    what tools the system possesses dynamically, without needing
    to scrape the Python codebase.
    """
    from sre_agent.agent import TOOL_NAME_MAP

    tools_list = []
    for name, tool_func in TOOL_NAME_MAP.items():
        # Get ADK tool schema representation if available, else fallback
        docstring = getattr(tool_func, "__doc__", "No description available.")
        if docstring:
            docstring = docstring.strip().split("\n")[0]  # Just the first line

        tools_list.append(
            {
                "name": name,
                "description": docstring,
            }
        )

    return {
        "count": len(tools_list),
        "tools": sorted(tools_list, key=lambda t: t["name"]),
    }


class LoginRequest(BaseModel):
    """Request model for the login endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    access_token: str
    id_token: str | None = Field(default=None, description="OIDC ID Token for identity")
    project_id: str | None = None


@router.post("/api/auth/login")
async def login(request: LoginRequest, response: Response) -> dict[str, Any]:
    """Exchange a Google access token for a session cookie.

    This endpoint validates the token, creates/retrieves a session,
    and sets an HTTP-only cookie for stateful authentication.
    """
    # 1. Validate credentials
    # If id_token is provided, use it for faster local identity verification.
    # Otherwise fallback to access_token validation (now cached).
    if request.id_token:
        token_info = await validate_id_token(request.id_token)
    else:
        token_info = await validate_access_token(request.access_token)

    if not token_info.valid:
        raise HTTPException(
            status_code=401, detail=f"Invalid credentials: {token_info.error}"
        )

    if not token_info.email:
        raise HTTPException(
            status_code=401, detail="Identity verification failed: no email found"
        )

    # 2. Get or Create session for this user
    session_manager = get_session_service()

    # Create a new session for this login to ensure fresh state
    # or reuse an existing one if provided (though login usually implies fresh start)
    # SECURITY: Encrypt the access token before storage
    encrypted_access_token = encrypt_token(request.access_token)

    initial_state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: encrypted_access_token,
        "user_email": token_info.email,
    }
    if request.project_id:
        from sre_agent.auth import SESSION_STATE_PROJECT_ID_KEY

        initial_state[SESSION_STATE_PROJECT_ID_KEY] = request.project_id

    session = await session_manager.create_session(
        user_id=token_info.email,
        initial_state=initial_state,
    )

    # 3. Set the session cookie
    # httponly: true prevents JavaScript from accessing the cookie
    # secure: true (should be true in production/HTTPS)
    # samesite: Lax is a good middle ground for balancing security and UX
    response.set_cookie(
        key="sre_session_id",
        value=session.id,
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
        samesite="lax",
        max_age=3600 * 24 * 7,  # 7 days
    )

    logger.info(f"🔑 User {token_info.email} logged in. Session: {session.id}")

    return {
        "status": "success",
        "session_id": session.id,
        "email": token_info.email,
    }


@router.post("/api/auth/logout")
async def logout(response: Response) -> dict[str, Any]:
    """Log out by clearing the session cookie."""
    response.delete_cookie(key="sre_session_id")
    return {"status": "success"}


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

    # Optimized Identity Check: Use X-ID-Token if provided
    id_token_header = request.headers.get("X-ID-Token")
    if id_token_header:
        token_info = await validate_id_token(id_token_header)
    else:
        token = auth_header.split(" ")[1]
        # Validate the access token with Google (now cached)
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
