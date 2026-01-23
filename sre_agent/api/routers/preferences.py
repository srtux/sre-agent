"""User preferences endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sre_agent.services import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class SetProjectRequest(BaseModel):
    """Request model for setting selected project."""

    project_id: str
    user_id: str = "default"


class SetToolConfigRequest(BaseModel):
    """Request model for setting tool configuration."""

    enabled_tools: dict[str, bool]
    user_id: str = "default"


class SetRecentProjectsRequest(BaseModel):
    """Request model for setting recent projects."""

    projects: list[dict[str, str]]
    user_id: str = "default"


@router.get("/project")
async def get_selected_project(user_id: str = "default") -> Any:
    """Get the selected project for a user."""
    try:
        storage = get_storage_service()
        project_id = await storage.get_selected_project(user_id)
        return {"project_id": project_id}
    except Exception as e:
        logger.error(f"Error getting project preference: {e}")
        return {"project_id": None}


@router.post("/project")
async def set_selected_project(request: SetProjectRequest) -> Any:
    """Set the selected project for a user."""
    try:
        storage = get_storage_service()
        await storage.set_selected_project(request.project_id, request.user_id)
        return {"success": True, "project_id": request.project_id}
    except Exception as e:
        logger.error(f"Error setting project preference: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/tools")
async def get_tool_preferences(user_id: str = "default") -> Any:
    """Get tool configuration preferences for a user."""
    try:
        storage = get_storage_service()
        tools = await storage.get_tool_config(user_id)
        return {"enabled_tools": tools or {}}
    except Exception as e:
        logger.error(f"Error getting tool preferences: {e}")
        return {"enabled_tools": {}}


@router.post("/tools")
async def set_tool_preferences(request: SetToolConfigRequest) -> Any:
    """Set tool configuration preferences for a user."""
    try:
        storage = get_storage_service()
        await storage.set_tool_config(request.enabled_tools, request.user_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting tool preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/recent")
async def get_recent_projects(user_id: str = "default") -> Any:
    """Get recent projects for a user."""
    try:
        storage = get_storage_service()
        projects = await storage.get_recent_projects(user_id)
        return {"projects": projects or []}
    except Exception as e:
        logger.error(f"Error getting recent projects: {e}")
        return {"projects": []}


@router.post("/projects/recent")
async def set_recent_projects(request: SetRecentProjectsRequest) -> Any:
    """Set recent projects for a user."""
    try:
        storage = get_storage_service()
        await storage.set_recent_projects(request.projects, request.user_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error setting recent projects: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
