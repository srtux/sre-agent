"""Memory Manager for SRE Agent.

This module provides the central interface for storing and retrieving investigation context
using Vertex AI Memory Bank (or fallback persistence).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from google.adk.memory import VertexAiMemoryBankService

from sre_agent.schema import Confidence, InvestigationPhase, MemoryItem

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages investigation state and findings using Vertex AI Memory Bank."""

    def __init__(self, project_id: str, location: str = "us-central1"):
        """Initialize the Memory Manager.

        Args:
            project_id: GCP Project ID.
            location: GCP Location (default: us-central1).
        """
        self.project_id = project_id
        self.location = location
        self.memory_service: Any | None = None
        self._check_init_memory_service()

        # Local state cache (for current execution)
        self._current_state = InvestigationPhase.INITIATED
        self._findings_cache: list[MemoryItem] = []

    def _check_init_memory_service(self) -> None:
        """Initialize the Vertex AI Memory Service if credentials allow."""
        try:
            # We use a specific corpus for SRE investigations if configured,
            # otherwise allow it to separate by session_id automatically.
            self.memory_service = VertexAiMemoryBankService(
                project=self.project_id,
                location=self.location,
            )
            logger.info(f"✅ Memory Manager initialized for project {self.project_id}")
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to initialize Vertex AI Memory Service: {e}. "
                "Falling back to Local SQLite Memory."
            )
            try:
                from sre_agent.memory.local import LocalMemoryService

                self.memory_service = LocalMemoryService()
                logger.info("✅ Local Memory Service initialized")
            except Exception as local_e:
                logger.error(
                    f"❌ Failed to initialize Local Memory fallback: {local_e}"
                )
                self.memory_service = None

    async def add_finding(
        self,
        description: str,
        source_tool: str,
        confidence: Confidence = Confidence.MEDIUM,
        structured_data: dict[str, Any] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Add a finding to memory.

        Args:
            description: Human-readable description.
            source_tool: Tool that produced the finding.
            confidence: Confidence level.
            structured_data: Optional raw data.
            session_id: Current session ID (required for persistence).
            user_id: The authenticated user ID (email) for isolation.
        """
        item = MemoryItem(
            source_tool=source_tool,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description,
            structured_data=structured_data,
        )
        self._findings_cache.append(item)

        if self.memory_service and session_id:
            try:
                # Store as unstructured text for semantic search
                await self.memory_service.save_memory(
                    session_id=session_id,
                    memory_content=f"[{source_tool}] {description}",
                    metadata={
                        "confidence": confidence.value,
                        "timestamp": item.timestamp,
                        "tool": source_tool,
                        "type": "finding",
                        "user_id": user_id or "anonymous",
                    },
                )
            except Exception as e:
                logger.error(f"Failed to save finding to Memory Bank: {e}")

    async def get_relevant_findings(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[MemoryItem]:
        """Retrieve relevant findings from memory.

        Args:
            query: Semantic query string.
            session_id: Session ID to scope search.
            limit: Max results.
            user_id: The authenticated user ID (email) for isolation.

        Returns:
            List of MemoryItems (reconstructed from storage).
        """
        results: list[MemoryItem] = []

        # 1. Search persistence if available
        if self.memory_service:
            try:
                memories = await self.memory_service.search_memory(
                    session_id=session_id,
                    query=query,
                    limit=limit * 2,  # Fetch extra for client-side filtering
                )
                for mem in memories:
                    # STRICT SECURITY: Filter by user_id
                    # We default to "anonymous" to prevent None matching everything
                    mem_user_id = mem.metadata.get("user_id", "anonymous")
                    search_user_id = user_id or "anonymous"

                    if mem_user_id != search_user_id:
                        continue

                    # simplistic reconstruction
                    results.append(
                        MemoryItem(
                            source_tool=mem.metadata.get("tool", "unknown"),
                            confidence=Confidence(
                                mem.metadata.get("confidence", Confidence.MEDIUM.value)
                            ),
                            timestamp=mem.metadata.get(
                                "timestamp", datetime.now(timezone.utc).isoformat()
                            ),
                            description=mem.content,
                            structured_data=None,  # Not persisted in simple text memory
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to search Memory Bank: {e}")

        # Limit results after filtering
        results = results[:limit]

        # 2. Add local cache if not present (simple dedup)
        # In a real impl, we might merge/rank, but here we just ensure we have *something*
        if not results:
            return self._findings_cache[-limit:]  # Return most recent if offline

        return results

    async def update_state(
        self, state: InvestigationPhase, session_id: str | None = None
    ) -> None:
        """Update the investigation state."""
        self._current_state = state
        logger.info(f"🔄 Investigation State transitioned to: {state.value}")

        if self.memory_service and session_id:
            try:
                # We store state transition as a memory events too
                await self.memory_service.save_memory(
                    session_id=session_id,
                    memory_content=f"Investigation state changed to {state.value}",
                    metadata={"type": "state_change", "new_state": state.value},
                )
            except Exception as e:
                logger.error(f"Failed to persist state change: {e}")

    def get_state(self) -> InvestigationPhase:
        """Get the current investigation state."""
        return self._current_state
