"""Factory for getting MemoryManager instance."""

import os

from .manager import MemoryManager

_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global MemoryManager instance.

    Returns:
        The MemoryManager instance.
    """
    global _memory_manager

    if _memory_manager is None:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCP_PROJECT_ID"
        )
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project_id:
            # Fallback for tests or local dev without env vars
            project_id = "unknown-project"

        _memory_manager = MemoryManager(project_id=project_id, location=location)

    return _memory_manager
