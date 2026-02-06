"""ADK model callbacks for cost tracking, token budgeting, and observability.

Provides before_model_callback and after_model_callback that intercept
every LLM inference call to:
- Track token usage (input/output) per agent and session
- Estimate API cost based on model pricing
- Enforce token budgets to prevent runaway investigations
- Emit metrics for monitoring and dashboards

Usage:
    from sre_agent.core.model_callbacks import (
        before_model_callback,
        after_model_callback,
        get_usage_tracker,
    )

    agent = LlmAgent(
        ...,
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
    )
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from sre_agent.core.summarizer import get_summarizer

logger = logging.getLogger(__name__)

# Token budget environment variable (0 = unlimited)
_TOKEN_BUDGET_ENV = "SRE_AGENT_TOKEN_BUDGET"
_DEFAULT_TOKEN_BUDGET = 0  # unlimited by default

# Cost per 1M tokens (USD) — Gemini 2.5 pricing as of 2026-02
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

# Default pricing for unknown models
_DEFAULT_PRICING: dict[str, float] = {"input": 0.50, "output": 2.00}


@dataclass
class ModelCallMetrics:
    """Metrics for a single model call."""

    agent_name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class UsageTracker:
    """Thread-safe accumulator for model usage across a session.

    Tracks per-agent and aggregate token usage, cost, and call counts.
    Can enforce a configurable token budget.
    """

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _calls: list[ModelCallMetrics] = field(default_factory=list)
    _total_input_tokens: int = 0
    _total_output_tokens: int = 0
    _total_cost_usd: float = 0.0
    _total_calls: int = 0
    _per_agent_input: dict[str, int] = field(default_factory=dict)
    _per_agent_output: dict[str, int] = field(default_factory=dict)
    _per_agent_calls: dict[str, int] = field(default_factory=dict)

    def record(self, metrics: ModelCallMetrics) -> None:
        """Record a model call's metrics."""
        with self._lock:
            self._calls.append(metrics)
            self._total_input_tokens += metrics.input_tokens
            self._total_output_tokens += metrics.output_tokens
            self._total_cost_usd += metrics.estimated_cost_usd
            self._total_calls += 1

            agent = metrics.agent_name
            self._per_agent_input[agent] = (
                self._per_agent_input.get(agent, 0) + metrics.input_tokens
            )
            self._per_agent_output[agent] = (
                self._per_agent_output.get(agent, 0) + metrics.output_tokens
            )
            self._per_agent_calls[agent] = self._per_agent_calls.get(agent, 0) + 1

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens across all calls."""
        with self._lock:
            return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens across all calls."""
        with self._lock:
            return self._total_output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) across all calls."""
        with self._lock:
            return self._total_input_tokens + self._total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        """Total estimated cost in USD."""
        with self._lock:
            return self._total_cost_usd

    @property
    def total_calls(self) -> int:
        """Total number of model calls."""
        with self._lock:
            return self._total_calls

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of usage across all agents."""
        with self._lock:
            return {
                "total_calls": self._total_calls,
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "total_tokens": self._total_input_tokens + self._total_output_tokens,
                "estimated_cost_usd": round(self._total_cost_usd, 6),
                "per_agent": {
                    agent: {
                        "calls": self._per_agent_calls.get(agent, 0),
                        "input_tokens": self._per_agent_input.get(agent, 0),
                        "output_tokens": self._per_agent_output.get(agent, 0),
                    }
                    for agent in self._per_agent_calls
                },
            }

    def is_over_budget(self) -> bool:
        """Check if the total tokens exceed the configured budget."""
        budget = _get_token_budget()
        if budget <= 0:
            return False
        with self._lock:
            return (self._total_input_tokens + self._total_output_tokens) > budget

    def reset(self) -> None:
        """Reset all tracked metrics."""
        with self._lock:
            self._calls.clear()
            self._total_input_tokens = 0
            self._total_output_tokens = 0
            self._total_cost_usd = 0.0
            self._total_calls = 0
            self._per_agent_input.clear()
            self._per_agent_output.clear()
            self._per_agent_calls.clear()


# Module-level singleton
_usage_tracker: UsageTracker | None = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> UsageTracker:
    """Get or create the global usage tracker singleton."""
    global _usage_tracker
    if _usage_tracker is None:
        with _tracker_lock:
            if _usage_tracker is None:
                _usage_tracker = UsageTracker()
    return _usage_tracker


def reset_usage_tracker() -> None:
    """Reset the global usage tracker (for testing)."""
    global _usage_tracker
    with _tracker_lock:
        _usage_tracker = None


def _get_token_budget() -> int:
    """Get the configured token budget from environment."""
    try:
        return int(os.environ.get(_TOKEN_BUDGET_ENV, str(_DEFAULT_TOKEN_BUDGET)))
    except (ValueError, TypeError):
        return _DEFAULT_TOKEN_BUDGET


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a model call in USD.

    Args:
        model: Model name (e.g. "gemini-2.5-flash").
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    # Find pricing — try exact match first, then prefix match
    pricing = _MODEL_PRICING.get(model)
    if pricing is None:
        for model_prefix, model_pricing in _MODEL_PRICING.items():
            if model.startswith(model_prefix):
                pricing = model_pricing
                break
    if pricing is None:
        pricing = _DEFAULT_PRICING

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """ADK before_model_callback for token budget enforcement.

    Checks if the session has exceeded the token budget. If so,
    returns an LlmResponse that short-circuits the LLM call with a
    budget-exceeded message.

    Args:
        callback_context: ADK callback context with state and agent info.
        llm_request: The LLM request about to be sent.

    Returns:
        None to proceed normally, or LlmResponse to skip the LLM call.
    """
    tracker = get_usage_tracker()

    # Check token budget
    if tracker.is_over_budget():
        budget = _get_token_budget()
        total = tracker.total_tokens
        logger.warning(
            f"Token budget exceeded: {total} > {budget}. "
            "Halting LLM call to prevent runaway cost."
        )
        return LlmResponse(
            content=genai_types.Content(
                parts=[
                    genai_types.Part(
                        text=(
                            f"Investigation paused: token budget exhausted "
                            f"({total:,} / {budget:,} tokens used). "
                            "Please summarize findings with available data."
                        )
                    )
                ]
            ),
            turn_complete=True,
        )

    # Store start time in callback_context state for after_model_callback
    if hasattr(callback_context, "state"):
        callback_context.state["_model_call_start_time"] = time.time()

    # EMERGENCY CONTEXT WINDOWING: Prevent 400 INVALID_ARGUMENT (Token Limit)
    # The Gemini Flash 2.5 limit is ~1.04M tokens.
    # We use a conservative estimate to trigger compaction well before the hard limit.
    SAFE_TRIGGER_TOKENS = 750_000  # Start compacting at 750k to be safe
    CHARS_PER_TOKEN = 2.5  # More realistic for logs and code (English text is ~4)

    total_chars = 0
    # 1. Count System Instructions
    if hasattr(llm_request, "system_instructions") and llm_request.system_instructions:
        for content in llm_request.system_instructions:
            if content.parts:
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        total_chars += len(text)

    # 2. Count History and Current Content
    for content in llm_request.contents:
        if content.parts:
            for part in content.parts:
                text = getattr(part, "text", None)
                if text:
                    total_chars += len(text)
                elif hasattr(part, "function_call") and part.function_call:
                    # Function call has name and args
                    fc_name = part.function_call.name or "unknown"
                    fc_args = (
                        str(part.function_call.args) if part.function_call.args else ""
                    )
                    total_chars += len(str(fc_name)) + len(fc_args)
                elif hasattr(part, "function_response") and part.function_response:
                    # Function response can be huge (e.g. log list).
                    # We use the length of the string representation of the response object.
                    resp = getattr(part.function_response, "response", None)
                    total_chars += len(str(resp)) if resp is not None else 0
                else:
                    # Default for other types
                    total_chars += 500

    estimated_tokens = int(total_chars / CHARS_PER_TOKEN)

    if estimated_tokens > SAFE_TRIGGER_TOKENS:
        agent_name = getattr(callback_context, "agent_name", "unknown")
        logger.warning(
            f"⚠️ Emergency context compaction triggered for {agent_name}: "
            f"Estimated {estimated_tokens:,} tokens > {SAFE_TRIGGER_TOKENS:,}."
        )

        # Strategy: Keep system/first message, last few messages, and compact middle.
        # We enforce this if history is long enough, otherwise we might need to truncate individual messages.
        if len(llm_request.contents) > 2:
            first_msg = llm_request.contents[0]
            # Keep last 6 messages (3 turns) to clear more space if we're very full
            num_recent = 6 if estimated_tokens > 900_000 else 10
            recent_msgs = llm_request.contents[-num_recent:]
            middle_msgs = llm_request.contents[1:-num_recent]

            if middle_msgs:
                # COMPACT the middle turns
                middle_summary = _compact_llm_contents(middle_msgs)

                compacted_indicator = genai_types.Content(
                    role="user",
                    parts=[
                        genai_types.Part(
                            text=(
                                f"\n\n[SRE AGENT: Middle {len(middle_msgs)} turns compacted to stay within context limits]\n"
                                f"SUMMARY OF PREVIOUS HISTORY:\n{middle_summary}\n\n"
                            )
                        )
                    ],
                )

                # Reconstruct contents
                new_contents = [first_msg, compacted_indicator, *recent_msgs]
                llm_request.contents = new_contents

                # Recalculate and log
                new_chars = sum(
                    len(p.text) if hasattr(p, "text") and p.text else 500
                    for c in new_contents
                    for p in (c.parts or [])
                )
                logger.info(
                    f"✅ Compacted context for {agent_name}: ~{int(new_chars / CHARS_PER_TOKEN):,} tokens."
                )
            else:
                logger.warning(
                    f"⚠️ Context too large ({estimated_tokens:,} tokens) but contains only {len(llm_request.contents)} messages. "
                    "Individual messages might be exceeding tool truncation limits."
                )

    return None


def _compact_llm_contents(contents: list[genai_types.Content]) -> str:
    """Heuristically compact LLM contents into a summary string.

    Args:
        contents: List of Content objects to compact.

    Returns:
        A condensed string representation.
    """
    summarizer = get_summarizer()
    summaries = []

    for content in contents:
        # Determine event type and content for the summarizer
        if content.role == "model":
            # Assistant turns: check for tool calls or thoughts
            has_tool_call = False
            if content.parts:
                for part in content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        summaries.append(f"• Called tool: {part.function_call.name}")
                        has_tool_call = True

            if not has_tool_call and content.parts:
                text = "".join(
                    p.text for p in content.parts if hasattr(p, "text") and p.text
                )
                if text:
                    summaries.append(f"• Thought: {text[:100]}...")

        elif content.role == "user":
            # User turns: check for tool responses or messages
            has_tool_res = False
            if content.parts:
                for part in content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        name = part.function_response.name or "unknown"
                        resp = part.function_response.response
                        summaries.append(
                            f"  └ Result: {summarizer._summarize_tool_output(name, resp)}"
                        )
                        has_tool_res = True

            if not has_tool_res and content.parts:
                text = "".join(
                    p.text for p in content.parts if hasattr(p, "text") and p.text
                )
                if text:
                    summaries.append(f"• User: {text[:100]}...")

    # Join and truncate the whole summary if it's still too long
    result = "\n".join(summaries)
    if len(result) > 4000:
        result = result[:4000] + "\n... [summary further truncated]"

    return result


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """ADK after_model_callback for token usage tracking and cost estimation.

    Records token usage from the model response, estimates cost,
    and logs the metrics. Also emits per-agent usage info.

    Args:
        callback_context: ADK callback context with state and agent info.
        llm_response: The LLM response received.

    Returns:
        None (does not modify the response).
    """
    tracker = get_usage_tracker()

    # Extract timing
    start_time = 0.0
    state = callback_context.state
    if state is not None:
        start_time = state.get("_model_call_start_time", 0.0)
        # Clear the start time to avoid double-counting
        state["_model_call_start_time"] = None
    duration_ms = (time.time() - start_time) * 1000 if start_time > 0 else 0.0

    # Extract agent name
    agent_name = "unknown"
    if hasattr(callback_context, "agent_name"):
        agent_name = callback_context.agent_name
    elif hasattr(callback_context, "state"):
        agent_name = callback_context.state.get("_agent_name", "unknown")

    # Extract token usage from response (LlmResponse uses camelCase attrs)
    input_tokens = 0
    output_tokens = 0
    model_name = "unknown"

    usage = getattr(llm_response, "usageMetadata", None)
    if usage is not None:
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0

    # Extract model name
    model_name = getattr(llm_response, "modelVersion", None) or "unknown"

    # Calculate cost
    estimated_cost = _estimate_cost(model_name, input_tokens, output_tokens)

    # Record metrics
    metrics = ModelCallMetrics(
        agent_name=agent_name,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
        estimated_cost_usd=estimated_cost,
    )
    tracker.record(metrics)

    # Log at appropriate level
    if input_tokens + output_tokens > 0:
        logger.info(
            f"LLM call: agent={agent_name} model={model_name} "
            f"tokens={input_tokens}+{output_tokens} "
            f"cost=${estimated_cost:.6f} duration={duration_ms:.0f}ms "
            f"[session total: {tracker.total_tokens:,} tokens, "
            f"${tracker.total_cost_usd:.4f}]"
        )

    return None
