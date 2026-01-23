"""Vertex AI Memory Bank service for SRE Agent context retention."""

import logging
import os
from typing import Any

from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import Session

logger = logging.getLogger(__name__)


class SREMemoryManager:
    """Manager for Vertex AI Memory Bank interactions.

    Provides specialized methods for SRE investigations:
    - Finding similar past incidents
    - Summarizing current investigation state
    - Categorizing findings per service/project
    """

    def __init__(
        self, project_id: str | None = None, location: str = "us-central1"
    ) -> None:
        """Initialize memory service.

        Args:
            project_id: GCP Project ID
            location: Google Cloud region
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._memory_service: VertexAiMemoryBankService | None = None

        if self.project_id:
            try:
                self._memory_service = VertexAiMemoryBankService(
                    project=self.project_id,
                    location=self.location,
                )
                logger.info(
                    f"VertexAiMemoryBankService initialized for {self.project_id} in {self.location}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize VertexAiMemoryBankService: {e}")
        else:
            logger.info("No project_id provided; VertexAiMemoryBankService disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if memory service is available."""
        return self._memory_service is not None

    async def add_session_to_memory(self, session: Session) -> bool:
        """Store session events in long-term memory for search.

        Args:
            session: The ADK Session object containing history/findings

        Returns:
            True if successfully stored
        """
        if not self._memory_service:
            return False

        try:
            await self._memory_service.add_session_to_memory(session)
            logger.debug(f"Session {session.id} added to Memory Bank")
            return True
        except Exception as e:
            logger.error(f"Error adding session to memory: {e}")
            return False

    async def search_similar_incidents(
        self, query: str, user_id: str = "default", app_name: str = "sre_agent"
    ) -> list[dict[str, Any]]:
        """Search past investigations for similar failure patterns.

        Args:
            query: The search query (e.g., "high latency in checkout service")
            user_id: The ID of the user
            app_name: The application identifier

        Returns:
            List of matching memory entries
        """
        if not self._memory_service:
            return []

        try:
            response = await self._memory_service.search_memory(
                app_name=app_name, user_id=user_id, query=query
            )

            # Convert response entries to dicts for easier consumption by LLM
            results = []
            if hasattr(response, "memories") and response.memories:
                for memory in response.memories:
                    results.append(
                        {
                            "id": memory.id,
                            "text": memory.text or "",
                            "metadata": memory.metadata or {},
                            "relevance_score": getattr(memory, "relevance_score", 0.0),
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []


# ============================================================================
# Singleton Access
# ============================================================================

_memory_manager: SREMemoryManager | None = None


def get_memory_manager() -> SREMemoryManager:
    """Get the singleton SREMemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = SREMemoryManager()
    return _memory_manager
