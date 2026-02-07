"""Mistake Advisor — provides pre-tool guidance from past mistakes.

This module sits in the before_tool callback chain and:
1. Queries the MistakeMemoryStore for relevant past mistakes
2. Generates concise, actionable advice ("don't do X, do Y instead")
3. Returns the advice as a modified tool-args dict or injects it into context

It also provides prompt-level lessons for injection into the developer
context, giving the agent a "cheat sheet" of its most common mistakes.
"""

import logging
from typing import Any

from sre_agent.memory.mistake_store import (
    MistakeMemoryStore,
    get_mistake_store,
)
from sre_agent.schema import MistakeRecord

logger = logging.getLogger(__name__)


def format_lesson(record: MistakeRecord) -> str:
    """Format a single MistakeRecord into a concise lesson string.

    If the record has a correction, produces a "DON'T / DO" pair.
    Otherwise, produces a warning with the error pattern.

    Args:
        record: The mistake record to format.

    Returns:
        A formatted lesson string.
    """
    tool = record.tool_name
    count = record.occurrence_count
    category = record.category.value

    if record.correction:
        return f"- [{tool}] ({category}, seen {count}x): {record.correction}"
    else:
        # No correction yet — warn about the error pattern
        error_preview = record.error_message[:120]
        return f"- [{tool}] ({category}, seen {count}x): AVOID: {error_preview}"


def format_tool_advice(records: list[MistakeRecord]) -> str:
    """Format a list of mistake records into advice text for a specific tool.

    Args:
        records: Mistake records for the tool.

    Returns:
        Formatted advice string, or empty string if no records.
    """
    if not records:
        return ""

    lines = [
        f"PAST MISTAKES for '{records[0].tool_name}' ({len(records)} known pitfall(s)):"
    ]
    for record in records:
        lines.append(format_lesson(record))
    return "\n".join(lines)


class MistakeAdvisor:
    """Provides pre-tool advice and prompt-level lessons from past mistakes.

    Uses the MistakeMemoryStore to look up relevant mistakes and format
    them as actionable guidance for the agent.
    """

    def __init__(self, store: MistakeMemoryStore | None = None) -> None:
        """Initialize the advisor.

        Args:
            store: Optional MistakeMemoryStore. Uses singleton if None.
        """
        self._store = store

    @property
    def store(self) -> MistakeMemoryStore:
        """Lazily resolve the store singleton."""
        if self._store is None:
            self._store = get_mistake_store()
        return self._store

    async def get_tool_advice(self, tool_name: str) -> str:
        """Get advice for a specific tool based on past mistakes.

        Called in the before_tool callback to inject guidance before
        the tool executes.

        Args:
            tool_name: The tool about to be called.

        Returns:
            Advice string, or empty string if no relevant mistakes.
        """
        try:
            records = await self.store.get_mistakes_for_tool(tool_name)
            return format_tool_advice(records)
        except Exception:
            logger.debug("Failed to get tool advice for %s", tool_name, exc_info=True)
            return ""

    async def get_prompt_lessons(self, limit: int = 10) -> str:
        """Get top lessons for injection into the agent prompt.

        Returns a formatted block of the most common mistakes and their
        corrections, suitable for inclusion in the developer context of
        the prompt composer.

        Args:
            limit: Maximum number of lessons to include.

        Returns:
            Formatted lessons block, or empty string if none.
        """
        try:
            # Prioritize mistakes that have corrections (most valuable)
            corrected = await self.store.get_corrected_mistakes(limit=limit)
            remaining = limit - len(corrected)

            # Fill remainder with top uncorrected mistakes
            top_all: list[MistakeRecord] = []
            if remaining > 0:
                top_all = await self.store.get_top_mistakes(limit=limit)
                # Deduplicate: exclude fingerprints already in corrected
                corrected_fps = {r.fingerprint for r in corrected}
                top_all = [r for r in top_all if r.fingerprint not in corrected_fps][
                    :remaining
                ]

            combined = list(corrected) + top_all
            if not combined:
                return ""

            lines = [
                "### Learned Lessons from Past Mistakes",
                "The following mistakes have been observed in previous sessions. "
                "Apply these lessons to AVOID repeating them:",
                "",
            ]
            for record in combined:
                lines.append(format_lesson(record))

            return "\n".join(lines)
        except Exception:
            logger.debug("Failed to get prompt lessons", exc_info=True)
            return ""

    async def get_mistake_summary(self) -> dict[str, Any]:
        """Get a summary of the mistake database for diagnostics.

        Returns:
            Dict with total_mistakes, top_tools, and correction_rate.
        """
        try:
            total = await self.store.count_mistakes()
            top = await self.store.get_top_mistakes(limit=5)
            corrected = await self.store.get_corrected_mistakes(limit=100)

            top_tools: dict[str, int] = {}
            for record in top:
                top_tools[record.tool_name] = record.occurrence_count

            return {
                "total_mistakes": total,
                "top_tools": top_tools,
                "corrected_count": len(corrected),
                "correction_rate": len(corrected) / total if total > 0 else 0.0,
            }
        except Exception:
            logger.debug("Failed to get mistake summary", exc_info=True)
            return {
                "total_mistakes": 0,
                "top_tools": {},
                "corrected_count": 0,
                "correction_rate": 0.0,
            }


# ── Singleton Factory ────────────────────────────────────────────────

_advisor: MistakeAdvisor | None = None


def get_mistake_advisor() -> MistakeAdvisor:
    """Get or create the global MistakeAdvisor singleton.

    Returns:
        The MistakeAdvisor instance.
    """
    global _advisor
    if _advisor is None:
        _advisor = MistakeAdvisor()
    return _advisor
