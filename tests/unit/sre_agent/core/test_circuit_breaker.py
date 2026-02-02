"""Tests for the Circuit Breaker pattern implementation.

Validates all circuit breaker states and transitions:
- CLOSED -> OPEN on failure threshold
- OPEN -> HALF_OPEN after recovery timeout
- HALF_OPEN -> CLOSED on success threshold
- HALF_OPEN -> OPEN on failure during recovery
"""

import time

import pytest

from sre_agent.core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the singleton between tests."""
    CircuitBreakerRegistry.reset()


class TestCircuitBreakerRegistry:
    """Tests for the CircuitBreakerRegistry singleton."""

    def test_singleton_pattern(self) -> None:
        """Registry should be a singleton."""
        reg1 = CircuitBreakerRegistry()
        reg2 = CircuitBreakerRegistry()
        assert reg1 is reg2

    def test_reset_creates_new_instance(self) -> None:
        """Reset should create a new singleton instance."""
        reg1 = CircuitBreakerRegistry()
        reg1.record_failure("test_tool")
        CircuitBreakerRegistry.reset()
        reg2 = CircuitBreakerRegistry()
        assert reg2.get_status("test_tool")["failure_count"] == 0


class TestCircuitBreakerClosedState:
    """Tests for CLOSED state behavior."""

    def test_allows_calls_when_closed(self) -> None:
        """Calls should pass through in CLOSED state."""
        registry = CircuitBreakerRegistry()
        assert registry.pre_call("my_tool") is True

    def test_stays_closed_on_success(self) -> None:
        """State should remain CLOSED on successful calls."""
        registry = CircuitBreakerRegistry()
        registry.record_success("my_tool")
        status = registry.get_status("my_tool")
        assert status["state"] == "closed"

    def test_counts_failures(self) -> None:
        """Failure count should increment."""
        registry = CircuitBreakerRegistry()
        registry.record_failure("my_tool")
        registry.record_failure("my_tool")
        status = registry.get_status("my_tool")
        assert status["failure_count"] == 2

    def test_success_decrements_failure_count(self) -> None:
        """Success should reduce failure count by 1."""
        registry = CircuitBreakerRegistry()
        registry.record_failure("my_tool")
        registry.record_failure("my_tool")
        registry.record_success("my_tool")
        status = registry.get_status("my_tool")
        assert status["failure_count"] == 1


class TestCircuitBreakerOpenTransition:
    """Tests for CLOSED -> OPEN transition."""

    def test_opens_on_failure_threshold(self) -> None:
        """Circuit should open after failure_threshold failures."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=3)
        registry.configure("my_tool", config)

        for _ in range(3):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        status = registry.get_status("my_tool")
        assert status["state"] == "open"

    def test_blocks_calls_when_open(self) -> None:
        """Calls should be blocked when circuit is OPEN."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60)
        registry.configure("my_tool", config)

        # Trip the circuit
        for _ in range(2):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            registry.pre_call("my_tool")

        assert exc_info.value.tool_name == "my_tool"
        assert exc_info.value.retry_after_seconds > 0

    def test_tracks_short_circuit_count(self) -> None:
        """Should count calls that were short-circuited."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60)
        registry.configure("my_tool", config)

        for _ in range(2):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        # Try blocked calls
        for _ in range(3):
            try:
                registry.pre_call("my_tool")
            except CircuitBreakerOpenError:
                pass

        status = registry.get_status("my_tool")
        assert status["total_short_circuits"] == 3


class TestCircuitBreakerHalfOpenTransition:
    """Tests for OPEN -> HALF_OPEN transition."""

    def test_transitions_to_half_open_after_timeout(self) -> None:
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=0.1)
        registry.configure("my_tool", config)

        for _ in range(2):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should allow the call now (half-open)
        assert registry.pre_call("my_tool") is True
        status = registry.get_status("my_tool")
        assert status["state"] == "half_open"


class TestCircuitBreakerRecovery:
    """Tests for HALF_OPEN recovery behavior."""

    def test_closes_on_success_threshold(self) -> None:
        """Circuit should close after success_threshold successes in half-open."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=0.1,
            success_threshold=2,
            half_open_max_calls=3,
        )
        registry.configure("my_tool", config)

        # Trip the circuit
        for _ in range(2):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        time.sleep(0.15)

        # First call transitions to half-open
        registry.pre_call("my_tool")
        registry.record_success("my_tool")
        registry.record_success("my_tool")

        status = registry.get_status("my_tool")
        assert status["state"] == "closed"
        assert status["failure_count"] == 0

    def test_reopens_on_failure_in_half_open(self) -> None:
        """Circuit should reopen if a failure occurs during half-open."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=0.1,
            success_threshold=2,
        )
        registry.configure("my_tool", config)

        # Trip the circuit
        for _ in range(2):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        time.sleep(0.15)

        # Transition to half-open
        registry.pre_call("my_tool")
        # Fail during recovery
        registry.record_failure("my_tool")

        status = registry.get_status("my_tool")
        assert status["state"] == "open"


class TestCircuitBreakerStatus:
    """Tests for status reporting."""

    def test_get_status_unknown_tool(self) -> None:
        """Status of unknown tool should be CLOSED with zero counts."""
        registry = CircuitBreakerRegistry()
        status = registry.get_status("unknown_tool")
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["total_calls"] == 0

    def test_get_all_status(self) -> None:
        """Should return status for all tracked tools."""
        registry = CircuitBreakerRegistry()
        registry.pre_call("tool_a")
        registry.pre_call("tool_b")
        all_status = registry.get_all_status()
        assert "tool_a" in all_status
        assert "tool_b" in all_status

    def test_get_open_circuits(self) -> None:
        """Should return names of tools with open circuits."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=1)
        registry.configure("failing_tool", config)

        registry.pre_call("failing_tool")
        registry.record_failure("failing_tool")

        open_circuits = registry.get_open_circuits()
        assert "failing_tool" in open_circuits

    def test_retry_after_in_open_status(self) -> None:
        """Open circuit status should include retry_after_seconds."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=60)
        registry.configure("my_tool", config)

        registry.pre_call("my_tool")
        registry.record_failure("my_tool")

        status = registry.get_status("my_tool")
        assert "retry_after_seconds" in status
        assert status["retry_after_seconds"] > 0


class TestCircuitBreakerConfig:
    """Tests for custom configuration."""

    def test_custom_config_per_tool(self) -> None:
        """Different tools can have different configs."""
        registry = CircuitBreakerRegistry()
        registry.configure("tool_a", CircuitBreakerConfig(failure_threshold=3))
        registry.configure("tool_b", CircuitBreakerConfig(failure_threshold=10))

        # tool_a should open after 3 failures
        for _ in range(3):
            registry.pre_call("tool_a")
            registry.record_failure("tool_a")
        assert registry.get_status("tool_a")["state"] == "open"

        # tool_b should still be closed after 3 failures
        for _ in range(3):
            registry.pre_call("tool_b")
            registry.record_failure("tool_b")
        assert registry.get_status("tool_b")["state"] == "closed"

    def test_default_config_used_for_unconfigured_tools(self) -> None:
        """Unconfigured tools should use default config (5 failures)."""
        registry = CircuitBreakerRegistry()

        for _ in range(4):
            registry.pre_call("my_tool")
            registry.record_failure("my_tool")

        assert registry.get_status("my_tool")["state"] == "closed"

        registry.pre_call("my_tool")
        registry.record_failure("my_tool")
        assert registry.get_status("my_tool")["state"] == "open"


class TestCircuitBreakerOpenError:
    """Tests for the CircuitBreakerOpenError exception."""

    def test_error_contains_tool_name(self) -> None:
        """Error should include the tool name."""
        error = CircuitBreakerOpenError("my_tool", 30.0)
        assert error.tool_name == "my_tool"
        assert "my_tool" in str(error)

    def test_error_contains_retry_after(self) -> None:
        """Error should include retry_after_seconds."""
        error = CircuitBreakerOpenError("my_tool", 42.5)
        assert error.retry_after_seconds == 42.5
        assert "42.5" in str(error)
