"""Memory event helpers for real-time memory action visibility.

This module provides utilities for emitting memory events to the frontend,
allowing users to see when the agent memorizes learnings, searches memory,
or learns investigation patterns.

Event Schema:
    {
        "type": "memory",
        "action": "stored|searched|pattern_learned|pattern_applied",
        "category": "failure|success|pattern|search",
        "title": "Short title for toast",
        "description": "Detailed description",
        "tool_name": "The tool that triggered this",
        "metadata": {...}  # Optional additional data
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MemoryAction(str, Enum):
    """Types of memory actions that can be emitted."""

    STORED = "stored"  # Finding stored to memory
    SEARCHED = "searched"  # Memory searched
    PATTERN_LEARNED = "pattern_learned"  # Investigation pattern learned
    PATTERN_APPLIED = "pattern_applied"  # Past pattern used
    TOOL_TRACKED = "tool_tracked"  # Tool call recorded for sequence


class MemoryCategory(str, Enum):
    """Categories of memory events."""

    FAILURE = "failure"  # Learning from a failure
    SUCCESS = "success"  # Recording a successful finding
    PATTERN = "pattern"  # Investigation pattern
    SEARCH = "search"  # Memory search
    TRACKING = "tracking"  # Tool sequence tracking


@dataclass
class MemoryEvent:
    """A memory event to be emitted to the frontend."""

    action: MemoryAction
    category: MemoryCategory
    title: str
    description: str
    tool_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        """Convert to JSON string for streaming."""
        return json.dumps(
            {
                "type": "memory",
                "action": self.action.value,
                "category": self.category.value,
                "title": self.title,
                "description": self.description,
                "tool_name": self.tool_name,
                "metadata": self.metadata,
                "timestamp": self.timestamp,
            },
            default=str,
        )


class MemoryEventBus:
    """Thread-safe event bus for memory events.

    Events are queued and can be consumed by the streaming endpoint.
    Each session has its own event queue.
    """

    _instance: MemoryEventBus | None = None
    _lock: asyncio.Lock

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._queues: dict[str, asyncio.Queue[MemoryEvent]] = {}
        self._lock = asyncio.Lock()
        self._enabled = True  # Can be disabled via config

    @classmethod
    def get_instance(cls) -> MemoryEventBus:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = MemoryEventBus()
        return cls._instance

    @property
    def enabled(self) -> bool:
        """Check if memory events are enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable memory events."""
        self._enabled = enabled

    async def get_queue(self, session_id: str) -> asyncio.Queue[MemoryEvent]:
        """Get or create a queue for a session."""
        async with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = asyncio.Queue()
            return self._queues[session_id]

    async def emit(self, session_id: str | None, event: MemoryEvent) -> None:
        """Emit a memory event to the queue.

        Args:
            session_id: The session to emit to. If None, uses "global".
            event: The memory event to emit.
        """
        if not self._enabled:
            return

        sid = session_id or "global"
        queue = await self.get_queue(sid)
        await queue.put(event)
        logger.debug(f"Memory event emitted: {event.action.value} - {event.title}")

    def emit_sync(self, session_id: str | None, event: MemoryEvent) -> None:
        """Synchronously emit a memory event (creates task in background).

        This is useful for callbacks that can't be async.
        """
        if not self._enabled:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Store task reference to prevent GC (per ruff RUF006)
                task = asyncio.create_task(self.emit(session_id, event))
                task.add_done_callback(
                    lambda t: None
                )  # Prevent unhandled exception warning
            else:
                loop.run_until_complete(self.emit(session_id, event))
        except RuntimeError:
            # No event loop, skip
            logger.debug("No event loop available for memory event")

    async def drain_events(self, session_id: str) -> AsyncGenerator[MemoryEvent, None]:
        """Drain all pending events for a session.

        This is non-blocking - returns immediately if no events are pending.
        """
        queue = await self.get_queue(session_id)
        while not queue.empty():
            try:
                event = queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                break

    async def cleanup_session(self, session_id: str) -> None:
        """Remove a session's queue when done."""
        async with self._lock:
            if session_id in self._queues:
                del self._queues[session_id]


# Singleton accessor
def get_memory_event_bus() -> MemoryEventBus:
    """Get the global memory event bus."""
    return MemoryEventBus.get_instance()


# ============================================================================
# Event Creation Helpers
# ============================================================================


def create_failure_learning_event(
    tool_name: str,
    error_summary: str,
    lesson: str,
) -> MemoryEvent:
    """Create an event for learning from a tool failure."""
    return MemoryEvent(
        action=MemoryAction.STORED,
        category=MemoryCategory.FAILURE,
        title=f"Learned from {tool_name} failure",
        description=f"Error: {error_summary[:100]}...\nLesson stored for future reference.",
        tool_name=tool_name,
        metadata={"lesson_preview": lesson[:200] if len(lesson) > 200 else lesson},
    )


def create_success_finding_event(
    tool_name: str,
    finding_type: str,
    finding_summary: str,
) -> MemoryEvent:
    """Create an event for storing a successful finding."""
    return MemoryEvent(
        action=MemoryAction.STORED,
        category=MemoryCategory.SUCCESS,
        title=f"Memorized: {finding_type}",
        description=finding_summary[:200]
        + ("..." if len(finding_summary) > 200 else ""),
        tool_name=tool_name,
        metadata={"finding_type": finding_type},
    )


def create_pattern_learned_event(
    symptom_type: str,
    root_cause: str,
    tool_sequence: list[str],
) -> MemoryEvent:
    """Create an event for learning an investigation pattern."""
    return MemoryEvent(
        action=MemoryAction.PATTERN_LEARNED,
        category=MemoryCategory.PATTERN,
        title=f"Learned pattern: {symptom_type}",
        description=f"Root cause: {root_cause}\nTool sequence: {' → '.join(tool_sequence[:5])}",
        metadata={
            "symptom_type": symptom_type,
            "root_cause": root_cause,
            "tool_count": len(tool_sequence),
        },
    )


def create_pattern_applied_event(
    symptom_type: str,
    confidence: float,
    tool_sequence: list[str],
) -> MemoryEvent:
    """Create an event for applying a past pattern."""
    return MemoryEvent(
        action=MemoryAction.PATTERN_APPLIED,
        category=MemoryCategory.PATTERN,
        title=f"Using learned pattern: {symptom_type}",
        description=f"Confidence: {confidence:.0%}\nSuggested: {' → '.join(tool_sequence[:3])}...",
        metadata={
            "symptom_type": symptom_type,
            "confidence": confidence,
            "tool_sequence": tool_sequence[:5],
        },
    )


def create_memory_search_event(
    query: str,
    result_count: int,
) -> MemoryEvent:
    """Create an event for a memory search."""
    return MemoryEvent(
        action=MemoryAction.SEARCHED,
        category=MemoryCategory.SEARCH,
        title=f"Memory searched: {result_count} result(s)",
        description=f"Query: {query[:100]}{'...' if len(query) > 100 else ''}",
        metadata={"query": query, "result_count": result_count},
    )


def create_tool_tracking_event(tool_name: str, sequence_length: int) -> MemoryEvent:
    """Create an event for tracking a tool call in the sequence."""
    return MemoryEvent(
        action=MemoryAction.TOOL_TRACKED,
        category=MemoryCategory.TRACKING,
        title=f"Tracking: {tool_name}",
        description=f"Tool #{sequence_length} in current investigation",
        tool_name=tool_name,
        metadata={"sequence_position": sequence_length},
    )
