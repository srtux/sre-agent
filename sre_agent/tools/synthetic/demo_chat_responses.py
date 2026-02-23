"""Pre-recorded agent investigation responses for demo/guest mode.

Streams ALL event types to showcase every frontend feature: session, text,
tool-call, tool-response, dashboard (all 7 widget types), agent_activity,
council_graph, memory, and trace_info.

The demo tells the story of investigating a checkout latency spike in the
Cymbal Assistant caused by a bad prompt change in the Product Discovery Agent
(v2.4.1).
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ID = "cymbal-shops-demo"
_INVESTIGATION_ID = "inv-cymbal-001"
_SESSION_ID = "demo-session-001"

# A deterministic degraded trace for the waterfall widget (22 spans).
_TRACE_ID = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _event(data: dict[str, Any]) -> str:
    """Serialize a single event dict to a compact JSON line."""
    return json.dumps(data, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Span helpers for waterfall trace
# ---------------------------------------------------------------------------


def _waterfall_spans() -> list[dict[str, Any]]:
    """Build 22 spans for a degraded Cymbal Assistant trace.

    The trace mirrors the structure from ``DemoDataGenerator`` but is
    self-contained so the module has no runtime dependency on the generator.
    """
    spans: list[dict[str, Any]] = []

    def _span(
        span_id: str,
        name: str,
        start: str,
        end: str,
        parent: str | None,
        *,
        status: str = "OK",
        attrs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "span_id": span_id,
            "trace_id": _TRACE_ID,
            "name": name,
            "start_time": start,
            "end_time": end,
            "parent_span_id": parent,
            "attributes": attrs or {},
            "status": status,
        }

    # Root span
    spans.append(
        _span(
            "0000000000000001",
            "cymbal-assistant",
            "2026-02-18T08:15:00.000Z",
            "2026-02-18T08:15:04.800Z",
            None,
            attrs={
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": "cymbal-assistant",
                "cymbal.release_version": "v2.4.1",
            },
        )
    )
    # Orchestrator LLM call
    spans.append(
        _span(
            "0000000000000002",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:00.050Z",
            "2026-02-18T08:15:00.350Z",
            "0000000000000001",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )
    # Product Discovery Agent span
    spans.append(
        _span(
            "0000000000000003",
            "product-discovery",
            "2026-02-18T08:15:00.400Z",
            "2026-02-18T08:15:03.600Z",
            "0000000000000001",
            attrs={
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": "product-discovery",
            },
        )
    )
    # Product Discovery LLM call
    spans.append(
        _span(
            "0000000000000004",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:00.450Z",
            "2026-02-18T08:15:00.750Z",
            "0000000000000003",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )
    # --- Anomalous tool calls (N+1 pattern) ---
    # Normal: 2-3 tool calls.  Degraded: 8 redundant inventory checks
    base_ms = 800
    for i in range(8):
        sid = f"00000000000000{i + 5:02x}"
        s = f"2026-02-18T08:15:00.{base_ms + i * 120:03d}Z"
        e = f"2026-02-18T08:15:00.{base_ms + i * 120 + 100:03d}Z"
        spans.append(
            _span(
                sid,
                "tool:check_availability",
                s,
                e,
                "0000000000000003",
                attrs={
                    "gen_ai.tool.name": "check_availability",
                    "gen_ai.tool.call.id": f"call_inv_{i:03d}",
                },
            )
        )
    # Extra LLM call after inventory checks
    spans.append(
        _span(
            "000000000000000d",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:01.800Z",
            "2026-02-18T08:15:02.100Z",
            "0000000000000003",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )
    # Anomalous delegation to Fulfillment Agent
    spans.append(
        _span(
            "000000000000000e",
            "fulfillment",
            "2026-02-18T08:15:02.150Z",
            "2026-02-18T08:15:03.200Z",
            "0000000000000003",
            attrs={
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": "fulfillment",
            },
        )
    )
    # Fulfillment LLM call
    spans.append(
        _span(
            "000000000000000f",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:02.200Z",
            "2026-02-18T08:15:02.500Z",
            "000000000000000e",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )
    # validate_coupon tool call (429 error)
    spans.append(
        _span(
            "0000000000000010",
            "tool:validate_coupon",
            "2026-02-18T08:15:02.550Z",
            "2026-02-18T08:15:02.950Z",
            "000000000000000e",
            status="ERROR",
            attrs={
                "gen_ai.tool.name": "validate_coupon",
                "gen_ai.tool.call.id": "call_coupon_001",
            },
        )
    )
    # Payment MCP span
    spans.append(
        _span(
            "0000000000000011",
            "payment-mcp",
            "2026-02-18T08:15:03.000Z",
            "2026-02-18T08:15:03.400Z",
            "000000000000000e",
            status="ERROR",
            attrs={
                "gen_ai.operation.name": "invoke_tool",
                "gen_ai.agent.name": "payment-mcp",
            },
        )
    )
    # Checkout Agent span
    spans.append(
        _span(
            "0000000000000012",
            "checkout",
            "2026-02-18T08:15:03.650Z",
            "2026-02-18T08:15:04.500Z",
            "0000000000000001",
            attrs={
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": "checkout",
            },
        )
    )
    # Checkout LLM call
    spans.append(
        _span(
            "0000000000000013",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:03.700Z",
            "2026-02-18T08:15:04.000Z",
            "0000000000000012",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )
    # Checkout tool call
    spans.append(
        _span(
            "0000000000000014",
            "tool:process_payment",
            "2026-02-18T08:15:04.050Z",
            "2026-02-18T08:15:04.350Z",
            "0000000000000012",
            attrs={
                "gen_ai.tool.name": "process_payment",
                "gen_ai.tool.call.id": "call_pay_001",
            },
        )
    )
    # Final orchestrator LLM call (response generation)
    spans.append(
        _span(
            "0000000000000015",
            "llm:gemini-2.5-flash",
            "2026-02-18T08:15:04.400Z",
            "2026-02-18T08:15:04.750Z",
            "0000000000000001",
            attrs={"gen_ai.request.model": "gemini-2.5-flash"},
        )
    )

    return spans


# ---------------------------------------------------------------------------
# Dashboard data payloads
# ---------------------------------------------------------------------------

_INCIDENT_TIMELINE_DATA: dict[str, Any] = {
    "incident_id": "inc-cymbal-2026-001",
    "title": "Cymbal Assistant Checkout Latency Spike",
    "start_time": "2026-02-18T02:15:00Z",
    "end_time": "2026-02-20T15:45:00Z",
    "status": "resolved",
    "events": [
        {
            "id": "evt-1",
            "timestamp": "2026-02-18T02:15:00Z",
            "type": "deployment",
            "title": "Release v2.4.1 deployed",
            "description": "Product Discovery Agent prompt updated",
            "severity": "info",
            "metadata": {"version": "v2.4.1"},
            "is_correlated": True,
        },
        {
            "id": "evt-2",
            "timestamp": "2026-02-18T02:30:00Z",
            "type": "incident",
            "title": "Tool call volume anomaly",
            "description": "",
            "severity": "high",
            "metadata": {},
            "is_correlated": True,
        },
        {
            "id": "evt-3",
            "timestamp": "2026-02-18T08:00:00Z",
            "type": "alert",
            "title": "Payment MCP rate limiting (429s)",
            "description": "",
            "severity": "critical",
            "metadata": {},
            "is_correlated": True,
        },
        {
            "id": "evt-4",
            "timestamp": "2026-02-20T11:30:00Z",
            "type": "alert",
            "title": "Anomalous tool call volume detected",
            "description": "",
            "severity": "critical",
            "metadata": {},
            "is_correlated": True,
        },
        {
            "id": "evt-5",
            "timestamp": "2026-02-20T15:45:00Z",
            "type": "recovery",
            "title": "Rollback to v2.4.0",
            "description": "",
            "severity": "info",
            "metadata": {},
            "is_correlated": True,
        },
    ],
    "root_cause": (
        "Bad prompt change in Product Discovery Agent (v2.4.1) caused "
        "excessive tool calls to Inventory and Payment MCP servers"
    ),
    "ttd_seconds": 205500,
    "ttm_seconds": 220800,
}

_METRIC_CHART_DATA: dict[str, Any] = {
    "series": [
        {
            "metric_name": "Agent Response Latency (ms)",
            "labels": {"agent": "product-discovery", "version": "v2.4.1"},
            "points": [
                {"timestamp": "2026-02-17T00:00:00Z", "value": 520.0},
                {"timestamp": "2026-02-18T00:00:00Z", "value": 540.0},
                {"timestamp": "2026-02-18T03:00:00Z", "value": 1800.0},
                {"timestamp": "2026-02-18T06:00:00Z", "value": 2900.0},
                {"timestamp": "2026-02-18T12:00:00Z", "value": 3200.0},
                {"timestamp": "2026-02-19T00:00:00Z", "value": 3150.0},
                {"timestamp": "2026-02-20T12:00:00Z", "value": 3100.0},
                {"timestamp": "2026-02-20T16:00:00Z", "value": 800.0},
                {"timestamp": "2026-02-21T00:00:00Z", "value": 530.0},
            ],
        },
        {
            "metric_name": "Tool Calls per Request",
            "labels": {"agent": "product-discovery"},
            "points": [
                {"timestamp": "2026-02-17T00:00:00Z", "value": 6.0},
                {"timestamp": "2026-02-18T03:00:00Z", "value": 12.0},
                {"timestamp": "2026-02-18T12:00:00Z", "value": 18.0},
                {"timestamp": "2026-02-20T16:00:00Z", "value": 7.0},
                {"timestamp": "2026-02-21T00:00:00Z", "value": 6.0},
            ],
        },
    ],
}

_TRACE_WATERFALL_DATA: dict[str, Any] = {
    "trace_id": _TRACE_ID,
    "spans": _waterfall_spans(),
}

_LOG_ENTRIES_DATA: dict[str, Any] = {
    "entries": [
        {
            "timestamp": "2026-02-18T08:15:32Z",
            "severity": "ERROR",
            "text_payload": (
                "Payment MCP returned 429 Too Many Requests for validate_coupon"
            ),
            "json_payload": None,
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "cymbal-assistant"},
            },
            "trace_id": None,
        },
        {
            "timestamp": "2026-02-18T08:15:33Z",
            "severity": "WARNING",
            "text_payload": (
                "Product Discovery Agent making unexpected calls "
                "to Inventory MCP check_availability"
            ),
            "json_payload": None,
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "cymbal-assistant"},
            },
            "trace_id": None,
        },
        {
            "timestamp": "2026-02-18T08:15:34Z",
            "severity": "ERROR",
            "text_payload": (
                "Tool call budget exceeded: 18 calls in single turn (threshold: 10)"
            ),
            "json_payload": None,
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "cymbal-assistant"},
            },
            "trace_id": None,
        },
        {
            "timestamp": "2026-02-18T08:15:35Z",
            "severity": "INFO",
            "text_payload": (
                "Product Discovery Agent delegated to Fulfillment Agent "
                "(unexpected delegation pattern)"
            ),
            "json_payload": None,
            "resource": {
                "type": "cloud_run_revision",
                "labels": {"service_name": "cymbal-assistant"},
            },
            "trace_id": None,
        },
    ],
}

_COUNCIL_SYNTHESIS_DATA: dict[str, Any] = {
    "synthesis": (
        "## Root Cause Analysis\n\n"
        "The checkout latency spike was caused by a prompt change in the "
        "Product Discovery Agent (v2.4.1) that introduced an N+1 tool-call "
        "anti-pattern. Each user query now triggers 8 redundant "
        "`check_availability` calls to the Inventory MCP and unexpected "
        "delegation to the Fulfillment Agent, which in turn overwhelms the "
        "Payment MCP with `validate_coupon` requests causing 429 rate-limit "
        "errors.\n\n"
        "### Impact\n"
        "- P99 latency increased from 800ms to 4500ms\n"
        "- Error rate rose from 0.1% to 8.5%\n"
        "- Payment MCP availability degraded\n\n"
        "### Recommendation\n"
        "Immediately roll back to v2.4.0 and add tool-call budget guardrails."
    ),
    "overall_severity": "critical",
    "overall_confidence": 0.92,
    "mode": "standard",
    "rounds": 1,
    "panels": [
        {
            "panel": "trace",
            "summary": (
                "Degraded traces show 18-22 spans (normal: 8-12). "
                "N+1 tool calls to Inventory and Payment MCPs."
            ),
            "severity": "critical",
            "confidence": 0.95,
            "evidence": ["trace:a1b2c3d4..."],
            "recommended_actions": ["Roll back to v2.4.0"],
        },
        {
            "panel": "metrics",
            "summary": (
                "P99 latency spiked from 800ms to 4500ms after v2.4.1 "
                "deploy. Error rate increased from 0.1% to 8.5%."
            ),
            "severity": "critical",
            "confidence": 0.93,
            "evidence": ["metric:latency_p99"],
            "recommended_actions": ["Set up latency alerts"],
        },
        {
            "panel": "logs",
            "summary": (
                "429 Too Many Requests errors from Payment MCP. "
                "Unexpected delegation to Fulfillment Agent logged."
            ),
            "severity": "warning",
            "confidence": 0.88,
            "evidence": ["log:payment_429"],
            "recommended_actions": ["Add rate limiting on agent side"],
        },
        {
            "panel": "alerts",
            "summary": (
                "4 active alerts triggered. Payment MCP rate limiting "
                "is the highest severity."
            ),
            "severity": "critical",
            "confidence": 0.90,
            "evidence": ["alert:payment_rate_limit"],
            "recommended_actions": ["Investigate prompt changes"],
        },
    ],
    "critic_report": None,
    "activity_graph": None,
}

_METRICS_DASHBOARD_DATA: dict[str, Any] = {
    "metrics": [
        {
            "id": "m1",
            "name": "Response Latency P99",
            "unit": "ms",
            "current_value": 3200.0,
            "previous_value": 800.0,
            "threshold": 1000.0,
            "history": [
                {"timestamp": "2026-02-17T00:00:00Z", "value": 800.0},
                {"timestamp": "2026-02-18T06:00:00Z", "value": 3200.0},
            ],
            "status": "critical",
            "anomaly_description": "300% increase after v2.4.1 deploy",
        },
        {
            "id": "m2",
            "name": "Error Rate",
            "unit": "%",
            "current_value": 8.5,
            "previous_value": 0.1,
            "threshold": 5.0,
            "history": [],
            "status": "critical",
        },
        {
            "id": "m3",
            "name": "Tool Calls/Request",
            "unit": "count",
            "current_value": 18.0,
            "previous_value": 6.0,
            "threshold": 12.0,
            "history": [],
            "status": "warning",
        },
        {
            "id": "m4",
            "name": "Token Usage/Request",
            "unit": "tokens",
            "current_value": 4200.0,
            "previous_value": 2100.0,
            "threshold": None,
            "history": [],
            "status": "warning",
        },
    ],
}

_REMEDIATION_PLAN_DATA: dict[str, Any] = {
    "summary": (
        "Roll back Product Discovery Agent to v2.4.0 to resolve excessive "
        "tool calls and Payment MCP rate limiting"
    ),
    "severity": "critical",
    "confidence": 0.95,
    "actions": [
        {
            "id": "r1",
            "title": "Rollback to v2.4.0",
            "description": (
                "Revert the Product Discovery Agent system prompt "
                "to the previous version"
            ),
            "step": 1,
            "estimated_duration": "5m",
            "requires_approval": True,
            "kubectl_command": None,
            "gcloud_command": (
                "gcloud ai agents versions rollback cymbal-assistant "
                "--version=v2.4.0 --region=us-central1"
            ),
        },
        {
            "id": "r2",
            "title": "Verify recovery",
            "description": (
                "Monitor latency and error rate for 15 minutes after rollback"
            ),
            "step": 2,
            "estimated_duration": "15m",
            "requires_approval": False,
        },
        {
            "id": "r3",
            "title": "Add prompt change guardrails",
            "description": (
                "Implement tool call budget limits and delegation whitelist per agent"
            ),
            "step": 3,
            "estimated_duration": "2h",
            "requires_approval": False,
        },
    ],
}


# ---------------------------------------------------------------------------
# Council graph event data
# ---------------------------------------------------------------------------


def _council_graph_event() -> dict[str, Any]:
    """Build the full council_graph event for Turn 3."""
    base_ts = "2026-02-20T12:00:"
    return {
        "type": "council_graph",
        "investigation_id": _INVESTIGATION_ID,
        "mode": "standard",
        "started_at": f"{base_ts}00Z",
        "completed_at": f"{base_ts}45Z",
        "debate_rounds": 0,
        "total_tool_calls": 12,
        "total_llm_calls": 8,
        "agents": [
            {
                "agent_id": "root",
                "agent_name": "auto-sre",
                "agent_type": "root",
                "parent_id": None,
                "status": "completed",
                "started_at": f"{base_ts}00Z",
                "completed_at": f"{base_ts}45Z",
                "tool_calls": [],
                "llm_calls": [
                    {
                        "call_id": "llm-1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 2500,
                        "output_tokens": 800,
                        "duration_ms": 1200,
                        "timestamp": f"{base_ts}01Z",
                    },
                ],
                "output_summary": "Orchestrated investigation",
            },
            {
                "agent_id": "trace-panel",
                "agent_name": "Trace Analyst",
                "agent_type": "panel",
                "parent_id": "root",
                "status": "completed",
                "started_at": f"{base_ts}02Z",
                "completed_at": f"{base_ts}18Z",
                "tool_calls": [
                    {
                        "call_id": "tc-t1",
                        "tool_name": "fetch_trace",
                        "duration_ms": 450,
                        "timestamp": f"{base_ts}03Z",
                    },
                    {
                        "call_id": "tc-t2",
                        "tool_name": "compare_trace_spans",
                        "duration_ms": 320,
                        "timestamp": f"{base_ts}08Z",
                    },
                    {
                        "call_id": "tc-t3",
                        "tool_name": "analyze_trace_patterns",
                        "duration_ms": 280,
                        "timestamp": f"{base_ts}12Z",
                    },
                ],
                "llm_calls": [
                    {
                        "call_id": "llm-t1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 3200,
                        "output_tokens": 600,
                        "duration_ms": 900,
                        "timestamp": f"{base_ts}15Z",
                    },
                ],
                "output_summary": (
                    "Degraded traces show 18-22 spans with N+1 tool call pattern"
                ),
            },
            {
                "agent_id": "metrics-panel",
                "agent_name": "Metrics Analyst",
                "agent_type": "panel",
                "parent_id": "root",
                "status": "completed",
                "started_at": f"{base_ts}02Z",
                "completed_at": f"{base_ts}16Z",
                "tool_calls": [
                    {
                        "call_id": "tc-m1",
                        "tool_name": "list_time_series",
                        "duration_ms": 380,
                        "timestamp": f"{base_ts}03Z",
                    },
                    {
                        "call_id": "tc-m2",
                        "tool_name": "detect_metric_anomalies",
                        "duration_ms": 420,
                        "timestamp": f"{base_ts}08Z",
                    },
                ],
                "llm_calls": [
                    {
                        "call_id": "llm-m1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 2800,
                        "output_tokens": 550,
                        "duration_ms": 850,
                        "timestamp": f"{base_ts}12Z",
                    },
                ],
                "output_summary": ("P99 latency spiked 300% after v2.4.1 deploy"),
            },
            {
                "agent_id": "logs-panel",
                "agent_name": "Log Analyst",
                "agent_type": "panel",
                "parent_id": "root",
                "status": "completed",
                "started_at": f"{base_ts}02Z",
                "completed_at": f"{base_ts}15Z",
                "tool_calls": [
                    {
                        "call_id": "tc-l1",
                        "tool_name": "list_log_entries",
                        "duration_ms": 350,
                        "timestamp": f"{base_ts}03Z",
                    },
                    {
                        "call_id": "tc-l2",
                        "tool_name": "analyze_log_patterns",
                        "duration_ms": 290,
                        "timestamp": f"{base_ts}07Z",
                    },
                ],
                "llm_calls": [
                    {
                        "call_id": "llm-l1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 2200,
                        "output_tokens": 480,
                        "duration_ms": 780,
                        "timestamp": f"{base_ts}10Z",
                    },
                ],
                "output_summary": (
                    "429 errors from Payment MCP; unexpected delegation patterns"
                ),
            },
            {
                "agent_id": "alerts-panel",
                "agent_name": "Alert Analyst",
                "agent_type": "panel",
                "parent_id": "root",
                "status": "completed",
                "started_at": f"{base_ts}02Z",
                "completed_at": f"{base_ts}14Z",
                "tool_calls": [
                    {
                        "call_id": "tc-a1",
                        "tool_name": "list_alerts",
                        "duration_ms": 300,
                        "timestamp": f"{base_ts}03Z",
                    },
                    {
                        "call_id": "tc-a2",
                        "tool_name": "get_alert_details",
                        "duration_ms": 250,
                        "timestamp": f"{base_ts}06Z",
                    },
                ],
                "llm_calls": [
                    {
                        "call_id": "llm-a1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 1800,
                        "output_tokens": 420,
                        "duration_ms": 720,
                        "timestamp": f"{base_ts}09Z",
                    },
                ],
                "output_summary": (
                    "4 active alerts; Payment MCP rate limiting is highest severity"
                ),
            },
            {
                "agent_id": "synthesizer",
                "agent_name": "Synthesizer",
                "agent_type": "synthesizer",
                "parent_id": "root",
                "status": "completed",
                "started_at": f"{base_ts}20Z",
                "completed_at": f"{base_ts}42Z",
                "tool_calls": [],
                "llm_calls": [
                    {
                        "call_id": "llm-s1",
                        "model": "gemini-2.5-flash",
                        "input_tokens": 4500,
                        "output_tokens": 1200,
                        "duration_ms": 1500,
                        "timestamp": f"{base_ts}22Z",
                    },
                ],
                "output_summary": (
                    "Root cause: bad prompt change in v2.4.1 causing N+1 tool calls"
                ),
            },
        ],
    }


# ---------------------------------------------------------------------------
# Turn builders
# ---------------------------------------------------------------------------


def _build_turn_1() -> list[str]:
    """Turn 1 — 'Investigate the checkout latency spike'."""
    events: list[str] = []

    # Session init
    events.append(
        _event(
            {
                "type": "session",
                "session_id": _SESSION_ID,
            }
        )
    )

    # Opening text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "I'll investigate the checkout latency issue in Cymbal Assistant. "
                    "Let me start by checking active alerts and recent metrics to "
                    "understand the scope of the problem."
                ),
            }
        )
    )

    # Agent activity — root started
    events.append(
        _event(
            {
                "type": "agent_activity",
                "investigation_id": _INVESTIGATION_ID,
                "agent": {
                    "agent_id": "root",
                    "agent_name": "auto-sre",
                    "agent_type": "root",
                    "parent_id": None,
                    "status": "running",
                    "started_at": "2026-02-20T12:00:00Z",
                    "completed_at": None,
                    "tool_calls": [],
                    "llm_calls": [],
                    "output_summary": "",
                },
            }
        )
    )

    # Tool call: list_alerts
    events.append(
        _event(
            {
                "type": "tool-call",
                "tool_name": "list_alerts",
                "args": {"project_id": _PROJECT_ID},
                "id": "call_001",
            }
        )
    )

    # Tool response: list_alerts
    events.append(
        _event(
            {
                "type": "tool-response",
                "tool_name": "list_alerts",
                "result": {
                    "status": "success",
                    "alerts": [
                        {
                            "name": "Payment MCP 429 Rate Limiting",
                            "severity": "CRITICAL",
                            "state": "ACTIVE",
                            "started": "2026-02-18T08:00:00Z",
                        },
                        {
                            "name": "Checkout Latency P99 > 3s",
                            "severity": "CRITICAL",
                            "state": "ACTIVE",
                            "started": "2026-02-18T03:00:00Z",
                        },
                        {
                            "name": "Tool Call Volume Anomaly",
                            "severity": "WARNING",
                            "state": "ACTIVE",
                            "started": "2026-02-18T02:30:00Z",
                        },
                        {
                            "name": "Agent Error Rate > 5%",
                            "severity": "CRITICAL",
                            "state": "ACTIVE",
                            "started": "2026-02-18T06:00:00Z",
                        },
                    ],
                },
                "id": "call_001",
            }
        )
    )

    # Dashboard: incident timeline
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "alerts",
                "widget_type": "x-sre-incident-timeline",
                "tool_name": "list_alerts",
                "data": _INCIDENT_TIMELINE_DATA,
            }
        )
    )

    # Tool call: list_time_series
    events.append(
        _event(
            {
                "type": "tool-call",
                "tool_name": "list_time_series",
                "args": {
                    "project_id": _PROJECT_ID,
                    "metric_type": "custom.googleapis.com/agent/response_latency",
                    "interval_hours": 96,
                },
                "id": "call_002",
            }
        )
    )

    # Tool response: list_time_series
    events.append(
        _event(
            {
                "type": "tool-response",
                "tool_name": "list_time_series",
                "result": {
                    "status": "success",
                    "series_count": 2,
                    "series": _METRIC_CHART_DATA["series"],
                },
                "id": "call_002",
            }
        )
    )

    # Dashboard: metric chart
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "metrics",
                "widget_type": "x-sre-metric-chart",
                "tool_name": "list_time_series",
                "data": _METRIC_CHART_DATA,
            }
        )
    )

    # Summary text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "I found **4 active alerts** and a significant latency spike "
                    "correlated with the v2.4.1 deployment on Feb 18. The P99 latency "
                    "jumped from ~520ms to over 3200ms, and tool calls per request "
                    "tripled from 6 to 18. Let me dig into the traces next."
                ),
            }
        )
    )

    return events


def _build_turn_2() -> list[str]:
    """Turn 2 — 'Show me the traces'."""
    events: list[str] = []

    # Opening text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "Let me analyze the distributed traces from the degraded period "
                    "and check the corresponding logs for error patterns."
                ),
            }
        )
    )

    # Tool call: fetch_trace
    events.append(
        _event(
            {
                "type": "tool-call",
                "tool_name": "fetch_trace",
                "args": {
                    "project_id": _PROJECT_ID,
                    "trace_id": _TRACE_ID,
                },
                "id": "call_003",
            }
        )
    )

    # Tool response: fetch_trace (degraded trace with 22 spans)
    events.append(
        _event(
            {
                "type": "tool-response",
                "tool_name": "fetch_trace",
                "result": {
                    "status": "success",
                    "trace_id": _TRACE_ID,
                    "span_count": len(_TRACE_WATERFALL_DATA["spans"]),
                    "duration_ms": 4800,
                    "has_errors": True,
                },
                "id": "call_003",
            }
        )
    )

    # Dashboard: trace waterfall
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "traces",
                "widget_type": "x-sre-trace-waterfall",
                "tool_name": "fetch_trace",
                "data": _TRACE_WATERFALL_DATA,
            }
        )
    )

    # Tool call: list_log_entries
    events.append(
        _event(
            {
                "type": "tool-call",
                "tool_name": "list_log_entries",
                "args": {
                    "project_id": _PROJECT_ID,
                    "filter_str": (
                        'resource.type="cloud_run_revision" '
                        "AND severity>=WARNING "
                        'AND timestamp>="2026-02-18T08:00:00Z"'
                    ),
                    "page_size": 50,
                },
                "id": "call_004",
            }
        )
    )

    # Tool response: list_log_entries
    events.append(
        _event(
            {
                "type": "tool-response",
                "tool_name": "list_log_entries",
                "result": {
                    "status": "success",
                    "entry_count": len(_LOG_ENTRIES_DATA["entries"]),
                    "entries": _LOG_ENTRIES_DATA["entries"],
                },
                "id": "call_004",
            }
        )
    )

    # Dashboard: log entries
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "logs",
                "widget_type": "x-sre-log-entries-viewer",
                "tool_name": "list_log_entries",
                "data": _LOG_ENTRIES_DATA,
            }
        )
    )

    # Summary text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "The trace shows **22 spans** (normal is 8-12). The Product "
                    "Discovery Agent is making 8 redundant `check_availability` calls "
                    "to the Inventory MCP (N+1 pattern) and unexpectedly delegating "
                    "to the Fulfillment Agent. The Payment MCP is returning 429 errors "
                    "from the resulting `validate_coupon` overload."
                ),
            }
        )
    )

    return events


def _build_turn_3() -> list[str]:
    """Turn 3 — 'What's the root cause?'."""
    events: list[str] = []

    # Opening text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "Based on my analysis across all signals — traces, metrics, "
                    "logs, and alerts — here is the synthesized root cause assessment "
                    "from the Council of Experts."
                ),
            }
        )
    )

    # Dashboard: council synthesis
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "council",
                "widget_type": "x-sre-council-synthesis",
                "tool_name": "run_council_investigation",
                "data": _COUNCIL_SYNTHESIS_DATA,
            }
        )
    )

    # Council graph event
    events.append(_event(_council_graph_event()))

    # Dashboard: golden signals metrics dashboard
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "metrics",
                "widget_type": "x-sre-metrics-dashboard",
                "tool_name": "get_golden_signals",
                "data": _METRICS_DASHBOARD_DATA,
            }
        )
    )

    # Memory event: pattern learned
    events.append(
        _event(
            {
                "type": "memory",
                "action": "pattern_learned",
                "category": "pattern",
                "title": "Prompt change detection",
                "description": (
                    "Agent prompt changes (v2.4.1) can cause cascading failures "
                    "through N+1 tool call patterns. Monitor tool call volume after "
                    "any prompt or model update."
                ),
                "tool_name": None,
                "metadata": {
                    "trigger": "v2.4.1 deploy",
                    "signal_correlation": [
                        "latency_spike",
                        "tool_call_anomaly",
                        "rate_limiting",
                    ],
                },
                "timestamp": "2026-02-20T12:01:00Z",
            }
        )
    )

    # Root cause text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "**Root cause**: The v2.4.1 release changed the Product Discovery "
                    "Agent's system prompt, introducing an N+1 tool-call anti-pattern. "
                    "Each user query now triggers 8 redundant `check_availability` "
                    "calls and unexpected delegation to the Fulfillment Agent. This "
                    "cascades into Payment MCP rate limiting (429s), pushing P99 "
                    "latency from 800ms to 4500ms and error rate from 0.1% to 8.5%.\n\n"
                    "**Confidence**: 92% across all panels (trace: 95%, metrics: 93%, "
                    "logs: 88%, alerts: 90%)."
                ),
            }
        )
    )

    return events


def _build_turn_4() -> list[str]:
    """Turn 4 — 'How do I fix it?'."""
    events: list[str] = []

    # Opening text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "Here's my remediation plan based on the root cause analysis. "
                    "The primary action requires approval before execution."
                ),
            }
        )
    )

    # Dashboard: remediation plan
    events.append(
        _event(
            {
                "type": "dashboard",
                "category": "remediation",
                "widget_type": "x-sre-remediation-plan",
                "tool_name": "generate_remediation_suggestions",
                "data": _REMEDIATION_PLAN_DATA,
            }
        )
    )

    # Trace info event
    events.append(
        _event(
            {
                "type": "trace_info",
                "trace_id": _TRACE_ID,
                "project_id": _PROJECT_ID,
                "trace_url": None,
            }
        )
    )

    # Closing text
    events.append(
        _event(
            {
                "type": "text",
                "content": (
                    "The primary action is to **roll back to v2.4.0** using:\n\n"
                    "```\n"
                    "gcloud ai agents versions rollback cymbal-assistant "
                    "--version=v2.4.0 --region=us-central1\n"
                    "```\n\n"
                    "After rollback, monitor latency and error rate for 15 minutes to "
                    "confirm recovery. As a follow-up, implement tool-call budget "
                    "limits and delegation whitelists to prevent similar cascading "
                    "failures from future prompt changes."
                ),
            }
        )
    )

    return events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_demo_turns() -> list[list[str]]:
    """Return 4 turns of pre-recorded investigation events.

    Each turn is a list of NDJSON lines (strings).  The four turns tell
    the story of investigating a checkout latency spike in the Cymbal
    Assistant demo application:

    1. Investigate alerts and metrics
    2. Analyze traces and logs
    3. Synthesize root cause (council)
    4. Remediation plan

    Every event type supported by the frontend is emitted at least once:
    session, text, tool-call, tool-response, dashboard (7 widget types),
    agent_activity, council_graph, memory, and trace_info.
    """
    return [
        _build_turn_1(),
        _build_turn_2(),
        _build_turn_3(),
        _build_turn_4(),
    ]


def get_demo_suggestions() -> list[str]:
    """Return follow-up suggestions for the demo."""
    return [
        "Show me the degraded traces",
        "What changed in the last deployment?",
        "Compare before and after the release",
        "Generate a postmortem report",
    ]
