"""GenAI semantic convention attribute parsing for agent traces.

Pure functions that transform raw BigQuery rows and Cloud Trace spans
into typed AgentSpanInfo models and detect anti-patterns.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from typing import Any

from sre_agent.schema import (
    AgentAntiPattern,
    AgentSpanInfo,
    AgentSpanKind,
    GenAIOperationType,
    Severity,
)

logger = logging.getLogger(__name__)

# ============================================================================
# GenAI Semantic Convention Attribute Keys
# ============================================================================

GENAI_OPERATION_NAME = "gen_ai.operation.name"
GENAI_AGENT_NAME = "gen_ai.agent.name"
GENAI_AGENT_ID = "gen_ai.agent.id"
GENAI_TOOL_NAME = "gen_ai.tool.name"
GENAI_TOOL_CALL_ID = "gen_ai.tool.call.id"
GENAI_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GENAI_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GENAI_REQUEST_MODEL = "gen_ai.request.model"
GENAI_RESPONSE_MODEL = "gen_ai.response.model"
GENAI_FINISH_REASONS = "gen_ai.response.finish_reasons"
CLOUD_RESOURCE_ID = "cloud.resource_id"

# Mapping from gen_ai.operation.name values to our enums
_OPERATION_MAP: dict[str, GenAIOperationType] = {
    "invoke_agent": GenAIOperationType.INVOKE_AGENT,
    "execute_tool": GenAIOperationType.EXECUTE_TOOL,
    "generate_content": GenAIOperationType.GENERATE_CONTENT,
    "chat": GenAIOperationType.CHAT,
}

_OPERATION_TO_KIND: dict[GenAIOperationType, AgentSpanKind] = {
    GenAIOperationType.INVOKE_AGENT: AgentSpanKind.AGENT_INVOCATION,
    GenAIOperationType.EXECUTE_TOOL: AgentSpanKind.TOOL_EXECUTION,
    GenAIOperationType.GENERATE_CONTENT: AgentSpanKind.LLM_CALL,
    GenAIOperationType.CHAT: AgentSpanKind.LLM_CALL,
}


def classify_span(
    attrs: dict[str, str],
) -> tuple[AgentSpanKind, GenAIOperationType]:
    """Classify a span by its GenAI semantic convention attributes.

    Args:
        attrs: Span attributes dictionary.

    Returns:
        Tuple of (AgentSpanKind, GenAIOperationType).
    """
    operation_name = attrs.get(GENAI_OPERATION_NAME, "")
    operation = _OPERATION_MAP.get(operation_name, GenAIOperationType.UNKNOWN)
    kind = _OPERATION_TO_KIND.get(operation, AgentSpanKind.UNKNOWN)

    # Detect sub-agent delegation: invoke_agent with a different agent name
    # than the parent (handled at tree-build time, but we can hint here)
    if operation == GenAIOperationType.INVOKE_AGENT and attrs.get(GENAI_AGENT_NAME):
        kind = AgentSpanKind.AGENT_INVOCATION

    return kind, operation


def _safe_int(value: str | int | float | None) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value: str | int | float | None) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _extract_attrs_from_json(raw_attributes: str | dict[str, Any] | None) -> dict[str, str]:
    """Extract a flat string->string dict from JSON attributes.

    BigQuery stores attributes as a JSON string with nested structure.
    Cloud Trace uses a labels dict directly.
    """
    if raw_attributes is None:
        return {}
    if isinstance(raw_attributes, dict):
        return {str(k): str(v) for k, v in raw_attributes.items()}
    try:
        parsed = json.loads(raw_attributes)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _parse_finish_reasons(raw: str | list[Any] | None) -> list[str]:
    """Parse finish reasons from various formats."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(r) for r in raw]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(r) for r in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [str(raw)] if raw else []


def parse_bq_row_to_agent_span(row: dict[str, Any]) -> AgentSpanInfo:
    """Parse a BigQuery row into an AgentSpanInfo.

    Expects the row shape from the _AllSpans BQ export with JSON attributes.

    Args:
        row: Dict from BigQuery result row.

    Returns:
        Parsed AgentSpanInfo.
    """
    raw_attrs = row.get("attributes", {})
    attrs = _extract_attrs_from_json(raw_attrs)

    # Also extract resource attributes
    raw_resource = row.get("resource", {})
    if isinstance(raw_resource, str):
        try:
            raw_resource = json.loads(raw_resource)
        except (json.JSONDecodeError, TypeError):
            raw_resource = {}
    resource_attrs = _extract_attrs_from_json(
        raw_resource.get("attributes") if isinstance(raw_resource, dict) else None
    )

    # Merge resource attributes with span attributes (span takes precedence)
    merged_attrs = {**resource_attrs, **attrs}

    kind, operation = classify_span(merged_attrs)

    # Parse status
    raw_status = row.get("status", {})
    if isinstance(raw_status, str):
        try:
            raw_status = json.loads(raw_status)
        except (json.JSONDecodeError, TypeError):
            raw_status = {}
    status_code = _safe_int(
        raw_status.get("code") if isinstance(raw_status, dict) else None
    ) or 0
    error_message = (
        raw_status.get("message") if isinstance(raw_status, dict) else None
    )

    # Parse timestamps
    start_time = row.get("start_time", "")
    end_time = row.get("end_time", "")
    duration_nano = _safe_float(row.get("duration_nano", 0))
    duration_ms = duration_nano / 1_000_000 if duration_nano else 0.0

    return AgentSpanInfo(
        span_id=str(row.get("span_id", "")),
        parent_span_id=str(row["parent_span_id"]) if row.get("parent_span_id") else None,
        name=str(row.get("name", "")),
        kind=kind,
        operation=operation,
        start_time_iso=str(start_time),
        end_time_iso=str(end_time),
        duration_ms=duration_ms,
        agent_name=merged_attrs.get(GENAI_AGENT_NAME),
        agent_id=merged_attrs.get(GENAI_AGENT_ID),
        tool_name=merged_attrs.get(GENAI_TOOL_NAME),
        tool_call_id=merged_attrs.get(GENAI_TOOL_CALL_ID),
        model_requested=merged_attrs.get(GENAI_REQUEST_MODEL),
        model_used=merged_attrs.get(GENAI_RESPONSE_MODEL),
        input_tokens=_safe_int(merged_attrs.get(GENAI_INPUT_TOKENS)),
        output_tokens=_safe_int(merged_attrs.get(GENAI_OUTPUT_TOKENS)),
        finish_reasons=_parse_finish_reasons(merged_attrs.get(GENAI_FINISH_REASONS)),
        status_code=status_code,
        error_message=error_message,
        attributes=merged_attrs,
    )


def parse_cloud_trace_span_to_agent_span(span: dict[str, Any]) -> AgentSpanInfo:
    """Parse a Cloud Trace v1 API span into an AgentSpanInfo.

    Cloud Trace spans use a labels dict and different field names.

    Args:
        span: Dict from Cloud Trace API response.

    Returns:
        Parsed AgentSpanInfo.
    """
    labels = span.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}

    kind, operation = classify_span(labels)

    # Cloud Trace uses startTime / endTime in RFC3339
    start_time = span.get("startTime", "")
    end_time = span.get("endTime", "")

    # Calculate duration from timestamps
    duration_ms = 0.0
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration_ms = (end_dt - start_dt).total_seconds() * 1000
    except (ValueError, AttributeError):
        pass

    # Status from Cloud Trace
    status_code = 0
    error_message = None
    if labels.get("error") or span.get("status", {}).get("code", 0) != 0:
        status_code = 2
        error_message = labels.get("error") or span.get("status", {}).get("message")

    return AgentSpanInfo(
        span_id=str(span.get("spanId", "")),
        parent_span_id=str(span["parentSpanId"]) if span.get("parentSpanId") else None,
        name=str(span.get("name", "")),
        kind=kind,
        operation=operation,
        start_time_iso=str(start_time),
        end_time_iso=str(end_time),
        duration_ms=duration_ms,
        agent_name=labels.get(GENAI_AGENT_NAME),
        agent_id=labels.get(GENAI_AGENT_ID),
        tool_name=labels.get(GENAI_TOOL_NAME),
        tool_call_id=labels.get(GENAI_TOOL_CALL_ID),
        model_requested=labels.get(GENAI_REQUEST_MODEL),
        model_used=labels.get(GENAI_RESPONSE_MODEL),
        input_tokens=_safe_int(labels.get(GENAI_INPUT_TOKENS)),
        output_tokens=_safe_int(labels.get(GENAI_OUTPUT_TOKENS)),
        finish_reasons=_parse_finish_reasons(labels.get(GENAI_FINISH_REASONS)),
        status_code=status_code,
        error_message=error_message,
        attributes=labels,
    )


def build_interaction_tree(
    flat_spans: list[AgentSpanInfo],
) -> list[AgentSpanInfo]:
    """Build a parent-child tree from a flat list of spans.

    Args:
        flat_spans: Flat list of parsed spans.

    Returns:
        List of root spans with children populated.
    """
    span_map: dict[str, AgentSpanInfo] = {}
    children_map: dict[str, list[AgentSpanInfo]] = {}

    for span in flat_spans:
        span_map[span.span_id] = span
        parent = span.parent_span_id
        if parent:
            children_map.setdefault(parent, []).append(span)

    def _attach_children(span: AgentSpanInfo) -> AgentSpanInfo:
        kids = children_map.get(span.span_id, [])
        if not kids:
            return span
        attached_kids = [_attach_children(k) for k in kids]

        # Detect sub-agent delegation: child invoke_agent with different agent name
        updated_kids: list[AgentSpanInfo] = []
        for kid in attached_kids:
            if (
                kid.operation == GenAIOperationType.INVOKE_AGENT
                and kid.agent_name
                and kid.agent_name != span.agent_name
            ):
                # Re-classify as sub-agent delegation
                kid = AgentSpanInfo(
                    **{
                        **kid.model_dump(),
                        "kind": AgentSpanKind.SUB_AGENT_DELEGATION,
                    }
                )
            updated_kids.append(kid)

        return AgentSpanInfo(**{**span.model_dump(), "children": updated_kids})

    # Roots are spans with no parent or whose parent is not in span_map
    roots: list[AgentSpanInfo] = []
    for span in flat_spans:
        if span.parent_span_id is None or span.parent_span_id not in span_map:
            roots.append(_attach_children(span))

    return roots


def compute_graph_aggregates(root_spans: list[AgentSpanInfo]) -> dict[str, Any]:
    """Compute aggregate statistics from the interaction tree.

    Args:
        root_spans: Root spans with children attached.

    Returns:
        Dict with total_spans, total_input_tokens, total_output_tokens,
        total_llm_calls, total_tool_executions, unique_agents, unique_tools,
        unique_models, total_duration_ms.
    """
    total_spans = 0
    total_input = 0
    total_output = 0
    llm_calls = 0
    tool_execs = 0
    agents: set[str] = set()
    tools: set[str] = set()
    models: set[str] = set()
    min_start: str | None = None
    max_end: str | None = None

    def _walk(span: AgentSpanInfo) -> None:
        nonlocal total_spans, total_input, total_output, llm_calls, tool_execs
        nonlocal min_start, max_end
        total_spans += 1
        total_input += span.input_tokens or 0
        total_output += span.output_tokens or 0

        if span.kind == AgentSpanKind.LLM_CALL:
            llm_calls += 1
        elif span.kind == AgentSpanKind.TOOL_EXECUTION:
            tool_execs += 1

        if span.agent_name:
            agents.add(span.agent_name)
        if span.tool_name:
            tools.add(span.tool_name)
        if span.model_used:
            models.add(span.model_used)
        elif span.model_requested:
            models.add(span.model_requested)

        if min_start is None or span.start_time_iso < min_start:
            min_start = span.start_time_iso
        if max_end is None or span.end_time_iso > max_end:
            max_end = span.end_time_iso

        for child in span.children:
            _walk(child)

    for root in root_spans:
        _walk(root)

    # Compute total duration from root spans
    total_duration_ms = 0.0
    for root in root_spans:
        total_duration_ms = max(total_duration_ms, root.duration_ms)

    return {
        "total_spans": total_spans,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_llm_calls": llm_calls,
        "total_tool_executions": tool_execs,
        "unique_agents": sorted(agents),
        "unique_tools": sorted(tools),
        "unique_models": sorted(models),
        "total_duration_ms": total_duration_ms,
    }


def detect_anti_patterns(
    root_spans: list[AgentSpanInfo],
) -> list[AgentAntiPattern]:
    """Detect anti-patterns in agent interaction traces.

    Detectors:
    - Excessive retries: Same tool called >3x under same parent
    - Token waste: Output tokens > 5x input tokens on non-final LLM calls
    - Long chains: >8 sequential LLM calls without tool use
    - Redundant tool calls: Same tool+name combo appearing multiple times

    Args:
        root_spans: Root spans with children attached.

    Returns:
        List of detected anti-patterns.
    """
    patterns: list[AgentAntiPattern] = []

    def _check_excessive_retries(span: AgentSpanInfo) -> None:
        """Check for same tool called >3x under same parent."""
        tool_counts: Counter[str] = Counter()
        tool_span_ids: dict[str, list[str]] = {}
        for child in span.children:
            if child.kind == AgentSpanKind.TOOL_EXECUTION and child.tool_name:
                tool_counts[child.tool_name] += 1
                tool_span_ids.setdefault(child.tool_name, []).append(child.span_id)

        for tool_name, count in tool_counts.items():
            if count > 3:
                patterns.append(
                    AgentAntiPattern(
                        pattern_type="excessive_retries",
                        severity=Severity.HIGH,
                        description=(
                            f"Tool '{tool_name}' called {count} times under "
                            f"'{span.name}' — possible retry loop"
                        ),
                        affected_spans=tool_span_ids[tool_name],
                        recommendation=(
                            f"Investigate why '{tool_name}' needs {count} invocations. "
                            "Consider improving error handling or input validation."
                        ),
                        metric_value=float(count),
                    )
                )

    def _check_token_waste(span: AgentSpanInfo) -> None:
        """Check for output >> input tokens on non-final LLM calls."""
        llm_children = [
            c for c in span.children if c.kind == AgentSpanKind.LLM_CALL
        ]
        # Non-final = all except the last LLM call
        for llm_span in llm_children[:-1] if len(llm_children) > 1 else []:
            inp = llm_span.input_tokens or 0
            out = llm_span.output_tokens or 0
            if inp > 0 and out > 5 * inp:
                patterns.append(
                    AgentAntiPattern(
                        pattern_type="token_waste",
                        severity=Severity.MEDIUM,
                        description=(
                            f"LLM call '{llm_span.name}' produced {out} output tokens "
                            f"vs {inp} input tokens ({out / inp:.1f}x ratio) — "
                            "excessive generation in intermediate step"
                        ),
                        affected_spans=[llm_span.span_id],
                        recommendation=(
                            "Consider constraining output length for intermediate "
                            "reasoning steps or using a smaller model."
                        ),
                        metric_value=float(out) / float(inp),
                    )
                )

    def _check_long_chains(span: AgentSpanInfo) -> None:
        """Check for >8 sequential LLM calls without tool use."""
        consecutive_llm = 0
        chain_spans: list[str] = []
        for child in span.children:
            if child.kind == AgentSpanKind.LLM_CALL:
                consecutive_llm += 1
                chain_spans.append(child.span_id)
            else:
                if consecutive_llm > 8:
                    patterns.append(
                        AgentAntiPattern(
                            pattern_type="long_chain",
                            severity=Severity.MEDIUM,
                            description=(
                                f"{consecutive_llm} consecutive LLM calls without tool "
                                f"use under '{span.name}' — agent may be stuck in a loop"
                            ),
                            affected_spans=chain_spans.copy(),
                            recommendation=(
                                "The agent appears to be reasoning without acting. "
                                "Consider adding a tool call limit or forcing tool use."
                            ),
                            metric_value=float(consecutive_llm),
                        )
                    )
                consecutive_llm = 0
                chain_spans = []
        # Check trailing chain
        if consecutive_llm > 8:
            patterns.append(
                AgentAntiPattern(
                    pattern_type="long_chain",
                    severity=Severity.MEDIUM,
                    description=(
                        f"{consecutive_llm} consecutive LLM calls without tool "
                        f"use under '{span.name}' — agent may be stuck in a loop"
                    ),
                    affected_spans=chain_spans,
                    recommendation=(
                        "The agent appears to be reasoning without acting. "
                        "Consider adding a tool call limit or forcing tool use."
                    ),
                    metric_value=float(consecutive_llm),
                )
            )

    def _check_redundant_tool_calls(all_spans: list[AgentSpanInfo]) -> None:
        """Check for same tool name appearing multiple times across the tree."""
        tool_occurrences: Counter[str] = Counter()
        tool_span_ids: dict[str, list[str]] = {}

        def _collect(span: AgentSpanInfo) -> None:
            if span.kind == AgentSpanKind.TOOL_EXECUTION and span.tool_name:
                tool_occurrences[span.tool_name] += 1
                tool_span_ids.setdefault(span.tool_name, []).append(span.span_id)
            for child in span.children:
                _collect(child)

        for root in all_spans:
            _collect(root)

        for tool_name, count in tool_occurrences.items():
            if count > 3:
                patterns.append(
                    AgentAntiPattern(
                        pattern_type="redundant_tool_calls",
                        severity=Severity.LOW,
                        description=(
                            f"Tool '{tool_name}' invoked {count} times across "
                            "the trace — may indicate redundant work"
                        ),
                        affected_spans=tool_span_ids[tool_name],
                        recommendation=(
                            "Consider caching tool results or restructuring "
                            "agent logic to avoid repeated calls."
                        ),
                        metric_value=float(count),
                    )
                )

    # Run all detectors
    def _walk_for_patterns(span: AgentSpanInfo) -> None:
        _check_excessive_retries(span)
        _check_token_waste(span)
        _check_long_chains(span)
        for child in span.children:
            _walk_for_patterns(child)

    for root in root_spans:
        _walk_for_patterns(root)

    _check_redundant_tool_calls(root_spans)

    return patterns
