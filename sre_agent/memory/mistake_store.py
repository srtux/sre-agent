"""Persistent store for structured mistake records.

This module provides a store that captures, deduplicates, and retrieves
mistake records. It is the foundation of the self-improving loop: mistakes
are stored once, counted on recurrence, and enriched with corrections
when the agent self-corrects.

Architecture:
- **Persistence**: Delegated to the existing ``MemoryManager`` which uses
  Vertex AI Memory Bank in production and ``LocalMemoryService`` (SQLite)
  in local/dev mode. This ensures a single storage backend, proper user
  isolation, and semantic search via Vertex AI Vector Search.
- **Session cache**: An in-memory dict (keyed by fingerprint) provides
  fast deduplication and occurrence counting within the current process
  lifetime. The cache is populated from writes and is not authoritative
  across restarts — the Memory Bank is the source of truth.

Key Features:
- Fingerprint-based deduplication (same mistake increments count, not duplicates)
- Correction tracking (failed_args -> corrected_args mapping)
- Retrieval by tool name, category, or top-N most frequent
- All persistence flows through MemoryManager (Vertex AI / LocalMemoryService)
- User isolation via MemoryManager's user_id enforcement
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sre_agent.schema import Confidence, MistakeCategory, MistakeRecord

logger = logging.getLogger(__name__)

# Maximum number of lessons injected into the prompt context.
MAX_PROMPT_LESSONS = 10

# Maximum number of advice entries returned for a single tool.
MAX_TOOL_ADVICE = 5

# Prefix used to tag mistake entries in the Memory Bank so they can be
# distinguished from regular findings during retrieval.
_MISTAKE_PREFIX = "[MISTAKE]"

# Prefix used for correction entries.
_CORRECTION_PREFIX = "[CORRECTION]"


def _compute_fingerprint(
    tool_name: str,
    category: MistakeCategory,
    error_message: str,
) -> str:
    """Compute a stable fingerprint for deduplication.

    The fingerprint is a SHA-256 hash of the tool name, category, and a
    normalised form of the error message (lowercased, whitespace-collapsed).
    This ensures that cosmetically different but semantically identical errors
    are treated as the same mistake.

    Args:
        tool_name: Name of the tool.
        category: Classified mistake category.
        error_message: The raw error message.

    Returns:
        A hex-encoded SHA-256 fingerprint.
    """
    # Normalise: lowercase, collapse whitespace, strip
    normalised_error = " ".join(error_message.lower().split())
    raw = f"{tool_name}|{category.value}|{normalised_error}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _classify_mistake(error_message: str) -> MistakeCategory:
    """Classify an error message into a MistakeCategory.

    Uses pattern matching against known error signatures to assign the
    most specific category. Falls back to OTHER for unrecognised patterns.

    Args:
        error_message: The error message to classify.

    Returns:
        The best-matching MistakeCategory.
    """
    lower = error_message.lower()

    # Order matters — more specific patterns first.
    if any(
        kw in lower
        for kw in ("resource.type", "resource.labels", "wrong_resource_type")
    ):
        return MistakeCategory.WRONG_RESOURCE_TYPE

    if any(
        kw in lower
        for kw in ("invalid filter", "filter must", "could not parse filter")
    ):
        return MistakeCategory.INVALID_FILTER

    if any(kw in lower for kw in ("unknown metric", "metric.type", "invalid metric")):
        return MistakeCategory.INVALID_METRIC

    if any(kw in lower for kw in ("syntax error", "parse error", "malformed")):
        return MistakeCategory.SYNTAX_ERROR

    if any(
        kw in lower for kw in ("unsupported", "not supported", "unsupported_operation")
    ):
        return MistakeCategory.UNSUPPORTED_OPERATION

    if any(
        kw in lower
        for kw in (
            "invalid argument",
            "invalid_argument",
            "unrecognized field",
            "not a valid",
            "400",
        )
    ):
        return MistakeCategory.INVALID_ARGUMENT

    return MistakeCategory.OTHER


def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive keys and truncate long values.

    Args:
        args: Raw tool arguments.

    Returns:
        A sanitized copy safe for persistence.
    """
    sensitive_keys = {"access_token", "credentials", "token", "password", "secret"}
    safe: dict[str, Any] = {}
    for key, value in args.items():
        if key in sensitive_keys:
            continue
        if isinstance(value, str) and len(value) > 200:
            safe[key] = value[:200] + "..."
        else:
            safe[key] = value
    return safe


def _format_mistake_for_memory(record: MistakeRecord) -> str:
    """Format a MistakeRecord as text for Memory Bank storage.

    Uses a structured prefix so mistakes can be recognised when retrieved
    via semantic search.

    Args:
        record: The mistake record.

    Returns:
        Formatted text for ``MemoryManager.add_finding()``.
    """
    parts = [
        f"{_MISTAKE_PREFIX} Tool: {record.tool_name}",
        f"Category: {record.category.value}",
        f"Error: {record.error_message}",
        f"Args: {json.dumps(record.failed_args, default=str)}",
    ]
    if record.correction:
        parts.append(f"Correction: {record.correction}")
    if record.corrected_args:
        parts.append(
            f"Corrected Args: {json.dumps(record.corrected_args, default=str)}"
        )
    return "\n".join(parts)


class MistakeMemoryStore:
    """Mistake store backed by the existing MemoryManager pipeline.

    Uses an in-memory session cache for fast deduplication and occurrence
    counting, and delegates persistence to ``MemoryManager`` which routes
    to Vertex AI Memory Bank (production) or LocalMemoryService (local).

    All write operations require ``session_id`` and ``user_id`` so that
    the Memory Bank enforces strict user isolation.
    """

    def __init__(self) -> None:
        """Initialize the store with an empty session cache."""
        # fingerprint -> MistakeRecord (mutable via dict replacement)
        self._cache: dict[str, MistakeRecord] = {}

    # ── Write Operations ─────────────────────────────────────────────

    async def record_mistake(
        self,
        tool_name: str,
        error_message: str,
        failed_args: dict[str, Any],
        category: MistakeCategory | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> MistakeRecord:
        """Record a mistake, deduplicating by fingerprint.

        If a mistake with the same fingerprint already exists in the
        session cache, increments its occurrence count. On first
        occurrence, also persists to the Memory Bank via MemoryManager.

        Args:
            tool_name: Tool that produced the error.
            error_message: The error message received.
            failed_args: The arguments that caused the failure.
            category: Optional override for category. Auto-classified if None.
            session_id: Current session ID (for Memory Bank persistence).
            user_id: Authenticated user ID (for isolation).

        Returns:
            The stored MistakeRecord (new or updated).
        """
        resolved_category = category or _classify_mistake(error_message)
        safe_args = _sanitize_args(failed_args)
        fingerprint = _compute_fingerprint(tool_name, resolved_category, error_message)
        now = datetime.now(timezone.utc).isoformat()

        existing = self._cache.get(fingerprint)
        if existing:
            # Increment occurrence — replace frozen record with new count
            updated = MistakeRecord(
                tool_name=existing.tool_name,
                category=existing.category,
                error_message=existing.error_message,
                failed_args=safe_args,
                correction=existing.correction,
                corrected_args=existing.corrected_args,
                occurrence_count=existing.occurrence_count + 1,
                first_seen=existing.first_seen,
                last_seen=now,
                fingerprint=fingerprint,
            )
            self._cache[fingerprint] = updated
            logger.info(
                "Mistake reinforced: %s/%s (count=%d)",
                tool_name,
                resolved_category.value,
                updated.occurrence_count,
            )
            return updated

        # New mistake — create record and persist to Memory Bank
        record = MistakeRecord(
            tool_name=tool_name,
            category=resolved_category,
            error_message=error_message,
            failed_args=safe_args,
            correction=None,
            corrected_args=None,
            occurrence_count=1,
            first_seen=now,
            last_seen=now,
            fingerprint=fingerprint,
        )
        self._cache[fingerprint] = record

        # Persist through MemoryManager
        try:
            from sre_agent.memory.factory import get_memory_manager

            manager = get_memory_manager()
            await manager.add_finding(
                description=_format_mistake_for_memory(record),
                source_tool=tool_name,
                confidence=Confidence.HIGH,
                structured_data={
                    "type": "mistake",
                    "category": resolved_category.value,
                    "fingerprint": fingerprint,
                    "failed_args": safe_args,
                },
                session_id=session_id,
                user_id=user_id,
            )
        except Exception:
            logger.debug("Failed to persist mistake to Memory Bank", exc_info=True)

        logger.info("New mistake recorded: %s/%s", tool_name, resolved_category.value)
        return record

    async def record_correction(
        self,
        tool_name: str,
        error_message: str,
        correction: str,
        corrected_args: dict[str, Any],
        category: MistakeCategory | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Record a correction for a previously seen mistake.

        This is called when the agent self-corrects: it previously failed
        with a given error and then succeeded with different arguments.

        Args:
            tool_name: Tool that was corrected.
            error_message: The original error message.
            correction: Human-readable description of the correction.
            corrected_args: The arguments that worked.
            category: Optional override for category.
            session_id: Current session ID (for Memory Bank persistence).
            user_id: Authenticated user ID (for isolation).

        Returns:
            True if a matching mistake was found and updated.
        """
        resolved_category = category or _classify_mistake(error_message)
        fingerprint = _compute_fingerprint(tool_name, resolved_category, error_message)
        safe_corrected = _sanitize_args(corrected_args)

        existing = self._cache.get(fingerprint)
        if not existing:
            return False

        # Update cache with correction
        updated = MistakeRecord(
            tool_name=existing.tool_name,
            category=existing.category,
            error_message=existing.error_message,
            failed_args=existing.failed_args,
            correction=correction,
            corrected_args=safe_corrected,
            occurrence_count=existing.occurrence_count,
            first_seen=existing.first_seen,
            last_seen=existing.last_seen,
            fingerprint=fingerprint,
        )
        self._cache[fingerprint] = updated

        # Persist the correction to Memory Bank
        try:
            from sre_agent.memory.factory import get_memory_manager

            manager = get_memory_manager()
            await manager.add_finding(
                description=(
                    f"{_CORRECTION_PREFIX} Tool: {tool_name}\n"
                    f"Original error: {error_message}\n"
                    f"Correction: {correction}\n"
                    f"Corrected args: {json.dumps(safe_corrected, default=str)}"
                ),
                source_tool=tool_name,
                confidence=Confidence.HIGH,
                structured_data={
                    "type": "correction",
                    "category": resolved_category.value,
                    "fingerprint": fingerprint,
                    "corrected_args": safe_corrected,
                },
                session_id=session_id,
                user_id=user_id,
            )
        except Exception:
            logger.debug("Failed to persist correction to Memory Bank", exc_info=True)

        logger.info(
            "Correction recorded for %s/%s: %s",
            tool_name,
            resolved_category.value,
            correction[:80],
        )
        return True

    # ── Read Operations ──────────────────────────────────────────────

    async def get_mistakes_for_tool(
        self,
        tool_name: str,
        limit: int = MAX_TOOL_ADVICE,
    ) -> list[MistakeRecord]:
        """Retrieve past mistakes for a specific tool from the session cache.

        Returns the most frequent mistakes first, enabling the advisor
        to warn the agent about the most common pitfalls.

        Args:
            tool_name: Tool to look up.
            limit: Maximum number of records.

        Returns:
            List of MistakeRecords ordered by occurrence count (descending).
        """
        matches = [r for r in self._cache.values() if r.tool_name == tool_name]
        matches.sort(key=lambda r: r.occurrence_count, reverse=True)
        return matches[:limit]

    async def get_top_mistakes(
        self,
        limit: int = MAX_PROMPT_LESSONS,
    ) -> list[MistakeRecord]:
        """Retrieve the most frequent mistakes across all tools.

        Used to inject top lessons into the agent prompt context.

        Args:
            limit: Maximum number of records.

        Returns:
            List of MistakeRecords ordered by occurrence count (descending).
        """
        all_records = list(self._cache.values())
        all_records.sort(key=lambda r: r.occurrence_count, reverse=True)
        return all_records[:limit]

    async def get_mistakes_by_category(
        self,
        category: MistakeCategory,
        limit: int = MAX_TOOL_ADVICE,
    ) -> list[MistakeRecord]:
        """Retrieve mistakes filtered by category.

        Args:
            category: The category to filter by.
            limit: Maximum number of records.

        Returns:
            List of MistakeRecords for the category.
        """
        matches = [r for r in self._cache.values() if r.category == category]
        matches.sort(key=lambda r: r.occurrence_count, reverse=True)
        return matches[:limit]

    async def get_corrected_mistakes(
        self,
        limit: int = MAX_PROMPT_LESSONS,
    ) -> list[MistakeRecord]:
        """Retrieve mistakes that have known corrections.

        These are the most valuable for the self-improving loop: they
        provide concrete "don't do X, do Y instead" guidance.

        Args:
            limit: Maximum number of records.

        Returns:
            List of MistakeRecords that have corrections attached.
        """
        corrected = [r for r in self._cache.values() if r.correction is not None]
        corrected.sort(key=lambda r: r.occurrence_count, reverse=True)
        return corrected[:limit]

    async def count_mistakes(self) -> int:
        """Return the total number of unique mistakes in the session cache.

        Returns:
            Count of distinct mistake fingerprints.
        """
        return len(self._cache)

    async def load_from_memory_bank(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Pre-populate the session cache from the Memory Bank.

        Searches the Memory Bank for previously stored mistakes and loads
        them into the in-memory cache. This is called at session start to
        bootstrap the self-improving loop with cross-session knowledge.

        Args:
            session_id: Session ID for scoping the search.
            user_id: User ID for isolation.

        Returns:
            Number of mistakes loaded from the Memory Bank.
        """
        loaded = 0
        try:
            from sre_agent.memory.factory import get_memory_manager

            manager = get_memory_manager()
            findings = await manager.get_relevant_findings(
                query="MISTAKE tool failure error syntax invalid",
                session_id=session_id,
                limit=MAX_PROMPT_LESSONS * 2,
                user_id=user_id,
            )
            for finding in findings:
                desc = finding.description
                if _MISTAKE_PREFIX not in desc and _CORRECTION_PREFIX not in desc:
                    continue
                record = self._parse_memory_finding(desc, finding)
                if record and record.fingerprint not in self._cache:
                    self._cache[record.fingerprint] = record
                    loaded += 1
            if loaded:
                logger.info("Loaded %d past mistakes from Memory Bank", loaded)
        except Exception:
            logger.debug("Failed to load mistakes from Memory Bank", exc_info=True)
        return loaded

    def _parse_memory_finding(
        self, description: str, finding: Any
    ) -> MistakeRecord | None:
        """Parse a Memory Bank finding back into a MistakeRecord.

        Args:
            description: The text content of the finding.
            finding: The MemoryItem from the Memory Bank.

        Returns:
            A MistakeRecord, or None if parsing fails.
        """
        try:
            lines = description.strip().split("\n")
            data: dict[str, str] = {}
            for line in lines:
                if ":" in line:
                    key, _, value = line.partition(":")
                    data[key.strip()] = value.strip()

            tool_name = data.get(f"{_MISTAKE_PREFIX} Tool") or data.get(
                f"{_CORRECTION_PREFIX} Tool", "unknown"
            )
            category_str = data.get("Category", "other")
            error_message = data.get("Error") or data.get("Original error", "unknown")
            correction = data.get("Correction")

            try:
                category = MistakeCategory(category_str)
            except ValueError:
                category = MistakeCategory.OTHER

            failed_args: dict[str, Any] = {}
            if "Args" in data:
                try:
                    failed_args = json.loads(data["Args"])
                except (json.JSONDecodeError, TypeError):
                    pass

            corrected_args: dict[str, Any] | None = None
            if "Corrected Args" in data:
                try:
                    corrected_args = json.loads(data["Corrected Args"])
                except (json.JSONDecodeError, TypeError):
                    pass

            fingerprint = _compute_fingerprint(tool_name, category, error_message)

            return MistakeRecord(
                tool_name=tool_name,
                category=category,
                error_message=error_message,
                failed_args=failed_args,
                correction=correction,
                corrected_args=corrected_args,
                occurrence_count=1,
                first_seen=finding.timestamp,
                last_seen=finding.timestamp,
                fingerprint=fingerprint,
            )
        except Exception:
            logger.debug("Failed to parse mistake from Memory Bank", exc_info=True)
            return None


# ── Singleton Factory ────────────────────────────────────────────────

_store: MistakeMemoryStore | None = None


def get_mistake_store() -> MistakeMemoryStore:
    """Get or create the global MistakeMemoryStore singleton.

    Returns:
        The MistakeMemoryStore instance.
    """
    global _store
    if _store is None:
        _store = MistakeMemoryStore()
    return _store
