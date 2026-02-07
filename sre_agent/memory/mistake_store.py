"""Persistent store for structured mistake records.

This module provides a SQLite-backed store that captures, deduplicates, and
retrieves mistake records. It is the foundation of the self-improving loop:
mistakes are stored once, counted on recurrence, and enriched with corrections
when the agent self-corrects.

Key Features:
- Fingerprint-based deduplication (same mistake increments count, not duplicates)
- Correction tracking (failed_args -> corrected_args mapping)
- Retrieval by tool name, category, or top-N most frequent
- Thread-safe SQLite operations
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from sre_agent.schema import MistakeCategory, MistakeRecord

logger = logging.getLogger(__name__)

# Maximum number of lessons injected into the prompt context.
MAX_PROMPT_LESSONS = 10

# Maximum number of advice entries returned for a single tool.
MAX_TOOL_ADVICE = 5


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


class MistakeMemoryStore:
    """SQLite-backed persistent store for mistake records.

    Provides CRUD operations with fingerprint-based deduplication,
    occurrence counting, and correction tracking.
    """

    def __init__(self, db_path: str = ".sre_agent_mistakes.db") -> None:
        """Initialize the store and create tables if needed.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the mistakes table and indices."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mistakes (
                        fingerprint TEXT PRIMARY KEY,
                        tool_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        failed_args TEXT NOT NULL DEFAULT '{}',
                        correction TEXT,
                        corrected_args TEXT,
                        occurrence_count INTEGER NOT NULL DEFAULT 1,
                        first_seen TEXT NOT NULL,
                        last_seen TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_mistakes_tool
                    ON mistakes(tool_name, occurrence_count DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_mistakes_category
                    ON mistakes(category, occurrence_count DESC)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_mistakes_frequency
                    ON mistakes(occurrence_count DESC, last_seen DESC)
                """)
                conn.commit()
            logger.info("Mistake Memory Store initialized at %s", self.db_path)
        except Exception:
            logger.exception("Failed to initialize Mistake Memory Store")
            raise

    # ── Write Operations ─────────────────────────────────────────────

    async def record_mistake(
        self,
        tool_name: str,
        error_message: str,
        failed_args: dict[str, Any],
        category: MistakeCategory | None = None,
    ) -> MistakeRecord:
        """Record a mistake, deduplicating by fingerprint.

        If a mistake with the same fingerprint already exists, increments
        its occurrence count and updates last_seen. Otherwise, inserts a
        new record.

        Args:
            tool_name: Tool that produced the error.
            error_message: The error message received.
            failed_args: The arguments that caused the failure.
            category: Optional override for category. Auto-classified if None.

        Returns:
            The stored MistakeRecord (new or updated).
        """
        resolved_category = category or _classify_mistake(error_message)
        safe_args = _sanitize_args(failed_args)
        fingerprint = _compute_fingerprint(tool_name, resolved_category, error_message)
        now = datetime.now(timezone.utc).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if record already exists
                row = conn.execute(
                    "SELECT occurrence_count, first_seen, correction, corrected_args "
                    "FROM mistakes WHERE fingerprint = ?",
                    (fingerprint,),
                ).fetchone()

                if row:
                    new_count = row[0] + 1
                    first_seen = row[1]
                    correction = row[2]
                    corrected_args_json = row[3]
                    conn.execute(
                        "UPDATE mistakes SET occurrence_count = ?, last_seen = ?, "
                        "failed_args = ? WHERE fingerprint = ?",
                        (
                            new_count,
                            now,
                            json.dumps(safe_args, default=str),
                            fingerprint,
                        ),
                    )
                    conn.commit()
                    logger.info(
                        "Mistake reinforced: %s/%s (count=%d)",
                        tool_name,
                        resolved_category.value,
                        new_count,
                    )
                    return MistakeRecord(
                        tool_name=tool_name,
                        category=resolved_category,
                        error_message=error_message,
                        failed_args=safe_args,
                        correction=correction,
                        corrected_args=json.loads(corrected_args_json)
                        if corrected_args_json
                        else None,
                        occurrence_count=new_count,
                        first_seen=first_seen,
                        last_seen=now,
                        fingerprint=fingerprint,
                    )
                else:
                    conn.execute(
                        "INSERT INTO mistakes "
                        "(fingerprint, tool_name, category, error_message, "
                        "failed_args, occurrence_count, first_seen, last_seen) "
                        "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                        (
                            fingerprint,
                            tool_name,
                            resolved_category.value,
                            error_message,
                            json.dumps(safe_args, default=str),
                            now,
                            now,
                        ),
                    )
                    conn.commit()
                    logger.info(
                        "New mistake recorded: %s/%s",
                        tool_name,
                        resolved_category.value,
                    )
                    return MistakeRecord(
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
        except Exception:
            logger.exception("Failed to record mistake for %s", tool_name)
            # Return a transient record so callers don't break
            return MistakeRecord(
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

    async def record_correction(
        self,
        tool_name: str,
        error_message: str,
        correction: str,
        corrected_args: dict[str, Any],
        category: MistakeCategory | None = None,
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

        Returns:
            True if a matching mistake was found and updated.
        """
        resolved_category = category or _classify_mistake(error_message)
        fingerprint = _compute_fingerprint(tool_name, resolved_category, error_message)
        safe_corrected = _sanitize_args(corrected_args)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE mistakes SET correction = ?, corrected_args = ? "
                    "WHERE fingerprint = ?",
                    (
                        correction,
                        json.dumps(safe_corrected, default=str),
                        fingerprint,
                    ),
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(
                        "Correction recorded for %s/%s: %s",
                        tool_name,
                        resolved_category.value,
                        correction[:80],
                    )
                    return True
                return False
        except Exception:
            logger.exception("Failed to record correction for %s", tool_name)
            return False

    # ── Read Operations ──────────────────────────────────────────────

    async def get_mistakes_for_tool(
        self,
        tool_name: str,
        limit: int = MAX_TOOL_ADVICE,
    ) -> list[MistakeRecord]:
        """Retrieve past mistakes for a specific tool.

        Returns the most frequent mistakes first, enabling the advisor
        to warn the agent about the most common pitfalls.

        Args:
            tool_name: Tool to look up.
            limit: Maximum number of records.

        Returns:
            List of MistakeRecords ordered by occurrence count (descending).
        """
        return self._query_mistakes(
            "SELECT * FROM mistakes WHERE tool_name = ? "
            "ORDER BY occurrence_count DESC LIMIT ?",
            (tool_name, limit),
        )

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
        return self._query_mistakes(
            "SELECT * FROM mistakes ORDER BY occurrence_count DESC, last_seen DESC LIMIT ?",
            (limit,),
        )

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
        return self._query_mistakes(
            "SELECT * FROM mistakes WHERE category = ? "
            "ORDER BY occurrence_count DESC LIMIT ?",
            (category.value, limit),
        )

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
        return self._query_mistakes(
            "SELECT * FROM mistakes WHERE correction IS NOT NULL "
            "ORDER BY occurrence_count DESC LIMIT ?",
            (limit,),
        )

    async def count_mistakes(self) -> int:
        """Return the total number of unique mistakes stored.

        Returns:
            Count of distinct mistake fingerprints.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()
                return row[0] if row else 0
        except Exception:
            logger.exception("Failed to count mistakes")
            return 0

    # ── Internal Helpers ─────────────────────────────────────────────

    def _query_mistakes(
        self,
        sql: str,
        params: tuple[Any, ...],
    ) -> list[MistakeRecord]:
        """Execute a query and return MistakeRecords.

        Args:
            sql: SQL query string.
            params: Query parameters.

        Returns:
            List of MistakeRecords.
        """
        results: list[MistakeRecord] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                for row in conn.execute(sql, params):
                    try:
                        results.append(
                            MistakeRecord(
                                fingerprint=row["fingerprint"],
                                tool_name=row["tool_name"],
                                category=MistakeCategory(row["category"]),
                                error_message=row["error_message"],
                                failed_args=json.loads(row["failed_args"]),
                                correction=row["correction"],
                                corrected_args=json.loads(row["corrected_args"])
                                if row["corrected_args"]
                                else None,
                                occurrence_count=row["occurrence_count"],
                                first_seen=row["first_seen"],
                                last_seen=row["last_seen"],
                            )
                        )
                    except Exception:
                        logger.debug("Failed to deserialize mistake row", exc_info=True)
        except Exception:
            logger.exception("Failed to query mistakes")
        return results


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
