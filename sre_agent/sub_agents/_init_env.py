"""Shared environment initialization for sub-agents.

This module provides a centralized initialization function to avoid
duplicating vertexai.init() and project ID discovery across sub-agents.
"""

import os

import google.auth
import vertexai

# Module-level flag to track initialization status
_initialized: bool = False
_project_id: str | None = None
_location: str | None = None


def init_sub_agent_env() -> tuple[str | None, str]:
    """Initialize environment for sub-agent usage.

    This function:
    1. Discovers the GCP project ID from environment or credentials
    2. Initializes Vertex AI if configured
    3. Returns the project_id and location for use in sub-agents

    Returns:
        Tuple of (project_id, location)
    """
    global _initialized, _project_id, _location

    if _initialized:
        return _project_id, _location or "us-central1"

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCP_PROJECT_ID"
    )

    # Fallback: Try to get project from Application Default Credentials
    if not project_id:
        try:
            _, project_id = google.auth.default()
            if project_id:
                # Set env vars for downstream tools
                os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
                os.environ["GCP_PROJECT_ID"] = project_id
        except Exception:
            pass

    location = os.environ.get("GCP_LOCATION") or os.environ.get(
        "GOOGLE_CLOUD_LOCATION", "us-central1"
    )
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"

    if use_vertex and project_id:
        try:
            vertexai.init(project=project_id, location=location)
        except Exception:
            pass

    _initialized = True
    _project_id = project_id
    _location = location

    return project_id, location


def get_project_id() -> str | None:
    """Get the initialized project ID.

    Calls init_sub_agent_env() if not already initialized.

    Returns:
        The GCP project ID or None if not found.
    """
    if not _initialized:
        init_sub_agent_env()
    return _project_id


def get_location() -> str:
    """Get the initialized location.

    Calls init_sub_agent_env() if not already initialized.

    Returns:
        The GCP location (default: us-central1).
    """
    if not _initialized:
        init_sub_agent_env()
    return _location or "us-central1"
