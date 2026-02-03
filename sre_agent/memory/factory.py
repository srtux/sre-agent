"""Factory for getting MemoryManager and ADK memory service instances."""

import logging
import os
from typing import Any

from .manager import MemoryManager

logger = logging.getLogger(__name__)

_memory_manager: MemoryManager | None = None
_adk_memory_service: Any | None = None
_adk_memory_service_initialized: bool = False


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


def get_adk_memory_service() -> Any | None:
    """Get the ADK-native memory service for use with InvocationContext.

    This returns the raw VertexAiMemoryBankService (or None in local mode)
    that can be passed to InvocationContext.memory_service, enabling
    PreloadMemoryTool and LoadMemoryTool to function via
    tool_context.search_memory().

    Returns:
        The VertexAiMemoryBankService instance, or None if unavailable.
    """
    global _adk_memory_service, _adk_memory_service_initialized

    if _adk_memory_service_initialized:
        return _adk_memory_service

    _adk_memory_service_initialized = True

    agent_engine_id = os.environ.get("SRE_AGENT_ID")
    if not agent_engine_id:
        logger.info("SRE_AGENT_ID not set; ADK memory service disabled (local mode)")
        return None

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCP_PROJECT_ID"
    )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        logger.warning("No project ID for ADK memory service")
        return None

    try:
        from google.adk.memory import VertexAiMemoryBankService

        _adk_memory_service = VertexAiMemoryBankService(
            project=project_id,
            location=location,
        )
        logger.info(
            f"ADK memory service initialized for InvocationContext "
            f"(project={project_id}, location={location})"
        )
        return _adk_memory_service
    except Exception as e:
        logger.warning(f"Failed to initialize ADK memory service: {e}")
        return None
