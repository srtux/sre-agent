"""Tests for the MistakeMemoryStore — MemoryManager-backed mistake storage."""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.memory.mistake_store import (
    MistakeMemoryStore,
    _classify_mistake,
    _compute_fingerprint,
    _format_mistake_for_memory,
    _sanitize_args,
)
from sre_agent.schema import MistakeCategory, MistakeRecord

# ── Unit Tests: Pure Functions ─────────────────────────────────────────


class TestClassifyMistake:
    """Tests for automatic mistake classification."""

    def test_classify_invalid_filter(self) -> None:
        assert (
            _classify_mistake("Invalid filter expression: bad syntax")
            == MistakeCategory.INVALID_FILTER
        )

    def test_classify_filter_must(self) -> None:
        assert (
            _classify_mistake("filter must contain resource type")
            == MistakeCategory.INVALID_FILTER
        )

    def test_classify_could_not_parse_filter(self) -> None:
        assert (
            _classify_mistake("could not parse filter: missing quotes")
            == MistakeCategory.INVALID_FILTER
        )

    def test_classify_unknown_metric(self) -> None:
        assert (
            _classify_mistake("unknown metric: custom.googleapis.com/foo")
            == MistakeCategory.INVALID_METRIC
        )

    def test_classify_metric_type(self) -> None:
        assert (
            _classify_mistake("metric.type 'foo' is not recognized")
            == MistakeCategory.INVALID_METRIC
        )

    def test_classify_wrong_resource_type(self) -> None:
        assert (
            _classify_mistake("resource.type 'gke_container' is not valid")
            == MistakeCategory.WRONG_RESOURCE_TYPE
        )

    def test_classify_resource_labels(self) -> None:
        assert (
            _classify_mistake("resource.labels.container_name is required")
            == MistakeCategory.WRONG_RESOURCE_TYPE
        )

    def test_classify_syntax_error(self) -> None:
        assert (
            _classify_mistake("syntax error in PromQL expression")
            == MistakeCategory.SYNTAX_ERROR
        )

    def test_classify_parse_error(self) -> None:
        assert (
            _classify_mistake("parse error at position 15")
            == MistakeCategory.SYNTAX_ERROR
        )

    def test_classify_malformed(self) -> None:
        assert (
            _classify_mistake("malformed query string") == MistakeCategory.SYNTAX_ERROR
        )

    def test_classify_unsupported(self) -> None:
        assert (
            _classify_mistake("unsupported aggregation type")
            == MistakeCategory.UNSUPPORTED_OPERATION
        )

    def test_classify_not_supported(self) -> None:
        assert (
            _classify_mistake("this operation is not supported")
            == MistakeCategory.UNSUPPORTED_OPERATION
        )

    def test_classify_invalid_argument(self) -> None:
        assert (
            _classify_mistake("INVALID_ARGUMENT: unknown field name")
            == MistakeCategory.INVALID_ARGUMENT
        )

    def test_classify_400_error(self) -> None:
        assert _classify_mistake("400 Bad Request") == MistakeCategory.INVALID_ARGUMENT

    def test_classify_unrecognized_field(self) -> None:
        assert (
            _classify_mistake("unrecognized field 'foo'")
            == MistakeCategory.INVALID_ARGUMENT
        )

    def test_classify_not_a_valid(self) -> None:
        assert (
            _classify_mistake("'xyz' is not a valid resource type")
            == MistakeCategory.INVALID_ARGUMENT
        )

    def test_classify_other_fallback(self) -> None:
        assert (
            _classify_mistake("something completely different happened")
            == MistakeCategory.OTHER
        )

    def test_classify_empty_string(self) -> None:
        assert _classify_mistake("") == MistakeCategory.OTHER


class TestComputeFingerprint:
    """Tests for fingerprint computation."""

    def test_deterministic(self) -> None:
        fp1 = _compute_fingerprint(
            "tool_a", MistakeCategory.SYNTAX_ERROR, "parse error"
        )
        fp2 = _compute_fingerprint(
            "tool_a", MistakeCategory.SYNTAX_ERROR, "parse error"
        )
        assert fp1 == fp2

    def test_different_tools_different_fingerprint(self) -> None:
        fp1 = _compute_fingerprint("tool_a", MistakeCategory.SYNTAX_ERROR, "error")
        fp2 = _compute_fingerprint("tool_b", MistakeCategory.SYNTAX_ERROR, "error")
        assert fp1 != fp2

    def test_different_categories_different_fingerprint(self) -> None:
        fp1 = _compute_fingerprint("tool_a", MistakeCategory.SYNTAX_ERROR, "error")
        fp2 = _compute_fingerprint("tool_a", MistakeCategory.INVALID_FILTER, "error")
        assert fp1 != fp2

    def test_whitespace_normalised(self) -> None:
        fp1 = _compute_fingerprint("tool_a", MistakeCategory.OTHER, "parse  error")
        fp2 = _compute_fingerprint("tool_a", MistakeCategory.OTHER, "parse error")
        assert fp1 == fp2

    def test_case_insensitive(self) -> None:
        fp1 = _compute_fingerprint("tool_a", MistakeCategory.OTHER, "Parse Error")
        fp2 = _compute_fingerprint("tool_a", MistakeCategory.OTHER, "parse error")
        assert fp1 == fp2


class TestSanitizeArgs:
    """Tests for argument sanitization."""

    def test_removes_sensitive_keys(self) -> None:
        result = _sanitize_args(
            {
                "query": "SELECT 1",
                "access_token": "secret",
                "credentials": "private",
                "token": "tok123",
                "password": "pass",
                "secret": "shh",
            }
        )
        assert "query" in result
        assert "access_token" not in result
        assert "credentials" not in result
        assert "token" not in result
        assert "password" not in result
        assert "secret" not in result

    def test_truncates_long_values(self) -> None:
        result = _sanitize_args({"filter": "x" * 500})
        assert len(result["filter"]) <= 203  # 200 + "..."
        assert result["filter"].endswith("...")

    def test_preserves_short_values(self) -> None:
        result = _sanitize_args({"project_id": "my-proj", "limit": 10})
        assert result == {"project_id": "my-proj", "limit": 10}


class TestFormatMistakeForMemory:
    """Tests for Memory Bank formatting."""

    def test_formats_basic_mistake(self) -> None:
        record = MistakeRecord(
            tool_name="list_log_entries",
            category=MistakeCategory.INVALID_FILTER,
            error_message="Invalid filter",
            failed_args={"filter": "bad"},
            correction=None,
            corrected_args=None,
            occurrence_count=1,
            first_seen="2026-01-01T00:00:00Z",
            last_seen="2026-01-01T00:00:00Z",
            fingerprint="abc",
        )
        text = _format_mistake_for_memory(record)
        assert "[MISTAKE] Tool: list_log_entries" in text
        assert "Category: invalid_filter" in text
        assert "Error: Invalid filter" in text

    def test_formats_corrected_mistake(self) -> None:
        record = MistakeRecord(
            tool_name="query_promql",
            category=MistakeCategory.SYNTAX_ERROR,
            error_message="syntax error",
            failed_args={"q": "bad("},
            correction="Close the parenthesis",
            corrected_args={"q": "bad()"},
            occurrence_count=2,
            first_seen="2026-01-01T00:00:00Z",
            last_seen="2026-01-01T00:00:00Z",
            fingerprint="def",
        )
        text = _format_mistake_for_memory(record)
        assert "Correction: Close the parenthesis" in text
        assert "Corrected Args:" in text


# ── Integration Tests: Store Operations (MemoryManager-backed) ────────


@pytest.fixture
def store() -> MistakeMemoryStore:
    """Create a MistakeMemoryStore with mocked MemoryManager."""
    return MistakeMemoryStore()


class TestRecordMistake:
    """Tests for recording mistakes."""

    @pytest.mark.asyncio
    async def test_record_new_mistake(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager") as mock_factory:
            mock_manager = AsyncMock()
            mock_factory.return_value = mock_manager

            record = await store.record_mistake(
                tool_name="list_log_entries",
                error_message="Invalid filter expression: missing quotes around value",
                failed_args={"filter": "container_name=app"},
                session_id="sess-1",
                user_id="user@example.com",
            )
            assert record.tool_name == "list_log_entries"
            assert record.category == MistakeCategory.INVALID_FILTER
            assert record.occurrence_count == 1
            assert record.correction is None
            assert record.fingerprint

            # Verify persistence to Memory Bank
            mock_manager.add_finding.assert_called_once()
            call_kwargs = mock_manager.add_finding.call_args[1]
            assert call_kwargs["session_id"] == "sess-1"
            assert call_kwargs["user_id"] == "user@example.com"
            assert "[MISTAKE]" in call_kwargs["description"]

    @pytest.mark.asyncio
    async def test_deduplication_increments_count(
        self, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager") as mock_factory:
            mock_manager = AsyncMock()
            mock_factory.return_value = mock_manager

            await store.record_mistake(
                tool_name="query_promql",
                error_message="syntax error in expression",
                failed_args={"query": "bad(query"},
            )
            record2 = await store.record_mistake(
                tool_name="query_promql",
                error_message="syntax error in expression",
                failed_args={"query": "bad(query"},
            )
            assert record2.occurrence_count == 2
            # Only first occurrence persists to Memory Bank
            assert mock_manager.add_finding.call_count == 1

    @pytest.mark.asyncio
    async def test_explicit_category_override(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            record = await store.record_mistake(
                tool_name="some_tool",
                error_message="generic error",
                failed_args={},
                category=MistakeCategory.WRONG_RESOURCE_TYPE,
            )
            assert record.category == MistakeCategory.WRONG_RESOURCE_TYPE

    @pytest.mark.asyncio
    async def test_sensitive_args_stripped(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            record = await store.record_mistake(
                tool_name="tool_a",
                error_message="invalid argument: bad token",
                failed_args={"access_token": "secret", "query": "test"},
            )
            assert "secret" not in str(record.failed_args)
            assert record.failed_args.get("query") == "test"

    @pytest.mark.asyncio
    async def test_memory_bank_failure_does_not_break(
        self, store: MistakeMemoryStore
    ) -> None:
        """Even if Memory Bank persistence fails, the cache should work."""
        with patch(
            "sre_agent.memory.factory.get_memory_manager",
            side_effect=RuntimeError("Memory Bank unavailable"),
        ):
            record = await store.record_mistake(
                tool_name="tool_a",
                error_message="invalid filter expr",
                failed_args={},
            )
            assert record.occurrence_count == 1
            assert await store.count_mistakes() == 1


class TestRecordCorrection:
    """Tests for recording self-corrections."""

    @pytest.mark.asyncio
    async def test_record_correction_for_existing_mistake(
        self, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager") as mock_factory:
            mock_manager = AsyncMock()
            mock_factory.return_value = mock_manager

            await store.record_mistake(
                tool_name="list_log_entries",
                error_message="Invalid filter: missing prefix",
                failed_args={"filter": 'container_name="app"'},
            )
            updated = await store.record_correction(
                tool_name="list_log_entries",
                error_message="Invalid filter: missing prefix",
                correction="Use resource.labels.container_name instead",
                corrected_args={"filter": 'resource.labels.container_name="app"'},
                session_id="sess-1",
                user_id="user@example.com",
            )
            assert updated is True

            # Verify the correction persisted to cache
            records = await store.get_mistakes_for_tool("list_log_entries")
            assert len(records) == 1
            assert records[0].correction is not None
            assert "resource.labels" in records[0].correction

            # Verify correction persisted to Memory Bank
            assert mock_manager.add_finding.call_count == 2  # mistake + correction
            correction_call = mock_manager.add_finding.call_args[1]
            assert "[CORRECTION]" in correction_call["description"]

    @pytest.mark.asyncio
    async def test_correction_for_nonexistent_mistake_returns_false(
        self, store: MistakeMemoryStore
    ) -> None:
        updated = await store.record_correction(
            tool_name="ghost_tool",
            error_message="never happened",
            correction="doesn't matter",
            corrected_args={},
        )
        assert updated is False


class TestQueryMistakes:
    """Tests for querying mistakes from the session cache."""

    @pytest.mark.asyncio
    async def test_get_mistakes_for_tool(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter expr", {"f": "1"})
            await store.record_mistake("tool_a", "syntax error in query", {"q": "2"})
            await store.record_mistake("tool_b", "invalid filter expr", {"f": "3"})

        results = await store.get_mistakes_for_tool("tool_a")
        assert len(results) == 2
        assert all(r.tool_name == "tool_a" for r in results)

    @pytest.mark.asyncio
    async def test_get_top_mistakes_ordered_by_frequency(
        self, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter expr", {})
            await store.record_mistake("tool_a", "invalid filter expr", {})  # count=2
            await store.record_mistake("tool_b", "syntax error", {})  # count=1

        results = await store.get_top_mistakes(limit=10)
        assert len(results) == 2
        assert results[0].occurrence_count >= results[1].occurrence_count

    @pytest.mark.asyncio
    async def test_get_mistakes_by_category(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter expr", {})
            await store.record_mistake("tool_b", "unknown metric: foo", {})

        filter_mistakes = await store.get_mistakes_by_category(
            MistakeCategory.INVALID_FILTER
        )
        assert len(filter_mistakes) == 1
        assert filter_mistakes[0].category == MistakeCategory.INVALID_FILTER

    @pytest.mark.asyncio
    async def test_get_corrected_mistakes(self, store: MistakeMemoryStore) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter expr", {"f": "bad"})
            await store.record_correction(
                "tool_a", "invalid filter expr", "Use prefix", {"f": "good"}
            )
            await store.record_mistake("tool_b", "syntax error", {})  # no correction

        corrected = await store.get_corrected_mistakes()
        assert len(corrected) == 1
        assert corrected[0].tool_name == "tool_a"

    @pytest.mark.asyncio
    async def test_count_mistakes(self, store: MistakeMemoryStore) -> None:
        assert await store.count_mistakes() == 0
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter expr", {})
            await store.record_mistake("tool_b", "syntax error", {})
        assert await store.count_mistakes() == 2

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty_lists(
        self, store: MistakeMemoryStore
    ) -> None:
        assert await store.get_mistakes_for_tool("nonexistent") == []
        assert await store.get_top_mistakes() == []
        assert await store.get_corrected_mistakes() == []
        assert await store.count_mistakes() == 0


class TestLoadFromMemoryBank:
    """Tests for loading past mistakes from the Memory Bank."""

    @pytest.mark.asyncio
    async def test_loads_mistakes_from_memory_bank(
        self, store: MistakeMemoryStore
    ) -> None:
        """Test that past mistakes are loaded from the Memory Bank."""
        from sre_agent.schema import Confidence, MemoryItem

        mock_finding = MemoryItem(
            source_tool="list_log_entries",
            confidence=Confidence.HIGH,
            timestamp="2026-01-15T10:00:00Z",
            description=(
                "[MISTAKE] Tool: list_log_entries\n"
                "Category: invalid_filter\n"
                "Error: Invalid filter expression\n"
                'Args: {"filter": "bad"}'
            ),
        )

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_factory:
            mock_manager = AsyncMock()
            mock_manager.get_relevant_findings.return_value = [mock_finding]
            mock_factory.return_value = mock_manager

            loaded = await store.load_from_memory_bank(
                session_id="sess-1", user_id="user@example.com"
            )
            assert loaded == 1
            assert await store.count_mistakes() == 1

            records = await store.get_mistakes_for_tool("list_log_entries")
            assert len(records) == 1
            assert records[0].category == MistakeCategory.INVALID_FILTER

    @pytest.mark.asyncio
    async def test_skips_non_mistake_findings(self, store: MistakeMemoryStore) -> None:
        """Regular findings should not be loaded as mistakes."""
        from sre_agent.schema import Confidence, MemoryItem

        mock_finding = MemoryItem(
            source_tool="analyze_critical_path",
            confidence=Confidence.HIGH,
            timestamp="2026-01-15T10:00:00Z",
            description="Found bottleneck in payment-service (p99 = 2.3s)",
        )

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_factory:
            mock_manager = AsyncMock()
            mock_manager.get_relevant_findings.return_value = [mock_finding]
            mock_factory.return_value = mock_manager

            loaded = await store.load_from_memory_bank()
            assert loaded == 0

    @pytest.mark.asyncio
    async def test_memory_bank_failure_returns_zero(
        self, store: MistakeMemoryStore
    ) -> None:
        """Memory Bank failures should not crash, just return 0."""
        with patch(
            "sre_agent.memory.factory.get_memory_manager",
            side_effect=RuntimeError("Connection refused"),
        ):
            loaded = await store.load_from_memory_bank()
            assert loaded == 0
