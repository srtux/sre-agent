"""Deterministic demo data generator for the Cymbal Shops AI Shopping Assistant.

Produces ~400 traces across ~80 sessions over a 7-day window.  All data is
generated lazily on first access and cached.  The output formats match exactly
what the AgentOps UI expects from the backend API endpoints.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sre_agent.tools.synthetic.cymbal_assistant import (
    AGENTS,
    ANOMALOUS_DELEGATION,
    ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY,
    DEMO_USERS,
    INCIDENT_TIMELINE,
    JOURNEY_TEMPLATES,
    REASONING_ENGINE_ID,
    RESOURCE_ATTRIBUTES,
    JourneyTemplate,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BASE_TIME = datetime(2026, 2, 15, 0, 0, 0, tzinfo=timezone.utc)
_WINDOW_DAYS = 7
_END_TIME = _BASE_TIME + timedelta(days=_WINDOW_DAYS)

# Incident window boundaries (derived from INCIDENT_TIMELINE)
_INCIDENT_START = _BASE_TIME + timedelta(
    days=int(str(INCIDENT_TIMELINE[0]["day"])),
    hours=int(str(INCIDENT_TIMELINE[0]["hour"])),
    minutes=int(str(INCIDENT_TIMELINE[0]["minute"])),
)
_INCIDENT_END = _BASE_TIME + timedelta(
    days=int(str(INCIDENT_TIMELINE[4]["day"])),
    hours=int(str(INCIDENT_TIMELINE[4]["hour"])),
    minutes=int(str(INCIDENT_TIMELINE[4]["minute"])),
)

# Normal span timing ranges (ms)
_NORMAL_LLM_DURATION = (50, 120)
_NORMAL_TOOL_DURATION = (40, 200)
_NORMAL_AGENT_OVERHEAD = (15, 40)

# Degraded span timing (ms)
_DEGRADED_TOOL_DURATION = (150, 280)

# Token ranges
_INPUT_TOKENS_RANGE = (150, 600)
_OUTPUT_TOKENS_RANGE = (80, 400)

# Node colours for Sankey
_SANKEY_COLORS: dict[str, str] = {
    "cymbal-assistant": "#6366f1",
    "product-discovery": "#22c55e",
    "personalization": "#f59e0b",
    "checkout": "#3b82f6",
    "order-management": "#a855f7",
    "fulfillment": "#ef4444",
    "support": "#ec4899",
    # Generic fallbacks
    "llm": "#94a3b8",
    "tool": "#64748b",
}


# ---------------------------------------------------------------------------
# Span-tree templates per journey type
# ---------------------------------------------------------------------------


def _span_tree_for_journey(
    journey_type: str, agents_involved: list[str]
) -> list[dict[str, Any]]:
    """Return a template span tree for a given journey type.

    Each node is ``{"name": str, "op": str, "agent": str, "kind": "llm"|"tool"|"agent",
    "children": [...]}``.  Durations are filled in at generation time.
    """
    if journey_type == "search_browse_buy":
        return [
            {
                "name": "classify_intent",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
            {
                "name": "product-discovery",
                "op": "invoke_agent",
                "agent": "product-discovery",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_search",
                        "op": "generate_content",
                        "agent": "product-discovery",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "search_products",
                        "op": "execute_tool",
                        "agent": "product-discovery",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "personalization",
                        "op": "invoke_agent",
                        "agent": "personalization",
                        "kind": "agent",
                        "children": [
                            {
                                "name": "get_customer_profile",
                                "op": "execute_tool",
                                "agent": "personalization",
                                "kind": "tool",
                                "children": [],
                            },
                            {
                                "name": "get_personalized_recs",
                                "op": "execute_tool",
                                "agent": "personalization",
                                "kind": "tool",
                                "children": [],
                            },
                        ],
                    },
                    {
                        "name": "get_product_details",
                        "op": "execute_tool",
                        "agent": "product-discovery",
                        "kind": "tool",
                        "children": [],
                    },
                ],
            },
            {
                "name": "format_response",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
        ]
    if journey_type == "search_compare":
        return [
            {
                "name": "classify_intent",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
            {
                "name": "product-discovery",
                "op": "invoke_agent",
                "agent": "product-discovery",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_search",
                        "op": "generate_content",
                        "agent": "product-discovery",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "search_products",
                        "op": "execute_tool",
                        "agent": "product-discovery",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "get_reviews",
                        "op": "execute_tool",
                        "agent": "product-discovery",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "personalization",
                        "op": "invoke_agent",
                        "agent": "personalization",
                        "kind": "agent",
                        "children": [
                            {
                                "name": "get_customer_profile",
                                "op": "execute_tool",
                                "agent": "personalization",
                                "kind": "tool",
                                "children": [],
                            },
                            {
                                "name": "get_similar_products",
                                "op": "execute_tool",
                                "agent": "personalization",
                                "kind": "tool",
                                "children": [],
                            },
                        ],
                    },
                ],
            },
            {
                "name": "format_response",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
        ]
    if journey_type == "order_tracking":
        return [
            {
                "name": "classify_intent",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
            {
                "name": "order-management",
                "op": "invoke_agent",
                "agent": "order-management",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_lookup",
                        "op": "generate_content",
                        "agent": "order-management",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "get_order_status",
                        "op": "execute_tool",
                        "agent": "order-management",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "fulfillment",
                        "op": "invoke_agent",
                        "agent": "fulfillment",
                        "kind": "agent",
                        "children": [
                            {
                                "name": "track_shipment",
                                "op": "execute_tool",
                                "agent": "fulfillment",
                                "kind": "tool",
                                "children": [],
                            },
                            {
                                "name": "get_delivery_estimate",
                                "op": "execute_tool",
                                "agent": "fulfillment",
                                "kind": "tool",
                                "children": [],
                            },
                        ],
                    },
                ],
            },
            {
                "name": "format_response",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
        ]
    if journey_type == "return_refund":
        return [
            {
                "name": "classify_intent",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
            {
                "name": "order-management",
                "op": "invoke_agent",
                "agent": "order-management",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_return",
                        "op": "generate_content",
                        "agent": "order-management",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "get_order_status",
                        "op": "execute_tool",
                        "agent": "order-management",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "create_return",
                        "op": "execute_tool",
                        "agent": "order-management",
                        "kind": "tool",
                        "children": [],
                    },
                ],
            },
            {
                "name": "support",
                "op": "invoke_agent",
                "agent": "support",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_support",
                        "op": "generate_content",
                        "agent": "support",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "search_knowledge_base",
                        "op": "execute_tool",
                        "agent": "support",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "create_ticket",
                        "op": "execute_tool",
                        "agent": "support",
                        "kind": "tool",
                        "children": [],
                    },
                ],
            },
            {
                "name": "format_response",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
        ]
    if journey_type == "support_question":
        return [
            {
                "name": "classify_intent",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
            {
                "name": "support",
                "op": "invoke_agent",
                "agent": "support",
                "kind": "agent",
                "children": [
                    {
                        "name": "plan_support",
                        "op": "generate_content",
                        "agent": "support",
                        "kind": "llm",
                        "children": [],
                    },
                    {
                        "name": "search_knowledge_base",
                        "op": "execute_tool",
                        "agent": "support",
                        "kind": "tool",
                        "children": [],
                    },
                    {
                        "name": "get_customer_profile",
                        "op": "execute_tool",
                        "agent": "support",
                        "kind": "tool",
                        "children": [],
                    },
                ],
            },
            {
                "name": "format_response",
                "op": "generate_content",
                "agent": "cymbal-assistant",
                "kind": "llm",
                "children": [],
            },
        ]
    # browse_abandon_return
    return [
        {
            "name": "classify_intent",
            "op": "generate_content",
            "agent": "cymbal-assistant",
            "kind": "llm",
            "children": [],
        },
        {
            "name": "product-discovery",
            "op": "invoke_agent",
            "agent": "product-discovery",
            "kind": "agent",
            "children": [
                {
                    "name": "plan_search",
                    "op": "generate_content",
                    "agent": "product-discovery",
                    "kind": "llm",
                    "children": [],
                },
                {
                    "name": "search_products",
                    "op": "execute_tool",
                    "agent": "product-discovery",
                    "kind": "tool",
                    "children": [],
                },
                {
                    "name": "personalization",
                    "op": "invoke_agent",
                    "agent": "personalization",
                    "kind": "agent",
                    "children": [
                        {
                            "name": "get_customer_profile",
                            "op": "execute_tool",
                            "agent": "personalization",
                            "kind": "tool",
                            "children": [],
                        },
                        {
                            "name": "get_personalized_recs",
                            "op": "execute_tool",
                            "agent": "personalization",
                            "kind": "tool",
                            "children": [],
                        },
                    ],
                },
            ],
        },
        {
            "name": "checkout",
            "op": "invoke_agent",
            "agent": "checkout",
            "kind": "agent",
            "children": [
                {
                    "name": "plan_checkout",
                    "op": "generate_content",
                    "agent": "checkout",
                    "kind": "llm",
                    "children": [],
                },
                {
                    "name": "add_to_cart",
                    "op": "execute_tool",
                    "agent": "checkout",
                    "kind": "tool",
                    "children": [],
                },
                {
                    "name": "get_cart",
                    "op": "execute_tool",
                    "agent": "checkout",
                    "kind": "tool",
                    "children": [],
                },
            ],
        },
        {
            "name": "format_response",
            "op": "generate_content",
            "agent": "cymbal-assistant",
            "kind": "llm",
            "children": [],
        },
    ]


def _inject_anomalous_spans(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Inject anomalous tool calls and agent delegation into the span tree.

    Modifies the first agent-kind child that is product-discovery (if any).
    """
    import copy

    tree = copy.deepcopy(tree)
    for node in tree:
        if node["kind"] == "agent" and node["agent"] == "product-discovery":
            # Inject anomalous tools before the last child
            anomalous: list[dict[str, Any]] = []
            for tool_name in ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY:
                repeat = 5 if tool_name == "check_availability" else 3
                for _ in range(repeat):
                    anomalous.append(
                        {
                            "name": tool_name,
                            "op": "execute_tool",
                            "agent": "product-discovery",
                            "kind": "tool",
                            "children": [],
                            "anomalous": True,
                        }
                    )
            # Inject anomalous delegation
            anomalous.append(
                {
                    "name": ANOMALOUS_DELEGATION,
                    "op": "invoke_agent",
                    "agent": ANOMALOUS_DELEGATION,
                    "kind": "agent",
                    "anomalous": True,
                    "children": [
                        {
                            "name": "get_warehouse_stock",
                            "op": "execute_tool",
                            "agent": ANOMALOUS_DELEGATION,
                            "kind": "tool",
                            "children": [],
                        },
                        {
                            "name": "get_warehouse_stock",
                            "op": "execute_tool",
                            "agent": ANOMALOUS_DELEGATION,
                            "kind": "tool",
                            "children": [],
                        },
                        {
                            "name": "get_warehouse_stock",
                            "op": "execute_tool",
                            "agent": ANOMALOUS_DELEGATION,
                            "kind": "tool",
                            "children": [],
                        },
                        {
                            "name": "calculate_shipping",
                            "op": "execute_tool",
                            "agent": ANOMALOUS_DELEGATION,
                            "kind": "tool",
                            "children": [],
                        },
                        {
                            "name": "calculate_shipping",
                            "op": "execute_tool",
                            "agent": ANOMALOUS_DELEGATION,
                            "kind": "tool",
                            "children": [],
                        },
                    ],
                }
            )
            # Insert before the last child (get_product_details etc.)
            insert_pos = max(len(node["children"]) - 1, 1)
            node["children"] = (
                node["children"][:insert_pos]
                + anomalous
                + node["children"][insert_pos:]
            )
            break
    return tree


# ---------------------------------------------------------------------------
# Percentile helpers
# ---------------------------------------------------------------------------


def _percentile(values: list[float], pct: float) -> float:
    """Return the *pct*-th percentile (0-100) of *values*."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (pct / 100.0) * (len(s) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------


class DemoDataGenerator:
    """Deterministic demo data generator for Cymbal Shops.

    Uses ``random.Random(seed)`` for reproducibility.  Data is generated lazily
    on first access and cached.
    """

    def __init__(self, seed: int = 42) -> None:
        """Initialize with a deterministic random seed."""
        self._rng = random.Random(seed)
        self._sessions: list[dict[str, Any]] | None = None
        self._traces: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # Internal: deterministic hex IDs
    # ------------------------------------------------------------------

    def _hex_id(self, length: int) -> str:
        """Generate a deterministic hex string of *length* characters."""
        raw = self._rng.getrandbits(length * 4)
        return f"{raw:0{length}x}"

    # ------------------------------------------------------------------
    # Session generation
    # ------------------------------------------------------------------

    def _generate_sessions(self) -> list[dict[str, Any]]:
        """Produce ~80 sessions distributed across 7 days."""
        sessions: list[dict[str, Any]] = []
        user_pool = list(DEMO_USERS)

        # Build weighted journey pool
        journey_pool: list[JourneyTemplate] = []
        for j in JOURNEY_TEMPLATES:
            journey_pool.extend([j] * j.weight_pct)

        # Distribute sessions: ~11-12 per day for 7 days
        for day in range(_WINDOW_DAYS):
            sessions_today = self._rng.randint(10, 13)
            for _ in range(sessions_today):
                user = self._rng.choice(user_pool)
                journey = self._rng.choice(journey_pool)
                turns = self._rng.randint(*journey.turns_range)
                # Spread within the day (6am-23pm typical usage)
                hour = self._rng.randint(6, 23)
                minute = self._rng.randint(0, 59)
                second = self._rng.randint(0, 59)
                ts = _BASE_TIME + timedelta(
                    days=day, hours=hour, minutes=minute, seconds=second
                )
                session_id = self._hex_id(16)
                sessions.append(
                    {
                        "session_id": session_id,
                        "user_id": user.user_id,
                        "user_display_name": user.display_name,
                        "user_geo_region": user.geo_region,
                        "timestamp": ts,
                        "journey_type": journey.journey_type,
                        "turns": turns,
                        "agents_involved": list(journey.agents_involved),
                    }
                )
        sessions.sort(key=lambda s: s["timestamp"])
        return sessions

    # ------------------------------------------------------------------
    # Trace generation
    # ------------------------------------------------------------------

    def _is_degraded(self, ts: datetime) -> bool:
        """Is the given timestamp inside the incident window?"""
        return _INCIDENT_START <= ts <= _INCIDENT_END

    def _duration_ms(self, kind: str, anomalous: bool = False) -> int:
        if anomalous:
            return self._rng.randint(*_DEGRADED_TOOL_DURATION)
        if kind == "llm":
            return self._rng.randint(*_NORMAL_LLM_DURATION)
        if kind == "tool":
            return self._rng.randint(*_NORMAL_TOOL_DURATION)
        # agent overhead
        return self._rng.randint(*_NORMAL_AGENT_OVERHEAD)

    def _build_spans(
        self,
        tree: list[dict[str, Any]],
        trace_id: str,
        session_id: str,
        user_id: str,
        user_geo: str,
        journey_type: str,
        parent_span_id: str | None,
        start_time: datetime,
        is_degraded: bool,
        version: str,
    ) -> tuple[list[dict[str, Any]], datetime]:
        """Recursively build span dicts from a span tree template.

        Returns ``(spans, end_time)`` where *end_time* is the time after the
        last span finishes.
        """
        spans: list[dict[str, Any]] = []
        cursor = start_time

        for node in tree:
            span_id = self._hex_id(16)
            kind = node["kind"]
            is_anomalous = node.get("anomalous", False)
            op = node["op"]
            agent_name = node["agent"]
            agent_def = AGENTS.get(agent_name)
            model = agent_def.model if agent_def else "gemini-2.5-flash"

            # Determine span duration
            if kind == "agent" and node["children"]:
                # Agent spans wrap children; add overhead
                overhead_before = self._duration_ms("agent", is_anomalous)
                child_start = cursor + timedelta(milliseconds=overhead_before)
                child_spans, child_end = self._build_spans(
                    node["children"],
                    trace_id=trace_id,
                    session_id=session_id,
                    user_id=user_id,
                    user_geo=user_geo,
                    journey_type=journey_type,
                    parent_span_id=span_id,
                    start_time=child_start,
                    is_degraded=is_degraded,
                    version=version,
                )
                overhead_after = self._duration_ms("agent", is_anomalous)
                span_end = child_end + timedelta(milliseconds=overhead_after)
                spans_to_add = child_spans
            else:
                dur_ms = self._duration_ms(kind, is_anomalous)
                span_end = cursor + timedelta(milliseconds=dur_ms)
                spans_to_add = []

            dur_nano = int((span_end - cursor).total_seconds() * 1e9)

            # Build attributes
            attributes: dict[str, Any] = {
                "gen_ai.system": "vertex_ai",
                "gen_ai.operation.name": op,
                "gen_ai.agent.name": agent_name,
                "gen_ai.agent.id": f"{agent_name}-v1",
                "gen_ai.conversation.id": session_id,
                "user.id": user_id,
                "user.geo.region": user_geo,
                "cymbal.release_version": version,
                "cymbal.journey_type": journey_type,
            }
            if kind == "llm":
                attributes["gen_ai.request.model"] = model
                attributes["gen_ai.response.model"] = f"{model}-001"
                attributes["gen_ai.usage.input_tokens"] = self._rng.randint(
                    *_INPUT_TOKENS_RANGE
                )
                attributes["gen_ai.usage.output_tokens"] = self._rng.randint(
                    *_OUTPUT_TOKENS_RANGE
                )
            if kind == "tool":
                attributes["gen_ai.tool.name"] = node["name"]
                attributes["gen_ai.tool.call.id"] = f"call_{self._hex_id(8)}"

            # Status: inject errors for anomalous validate_coupon (some 429s)
            status_code = 0  # UNSET (OK)
            status_message = ""
            events: list[dict[str, Any]] = []
            if is_anomalous and kind == "tool" and node["name"] == "validate_coupon":
                if self._rng.random() < 0.5:
                    status_code = 2  # ERROR
                    status_message = "429 Too Many Requests"
                    events.append(
                        {
                            "name": "exception",
                            "attributes": {
                                "exception.type": "RateLimitError",
                                "exception.message": "429 Too Many Requests from payment-mcp",
                                "exception.stacktrace": (
                                    "Traceback (most recent call last):\n"
                                    '  File "cymbal/tools/payment.py", line 42, in validate_coupon\n'
                                    "    raise RateLimitError(resp.status_code)\n"
                                    "RateLimitError: 429 Too Many Requests"
                                ),
                            },
                        }
                    )

            # Resource attributes with version override during incident
            resource_attrs = dict(RESOURCE_ATTRIBUTES)
            resource_attrs["service.version"] = version

            span = {
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "name": node["name"],
                "kind": 1,  # INTERNAL
                "start_time": cursor.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "end_time": span_end.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "duration_nano": dur_nano,
                "status": {"code": status_code, "message": status_message},
                "attributes": attributes,
                "resource": {"attributes": resource_attrs},
                "events": events,
                "links": [],
            }
            spans.append(span)
            spans.extend(spans_to_add)
            cursor = span_end

        return spans, cursor

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate all traces from sessions."""
        sessions = self.get_sessions()
        traces: list[dict[str, Any]] = []

        for session in sessions:
            turn_gap = timedelta(seconds=self._rng.randint(15, 90))
            ts = session["timestamp"]
            journey_type = session["journey_type"]
            agents_involved = session["agents_involved"]
            degraded = self._is_degraded(ts)
            version = "v2.4.1" if degraded else "v2.4.0"

            for _turn_idx in range(session["turns"]):
                trace_id = self._hex_id(32)
                root_span_id = self._hex_id(16)

                # Build span tree
                tree = _span_tree_for_journey(journey_type, agents_involved)
                if degraded and any(a == "product-discovery" for a in agents_involved):
                    tree = _inject_anomalous_spans(tree)

                # Build child spans
                child_start = ts + timedelta(milliseconds=self._rng.randint(5, 20))
                child_spans, child_end = self._build_spans(
                    tree,
                    trace_id=trace_id,
                    session_id=session["session_id"],
                    user_id=session["user_id"],
                    user_geo=session["user_geo_region"],
                    journey_type=journey_type,
                    parent_span_id=root_span_id,
                    start_time=child_start,
                    is_degraded=degraded,
                    version=version,
                )

                root_end = child_end + timedelta(milliseconds=self._rng.randint(5, 20))
                root_dur_nano = int((root_end - ts).total_seconds() * 1e9)

                root_attrs: dict[str, Any] = {
                    "gen_ai.system": "vertex_ai",
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.agent.name": "cymbal-assistant",
                    "gen_ai.agent.id": "cymbal-assistant-v1",
                    "gen_ai.conversation.id": session["session_id"],
                    "user.id": session["user_id"],
                    "user.geo.region": session["user_geo_region"],
                    "cymbal.release_version": version,
                    "cymbal.journey_type": journey_type,
                }

                resource_attrs = dict(RESOURCE_ATTRIBUTES)
                resource_attrs["service.version"] = version

                root_span = {
                    "trace_id": trace_id,
                    "span_id": root_span_id,
                    "parent_span_id": None,
                    "name": "cymbal-assistant",
                    "kind": 1,
                    "start_time": ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "end_time": root_end.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "duration_nano": root_dur_nano,
                    "status": {"code": 0, "message": ""},
                    "attributes": root_attrs,
                    "resource": {"attributes": resource_attrs},
                    "events": [],
                    "links": [],
                }

                all_spans = [root_span, *child_spans]

                # Propagate error status to root if any child has error
                if any(s["status"]["code"] == 2 for s in child_spans):
                    root_span["status"] = {"code": 2, "message": "child span error"}

                traces.append(
                    {
                        "trace_id": trace_id,
                        "session_id": session["session_id"],
                        "timestamp": ts,
                        "is_degraded": degraded,
                        "journey_type": journey_type,
                        "user_id": session["user_id"],
                        "version": version,
                        "spans": all_spans,
                    }
                )
                ts = ts + turn_gap + timedelta(seconds=self._rng.randint(5, 30))

        traces.sort(key=lambda t: t["timestamp"])
        return traces

    # ------------------------------------------------------------------
    # Public: raw data
    # ------------------------------------------------------------------

    def get_sessions(self) -> list[dict[str, Any]]:
        """Return all generated sessions."""
        if self._sessions is None:
            self._sessions = self._generate_sessions()
        return self._sessions

    def get_all_traces(self) -> list[dict[str, Any]]:
        """Return all generated traces."""
        if self._traces is None:
            self._traces = self._generate_traces()
        return self._traces

    # ------------------------------------------------------------------
    # Filtering helpers
    # ------------------------------------------------------------------

    def _filter_traces(
        self,
        hours: float = 168,
        service_name: str | None = None,
        errors_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Filter traces by time window and optional service name."""
        cutoff = _END_TIME - timedelta(hours=hours)
        traces = [t for t in self.get_all_traces() if t["timestamp"] >= cutoff]
        if service_name:
            traces = [
                t
                for t in traces
                if any(
                    s["resource"]["attributes"].get("service.name") == service_name
                    for s in t["spans"]
                )
            ]
        if errors_only:
            traces = [
                t for t in traces if any(s["status"]["code"] == 2 for s in t["spans"])
            ]
        return traces

    def _filter_sessions(self, hours: float = 168) -> list[dict[str, Any]]:
        cutoff = _END_TIME - timedelta(hours=hours)
        return [s for s in self.get_sessions() if s["timestamp"] >= cutoff]

    def _previous_period_traces(self, hours: float) -> list[dict[str, Any]]:
        """Get traces from the period *before* the current window for trend calculations."""
        end = _END_TIME - timedelta(hours=hours)
        start = end - timedelta(hours=hours)
        return [t for t in self.get_all_traces() if start <= t["timestamp"] < end]

    # ------------------------------------------------------------------
    # Span-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _span_duration_ms(span: dict[str, Any]) -> float:
        return float(span["duration_nano"]) / 1e6

    @staticmethod
    def _span_is_llm(span: dict[str, Any]) -> bool:
        return bool(
            span.get("attributes", {}).get("gen_ai.operation.name")
            == "generate_content"
        )

    @staticmethod
    def _span_is_tool(span: dict[str, Any]) -> bool:
        return bool(
            span.get("attributes", {}).get("gen_ai.operation.name") == "execute_tool"
        )

    @staticmethod
    def _span_is_agent(span: dict[str, Any]) -> bool:
        return bool(
            span.get("attributes", {}).get("gen_ai.operation.name") == "invoke_agent"
        )

    @staticmethod
    def _span_tokens(span: dict[str, Any]) -> int:
        attrs = span.get("attributes", {})
        return int(attrs.get("gen_ai.usage.input_tokens", 0)) + int(
            attrs.get("gen_ai.usage.output_tokens", 0)
        )

    @staticmethod
    def _span_has_error(span: dict[str, Any]) -> bool:
        return bool(span.get("status", {}).get("code") == 2)

    @staticmethod
    def _trace_duration_ms(trace: dict[str, Any]) -> float:
        root = trace["spans"][0]
        return float(root["duration_nano"]) / 1e6

    @staticmethod
    def _trace_total_tokens(trace: dict[str, Any]) -> int:
        total = 0
        for s in trace["spans"]:
            attrs = s.get("attributes", {})
            total += attrs.get("gen_ai.usage.input_tokens", 0) + attrs.get(
                "gen_ai.usage.output_tokens", 0
            )
        return total

    @staticmethod
    def _trace_error_count(trace: dict[str, Any]) -> int:
        return sum(1 for s in trace["spans"] if s.get("status", {}).get("code") == 2)

    # ------------------------------------------------------------------
    # Graph endpoints
    # ------------------------------------------------------------------

    def get_topology(
        self,
        hours: float = 168,
        errors_only: bool = False,
        service_name: str | None = None,
    ) -> dict[str, Any]:
        """Build topology graph matching AgentOps UI format."""
        traces = self._filter_traces(hours, service_name, errors_only)

        # Aggregate per-node and per-edge stats
        node_stats: dict[
            str, dict[str, Any]
        ] = {}  # id -> {exec, tokens, errors, durations}
        edge_stats: dict[
            tuple[str, str], dict[str, Any]
        ] = {}  # (src, tgt) -> {calls, durations, errors, tokens}

        for trace in traces:
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                if op == "invoke_agent":
                    node_id = attrs.get("gen_ai.agent.name", span["name"])
                    node_type = "agent"
                elif op == "execute_tool":
                    node_id = attrs.get("gen_ai.tool.name", span["name"])
                    node_type = "tool"
                elif op == "generate_content":
                    node_id = span["name"]
                    node_type = "llm"
                else:
                    continue

                if node_id not in node_stats:
                    node_stats[node_id] = {
                        "type": node_type,
                        "exec": 0,
                        "tokens": 0,
                        "errors": 0,
                        "durations": [],
                    }
                ns = node_stats[node_id]
                ns["exec"] += 1
                ns["tokens"] += self._span_tokens(span)
                if self._span_has_error(span):
                    ns["errors"] += 1
                ns["durations"].append(self._span_duration_ms(span))

                # Edge: parent -> this span
                if span["parent_span_id"]:
                    # Find parent span to get its name
                    parent_name: str | None = None
                    for ps in trace["spans"]:
                        if ps["span_id"] == span["parent_span_id"]:
                            p_attrs = ps.get("attributes", {})
                            p_op = p_attrs.get("gen_ai.operation.name", "")
                            if p_op == "invoke_agent":
                                parent_name = p_attrs.get(
                                    "gen_ai.agent.name", ps["name"]
                                )
                            elif p_op == "execute_tool":
                                parent_name = p_attrs.get(
                                    "gen_ai.tool.name", ps["name"]
                                )
                            elif p_op == "generate_content":
                                parent_name = ps["name"]
                            else:
                                parent_name = ps["name"]
                            break
                    if parent_name and parent_name != node_id:
                        ek = (parent_name, node_id)
                        if ek not in edge_stats:
                            edge_stats[ek] = {
                                "calls": 0,
                                "durations": [],
                                "errors": 0,
                                "tokens": 0,
                            }
                        es = edge_stats[ek]
                        es["calls"] += 1
                        es["durations"].append(self._span_duration_ms(span))
                        if self._span_has_error(span):
                            es["errors"] += 1
                        es["tokens"] += self._span_tokens(span)

        # Layout positions: root at top, agents middle, tools/llm bottom
        all_nodes = list(node_stats.keys())
        agents = [n for n in all_nodes if node_stats[n]["type"] == "agent"]
        tools = [n for n in all_nodes if node_stats[n]["type"] == "tool"]
        llms = [n for n in all_nodes if node_stats[n]["type"] == "llm"]

        def _positions(names: list[str], y: float) -> dict[str, dict[str, float]]:
            pos: dict[str, dict[str, float]] = {}
            for i, name in enumerate(sorted(names)):
                x = (i - len(names) / 2) * 200 + 400
                pos[name] = {"x": x, "y": y}
            return pos

        positions: dict[str, dict[str, float]] = {}
        positions.update(_positions(agents, 100.0))
        positions.update(_positions(llms, 300.0))
        positions.update(_positions(tools, 500.0))

        nodes = []
        for nid, ns in node_stats.items():
            avg_dur = (
                sum(ns["durations"]) / len(ns["durations"]) if ns["durations"] else 0.0
            )
            nodes.append(
                {
                    "id": nid,
                    "type": ns["type"],
                    "data": {
                        "label": nid,
                        "nodeType": ns["type"],
                        "executionCount": ns["exec"],
                        "totalTokens": ns["tokens"],
                        "errorCount": ns["errors"],
                        "avgDurationMs": round(avg_dur, 2),
                    },
                    "position": positions.get(nid, {"x": 400.0, "y": 300.0}),
                }
            )

        edges = []
        for (src, tgt), es in edge_stats.items():
            avg_dur = (
                sum(es["durations"]) / len(es["durations"]) if es["durations"] else 0.0
            )
            edges.append(
                {
                    "id": f"{src}->{tgt}",
                    "source": src,
                    "target": tgt,
                    "data": {
                        "callCount": es["calls"],
                        "avgDurationMs": round(avg_dur, 2),
                        "errorCount": es["errors"],
                        "totalTokens": es["tokens"],
                    },
                }
            )

        return {"nodes": nodes, "edges": edges}

    def get_trajectories(
        self,
        hours: float = 168,
        errors_only: bool = False,
        service_name: str | None = None,
    ) -> dict[str, Any]:
        """Build Sankey trajectory data matching AgentOps UI format."""
        traces = self._filter_traces(hours, service_name, errors_only)

        node_set: set[str] = set()
        link_counts: dict[tuple[str, str], int] = {}

        for trace in traces:
            # Build ordered sequence of agent/tool names from spans (skip LLM)
            sequence: list[str] = []
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                if op == "invoke_agent":
                    name = attrs.get("gen_ai.agent.name", span["name"])
                elif op == "execute_tool":
                    name = attrs.get("gen_ai.tool.name", span["name"])
                else:
                    continue
                if not sequence or sequence[-1] != name:
                    sequence.append(name)
                    node_set.add(name)

            for i in range(len(sequence) - 1):
                key = (sequence[i], sequence[i + 1])
                link_counts[key] = link_counts.get(key, 0) + 1

        nodes = [
            {"id": nid, "nodeColor": _SANKEY_COLORS.get(nid, "#64748b")}
            for nid in sorted(node_set)
        ]
        links = [
            {"source": src, "target": tgt, "value": cnt}
            for (src, tgt), cnt in sorted(link_counts.items())
        ]

        return {"nodes": nodes, "links": links, "loopTraces": []}

    def get_node_detail(
        self, node_id: str, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Get detailed info for a specific topology node."""
        traces = self._filter_traces(hours, service_name)

        durations: list[float] = []
        input_tokens = 0
        output_tokens = 0
        error_count = 0
        total_invocations = 0
        error_messages: dict[str, int] = {}
        recent_payloads: list[dict[str, Any]] = []
        node_type = "agent"

        for trace in traces:
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                if op == "invoke_agent":
                    span_node_id = attrs.get("gen_ai.agent.name", span["name"])
                    nt = "agent"
                elif op == "execute_tool":
                    span_node_id = attrs.get("gen_ai.tool.name", span["name"])
                    nt = "tool"
                elif op == "generate_content":
                    span_node_id = span["name"]
                    nt = "llm"
                else:
                    continue

                if span_node_id != node_id:
                    continue

                node_type = nt
                total_invocations += 1
                dur = self._span_duration_ms(span)
                durations.append(dur)
                input_tokens += attrs.get("gen_ai.usage.input_tokens", 0)
                output_tokens += attrs.get("gen_ai.usage.output_tokens", 0)

                if self._span_has_error(span):
                    error_count += 1
                    msg = span["status"].get("message", "Unknown error")
                    error_messages[msg] = error_messages.get(msg, 0) + 1

                if len(recent_payloads) < 10:
                    payload: dict[str, Any] = {
                        "traceId": trace["trace_id"],
                        "spanId": span["span_id"],
                        "timestamp": span.get("start_time"),
                        "nodeType": nt,
                        "prompt": None,
                        "completion": None,
                        "toolInput": None,
                        "toolOutput": None,
                    }
                    if nt == "llm":
                        payload["prompt"] = f"[{span['name']}] prompt content"
                        payload["completion"] = f"[{span['name']}] completion content"
                    elif nt == "tool":
                        payload["toolInput"] = f'{{"tool": "{span["name"]}"}}'
                        payload["toolOutput"] = (
                            f'{{"status": "ok", "tool": "{span["name"]}"}}'
                        )
                    recent_payloads.append(payload)

        error_rate = error_count / total_invocations if total_invocations else 0.0
        # Estimate cost: $0.075 per 1M input tokens, $0.30 per 1M output tokens
        estimated_cost = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000

        error_list = [
            {"message": msg, "count": cnt} for msg, cnt in error_messages.items()
        ]
        error_list.sort(key=lambda e: -e["count"])  # type: ignore[operator]
        top_errors = error_list[:5]

        return {
            "nodeId": node_id,
            "nodeType": node_type,
            "label": node_id,
            "totalInvocations": total_invocations,
            "errorRate": round(error_rate, 4),
            "errorCount": error_count,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "estimatedCost": round(estimated_cost, 4),
            "latency": {
                "p50": round(_percentile(durations, 50), 2),
                "p95": round(_percentile(durations, 95), 2),
                "p99": round(_percentile(durations, 99), 2),
            },
            "topErrors": top_errors,
            "recentPayloads": recent_payloads,
        }

    def get_edge_detail(
        self,
        source_id: str,
        target_id: str,
        hours: float = 168,
        service_name: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed info for a topology edge."""
        traces = self._filter_traces(hours, service_name)

        durations: list[float] = []
        error_count = 0
        call_count = 0
        input_tokens = 0
        output_tokens = 0

        for trace in traces:
            span_map: dict[str, dict[str, Any]] = {
                s["span_id"]: s for s in trace["spans"]
            }
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                if op == "invoke_agent":
                    child_id = attrs.get("gen_ai.agent.name", span["name"])
                elif op == "execute_tool":
                    child_id = attrs.get("gen_ai.tool.name", span["name"])
                elif op == "generate_content":
                    child_id = span["name"]
                else:
                    continue

                if child_id != target_id:
                    continue
                if not span["parent_span_id"]:
                    continue

                parent = span_map.get(span["parent_span_id"])
                if not parent:
                    continue
                p_attrs = parent.get("attributes", {})
                p_op = p_attrs.get("gen_ai.operation.name", "")
                if p_op == "invoke_agent":
                    parent_name = p_attrs.get("gen_ai.agent.name", parent["name"])
                elif p_op == "execute_tool":
                    parent_name = p_attrs.get("gen_ai.tool.name", parent["name"])
                elif p_op == "generate_content":
                    parent_name = parent["name"]
                else:
                    parent_name = parent["name"]

                if parent_name != source_id:
                    continue

                call_count += 1
                durations.append(self._span_duration_ms(span))
                if self._span_has_error(span):
                    error_count += 1
                input_tokens += attrs.get("gen_ai.usage.input_tokens", 0)
                output_tokens += attrs.get("gen_ai.usage.output_tokens", 0)

        error_rate = error_count / call_count if call_count else 0.0
        return {
            "sourceId": source_id,
            "targetId": target_id,
            "callCount": call_count,
            "errorCount": error_count,
            "errorRate": round(error_rate, 4),
            "avgDurationMs": round((sum(durations) / len(durations)), 2)
            if durations
            else 0.0,
            "p95DurationMs": round(_percentile(durations, 95), 2),
            "p99DurationMs": round(_percentile(durations, 99), 2),
            "totalTokens": input_tokens + output_tokens,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        }

    def get_timeseries(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Get per-node timeseries for topology sparklines.

        Returns ``{series: {nodeId: [{bucket, callCount, errorCount,
        avgDurationMs, totalTokens, totalCost}]}}``.
        """
        traces = self._filter_traces(hours, service_name)

        bucket_minutes = 60 if hours >= 24 else 5
        bucket_delta = timedelta(minutes=bucket_minutes)
        start = _END_TIME - timedelta(hours=hours)

        # node_id -> bucket_key -> list of span dicts
        per_node: dict[str, dict[str, list[dict[str, Any]]]] = {}

        for trace in traces:
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                if op == "invoke_agent":
                    node_id = attrs.get("gen_ai.agent.name", span["name"])
                elif op == "execute_tool":
                    node_id = attrs.get("gen_ai.tool.name", span["name"])
                elif op == "generate_content":
                    node_id = span["name"]
                else:
                    continue

                ts = trace["timestamp"]
                bucket_start = start + timedelta(
                    minutes=((ts - start).total_seconds() // (bucket_minutes * 60))
                    * bucket_minutes
                )
                key = bucket_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                per_node.setdefault(node_id, {}).setdefault(key, []).append(span)

        # Build series
        series: dict[str, list[dict[str, Any]]] = {}
        for node_id, buckets in per_node.items():
            points: list[dict[str, Any]] = []
            # Ensure contiguous buckets
            t = start
            while t < _END_TIME:
                key = t.strftime("%Y-%m-%dT%H:%M:%SZ")
                spans = buckets.get(key, [])
                durations = [self._span_duration_ms(s) for s in spans]
                tokens = sum(self._span_tokens(s) for s in spans)
                errors = sum(1 for s in spans if self._span_has_error(s))
                avg_dur = (sum(durations) / len(durations)) if durations else 0.0
                points.append(
                    {
                        "bucket": key,
                        "callCount": len(spans),
                        "errorCount": errors,
                        "avgDurationMs": round(avg_dur, 1),
                        "totalTokens": tokens,
                        "totalCost": round(tokens * 0.0000005, 6),
                    }
                )
                t += bucket_delta
            series[node_id] = points

        return {"series": series}

    def get_context_graph(self, session_id: str) -> dict[str, Any]:
        """Synthesize a complex Context Graph for the UI from session traces.

        Matches the { nodes: ContextNode[], edges: ContextEdge[] } format expected by ContextGraphViewer.
        """
        traces = [t for t in self.get_all_traces() if t["session_id"] == session_id]
        if not traces:
            return {"nodes": [], "edges": []}

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # Start with an incident node dynamically located around the beginning of the session
        session_start = traces[0]["timestamp"]
        nodes.append(
            {
                "id": "inc-0",
                "type": "INCIDENT",
                "label": "Incident Detected: Shopping Cart Abandonment Anomaly",
                "timestamp": (session_start - timedelta(minutes=5)).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
                "metadata": {"duration": 0},
            }
        )

        last_main_id = "inc-0"
        node_idx = 1

        # Sort traces by time
        traces.sort(key=lambda x: x["timestamp"])

        for trace in traces:
            # Add a THOUGHT node for the turn
            thought_id = f"thought-{node_idx}"
            nodes.append(
                {
                    "id": thought_id,
                    "type": "THOUGHT",
                    "label": f"Analyze telemetry and user journey for {session_id[:8]}",
                    "timestamp": trace["timestamp"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                }
            )
            edges.append(
                {"source": last_main_id, "target": thought_id, "label": "leads to"}
            )
            last_main_id = thought_id
            node_idx += 1

            # Map tools in the trace into the graph
            # First, find all execute_tool spans
            tool_spans = []
            for span in trace["spans"]:
                if self._span_is_tool(span):
                    tool_spans.append(span)

            # Order them by start_time
            tool_spans.sort(key=lambda s: s["start_time"])

            for tool in tool_spans:
                tool_name = tool.get("attributes", {}).get(
                    "gen_ai.tool.name", tool["name"]
                )
                tool_id = f"tool-{node_idx}"
                nodes.append(
                    {
                        "id": tool_id,
                        "type": "TOOL_CALL",
                        "label": tool_name,
                        "timestamp": tool["start_time"],
                        "metadata": {
                            "duration": self._span_duration_ms(tool),
                            "tokenCount": self._span_tokens(tool),
                        },
                    }
                )
                edges.append(
                    {"source": thought_id, "target": tool_id, "label": "calls"}
                )
                node_idx += 1

                # Add observation after the tool call
                obs_id = f"obs-{node_idx}"
                nodes.append(
                    {
                        "id": obs_id,
                        "type": "OBSERVATION",
                        "label": f"Result from {tool_name}",
                        "timestamp": tool["end_time"],
                    }
                )
                edges.append({"source": tool_id, "target": obs_id, "label": "returns"})
                node_idx += 1

        # Final Action node at the very end
        if len(traces) > 0:
            final_trace = traces[-1]
            action_id = f"action-{node_idx}"
            nodes.append(
                {
                    "id": action_id,
                    "type": "ACTION",
                    "label": "Mitigation Applied / Recommendation provided",
                    "timestamp": (
                        final_trace["timestamp"] + timedelta(seconds=120)
                    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "metadata": {"duration": 1500},
                }
            )
            edges.append(
                {"source": last_main_id, "target": action_id, "label": "executes"}
            )

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Dashboard endpoints
    # ------------------------------------------------------------------

    def get_dashboard_kpis(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return KPI metrics matching AgentOps UI format."""
        traces = self._filter_traces(hours, service_name)
        sessions = self._filter_sessions(hours)
        prev_traces = self._previous_period_traces(hours)

        # Current period
        total_sessions = len(sessions)
        avg_turns = (
            (sum(s["turns"] for s in sessions) / len(sessions)) if sessions else 0.0
        )
        root_invocations = len(traces)
        error_traces = sum(
            1 for t in traces if any(s["status"]["code"] == 2 for s in t["spans"])
        )
        error_rate = error_traces / root_invocations if root_invocations else 0.0

        # Previous period
        prev_session_ids = {t["session_id"] for t in prev_traces}
        prev_sessions_count = len(prev_session_ids)
        prev_root = len(prev_traces)
        prev_errors = sum(
            1 for t in prev_traces if any(s["status"]["code"] == 2 for s in t["spans"])
        )
        prev_error_rate = prev_errors / prev_root if prev_root else 0.0

        # Compute turns for previous sessions
        prev_session_turns: dict[str, int] = {}
        for t in prev_traces:
            sid = t["session_id"]
            prev_session_turns[sid] = prev_session_turns.get(sid, 0) + 1
        prev_avg_turns = (
            (sum(prev_session_turns.values()) / len(prev_session_turns))
            if prev_session_turns
            else 0.0
        )

        def _trend(current: float, previous: float) -> float:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round(((current - previous) / previous) * 100, 2)

        return {
            "kpis": {
                "totalSessions": total_sessions,
                "avgTurns": round(avg_turns, 2),
                "rootInvocations": root_invocations,
                "errorRate": round(error_rate, 4),
                "totalSessionsTrend": _trend(total_sessions, prev_sessions_count),
                "avgTurnsTrend": _trend(avg_turns, prev_avg_turns),
                "rootInvocationsTrend": _trend(root_invocations, prev_root),
                "errorRateTrend": _trend(error_rate, prev_error_rate),
            }
        }

    def get_dashboard_timeseries(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return timeseries data bucketed appropriately."""
        traces = self._filter_traces(hours, service_name)

        # Determine bucket size
        if hours < 24:
            bucket_minutes = 5
        else:
            bucket_minutes = 60

        bucket_delta = timedelta(minutes=bucket_minutes)
        start = _END_TIME - timedelta(hours=hours)

        # Create buckets
        buckets: dict[str, list[dict[str, Any]]] = {}
        t = start
        while t < _END_TIME:
            key = t.strftime("%Y-%m-%dT%H:%M:%SZ")
            buckets[key] = []
            t += bucket_delta

        # Assign traces to buckets
        for trace in traces:
            ts = trace["timestamp"]
            bucket_start = start + timedelta(
                minutes=((ts - start).total_seconds() // (bucket_minutes * 60))
                * bucket_minutes
            )
            key = bucket_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            if key in buckets:
                buckets[key].append(trace)

        latency_series: list[dict[str, Any]] = []
        qps_series: list[dict[str, Any]] = []
        token_series: list[dict[str, Any]] = []

        for ts_key in sorted(buckets.keys()):
            bucket_traces = buckets[ts_key]
            durations = [self._trace_duration_ms(t) for t in bucket_traces]
            bucket_seconds = bucket_minutes * 60

            p50 = _percentile(durations, 50) if durations else 0.0
            p95 = _percentile(durations, 95) if durations else 0.0
            latency_series.append(
                {"timestamp": ts_key, "p50": round(p50, 2), "p95": round(p95, 2)}
            )

            qps_val = len(bucket_traces) / bucket_seconds if bucket_seconds else 0.0
            error_traces = sum(
                1
                for t in bucket_traces
                if any(s["status"]["code"] == 2 for s in t["spans"])
            )
            err_rate = error_traces / len(bucket_traces) if bucket_traces else 0.0
            qps_series.append(
                {
                    "timestamp": ts_key,
                    "qps": round(qps_val, 4),
                    "errorRate": round(err_rate, 4),
                }
            )

            input_tok = sum(
                s.get("attributes", {}).get("gen_ai.usage.input_tokens", 0)
                for t in bucket_traces
                for s in t["spans"]
            )
            output_tok = sum(
                s.get("attributes", {}).get("gen_ai.usage.output_tokens", 0)
                for t in bucket_traces
                for s in t["spans"]
            )
            token_series.append(
                {"timestamp": ts_key, "input": input_tok, "output": output_tok}
            )

        return {
            "latency": latency_series,
            "qps": qps_series,
            "tokens": token_series,
        }

    def get_dashboard_models(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return model call statistics."""
        traces = self._filter_traces(hours, service_name)
        model_stats: dict[str, dict[str, Any]] = {}

        for trace in traces:
            for span in trace["spans"]:
                if not self._span_is_llm(span):
                    continue
                attrs = span.get("attributes", {})
                model = attrs.get("gen_ai.request.model", "unknown")
                if model not in model_stats:
                    model_stats[model] = {
                        "calls": 0,
                        "errors": 0,
                        "quota_exits": 0,
                        "tokens": 0,
                        "durations": [],
                    }
                ms = model_stats[model]
                ms["calls"] += 1
                ms["durations"].append(self._span_duration_ms(span))
                ms["tokens"] += self._span_tokens(span)
                if self._span_has_error(span):
                    ms["errors"] += 1

        model_calls = []
        for model_name, ms in sorted(model_stats.items()):
            err_rate = ms["errors"] / ms["calls"] if ms["calls"] else 0.0
            model_calls.append(
                {
                    "modelName": model_name,
                    "totalCalls": ms["calls"],
                    "p95Duration": round(_percentile(ms["durations"], 95), 2),
                    "errorRate": round(err_rate, 4),
                    "quotaExits": ms["quota_exits"],
                    "tokensUsed": ms["tokens"],
                }
            )

        return {"modelCalls": model_calls}

    def get_dashboard_tools(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return tool call statistics."""
        traces = self._filter_traces(hours, service_name)
        tool_stats: dict[str, dict[str, Any]] = {}

        for trace in traces:
            for span in trace["spans"]:
                if not self._span_is_tool(span):
                    continue
                attrs = span.get("attributes", {})
                tool_name = attrs.get("gen_ai.tool.name", span["name"])
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {"calls": 0, "errors": 0, "durations": []}
                ts = tool_stats[tool_name]
                ts["calls"] += 1
                ts["durations"].append(self._span_duration_ms(span))
                if self._span_has_error(span):
                    ts["errors"] += 1

        tool_calls = []
        for tn, ts in sorted(tool_stats.items()):
            err_rate = ts["errors"] / ts["calls"] if ts["calls"] else 0.0
            tool_calls.append(
                {
                    "toolName": tn,
                    "totalCalls": ts["calls"],
                    "p95Duration": round(_percentile(ts["durations"], 95), 2),
                    "errorRate": round(err_rate, 4),
                }
            )

        return {"toolCalls": tool_calls}

    def get_dashboard_logs(
        self, hours: float = 168, limit: int = 2000, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return synthetic agent logs."""
        traces = self._filter_traces(hours, service_name)
        logs: list[dict[str, Any]] = []

        for trace in traces:
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                agent_name = attrs.get("gen_ai.agent.name", "cymbal-assistant")
                severity = "ERROR" if self._span_has_error(span) else "INFO"
                op = attrs.get("gen_ai.operation.name", "")

                if op == "invoke_agent":
                    message = f"Agent {agent_name} invoked"
                elif op == "execute_tool":
                    tool_name = attrs.get("gen_ai.tool.name", span["name"])
                    if self._span_has_error(span):
                        message = f"Tool {tool_name} failed: {span['status'].get('message', 'error')}"
                    else:
                        message = f"Tool {tool_name} executed successfully"
                elif op == "generate_content":
                    message = f"LLM call {span['name']} completed"
                else:
                    continue

                logs.append(
                    {
                        "timestamp": span["start_time"],
                        "agentId": attrs.get("gen_ai.agent.id", f"{agent_name}-v1"),
                        "severity": severity,
                        "message": message,
                        "traceId": trace["trace_id"],
                        "spanId": span["span_id"],
                        "agentName": agent_name,
                        "resourceId": REASONING_ENGINE_ID,
                    }
                )

                if len(logs) >= limit:
                    return {"agentLogs": logs}

        return {"agentLogs": logs}

    def get_dashboard_sessions(
        self, hours: float = 168, limit: int = 2000, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return per-session aggregation for the dashboard."""
        traces = self._filter_traces(hours, service_name)

        # Group traces by session
        session_traces: dict[str, list[dict[str, Any]]] = {}
        for t in traces:
            sid = t["session_id"]
            if sid not in session_traces:
                session_traces[sid] = []
            session_traces[sid].append(t)

        agent_sessions: list[dict[str, Any]] = []
        for sid, st in sorted(
            session_traces.items(), key=lambda x: x[1][0]["timestamp"]
        ):
            all_spans = [s for t in st for s in t["spans"]]
            total_tokens = sum(self._span_tokens(s) for s in all_spans)
            error_count = sum(1 for s in all_spans if self._span_has_error(s))
            latencies = [self._trace_duration_ms(t) for t in st]
            llm_calls = sum(1 for s in all_spans if self._span_is_llm(s))
            tool_calls = sum(1 for s in all_spans if self._span_is_tool(s))
            tool_errors = sum(
                1
                for s in all_spans
                if self._span_is_tool(s) and self._span_has_error(s)
            )
            llm_errors = sum(
                1 for s in all_spans if self._span_is_llm(s) and self._span_has_error(s)
            )

            agent_sessions.append(
                {
                    "timestamp": st[0]["spans"][0]["start_time"],
                    "sessionId": sid,
                    "turns": len(st),
                    "latestTraceId": st[-1]["trace_id"],
                    "totalTokens": total_tokens,
                    "errorCount": error_count,
                    "avgLatencyMs": round((sum(latencies) / len(latencies)), 2)
                    if latencies
                    else 0.0,
                    "p95LatencyMs": round(_percentile(latencies, 95), 2),
                    "agentName": "cymbal-assistant",
                    "resourceId": REASONING_ENGINE_ID,
                    "spanCount": len(all_spans),
                    "llmCallCount": llm_calls,
                    "toolCallCount": tool_calls,
                    "toolErrorCount": tool_errors,
                    "llmErrorCount": llm_errors,
                }
            )

            if len(agent_sessions) >= limit:
                break

        return {"agentSessions": agent_sessions}

    def get_dashboard_traces(
        self, hours: float = 168, limit: int = 2000, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return per-trace data for the dashboard."""
        traces = self._filter_traces(hours, service_name)
        agent_traces: list[dict[str, Any]] = []

        for trace in traces[:limit]:
            spans = trace["spans"]
            total_tokens = self._trace_total_tokens(trace)
            error_count = self._trace_error_count(trace)
            latency = self._trace_duration_ms(trace)
            llm_calls = sum(1 for s in spans if self._span_is_llm(s))
            tool_calls = sum(1 for s in spans if self._span_is_tool(s))
            tool_errors = sum(
                1 for s in spans if self._span_is_tool(s) and self._span_has_error(s)
            )
            llm_errors = sum(
                1 for s in spans if self._span_is_llm(s) and self._span_has_error(s)
            )

            agent_traces.append(
                {
                    "timestamp": trace["spans"][0]["start_time"],
                    "traceId": trace["trace_id"],
                    "sessionId": trace["session_id"],
                    "totalTokens": total_tokens,
                    "errorCount": error_count,
                    "latencyMs": round(latency, 2),
                    "agentName": "cymbal-assistant",
                    "resourceId": REASONING_ENGINE_ID,
                    "spanCount": len(spans),
                    "llmCallCount": llm_calls,
                    "toolCallCount": tool_calls,
                    "toolErrorCount": tool_errors,
                    "llmErrorCount": llm_errors,
                }
            )

        return {"agentTraces": agent_traces}

    # ------------------------------------------------------------------
    # Registry endpoints
    # ------------------------------------------------------------------

    def get_registry_agents(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return agent registry data."""
        traces = self._filter_traces(hours, service_name)
        agent_stats: dict[str, dict[str, Any]] = {}

        for trace in traces:
            session_id = trace["session_id"]
            for span in trace["spans"]:
                if not self._span_is_agent(span):
                    continue
                attrs = span.get("attributes", {})
                agent_name = attrs.get("gen_ai.agent.name", span["name"])
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "sessions": set(),
                        "turns": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "errors": 0,
                        "durations": [],
                    }
                ag = agent_stats[agent_name]
                ag["sessions"].add(session_id)
                ag["turns"] += 1
                ag["durations"].append(self._span_duration_ms(span))
                if self._span_has_error(span):
                    ag["errors"] += 1

            # Aggregate tokens from LLM spans under each agent
            for span in trace["spans"]:
                if not self._span_is_llm(span):
                    continue
                attrs = span.get("attributes", {})
                agent_name = attrs.get("gen_ai.agent.name", "cymbal-assistant")
                if agent_name in agent_stats:
                    agent_stats[agent_name]["input_tokens"] += attrs.get(
                        "gen_ai.usage.input_tokens", 0
                    )
                    agent_stats[agent_name]["output_tokens"] += attrs.get(
                        "gen_ai.usage.output_tokens", 0
                    )

        agents_list = []
        for agent_name, ag in sorted(agent_stats.items()):
            total = ag["turns"]
            err_rate = ag["errors"] / total if total else 0.0
            agents_list.append(
                {
                    "serviceName": "cymbal-assistant",
                    "agentId": f"{agent_name}-v1",
                    "agentName": agent_name,
                    "totalSessions": len(ag["sessions"]),
                    "totalTurns": total,
                    "inputTokens": ag["input_tokens"],
                    "outputTokens": ag["output_tokens"],
                    "errorCount": ag["errors"],
                    "errorRate": round(err_rate, 4),
                    "p50DurationMs": round(_percentile(ag["durations"], 50), 2),
                    "p95DurationMs": round(_percentile(ag["durations"], 95), 2),
                }
            )

        return {"agents": agents_list}

    def get_registry_tools(
        self, hours: float = 168, service_name: str | None = None
    ) -> dict[str, Any]:
        """Return tool registry data."""
        traces = self._filter_traces(hours, service_name)
        tool_stats: dict[str, dict[str, Any]] = {}

        for trace in traces:
            for span in trace["spans"]:
                if not self._span_is_tool(span):
                    continue
                attrs = span.get("attributes", {})
                tool_name = attrs.get("gen_ai.tool.name", span["name"])
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {"calls": 0, "errors": 0, "durations": []}
                ts = tool_stats[tool_name]
                ts["calls"] += 1
                ts["durations"].append(self._span_duration_ms(span))
                if self._span_has_error(span):
                    ts["errors"] += 1

        tools_list = []
        for tn, ts in sorted(tool_stats.items()):
            err_rate = ts["errors"] / ts["calls"] if ts["calls"] else 0.0
            tools_list.append(
                {
                    "serviceName": "cymbal-assistant",
                    "toolId": tn,
                    "toolName": tn,
                    "executionCount": ts["calls"],
                    "errorCount": ts["errors"],
                    "errorRate": round(err_rate, 4),
                    "avgDurationMs": round(
                        (sum(ts["durations"]) / len(ts["durations"])), 2
                    )
                    if ts["durations"]
                    else 0.0,
                    "p95DurationMs": round(_percentile(ts["durations"], 95), 2),
                }
            )

        return {"tools": tools_list}

    # ------------------------------------------------------------------
    # Detail endpoints
    # ------------------------------------------------------------------

    def get_span_details(self, trace_id: str, span_id: str) -> dict[str, Any]:
        """Return detailed info for a specific span."""
        for trace in self.get_all_traces():
            if trace["trace_id"] != trace_id:
                continue
            for span in trace["spans"]:
                if span["span_id"] != span_id:
                    continue
                exceptions = []
                evaluations = []
                for evt in span.get("events", []):
                    if evt.get("name") == "exception":
                        evt_attrs = evt.get("attributes", {})
                        exceptions.append(
                            {
                                "message": evt_attrs.get("exception.message", ""),
                                "stacktrace": evt_attrs.get("exception.stacktrace", ""),
                                "type": evt_attrs.get("exception.type", ""),
                            }
                        )

                # Generate synthetic eval data for LLM spans
                is_llm = span.get("attributes", {}).get("gen_ai.system") is not None
                if is_llm:
                    rng = self._rng
                    for metric in ["coherence", "groundedness", "fluency", "safety"]:
                        evaluations.append(
                            {
                                "metricName": metric,
                                "score": round(rng.uniform(0.6, 1.0), 3),
                                "explanation": f"Demo: {metric} score for this LLM call.",
                            }
                        )

                return {
                    "traceId": trace_id,
                    "spanId": span_id,
                    "statusCode": span["status"]["code"],
                    "statusMessage": span["status"]["message"],
                    "exceptions": exceptions,
                    "evaluations": evaluations,
                    "attributes": span["attributes"],
                    "logs": [],
                }
        return {
            "traceId": trace_id,
            "spanId": span_id,
            "statusCode": 0,
            "statusMessage": "span not found",
            "exceptions": [],
            "evaluations": [],
            "attributes": {},
            "logs": [],
        }

    def get_trace_logs(self, trace_id: str) -> dict[str, Any]:
        """Return synthetic logs for a specific trace."""
        for trace in self.get_all_traces():
            if trace["trace_id"] != trace_id:
                continue
            logs: list[dict[str, Any]] = []
            for span in trace["spans"]:
                attrs = span.get("attributes", {})
                op = attrs.get("gen_ai.operation.name", "")
                severity = "ERROR" if self._span_has_error(span) else "INFO"

                if op == "invoke_agent":
                    payload = (
                        f"Agent {attrs.get('gen_ai.agent.name', span['name'])} invoked"
                    )
                elif op == "execute_tool":
                    tool = attrs.get("gen_ai.tool.name", span["name"])
                    if self._span_has_error(span):
                        payload = f"Tool {tool} failed: {span['status'].get('message', 'error')}"
                    else:
                        payload = f"Tool {tool} executed ({self._span_duration_ms(span):.0f}ms)"
                elif op == "generate_content":
                    tokens = self._span_tokens(span)
                    payload = f"LLM {span['name']} completed ({tokens} tokens)"
                else:
                    continue

                logs.append(
                    {
                        "timestamp": span.get("start_time"),
                        "severity": severity,
                        "payload": payload,
                    }
                )
            return {"traceId": trace_id, "logs": logs}

        return {"traceId": trace_id, "logs": []}

    def get_session_trajectory(self, session_id: str) -> dict[str, Any]:
        """Return the unaggregated chronological trajectory for a session."""
        spans = []
        for trace in self.get_all_traces():
            if trace["session_id"] == session_id:
                spans.extend(trace["spans"])

        if not spans:
            return {"sessionId": session_id, "trajectory": []}

        spans.sort(key=lambda s: s["start_time"])

        trajectory = []
        for s in spans:
            attrs = s.get("attributes", {})
            node_type = "Agent"
            if attrs.get("gen_ai.system"):
                node_type = "LLM"
            elif attrs.get("gen_ai.tool.name"):
                node_type = "Tool"

            prompt = attrs.get("gen_ai.prompt")
            completion = attrs.get("gen_ai.completion")
            tool_input = attrs.get("tool.input")
            tool_output = attrs.get("tool.output")
            system_message = None

            evaluations = []
            is_llm = attrs.get("gen_ai.system") is not None
            if is_llm:
                rng = self._rng
                for metric in ["coherence", "groundedness", "fluency", "safety"]:
                    evaluations.append(
                        {
                            "metricName": metric,
                            "score": round(rng.uniform(0.6, 1.0), 3),
                            "explanation": f"Demo: {metric} score for this LLM call.",
                        }
                    )

            op = attrs.get("gen_ai.operation.name", "")
            severity = "ERROR" if self._span_has_error(s) else "INFO"
            payload = None

            if op == "invoke_agent":
                payload = f"Agent {attrs.get('gen_ai.agent.name', s['name'])} invoked"
            elif op == "execute_tool":
                tool = attrs.get("gen_ai.tool.name", s["name"])
                if self._span_has_error(s):
                    payload = (
                        f"Tool {tool} failed: {s['status'].get('message', 'error')}"
                    )
                else:
                    payload = (
                        f"Tool {tool} executed ({self._span_duration_ms(s):.0f}ms)"
                    )
            elif op == "generate_content":
                tokens = self._span_tokens(s)
                payload = f"LLM {s['name']} completed ({tokens} tokens)"

            span_logs = []

            start_time = s.get("start_time")
            start_time_iso = None
            if start_time:
                start_time_iso = (
                    start_time.isoformat()
                    if hasattr(start_time, "isoformat")
                    else str(start_time)
                )

            if payload:
                span_logs.append(
                    {
                        "timestamp": start_time_iso,
                        "severity": severity,
                        "payload": payload,
                    }
                )

            duration_ms: float = 0.0
            end_time = s.get("end_time")
            if end_time and start_time:
                try:
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                except TypeError:
                    from datetime import datetime

                    try:
                        e_t = datetime.fromisoformat(
                            str(end_time).replace("Z", "+00:00")
                        )
                        s_t = datetime.fromisoformat(
                            str(start_time).replace("Z", "+00:00")
                        )
                        duration_ms = (e_t - s_t).total_seconds() * 1000
                    except Exception:
                        pass

            trajectory.append(
                {
                    "traceId": s["trace_id"],
                    "spanId": s["span_id"],
                    "startTime": start_time_iso,
                    "nodeType": node_type,
                    "nodeLabel": s["name"],
                    "durationMs": duration_ms,
                    "statusCode": s["status"]["code"],
                    "prompt": prompt,
                    "completion": completion,
                    "systemMessage": system_message,
                    "toolInput": tool_input,
                    "toolOutput": tool_output,
                    "evaluations": evaluations,
                    "logs": span_logs,
                }
            )

        return {"sessionId": session_id, "trajectory": trajectory}
