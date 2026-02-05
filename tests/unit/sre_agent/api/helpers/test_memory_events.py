"""Tests for memory event helpers."""

import json

import pytest

from sre_agent.api.helpers.memory_events import (
    MemoryAction,
    MemoryCategory,
    MemoryEvent,
    MemoryEventBus,
    create_failure_learning_event,
    create_memory_search_event,
    create_pattern_applied_event,
    create_pattern_learned_event,
    create_success_finding_event,
    create_tool_tracking_event,
    get_memory_event_bus,
)


class TestMemoryEvent:
    """Tests for MemoryEvent dataclass."""

    def test_create_memory_event(self) -> None:
        """Test creating a memory event with all fields."""
        event = MemoryEvent(
            action=MemoryAction.STORED,
            category=MemoryCategory.SUCCESS,
            title="Test finding stored",
            description="A test finding was stored to memory",
            tool_name="analyze_critical_path",
            metadata={"finding_type": "bottleneck"},
        )

        assert event.action == MemoryAction.STORED
        assert event.category == MemoryCategory.SUCCESS
        assert event.title == "Test finding stored"
        assert event.tool_name == "analyze_critical_path"
        assert event.metadata == {"finding_type": "bottleneck"}
        assert event.timestamp  # Should have a timestamp

    def test_to_json(self) -> None:
        """Test JSON serialization of memory event."""
        event = MemoryEvent(
            action=MemoryAction.PATTERN_LEARNED,
            category=MemoryCategory.PATTERN,
            title="Learned pattern: high_latency",
            description="Root cause: connection_pool",
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["type"] == "memory"
        assert data["action"] == "pattern_learned"
        assert data["category"] == "pattern"
        assert data["title"] == "Learned pattern: high_latency"
        assert data["description"] == "Root cause: connection_pool"
        assert data["tool_name"] is None
        assert data["metadata"] == {}
        assert "timestamp" in data


class TestMemoryEventBus:
    """Tests for MemoryEventBus singleton."""

    def test_get_instance_returns_singleton(self) -> None:
        """Test that get_instance returns the same instance."""
        bus1 = MemoryEventBus.get_instance()
        bus2 = MemoryEventBus.get_instance()
        assert bus1 is bus2

    def test_enabled_default(self) -> None:
        """Test that bus is enabled by default."""
        bus = MemoryEventBus()
        assert bus.enabled is True

    def test_set_enabled(self) -> None:
        """Test setting enabled state."""
        bus = MemoryEventBus()
        bus.set_enabled(False)
        assert bus.enabled is False
        bus.set_enabled(True)
        assert bus.enabled is True

    @pytest.mark.asyncio
    async def test_emit_and_drain(self) -> None:
        """Test emitting and draining events."""
        bus = MemoryEventBus()

        event = MemoryEvent(
            action=MemoryAction.STORED,
            category=MemoryCategory.FAILURE,
            title="Test event",
            description="Test description",
        )

        await bus.emit("test-session", event)

        events = []
        async for evt in bus.drain_events("test-session"):
            events.append(evt)

        assert len(events) == 1
        assert events[0].title == "Test event"

    @pytest.mark.asyncio
    async def test_emit_disabled(self) -> None:
        """Test that emit does nothing when disabled."""
        bus = MemoryEventBus()
        bus.set_enabled(False)

        event = MemoryEvent(
            action=MemoryAction.STORED,
            category=MemoryCategory.SUCCESS,
            title="Should not be stored",
            description="Test",
        )

        await bus.emit("test-session-disabled", event)

        events = []
        async for evt in bus.drain_events("test-session-disabled"):
            events.append(evt)

        assert len(events) == 0
        bus.set_enabled(True)  # Reset for other tests

    @pytest.mark.asyncio
    async def test_emit_with_none_session_id(self) -> None:
        """Test emit with None session_id uses 'global'."""
        bus = MemoryEventBus()

        event = MemoryEvent(
            action=MemoryAction.SEARCHED,
            category=MemoryCategory.SEARCH,
            title="Search event",
            description="Test",
        )

        await bus.emit(None, event)

        events = []
        async for evt in bus.drain_events("global"):
            events.append(evt)

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_drain_empty_queue(self) -> None:
        """Test draining an empty queue returns nothing."""
        bus = MemoryEventBus()

        events = []
        async for evt in bus.drain_events("nonexistent-session"):
            events.append(evt)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_cleanup_session(self) -> None:
        """Test cleaning up a session queue."""
        bus = MemoryEventBus()

        event = MemoryEvent(
            action=MemoryAction.STORED,
            category=MemoryCategory.SUCCESS,
            title="Test",
            description="Test",
        )

        await bus.emit("cleanup-session", event)
        await bus.cleanup_session("cleanup-session")

        # Queue should be removed, draining should create a new empty queue
        events = []
        async for evt in bus.drain_events("cleanup-session"):
            events.append(evt)

        assert len(events) == 0


class TestEventCreationHelpers:
    """Tests for event creation helper functions."""

    def test_create_failure_learning_event(self) -> None:
        """Test creating a failure learning event."""
        event = create_failure_learning_event(
            tool_name="query_metrics",
            error_summary="invalid filter: resource.type must be specified",
            lesson="[TOOL FAILURE] Always specify resource.type in metric filters",
        )

        assert event.action == MemoryAction.STORED
        assert event.category == MemoryCategory.FAILURE
        assert event.tool_name == "query_metrics"
        assert "query_metrics failure" in event.title
        assert "invalid filter" in event.description
        assert "lesson_preview" in event.metadata

    def test_create_success_finding_event(self) -> None:
        """Test creating a success finding event."""
        event = create_success_finding_event(
            tool_name="analyze_critical_path",
            finding_type="Critical path bottleneck",
            finding_summary="Service checkout-service has 500ms latency on /pay endpoint",
        )

        assert event.action == MemoryAction.STORED
        assert event.category == MemoryCategory.SUCCESS
        assert event.tool_name == "analyze_critical_path"
        assert "Critical path bottleneck" in event.title
        assert "checkout-service" in event.description
        assert event.metadata["finding_type"] == "Critical path bottleneck"

    def test_create_pattern_learned_event(self) -> None:
        """Test creating a pattern learned event."""
        event = create_pattern_learned_event(
            symptom_type="high_latency_checkout",
            root_cause="connection_pool_exhaustion",
            tool_sequence=["query_metrics", "fetch_trace", "analyze_critical_path"],
        )

        assert event.action == MemoryAction.PATTERN_LEARNED
        assert event.category == MemoryCategory.PATTERN
        assert "high_latency_checkout" in event.title
        assert "connection_pool_exhaustion" in event.description
        assert event.metadata["symptom_type"] == "high_latency_checkout"
        assert event.metadata["tool_count"] == 3

    def test_create_pattern_applied_event(self) -> None:
        """Test creating a pattern applied event."""
        event = create_pattern_applied_event(
            symptom_type="high_latency",
            confidence=0.85,
            tool_sequence=["fetch_trace", "analyze_spans"],
        )

        assert event.action == MemoryAction.PATTERN_APPLIED
        assert event.category == MemoryCategory.PATTERN
        assert "high_latency" in event.title
        assert "85%" in event.description
        assert event.metadata["confidence"] == 0.85

    def test_create_memory_search_event(self) -> None:
        """Test creating a memory search event."""
        event = create_memory_search_event(
            query="connection pool exhaustion",
            result_count=3,
        )

        assert event.action == MemoryAction.SEARCHED
        assert event.category == MemoryCategory.SEARCH
        assert "3 result" in event.title
        assert "connection pool" in event.description
        assert event.metadata["result_count"] == 3

    def test_create_tool_tracking_event(self) -> None:
        """Test creating a tool tracking event."""
        event = create_tool_tracking_event(
            tool_name="fetch_trace",
            sequence_length=5,
        )

        assert event.action == MemoryAction.TOOL_TRACKED
        assert event.category == MemoryCategory.TRACKING
        assert "fetch_trace" in event.title
        assert "Tool #5" in event.description
        assert event.metadata["sequence_position"] == 5

    def test_truncates_long_descriptions(self) -> None:
        """Test that long descriptions are truncated."""
        long_summary = "x" * 300
        event = create_success_finding_event(
            tool_name="test",
            finding_type="Test",
            finding_summary=long_summary,
        )

        # Description should be truncated with ellipsis
        assert len(event.description) < 250  # Max 200 + "..."

    def test_truncates_long_lesson_preview(self) -> None:
        """Test that long lesson previews are truncated."""
        long_lesson = "y" * 300
        event = create_failure_learning_event(
            tool_name="test",
            error_summary="error",
            lesson=long_lesson,
        )

        # Lesson preview should be truncated
        assert len(event.metadata["lesson_preview"]) <= 200


class TestGetMemoryEventBus:
    """Tests for get_memory_event_bus function."""

    def test_returns_singleton(self) -> None:
        """Test that function returns singleton instance."""
        bus1 = get_memory_event_bus()
        bus2 = get_memory_event_bus()
        assert bus1 is bus2
        assert isinstance(bus1, MemoryEventBus)
