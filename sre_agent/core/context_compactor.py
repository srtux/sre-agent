"""Context Compaction with Sliding Window.

Implements the sliding window strategy for efficient context utilization,
compacting older events into summaries while keeping recent events in full.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sre_agent.core.prompt_composer import SessionSummary
from sre_agent.core.summarizer import Summarizer, get_summarizer

logger = logging.getLogger(__name__)


@dataclass
class WorkingContext:
    """The working context sent to the LLM.

    Combines:
    - Compacted summary of older events
    - Recent raw events kept in full
    """

    summary: SessionSummary
    recent_events: list[dict[str, Any]]
    total_token_estimate: int = 0
    compaction_applied: bool = False
    last_compaction_timestamp: str | None = None


@dataclass
class CompactionConfig:
    """Configuration for context compaction."""

    # Token budget for working context
    token_budget: int = 32000

    # Trigger compaction when raw events exceed this
    compaction_trigger_tokens: int = 24000

    # Number of recent events to keep in full
    recent_events_count: int = 5

    # Minimum events before considering compaction
    min_events_for_compaction: int = 10

    # Characters per token estimate
    chars_per_token: int = 4


class ContextCompactor:
    """Manages context compaction for efficient LLM utilization.

    Strategy:
    1. Keep last N events in full (raw)
    2. Summarize older events into a compressed summary
    3. Trigger compaction when context exceeds threshold
    4. Store compaction events in the session for persistence
    """

    def __init__(
        self,
        config: CompactionConfig | None = None,
        summarizer: Summarizer | None = None,
    ) -> None:
        """Initialize the context compactor.

        Args:
            config: Compaction configuration
            summarizer: Summarizer instance for event compression
        """
        self.config = config or CompactionConfig()
        self.summarizer = summarizer or get_summarizer()

        # Track compaction state per session
        self._compaction_state: dict[str, dict[str, Any]] = {}

    def get_working_context(
        self,
        session_id: str,
        events: list[dict[str, Any]],
        existing_summary: SessionSummary | None = None,
    ) -> WorkingContext:
        """Get the working context for a session.

        Args:
            session_id: Session identifier
            events: All events in the session
            existing_summary: Previously stored summary (for resumption)

        Returns:
            WorkingContext with summary and recent events
        """
        if not events:
            return WorkingContext(
                summary=SessionSummary(summary_text="New session - no history."),
                recent_events=[],
                total_token_estimate=0,
            )

        # Estimate current token usage
        raw_tokens = self._estimate_tokens(events)
        logger.debug(f"Session {session_id}: {len(events)} events, ~{raw_tokens} tokens")

        # Check if compaction needed
        needs_compaction = (
            raw_tokens > self.config.compaction_trigger_tokens
            and len(events) > self.config.min_events_for_compaction
        )

        if needs_compaction:
            return self._compact_context(session_id, events, existing_summary)

        # No compaction needed - use existing summary + recent events
        recent = events[-self.config.recent_events_count :]

        if existing_summary:
            summary = existing_summary
        else:
            # Summarize all but recent events
            older_events = events[: -self.config.recent_events_count]
            if older_events:
                event_summary = self.summarizer.summarize_events(older_events)
                summary = SessionSummary(
                    summary_text=event_summary.summary_text,
                    key_findings=event_summary.key_findings,
                    tools_used=event_summary.tools_used,
                    last_compaction_turn=len(older_events),
                )
            else:
                summary = SessionSummary(summary_text="Beginning of session.")

        recent_tokens = self._estimate_tokens(recent)
        summary_tokens = len(summary.summary_text) // self.config.chars_per_token

        return WorkingContext(
            summary=summary,
            recent_events=recent,
            total_token_estimate=recent_tokens + summary_tokens,
            compaction_applied=False,
        )

    def _compact_context(
        self,
        session_id: str,
        events: list[dict[str, Any]],
        existing_summary: SessionSummary | None = None,
    ) -> WorkingContext:
        """Perform context compaction.

        Args:
            session_id: Session identifier
            events: All events to compact
            existing_summary: Previously stored summary

        Returns:
            WorkingContext with compacted summary
        """
        logger.info(f"Compacting context for session {session_id}")

        # Keep recent events in full
        recent = events[-self.config.recent_events_count :]
        older = events[: -self.config.recent_events_count]

        # Build compacted summary
        if existing_summary and existing_summary.last_compaction_turn > 0:
            # Incremental compaction: summarize new events and merge
            new_events_start = existing_summary.last_compaction_turn
            new_older = older[new_events_start:]

            if new_older:
                new_summary = self.summarizer.summarize_events(new_older)
                merged_text = (
                    f"{existing_summary.summary_text}\n\n"
                    f"[Subsequent events:]\n{new_summary.summary_text}"
                )
                merged_findings = (
                    existing_summary.key_findings + new_summary.key_findings
                )[-10:]
                merged_tools = list(
                    set(existing_summary.tools_used + new_summary.tools_used)
                )

                summary = SessionSummary(
                    summary_text=merged_text,
                    key_findings=merged_findings,
                    tools_used=merged_tools,
                    last_compaction_turn=len(older),
                )
            else:
                summary = existing_summary
        else:
            # Full compaction
            event_summary = self.summarizer.summarize_events(older)
            summary = SessionSummary(
                summary_text=event_summary.summary_text,
                key_findings=event_summary.key_findings,
                tools_used=event_summary.tools_used,
                last_compaction_turn=len(older),
            )

        # Update compaction state
        now = datetime.now(timezone.utc)
        self._compaction_state[session_id] = {
            "last_compaction": now.isoformat(),
            "events_compacted": len(older),
            "summary_tokens": len(summary.summary_text) // self.config.chars_per_token,
        }

        recent_tokens = self._estimate_tokens(recent)
        summary_tokens = len(summary.summary_text) // self.config.chars_per_token

        return WorkingContext(
            summary=summary,
            recent_events=recent,
            total_token_estimate=recent_tokens + summary_tokens,
            compaction_applied=True,
            last_compaction_timestamp=now.isoformat(),
        )

    def should_compact(self, events: list[dict[str, Any]]) -> bool:
        """Check if compaction should be triggered.

        Args:
            events: Events to check

        Returns:
            True if compaction should be performed
        """
        if len(events) < self.config.min_events_for_compaction:
            return False

        tokens = self._estimate_tokens(events)
        return tokens > self.config.compaction_trigger_tokens

    def _estimate_tokens(self, events: list[dict[str, Any]]) -> int:
        """Estimate token count for events.

        Args:
            events: Events to estimate

        Returns:
            Estimated token count
        """
        total_chars = 0
        for event in events:
            content = event.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            else:
                # Approximate for non-string content
                import json

                total_chars += len(json.dumps(content, default=str))

        return total_chars // self.config.chars_per_token

    def get_compaction_stats(self, session_id: str) -> dict[str, Any]:
        """Get compaction statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Statistics dictionary
        """
        state = self._compaction_state.get(session_id, {})
        return {
            "last_compaction": state.get("last_compaction"),
            "events_compacted": state.get("events_compacted", 0),
            "summary_tokens": state.get("summary_tokens", 0),
        }

    def clear_session(self, session_id: str) -> None:
        """Clear compaction state for a session.

        Args:
            session_id: Session to clear
        """
        if session_id in self._compaction_state:
            del self._compaction_state[session_id]


# Singleton instance
_context_compactor: ContextCompactor | None = None


def get_context_compactor(config: CompactionConfig | None = None) -> ContextCompactor:
    """Get the singleton context compactor instance."""
    global _context_compactor
    if _context_compactor is None:
        _context_compactor = ContextCompactor(config=config)
    return _context_compactor
