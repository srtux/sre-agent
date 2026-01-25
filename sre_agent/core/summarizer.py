"""Event Summarization Service.

Compresses tool outputs and session history into natural language
summaries for efficient context utilization.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EventSummary:
    """Summary of a set of events."""

    summary_text: str
    key_findings: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    error_count: int = 0
    events_summarized: int = 0
    token_estimate: int = 0


class Summarizer:
    """Summarizes events and tool outputs for context compaction.

    Uses heuristic-based summarization for tool outputs and can
    optionally use an LLM for complex summarization.
    """

    # Token estimates per character (conservative)
    CHARS_PER_TOKEN = 4

    # Maximum summary length
    MAX_SUMMARY_TOKENS = 2000

    def __init__(self, use_llm: bool = False) -> None:
        """Initialize the summarizer.

        Args:
            use_llm: Whether to use LLM for summarization (expensive)
        """
        self.use_llm = use_llm
        # Tool-specific summarization strategies
        self._tool_summarizers: dict[str, Any] = {
            "fetch_trace": self._summarize_trace,
            "list_traces": self._summarize_trace_list,
            "list_log_entries": self._summarize_logs,
            "analyze_aggregate_metrics": self._summarize_metrics,
            "analyze_trace_comprehensive": self._summarize_comprehensive,
            "extract_log_patterns": self._summarize_patterns,
            "query_promql": self._summarize_promql,
            "list_time_series": self._summarize_timeseries,
        }

    def summarize_event(self, event: dict[str, Any]) -> str:
        """Summarize a single event.

        Args:
            event: Event dictionary with type, content, etc.

        Returns:
            Summarized text
        """
        event_type = event.get("type", "unknown")
        content = event.get("content", "")

        if event_type == "user_message":
            # Keep user messages relatively intact
            return self._truncate(f"User: {content}", max_chars=200)

        elif event_type == "model_thought":
            return self._truncate(f"Agent thought: {content}", max_chars=150)

        elif event_type == "tool_call":
            tool_name = event.get("tool_name", "unknown")
            return f"Called tool: {tool_name}"

        elif event_type == "tool_output":
            tool_name = event.get("tool_name", "unknown")
            return self._summarize_tool_output(tool_name, content)

        else:
            return self._truncate(f"[{event_type}]: {content}", max_chars=100)

    def summarize_events(self, events: list[dict[str, Any]]) -> EventSummary:
        """Summarize a list of events.

        Args:
            events: List of event dictionaries

        Returns:
            EventSummary with compressed content
        """
        if not events:
            return EventSummary(
                summary_text="No events to summarize.",
                events_summarized=0,
            )

        summaries = []
        key_findings: list[str] = []
        tools_used: set[str] = set()
        error_count = 0

        for event in events:
            summary = self.summarize_event(event)
            summaries.append(summary)

            # Track tools used
            if event.get("type") == "tool_call":
                tool_name = event.get("tool_name", "")
                if tool_name:
                    tools_used.add(tool_name)

            # Track errors
            content = str(event.get("content", ""))
            if '"status": "error"' in content or "error" in content.lower():
                error_count += 1

            # Extract key findings
            finding = self._extract_finding(event)
            if finding:
                key_findings.append(finding)

        # Combine summaries
        combined = "\n".join(summaries)

        # Truncate if too long
        max_chars = self.MAX_SUMMARY_TOKENS * self.CHARS_PER_TOKEN
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n... [further history truncated]"

        token_estimate = len(combined) // self.CHARS_PER_TOKEN

        return EventSummary(
            summary_text=combined,
            key_findings=key_findings[:10],  # Keep top 10 findings
            tools_used=list(tools_used),
            error_count=error_count,
            events_summarized=len(events),
            token_estimate=token_estimate,
        )

    def _summarize_tool_output(self, tool_name: str, output: Any) -> str:
        """Summarize tool output using tool-specific strategy.

        Args:
            tool_name: Name of the tool
            output: Tool output (may be JSON string or dict)

        Returns:
            Summarized output
        """
        # Parse JSON if string
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                return self._truncate(f"Tool {tool_name} output: {output}", max_chars=200)

        # Use tool-specific summarizer if available
        summarizer = self._tool_summarizers.get(tool_name)
        if summarizer:
            try:
                result: str = summarizer(output)
                return result
            except Exception as e:
                logger.warning(f"Summarizer failed for {tool_name}: {e}")

        # Default summarization
        return self._default_summarize(tool_name, output)

    def _default_summarize(self, tool_name: str, output: dict[str, Any]) -> str:
        """Default summarization for tool output."""
        status = output.get("status", "unknown")

        if status == "error":
            error = output.get("error", "Unknown error")
            return f"Tool {tool_name} failed: {self._truncate(error, 100)}"

        result = output.get("result", {})

        # Try to extract key information
        if isinstance(result, dict):
            keys = list(result.keys())[:5]
            return f"Tool {tool_name} returned: {', '.join(keys)}"
        elif isinstance(result, list):
            return f"Tool {tool_name} returned {len(result)} items"
        else:
            return f"Tool {tool_name} completed ({status})"

    def _summarize_trace(self, output: dict[str, Any]) -> str:
        """Summarize trace fetch output."""
        result = output.get("result", {})
        if not result:
            return "Trace fetch: no data"

        span_count = result.get("span_count", 0)
        duration = result.get("total_duration_ms", 0)
        errors = result.get("error_count", 0)

        summary = f"Trace: {span_count} spans, {duration:.0f}ms duration"
        if errors > 0:
            summary += f", {errors} errors"

        return summary

    def _summarize_trace_list(self, output: dict[str, Any]) -> str:
        """Summarize trace list output."""
        result = output.get("result", {})
        traces = result.get("traces", [])
        return f"Listed {len(traces)} traces"

    def _summarize_logs(self, output: dict[str, Any]) -> str:
        """Summarize log entries output."""
        result = output.get("result", {})
        if isinstance(result, list):
            entry_count = len(result)
        else:
            entry_count = result.get("entry_count", 0)

        return f"Retrieved {entry_count} log entries"

    def _summarize_metrics(self, output: dict[str, Any]) -> str:
        """Summarize aggregate metrics output."""
        result = output.get("result", {})
        services = result.get("services_analyzed", 0)
        issues = result.get("issues_found", 0)

        summary = f"Analyzed {services} services"
        if issues > 0:
            summary += f", found {issues} issues"

        return summary

    def _summarize_comprehensive(self, output: dict[str, Any]) -> str:
        """Summarize comprehensive trace analysis output."""
        result = output.get("result", {})

        parts = []
        if "latency" in result:
            latency = result["latency"]
            parts.append(f"Latency: {latency.get('p99_ms', 0):.0f}ms P99")

        if "errors" in result:
            errors = result["errors"]
            parts.append(f"Errors: {errors.get('count', 0)}")

        if "critical_path" in result:
            cp = result["critical_path"]
            if isinstance(cp, list) and cp:
                parts.append(f"Critical path: {len(cp)} spans")

        return "Comprehensive analysis - " + ", ".join(parts) if parts else "Analyzed"

    def _summarize_patterns(self, output: dict[str, Any]) -> str:
        """Summarize log pattern extraction output."""
        result = output.get("result", {})
        patterns = result.get("patterns", [])
        return f"Extracted {len(patterns)} log patterns"

    def _summarize_promql(self, output: dict[str, Any]) -> str:
        """Summarize PromQL query output."""
        result = output.get("result", {})

        if isinstance(result, dict):
            data = result.get("data", {})
            result_type = data.get("resultType", "")
            results = data.get("result", [])
            return f"PromQL: {len(results)} {result_type} results"

        return "PromQL query completed"

    def _summarize_timeseries(self, output: dict[str, Any]) -> str:
        """Summarize time series output."""
        result = output.get("result", {})
        if isinstance(result, list):
            return f"Time series: {len(result)} series returned"
        return "Time series query completed"

    def _extract_finding(self, event: dict[str, Any]) -> str | None:
        """Extract a key finding from an event if present.

        Args:
            event: Event dictionary

        Returns:
            Finding string or None
        """
        content = event.get("content", "")

        # Look for explicit findings in tool outputs
        if event.get("type") == "tool_output":
            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    content = data
                except json.JSONDecodeError:
                    pass

            if isinstance(content, dict):
                result = content.get("result", {})
                if isinstance(result, dict):
                    # Check for root cause
                    if "root_cause" in result:
                        return f"Root cause: {result['root_cause'][:100]}"

                    # Check for bottleneck
                    if "bottleneck" in result:
                        return f"Bottleneck: {result['bottleneck'][:100]}"

                    # Check for anomalies
                    anomalies = result.get("anomalies", [])
                    if anomalies:
                        return f"Found {len(anomalies)} anomalies"

        return None

    def _truncate(self, text: str, max_chars: int = 200) -> str:
        """Truncate text to max characters."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."


# Singleton instance
_summarizer: Summarizer | None = None


def get_summarizer(use_llm: bool = False) -> Summarizer:
    """Get the singleton summarizer instance."""
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer(use_llm=use_llm)
    return _summarizer
