"""Local Memory Service implementation using SQLite.

This module provides a local fallback for the Memory Bank when Vertex AI is unavailable.
It implements the same interface but uses SQLite for persistence.

Key Features:
- STRICT User Isolation (user_id is mandatory)
- SQLite storage (.sre_agent_memory.db)
- JSON metadata support
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LocalMemoryItem:
    """Represents a retrieved memory item from local storage."""

    id: str
    content: str
    metadata: dict[str, Any]
    score: float = 1.0  # Placeholder for local search output


class LocalMemoryService:
    """SQLite-based implementation of Memory Service."""

    def __init__(self, db_path: str = ".sre_agent_memory.db"):
        """Initialize the local memory service.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Index for fast filtering by user
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memories_user
                    ON memories(user_id, created_at DESC)
                """)
                conn.commit()
            logger.info(f"✅ Local Memory Service initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize local memory DB: {e}")
            raise

    async def save_memory(
        self,
        session_id: str,
        memory_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a new memory item.

        Args:
            session_id: The session identifier.
            memory_content: The text content to save.
            metadata: Optional metadata (MUST include user_id).

        Returns:
            The ID of the saved memory.
        """
        metadata = metadata or {}
        user_id = metadata.get("user_id")

        if not user_id:
            logger.warning(
                "⚠️ Access denied: save_memory called without user_id metadata"
            )
            raise PermissionError("user_id is required for saving memory")

        memory_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO memories (id, user_id, session_id, content, metadata) VALUES (?, ?, ?, ?, ?)",
                    (
                        memory_id,
                        user_id,
                        session_id,
                        memory_content,
                        json.dumps(metadata),
                    ),
                )
                conn.commit()
            return memory_id
        except Exception as e:
            logger.error(f"Failed to save local memory: {e}")
            raise

    async def search_memory(
        self,
        session_id: str | None = None,
        query: str = "",
        limit: int = 5,
    ) -> list[LocalMemoryItem]:
        """Search for memories.

        NOTE: Local search is currently keyword-based (LIKE %query%),
        not semantic, as full embeddings require heavy local deps.

        Filtering by user_id will happen in the MemoryManager layer
        (which retrieves specific metadata), but we also support
        optimizing it here if we passed user_id explicitly.

        Since strict interface in manager.py calls `search_memory(session_id, query, limit)`,
        we return broad results and let Manager filter, OR we rely on session_id if provided.

        However, MemoryManager implementation of `get_relevant_findings` does STRICT
        client-side filtering after retrieval.
        """
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Simple keyword search
                cursor = conn.execute(
                    """
                    SELECT id, content, metadata
                    FROM memories
                    WHERE content LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit * 2),  # Fetch extra to account for filtering
                )

                for row in cursor:
                    try:
                        meta = json.loads(row[2])
                    except json.JSONDecodeError:
                        meta = {}

                    results.append(
                        LocalMemoryItem(
                            id=row[0],
                            content=row[1],
                            metadata=meta,
                            score=1.0,  # Dummy score for exact match
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to search local memory: {e}")

        return results

    async def add_session_to_memory(self, session: Any) -> None:
        """Store session events in long-term memory.

        This implements the sync-to-memory pattern for local development,
        extracting textual content from session events and indexing it.
        """
        user_id = getattr(session, "user_id", "anonymous")
        session_id = getattr(session, "id", "unknown")
        events = getattr(session, "events", [])

        if not events:
            logger.debug(f"No events to index for session {session_id}")
            return

        logger.info(
            f"Indexing {len(events)} events from session {session_id} into local memory"
        )

        for event in events:
            content_text = ""
            # Extract text from content parts
            if (
                hasattr(event, "content")
                and event.content
                and hasattr(event.content, "parts")
            ):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        content_text += part.text + "\n"

            if content_text.strip():
                try:
                    await self.save_memory(
                        session_id=session_id,
                        memory_content=content_text.strip(),
                        metadata={
                            "user_id": user_id,
                            "type": "session_event",
                            "author": getattr(event, "author", "unknown"),
                            "timestamp": getattr(event, "timestamp", None),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to index session event: {e}")
