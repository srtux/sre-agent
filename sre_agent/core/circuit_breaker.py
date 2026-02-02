"""Circuit Breaker pattern for resilient tool execution.

Implements the Circuit Breaker pattern to prevent cascading failures when
tools or external services are failing. This is a core SRE pattern that
protects the system from repeatedly calling broken dependencies.

States:
    CLOSED: Normal operation, calls pass through
    OPEN: Circuit is tripped, calls fail fast without execution
    HALF_OPEN: Testing if the service has recovered

Based on: https://martinfowler.com/bliki/CircuitBreaker.html
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker instance.

    Attributes:
        failure_threshold: Number of failures before opening the circuit.
        recovery_timeout_seconds: Seconds to wait before trying half-open.
        half_open_max_calls: Max calls allowed in half-open state to test recovery.
        success_threshold: Successes in half-open needed to close the circuit.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    half_open_max_calls: int = 1
    success_threshold: int = 2


@dataclass
class CircuitBreakerState:
    """Mutable state for a single circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    half_open_calls: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_short_circuits: int = 0


class CircuitBreakerOpenError(Exception):
    """Raised when a call is blocked by an open circuit breaker."""

    def __init__(self, tool_name: str, retry_after_seconds: float) -> None:
        self.tool_name = tool_name
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Circuit breaker OPEN for '{tool_name}'. "
            f"Retry after {retry_after_seconds:.1f}s."
        )


class CircuitBreakerRegistry:
    """Registry managing circuit breakers for all tools.

    Thread-safe singleton that tracks circuit state per tool name.
    """

    _instance: "CircuitBreakerRegistry | None" = None
    _breakers: dict[str, CircuitBreakerState]
    _configs: dict[str, CircuitBreakerConfig]
    _default_config: CircuitBreakerConfig

    def __new__(cls) -> "CircuitBreakerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._breakers = {}
            cls._instance._configs = {}
            cls._instance._default_config = CircuitBreakerConfig()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def configure(
        self, tool_name: str, config: CircuitBreakerConfig
    ) -> None:
        """Set custom configuration for a specific tool."""
        self._configs[tool_name] = config

    def _get_config(self, tool_name: str) -> CircuitBreakerConfig:
        """Get configuration for a tool, falling back to default."""
        return self._configs.get(tool_name, self._default_config)

    def _get_state(self, tool_name: str) -> CircuitBreakerState:
        """Get or create state for a tool."""
        if tool_name not in self._breakers:
            self._breakers[tool_name] = CircuitBreakerState()
        return self._breakers[tool_name]

    def pre_call(self, tool_name: str) -> bool:
        """Check if a call should proceed. Returns True if allowed.

        Raises:
            CircuitBreakerOpenError: If the circuit is open and not ready to retry.
        """
        state = self._get_state(tool_name)
        config = self._get_config(tool_name)
        now = time.time()

        state.total_calls += 1

        if state.state == CircuitState.CLOSED:
            return True

        if state.state == CircuitState.OPEN:
            elapsed = now - state.last_failure_time
            if elapsed >= config.recovery_timeout_seconds:
                # Transition to half-open
                state.state = CircuitState.HALF_OPEN
                state.half_open_calls = 0
                state.success_count = 0
                state.last_state_change = now
                logger.info(
                    f"Circuit breaker HALF_OPEN for '{tool_name}' "
                    f"(after {elapsed:.1f}s recovery timeout)"
                )
                return True
            else:
                remaining = config.recovery_timeout_seconds - elapsed
                state.total_short_circuits += 1
                raise CircuitBreakerOpenError(tool_name, remaining)

        if state.state == CircuitState.HALF_OPEN:
            if state.half_open_calls < config.half_open_max_calls:
                state.half_open_calls += 1
                return True
            else:
                raise CircuitBreakerOpenError(
                    tool_name, config.recovery_timeout_seconds
                )

        return True

    def record_success(self, tool_name: str) -> None:
        """Record a successful call."""
        state = self._get_state(tool_name)

        if state.state == CircuitState.HALF_OPEN:
            state.success_count += 1
            config = self._get_config(tool_name)
            if state.success_count >= config.success_threshold:
                state.state = CircuitState.CLOSED
                state.failure_count = 0
                state.success_count = 0
                state.last_state_change = time.time()
                logger.info(
                    f"Circuit breaker CLOSED for '{tool_name}' (recovered)"
                )
        elif state.state == CircuitState.CLOSED:
            # Reset failure count on success
            if state.failure_count > 0:
                state.failure_count = max(0, state.failure_count - 1)

    def record_failure(self, tool_name: str) -> None:
        """Record a failed call."""
        state = self._get_state(tool_name)
        config = self._get_config(tool_name)
        now = time.time()

        state.total_failures += 1

        if state.state == CircuitState.HALF_OPEN:
            # Recovery failed, re-open the circuit
            state.state = CircuitState.OPEN
            state.last_failure_time = now
            state.last_state_change = now
            logger.warning(
                f"Circuit breaker re-OPENED for '{tool_name}' "
                "(failed during half-open recovery)"
            )
        elif state.state == CircuitState.CLOSED:
            state.failure_count += 1
            state.last_failure_time = now
            if state.failure_count >= config.failure_threshold:
                state.state = CircuitState.OPEN
                state.last_state_change = now
                logger.warning(
                    f"Circuit breaker OPENED for '{tool_name}' "
                    f"({state.failure_count} consecutive failures)"
                )

    def get_status(self, tool_name: str) -> dict[str, Any]:
        """Get current status of a circuit breaker."""
        state = self._get_state(tool_name)
        config = self._get_config(tool_name)
        now = time.time()

        status: dict[str, Any] = {
            "tool_name": tool_name,
            "state": state.state.value,
            "failure_count": state.failure_count,
            "total_calls": state.total_calls,
            "total_failures": state.total_failures,
            "total_short_circuits": state.total_short_circuits,
            "config": {
                "failure_threshold": config.failure_threshold,
                "recovery_timeout_seconds": config.recovery_timeout_seconds,
            },
        }

        if state.state == CircuitState.OPEN:
            elapsed = now - state.last_failure_time
            remaining = max(0, config.recovery_timeout_seconds - elapsed)
            status["retry_after_seconds"] = round(remaining, 1)

        return status

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all tracked circuit breakers."""
        return {
            name: self.get_status(name) for name in sorted(self._breakers)
        }

    def get_open_circuits(self) -> list[str]:
        """Get names of all tools with open circuits."""
        return [
            name
            for name, state in self._breakers.items()
            if state.state == CircuitState.OPEN
        ]


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry singleton."""
    return CircuitBreakerRegistry()
