"""User preferences endpoints."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.auth import get_current_user_id
from sre_agent.services import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preferences", tags=["preferences"])


def _effective_user_id(explicit: str | None = None) -> str:
    """Return the authenticated user ID, falling back to an explicit override or 'default'.

    The auth middleware sets the user identity in a ContextVar.  We prefer that
    so per-user preferences work correctly even when the client does not send a
    ``user_id`` field.
    """
    if explicit and explicit != "default":
        return explicit
    return get_current_user_id() or "default"


class SetProjectRequest(BaseModel):
    """Request model for setting selected project."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str
    user_id: str = "default"


class SetToolConfigRequest(BaseModel):
    """Request model for setting tool configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled_tools: dict[str, bool]
    user_id: str = "default"


class SetRecentProjectsRequest(BaseModel):
    """Request model for setting recent projects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    projects: list[dict[str, str]]
    user_id: str = "default"


class SetStarredProjectsRequest(BaseModel):
    """Request model for setting starred projects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    projects: list[dict[str, str]]
    user_id: str = "default"


class ToggleStarRequest(BaseModel):
    """Request model for toggling a single project's starred state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str
    display_name: str = ""
    starred: bool = True
    user_id: str = "default"


@router.get("/project")
async def get_selected_project(user_id: str = "default") -> Any:
    """Get the selected project for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        project_id = await storage.get_selected_project(uid)
        return {"project_id": project_id}
    except Exception as e:
        logger.error(f"Error getting project preference: {e}")
        return {"project_id": None}


@router.post("/project")
async def set_selected_project(request: SetProjectRequest) -> Any:
    """Set the selected project for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        await storage.set_selected_project(request.project_id, uid)
        return {"success": True, "project_id": request.project_id}
    except Exception as e:
        logger.error(f"Error setting project preference: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/tools")
async def get_tool_preferences(user_id: str = "default") -> Any:
    """Get tool configuration preferences for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        tools = await storage.get_tool_config(uid)
        return {"enabled_tools": tools or {}}
    except Exception as e:
        logger.error(f"Error getting tool preferences: {e}")
        return {"enabled_tools": {}}


@router.post("/tools")
async def set_tool_preferences(request: SetToolConfigRequest) -> Any:
    """Set tool configuration preferences for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        await storage.set_tool_config(request.enabled_tools, uid)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting tool preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/recent")
async def get_recent_projects(user_id: str = "default") -> Any:
    """Get recent projects for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        projects = await storage.get_recent_projects(uid)
        return {"projects": projects or []}
    except Exception as e:
        logger.error(f"Error getting recent projects: {e}")
        return {"projects": []}


@router.post("/projects/recent")
async def set_recent_projects(request: SetRecentProjectsRequest) -> Any:
    """Set recent projects for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        await storage.set_recent_projects(request.projects, uid)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting recent projects: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/starred")
async def get_starred_projects(user_id: str = "default") -> Any:
    """Get starred (pinned) projects for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        projects = await storage.get_starred_projects(uid)
        return {"projects": projects or []}
    except Exception as e:
        logger.error(f"Error getting starred projects: {e}")
        return {"projects": []}


@router.post("/projects/starred")
async def set_starred_projects(request: SetStarredProjectsRequest) -> Any:
    """Set starred (pinned) projects for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        await storage.set_starred_projects(request.projects, uid)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting starred projects: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/projects/starred/toggle")
async def toggle_starred_project(request: ToggleStarRequest) -> Any:
    """Toggle the starred state of a single project.

    When ``starred`` is true the project is added; when false it is removed.
    """
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        current = await storage.get_starred_projects(uid) or []

        if request.starred:
            # Add if not already present
            if not any(p.get("project_id") == request.project_id for p in current):
                current.append(
                    {
                        "project_id": request.project_id,
                        "display_name": request.display_name or request.project_id,
                    }
                )
        else:
            # Remove
            current = [p for p in current if p.get("project_id") != request.project_id]

        await storage.set_starred_projects(current, uid)
        return {"success": True, "starred": request.starred, "projects": current}
    except Exception as e:
        logger.error(f"Error toggling starred project: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Recent & Saved Queries
# =============================================================================


class AddRecentQueryRequest(BaseModel):
    """Request model for adding a recent query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(description="The query text")
    panel_type: str = Field(description="Panel type: logs, metrics, traces, analytics")
    language: str = Field(
        default="", description="Query language (e.g. MQL, PromQL, SQL)"
    )
    user_id: str = "default"


class SaveQueryRequest(BaseModel):
    """Request model for saving a named query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Display name for the saved query")
    query: str = Field(description="The query text")
    panel_type: str = Field(description="Panel type: logs, metrics, traces, analytics")
    language: str = Field(default="", description="Query language")
    user_id: str = "default"


class UpdateSavedQueryRequest(BaseModel):
    """Request model for updating a saved query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = Field(default=None, description="Updated name")
    query: str | None = Field(default=None, description="Updated query text")
    user_id: str = "default"


class DeleteSavedQueryRequest(BaseModel):
    """Request model for deleting a saved query."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str = "default"


@router.get("/queries/recent")
async def get_recent_queries(
    user_id: str = "default",
    panel_type: str | None = None,
) -> Any:
    """Get recent queries for a user, optionally filtered by panel type."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        queries = await storage.get_recent_queries(uid, panel_type=panel_type)
        return {"queries": queries}
    except Exception as e:
        logger.error(f"Error getting recent queries: {e}")
        return {"queries": []}


@router.post("/queries/recent")
async def add_recent_query(request: AddRecentQueryRequest) -> Any:
    """Record a query execution to recent history."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        entry: dict[str, Any] = {
            "query": request.query,
            "panel_type": request.panel_type,
            "language": request.language,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        queries = await storage.add_recent_query(entry, uid)
        return {"success": True, "queries": queries}
    except Exception as e:
        logger.error(f"Error adding recent query: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/queries/saved")
async def get_saved_queries(
    user_id: str = "default",
    panel_type: str | None = None,
) -> Any:
    """Get saved (bookmarked) queries for a user."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        queries = await storage.get_saved_queries(uid, panel_type=panel_type)
        return {"queries": queries}
    except Exception as e:
        logger.error(f"Error getting saved queries: {e}")
        return {"queries": []}


@router.post("/queries/saved")
async def save_query(request: SaveQueryRequest) -> Any:
    """Save a named query."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "query": request.query,
            "panel_type": request.panel_type,
            "language": request.language,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        queries = await storage.add_saved_query(entry, uid)
        return {"success": True, "query": entry, "queries": queries}
    except Exception as e:
        logger.error(f"Error saving query: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/queries/saved/{query_id}")
async def update_saved_query(query_id: str, request: UpdateSavedQueryRequest) -> Any:
    """Update a saved query name or text."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(request.user_id)
        updates: dict[str, Any] = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.query is not None:
            updates["query"] = request.query
        queries = await storage.update_saved_query(query_id, updates, uid)
        return {"success": True, "queries": queries}
    except Exception as e:
        logger.error(f"Error updating saved query: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/queries/saved/{query_id}")
async def delete_saved_query(
    query_id: str,
    user_id: str = "default",
) -> Any:
    """Delete a saved query."""
    try:
        storage = get_storage_service()
        uid = _effective_user_id(user_id)
        queries = await storage.delete_saved_query(query_id, uid)
        return {"success": True, "queries": queries}
    except Exception as e:
        logger.error(f"Error deleting saved query: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
