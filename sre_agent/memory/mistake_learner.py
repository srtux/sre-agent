"""Mistake Learner — captures mistakes and detects self-corrections.

This module sits in the tool callback chain and:
1. Captures structured mistakes on tool failure (after_tool / on_error)
2. Detects self-corrections when a tool that previously failed now succeeds
3. Records corrections back to the MistakeMemoryStore
4. Emits UI events for real-time visibility

The self-correction detection works by tracking recent failures per tool
in a short-lived in-memory buffer. When a tool succeeds after a recent
failure, the success arguments are recorded as the "correction" for that
mistake.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sre_agent.api.helpers.memory_events import (
    MemoryAction,
    MemoryCategory,
    MemoryEvent,
    get_memory_event_bus,
)
from sre_agent.memory.mistake_store import (
    MistakeMemoryStore,
    _classify_mistake,
    _sanitize_args,
    get_mistake_store,
)
from sre_agent.schema import MistakeCategory

logger = logging.getLogger(__name__)

# Patterns in error messages that indicate a learnable (non-transient) mistake.
_LEARNABLE_PATTERNS: list[str] = [
    "invalid filter",
    "invalid argument",
    "unrecognized field",
    "parse error",
    "syntax error",
    "unknown metric",
    "resource.type",
    "resource.labels",
    "metric.type",
    "filter must",
    "could not parse",
    "malformed",
    "not a valid",
    "unsupported",
    "not supported",
    "400",
    "invalid_argument",
]

# Maximum number of recent failures to track per tool for correction detection.
_MAX_RECENT_FAILURES = 5


class _RecentFailure:
    """A short-lived record of a recent tool failure awaiting correction."""

    __slots__ = ("args", "category", "error_message", "timestamp", "tool_name")

    def __init__(
        self,
        tool_name: str,
        error_message: str,
        category: MistakeCategory,
        args: dict[str, Any],
    ) -> None:
        self.tool_name = tool_name
        self.error_message = error_message
        self.category = category
        self.args = args
        self.timestamp = datetime.now(timezone.utc)


class MistakeLearner:
    """Captures mistakes from tool failures and detects self-corrections.

    Maintains a per-tool buffer of recent failures. When a tool succeeds
    after a recent failure, the learner records the correction.
    """

    def __init__(self, store: MistakeMemoryStore | None = None) -> None:
        """Initialize the learner.

        Args:
            store: Optional MistakeMemoryStore instance. Uses singleton if None.
        """
        self._store = store
        # tool_name -> list of recent failures (FIFO, capped)
        self._recent_failures: dict[str, list[_RecentFailure]] = defaultdict(list)

    @property
    def store(self) -> MistakeMemoryStore:
        """Lazily resolve the store singleton."""
        if self._store is None:
            self._store = get_mistake_store()
        return self._store

    def _is_learnable(self, error_message: str) -> bool:
        """Check if an error message represents a learnable mistake.

        Args:
            error_message: The error message to check.

        Returns:
            True if the error matches a known learnable pattern.
        """
        lower = error_message.lower()
        return any(pattern in lower for pattern in _LEARNABLE_PATTERNS)

    async def on_tool_failure(
        self,
        tool_name: str,
        args: dict[str, Any],
        error_message: str,
        session_id: str | None = None,
    ) -> None:
        """Handle a tool failure: record the mistake and buffer for correction.

        Args:
            tool_name: Name of the tool that failed.
            args: Arguments that caused the failure.
            error_message: The error message received.
            session_id: Session ID for event routing.
        """
        if not self._is_learnable(error_message):
            return

        try:
            category = _classify_mistake(error_message)

            # Record to persistent store
            record = await self.store.record_mistake(
                tool_name=tool_name,
                error_message=error_message,
                failed_args=args,
                category=category,
            )

            # Buffer for correction detection
            failure = _RecentFailure(
                tool_name=tool_name,
                error_message=error_message,
                category=category,
                args=_sanitize_args(args),
            )
            recent = self._recent_failures[tool_name]
            recent.append(failure)
            if len(recent) > _MAX_RECENT_FAILURES:
                recent.pop(0)

            # Emit UI event
            event = MemoryEvent(
                action=MemoryAction.STORED,
                category=MemoryCategory.FAILURE,
                title=f"Mistake recorded: {tool_name}",
                description=(
                    f"Category: {category.value}\n"
                    f"Error: {error_message[:120]}\n"
                    f"Occurrences: {record.occurrence_count}"
                ),
                tool_name=tool_name,
                metadata={
                    "category": category.value,
                    "occurrence_count": record.occurrence_count,
                    "fingerprint": record.fingerprint,
                },
            )
            event_bus = get_memory_event_bus()
            await event_bus.emit(session_id, event)

        except Exception:
            logger.debug("Failed to record mistake for %s", tool_name, exc_info=True)

    async def on_tool_success(
        self,
        tool_name: str,
        args: dict[str, Any],
        session_id: str | None = None,
    ) -> None:
        """Handle a tool success: check for self-correction opportunity.

        If the tool recently failed and now succeeds, record the correction.

        Args:
            tool_name: Name of the tool that succeeded.
            args: Arguments used in the successful call.
            session_id: Session ID for event routing.
        """
        recent = self._recent_failures.get(tool_name)
        if not recent:
            return

        try:
            # Pop the most recent failure for this tool
            failure = recent.pop()
            safe_args = _sanitize_args(args)

            # Build a human-readable correction description
            correction = self._describe_correction(failure, safe_args)

            # Record the correction in persistent store
            updated = await self.store.record_correction(
                tool_name=tool_name,
                error_message=failure.error_message,
                correction=correction,
                corrected_args=args,
                category=failure.category,
            )

            if updated:
                logger.info(
                    "Self-correction detected for %s: %s",
                    tool_name,
                    correction[:100],
                )

                # Emit UI event
                event = MemoryEvent(
                    action=MemoryAction.PATTERN_LEARNED,
                    category=MemoryCategory.PATTERN,
                    title=f"Self-correction: {tool_name}",
                    description=correction[:200],
                    tool_name=tool_name,
                    metadata={
                        "category": failure.category.value,
                        "original_error": failure.error_message[:100],
                    },
                )
                event_bus = get_memory_event_bus()
                await event_bus.emit(session_id, event)

        except Exception:
            logger.debug("Failed to record correction for %s", tool_name, exc_info=True)

    def _describe_correction(
        self,
        failure: _RecentFailure,
        corrected_args: dict[str, Any],
    ) -> str:
        """Build a human-readable description of a self-correction.

        Compares the failed and corrected arguments to highlight what changed.

        Args:
            failure: The original failure record.
            corrected_args: The arguments that worked.

        Returns:
            A description like "Changed filter from 'X' to 'Y'".
        """
        changes: list[str] = []

        for key in set(failure.args) | set(corrected_args):
            old_val = failure.args.get(key)
            new_val = corrected_args.get(key)
            if old_val != new_val:
                old_repr = (
                    json.dumps(old_val, default=str)[:80] if old_val else "(absent)"
                )
                new_repr = (
                    json.dumps(new_val, default=str)[:80] if new_val else "(removed)"
                )
                changes.append(f"'{key}': {old_repr} -> {new_repr}")

        if changes:
            return (
                f"After error '{failure.error_message[:80]}', "
                f"corrected: {'; '.join(changes[:3])}"
            )
        return (
            f"After error '{failure.error_message[:80]}', "
            f"succeeded with same tool using different approach"
        )

    async def on_tool_exception(
        self,
        tool_name: str,
        args: dict[str, Any],
        error: Exception,
        session_id: str | None = None,
    ) -> None:
        """Handle a tool exception (raised, not returned as error response).

        Args:
            tool_name: Name of the tool that raised.
            args: Arguments passed to the tool.
            error: The exception that was raised.
            session_id: Session ID for event routing.
        """
        error_message = f"{type(error).__name__}: {error!s}"
        await self.on_tool_failure(
            tool_name=tool_name,
            args=args,
            error_message=error_message,
            session_id=session_id,
        )


# ── Singleton Factory ────────────────────────────────────────────────

_learner: MistakeLearner | None = None


def get_mistake_learner() -> MistakeLearner:
    """Get or create the global MistakeLearner singleton.

    Returns:
        The MistakeLearner instance.
    """
    global _learner
    if _learner is None:
        _learner = MistakeLearner()
    return _learner
