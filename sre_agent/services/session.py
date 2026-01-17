"""Session Service for SRE Agent.

Provides session management with history persistence.
Integrates with ADK sessions and provides conversation history.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sre_agent.services.storage import StorageService, get_storage_service

logger = logging.getLogger(__name__)


@dataclass
class SessionMessage:
    """A message in a session."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMessage":
        """Create from dictionary."""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """A conversation session."""

    id: str
    user_id: str
    title: str | None = None
    project_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: list[SessionMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }

    def to_summary(self) -> dict[str, Any]:
        """Convert to summary (without full message history)."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "preview": self._get_preview(),
        }

    def _get_preview(self) -> str:
        """Get a preview of the session (first user message)."""
        for msg in self.messages:
            if msg.role == "user":
                content = msg.content
                if len(content) > 100:
                    return content[:100] + "..."
                return content
        return ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", "default"),
            title=data.get("title"),
            project_id=data.get("project_id"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            messages=[
                SessionMessage.from_dict(m) for m in data.get("messages", [])
            ],
            metadata=data.get("metadata", {}),
        )


class SessionService:
    """Service for managing conversation sessions."""

    COLLECTION_SESSIONS = "sessions"

    def __init__(self, storage: StorageService):
        self.storage = storage

    async def create_session(
        self,
        user_id: str = "default",
        title: str | None = None,
        project_id: str | None = None,
    ) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            user_id=user_id,
            title=title,
            project_id=project_id,
        )

        # Save to storage
        await self.storage.backend.set(
            self.COLLECTION_SESSIONS,
            session_id,
            session.to_dict(),
        )

        logger.info(f"Created session {session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        data = await self.storage.backend.get(self.COLLECTION_SESSIONS, session_id)
        if data:
            return Session.from_dict(data)
        return None

    async def update_session(self, session: Session) -> None:
        """Update a session."""
        session.updated_at = datetime.utcnow().isoformat()
        await self.storage.backend.set(
            self.COLLECTION_SESSIONS,
            session.id,
            session.to_dict(),
        )

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        result = await self.storage.backend.delete(
            self.COLLECTION_SESSIONS,
            session_id,
        )
        if result:
            logger.info(f"Deleted session {session_id}")
        return result

    async def list_sessions(
        self,
        user_id: str = "default",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List sessions for a user (returns summaries)."""
        # Query by user_id
        sessions = await self.storage.backend.query(
            self.COLLECTION_SESSIONS,
            "user_id",
            user_id,
            limit=limit,
        )

        # Convert to Session objects and return summaries
        result = []
        for data in sessions:
            try:
                session = Session.from_dict(data)
                result.append(session.to_summary())
            except Exception as e:
                logger.warning(f"Error parsing session: {e}")

        # Sort by updated_at descending
        result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return result

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Session | None:
        """Add a message to a session."""
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        message = SessionMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        session.messages.append(message)

        # Auto-generate title from first user message
        if not session.title and role == "user":
            # Use first 50 chars of first user message as title
            session.title = content[:50] + ("..." if len(content) > 50 else "")

        await self.update_session(session)
        return session

    async def get_session_history(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Get message history for a session."""
        session = await self.get_session(session_id)
        if not session:
            return []
        return [m.to_dict() for m in session.messages]

    async def get_or_create_session(
        self,
        session_id: str | None = None,
        user_id: str = "default",
        project_id: str | None = None,
    ) -> Session:
        """Get existing session or create new one."""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session

        # Create new session
        return await self.create_session(
            user_id=user_id,
            project_id=project_id,
        )


# ============================================================================
# Singleton Access
# ============================================================================

_session_service: SessionService | None = None


def get_session_service() -> SessionService:
    """Get the singleton SessionService instance."""
    global _session_service
    if _session_service is None:
        storage = get_storage_service()
        _session_service = SessionService(storage)
    return _session_service
