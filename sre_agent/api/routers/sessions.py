"""Session management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from sre_agent.services import get_session_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str = "default"
    project_id: str | None = None
    title: str | None = None


class UpdateSessionRequest(BaseModel):
    """Request model for updating a session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str | None = None


@router.post("")
async def create_session(request: CreateSessionRequest) -> Any:
    """Create a new session using ADK session service.

    This endpoint initializes a new investigation session. It supports:
    - **Persistence**: Sessions are stored in SQLite (local) or Firestore (Cloud Run).
    - **Context**: Can be initialized with a specific GCP project context.
    - **State Management**: Tracks user preferences and conversation history.
    """
    try:
        session_manager = get_session_service()
        initial_state = {}
        if request.project_id:
            initial_state["project_id"] = request.project_id
        if request.title:
            initial_state["title"] = request.title

        session = await session_manager.create_session(
            user_id=request.user_id,
            initial_state=initial_state,
        )
        return {
            "id": session.id,
            "user_id": request.user_id,
            "project_id": request.project_id,
            "state": session.state,
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("")
async def list_sessions(user_id: str = "default") -> Any:
    """List sessions for a user using ADK session service."""
    try:
        session_manager = get_session_service()
        sessions = await session_manager.list_sessions(user_id=user_id)
        return {"sessions": [s.to_dict() for s in sessions]}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}")
async def get_session(session_id: str, user_id: str = "default") -> Any:
    """Get a session by ID using ADK session service."""
    try:
        session_manager = get_session_service()
        session = await session_manager.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert ADK session to response format
        events = session.events or []
        messages = []
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        messages.append(
                            {
                                "role": event.author,
                                "content": part.text,
                                "timestamp": event.timestamp,
                            }
                        )

        return {
            "id": session.id,
            "user_id": user_id,
            "state": session.state,
            "messages": messages,
            "last_update_time": session.last_update_time,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{session_id}")
async def delete_session(session_id: str, user_id: str = "default") -> Any:
    """Delete a session using ADK session service."""
    try:
        session_manager = get_session_service()
        result = await session_manager.delete_session(session_id, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user_id: str = "default",
) -> Any:
    """Update a session's state (e.g. title)."""
    try:
        session_manager = get_session_service()
        session = await session_manager.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        updates = {}
        if request.title is not None:
            updates["title"] = request.title

        if updates:
            await session_manager.update_session_state(session, updates)

        return {"message": "Session updated", "id": session_id, "updates": updates}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = "default") -> Any:
    """Get message history for a session from ADK events."""
    try:
        session_manager = get_session_service()
        session = await session_manager.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Extract messages from ADK events
        events = session.events or []
        messages = []
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        messages.append(
                            {
                                "role": event.author,
                                "content": part.text,
                                "timestamp": event.timestamp,
                            }
                        )

        return {"session_id": session_id, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
