"""Rule-based intent classifier for investigation mode selection.

Classifies user queries into investigation modes without an LLM call:
- FAST: Quick status checks, single-service queries
- STANDARD: Multi-signal investigation, general analysis
- DEBATE: Deep dive, root cause analysis, production incidents

Also determines the best signal type for FAST mode panel selection,
so the orchestrator routes to the most relevant panel (trace, metrics,
logs, or alerts) rather than always defaulting to traces.

Additionally provides routing classification for the 3-tier orchestrator:
- DIRECT: Simple data retrieval — call individual tools
- SUB_AGENT: Analysis — delegate to specialist sub-agents
- COUNCIL: Complex multi-signal investigation — council meeting
"""

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from .schemas import InvestigationMode, RoutingDecision

# Keywords that indicate a greeting or conversational message (no tools needed)
_GREETING_KEYWORDS: set[str] = {
    "hi",
    "hello",
    "hey",
    "howdy",
    "greetings",
    "good morning",
    "good afternoon",
    "good evening",
    "good day",
    "sup",
    "yo",
    "hola",
    "hiya",
    "heya",
}

# Conversational queries that don't need tool calls
_CONVERSATIONAL_KEYWORDS: set[str] = {
    "thanks",
    "thank you",
    "thx",
    "bye",
    "goodbye",
    "see you",
    "who are you",
    "what are you",
    "what can you do",
    "help me",
    "how do you work",
    "introduce yourself",
}

# Keywords that suggest a quick, lightweight check
_FAST_KEYWORDS: set[str] = {
    "status",
    "check",
    "quick",
    "health",
    "ping",
    "up",
    "down",
    "alive",
    "running",
    "current",
    "now",
    "overview",
    "summary",
    "brief",
    "glance",
}

# Keywords that suggest a deep, thorough investigation
_DEBATE_KEYWORDS: set[str] = {
    "root cause",
    "root-cause",
    "rootcause",
    "deep dive",
    "deep-dive",
    "deepdive",
    "thorough",
    "comprehensive",
    "incident",
    "outage",
    "postmortem",
    "post-mortem",
    "blast radius",
    "blast-radius",
    "production issue",
    "prod issue",
    "p0",
    "p1",
    "sev0",
    "sev1",
    "sev-0",
    "sev-1",
    "critical",
    "emergency",
    "urgent",
    "debate",
    "council",
    "all panels",
    "cross-examine",
    "cross examine",
}

# Patterns for debate mode (multi-word, checked via regex)
_DEBATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\bwhy\b.*\b(fail\w*|crash\w*|slow\w*|error\w*|down\w*)\b", re.IGNORECASE
    ),
    re.compile(r"\bwhat\b.*\bcaus(e|ed|ing)\b", re.IGNORECASE),
    re.compile(r"\binvestigat(e|ion)\b", re.IGNORECASE),
]

# Patterns for standard multi-signal council routing.
# These identify holistic service-health or cross-signal queries that benefit
# from the full 5-panel council rather than a single specialist sub-agent.
_STANDARD_COUNCIL_PATTERNS: list[re.Pattern[str]] = [
    # Service / system health questions
    re.compile(r"\b(health|wellness|status)\s+(of|for)\b", re.IGNORECASE),
    re.compile(
        r"\b(service|system|cluster|deployment)\s+(health|wellness|overview|diagnostic)\b",
        re.IGNORECASE,
    ),
    # "What's / what is / what are happening/wrong/going on" + service noun
    re.compile(
        r"\bwhat(?:'?s|\s+is|\s+are)\b.*\b(happening|wrong|going\s+on|the\s+issues?|the\s+problem)\b"
        r".*\b(service|system|app|api|cluster|pod|deployment|function)\b",
        re.IGNORECASE,
    ),
    # Performance degradation (without a specific signal keyword)
    re.compile(
        r"\b(performance\s+(issue|problem|degradation|anomaly|concern))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(service|system|api|app)\s+(is\s+)?(slow|degraded|impacted|struggling|flaky)\b",
        re.IGNORECASE,
    ),
    # End-to-end / holistic investigation scope
    re.compile(
        r"\b(end[\s\-]to[\s\-]end|e2e|full[\s\-](stack|diagnostic|picture|overview))\b",
        re.IGNORECASE,
    ),
    # "Look into / figure out / check out" + service noun
    re.compile(
        r"\b(look\s+into|figure\s+out|check\s+out)\b"
        r".*\b(service|system|app|api|cluster|deployment)\b",
        re.IGNORECASE,
    ),
    # Broad "how is X performing / doing"
    re.compile(
        r"\bhow\s+(is|are)\b.*\b(service|system|app|api|cluster|deployment)\b"
        r".*\b(perform\w*|do(?:ing)?|behav\w*|look\w*)\b",
        re.IGNORECASE,
    ),
]


class SignalType(str, Enum):
    """Signal type for panel selection in FAST mode."""

    TRACE = "trace"
    METRICS = "metrics"
    LOGS = "logs"
    ALERTS = "alerts"


# Signal-type keyword mapping for FAST mode panel routing
_TRACE_KEYWORDS: set[str] = {
    "trace",
    "traces",
    "span",
    "spans",
    "latency",
    "duration",
    "waterfall",
    "request",
    "endpoint",
    "api",
    "rpc",
    "grpc",
    "http",
    "service",
    "call",
    "slow",
    "timeout",
    "bottleneck",
    "critical path",
}

_METRICS_KEYWORDS: set[str] = {
    "metric",
    "metrics",
    "cpu",
    "memory",
    "disk",
    "network",
    "throughput",
    "qps",
    "rps",
    "rate",
    "utilization",
    "saturation",
    "promql",
    "time series",
    "timeseries",
    "slo",
    "sli",
    "error budget",
    "burn rate",
    "golden signals",
    "percentile",
    "p50",
    "p95",
    "p99",
}

_LOGS_KEYWORDS: set[str] = {
    "log",
    "logs",
    "logging",
    "error log",
    "exception",
    "stacktrace",
    "stack trace",
    "stderr",
    "stdout",
    "log entry",
    "log entries",
    "pattern",
    "drain",
    "severity",
    "crash",
    "panic",
    "oom",
    "oomkilled",
}

_ALERTS_KEYWORDS: set[str] = {
    "alert",
    "alerts",
    "alerting",
    "alarm",
    "alarms",
    "firing",
    "notification",
    "pager",
    "on-call",
    "oncall",
    "policy",
    "policies",
    "threshold",
    "triggered",
}


# ── Precompiled keyword patterns for word-boundary matching ──────────────


@lru_cache(maxsize=1)
def _compile_keyword_patterns() -> dict[str, list[re.Pattern[str]]]:
    r"""Compile all keyword sets into word-boundary regex patterns.

    Uses \b word boundaries so "rate" won't match inside "correlate".
    Multi-word phrases (e.g. "critical path") are matched as-is.

    Returns:
        Dict mapping category name to list of compiled patterns.
    """
    categories: dict[str, set[str]] = {
        "greeting": _GREETING_KEYWORDS,
        "conversational": _CONVERSATIONAL_KEYWORDS,
        "fast": _FAST_KEYWORDS,
        "debate": _DEBATE_KEYWORDS,
        "trace": _TRACE_KEYWORDS,
        "metrics": _METRICS_KEYWORDS,
        "logs": _LOGS_KEYWORDS,
        "alerts": _ALERTS_KEYWORDS,
        "analysis": _ANALYSIS_KEYWORDS,
    }
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for name, keywords in categories.items():
        patterns = []
        for kw in keywords:
            # Use word boundaries; for hyphenated keywords use raw match
            if "-" in kw or " " in kw:
                patterns.append(
                    re.compile(rf"(?:^|\s){re.escape(kw)}(?:\s|$)", re.IGNORECASE)
                )
            else:
                patterns.append(re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE))
        compiled[name] = patterns
    return compiled


def _count_keyword_matches(query: str, category: str) -> int:
    """Count keyword matches for a category using word-boundary patterns.

    Args:
        query: The lowercased user query.
        category: Category name (e.g. 'trace', 'metrics', 'logs', 'alerts').

    Returns:
        Number of keyword matches found.
    """
    patterns = _compile_keyword_patterns().get(category, [])
    return sum(1 for p in patterns if p.search(query))


def _has_keyword_match(query: str, category: str) -> bool:
    """Check if any keyword in the category matches the query.

    Args:
        query: The lowercased user query.
        category: Category name.

    Returns:
        True if at least one keyword matches.
    """
    patterns = _compile_keyword_patterns().get(category, [])
    return any(p.search(query) for p in patterns)


@dataclass(frozen=True)
class ClassificationResult:
    """Result of intent classification.

    Attributes:
        mode: The investigation mode (FAST, STANDARD, DEBATE).
        signal_type: Best-fit signal type for FAST mode panel routing.
            Only meaningful when mode is FAST; defaults to TRACE for
            STANDARD and DEBATE (which use all panels anyway).
    """

    mode: InvestigationMode
    signal_type: SignalType = SignalType.TRACE


def _detect_signal_type(query_lower: str) -> SignalType:
    """Detect the dominant signal type in a query.

    Uses word-boundary matching to count keyword hits for each signal type
    and returns the one with the most matches. Defaults to TRACE if no
    signal-specific keywords are found.

    Args:
        query_lower: Lowercased user query.

    Returns:
        The best-fit signal type.
    """
    signal_categories: dict[SignalType, str] = {
        SignalType.TRACE: "trace",
        SignalType.METRICS: "metrics",
        SignalType.LOGS: "logs",
        SignalType.ALERTS: "alerts",
    }
    scores = {
        signal: _count_keyword_matches(query_lower, category)
        for signal, category in signal_categories.items()
    }

    max_score = max(scores.values())
    if max_score == 0:
        return SignalType.TRACE  # Default fallback

    # Return the signal type with the highest score
    for signal_type, score in scores.items():
        if score == max_score:
            return signal_type

    return SignalType.TRACE


def classify_intent(query: str) -> InvestigationMode:
    """Classify a user query into an investigation mode.

    Uses keyword matching and pattern rules to determine the
    appropriate depth of investigation. No LLM call is made.

    Rules (applied in priority order):
    1. If query contains debate keywords/patterns -> DEBATE
    2. If query contains fast keywords and is short -> FAST
    3. Otherwise -> STANDARD

    Args:
        query: The user's investigation query.

    Returns:
        The recommended InvestigationMode.
    """
    return classify_intent_with_signal(query).mode


def classify_intent_with_signal(query: str) -> ClassificationResult:
    """Classify a user query into an investigation mode with signal type.

    Extended version of classify_intent that also determines the best
    signal type for FAST mode panel routing.

    Args:
        query: The user's investigation query.

    Returns:
        ClassificationResult with mode and signal_type.
    """
    query_lower = query.lower().strip()

    # Check for debate mode first (highest priority)
    if _has_keyword_match(query_lower, "debate"):
        return ClassificationResult(mode=InvestigationMode.DEBATE)

    for pattern in _DEBATE_PATTERNS:
        if pattern.search(query_lower):
            return ClassificationResult(mode=InvestigationMode.DEBATE)

    # Check for fast mode (short queries with status-like keywords)
    if _has_keyword_match(query_lower, "fast") and len(query_lower) < 100:
        signal_type = _detect_signal_type(query_lower)
        return ClassificationResult(
            mode=InvestigationMode.FAST,
            signal_type=signal_type,
        )

    # Default to standard
    return ClassificationResult(mode=InvestigationMode.STANDARD)


# =============================================================================
# 3-Tier Routing Classification
# =============================================================================

# Patterns for direct data retrieval queries
_DIRECT_PATTERNS: list[re.Pattern[str]] = [
    # "show me the logs", "get the traces", "list all alerts"
    re.compile(
        r"\b(show|list|get|fetch|display|give|pull|view|see)\b.*\b(logs?|traces?|alerts?|metrics?|time.?series)\b",
        re.IGNORECASE,
    ),
    # "what alerts are firing", "what metrics are available"
    re.compile(
        r"\bwhat\b.*\b(alerts?|metrics?|logs?|traces?)\b.*\b(are|is|available|firing|active|exist)\b",
        re.IGNORECASE,
    ),
    # Explicit trace ID or URL fetch
    re.compile(r"\b(trace|span)\b.*\b[0-9a-f]{16,32}\b", re.IGNORECASE),
    # "logs for service X", "metrics for project Y"
    re.compile(
        r"\b(logs?|metrics?|alerts?|traces?)\b\s+(for|from|of|in)\b",
        re.IGNORECASE,
    ),
]

# Keywords indicating analysis (SUB_AGENT tier)
# These suggest the user wants interpretation, not raw data.
_ANALYSIS_KEYWORDS: set[str] = {
    "analyze",
    "analyse",
    "analysis",
    "detect",
    "find pattern",
    "find patterns",
    "anomaly",
    "anomalies",
    "bottleneck",
    "bottlenecks",
    "compare",
    "comparison",
    "correlate",
    "correlation",
    "diagnose",
    "diagnosis",
    "explain",
    "identify",
    "inspect",
    "pattern",
    "patterns",
    "trend",
    "trends",
    "debug",
    "troubleshoot",
}

# Patterns for analysis queries (SUB_AGENT tier)
_ANALYSIS_PATTERNS: list[re.Pattern[str]] = [
    # "analyze the trace", "detect anomalies in metrics"
    re.compile(
        r"\b(analyz|analys|detect|diagnos|inspect|debug|troubleshoot)\w*\b",
        re.IGNORECASE,
    ),
    # "what's causing", "why is X slow" (single-signal scope)
    re.compile(r"\bwhat'?s?\b.*\b(wrong|happening|going on)\b", re.IGNORECASE),
    # "find the bottleneck", "identify the pattern"
    re.compile(
        r"\b(find|identify)\b.*\b(bottleneck|pattern|anomal|trend|issue)\w*\b",
        re.IGNORECASE,
    ),
    # "compare logs from X to Y", "correlate traces with metrics"
    re.compile(
        r"\b(compare|correlate)\b.*\b(logs?|traces?|metrics?|alerts?)\b",
        re.IGNORECASE,
    ),
]


@dataclass(frozen=True)
class RoutingResult:
    """Result of the 3-tier routing classification.

    Attributes:
        decision: The routing tier (DIRECT, SUB_AGENT, COUNCIL).
        signal_type: Best-fit signal type for tool/sub-agent selection.
        investigation_mode: Council investigation mode (only meaningful for COUNCIL).
        suggested_tools: Tool names suggested for DIRECT routing.
        suggested_agent: Sub-agent name suggested for SUB_AGENT routing.
    """

    decision: RoutingDecision
    signal_type: SignalType = SignalType.TRACE
    investigation_mode: InvestigationMode = InvestigationMode.STANDARD
    suggested_tools: tuple[str, ...] = ()
    suggested_agent: str = ""


# Mapping from signal type to suggested direct tools
_SIGNAL_TO_TOOLS: dict[SignalType, tuple[str, ...]] = {
    SignalType.TRACE: ("fetch_trace", "list_traces", "get_trace_by_url"),
    SignalType.METRICS: (
        "list_time_series",
        "query_promql",
        "list_metric_descriptors",
    ),
    SignalType.LOGS: ("list_log_entries", "get_logs_for_trace"),
    SignalType.ALERTS: ("list_alerts", "list_alert_policies", "get_alert"),
}

# Mapping from signal type to suggested sub-agent
_SIGNAL_TO_AGENT: dict[SignalType, str] = {
    SignalType.TRACE: "trace_analyst",
    SignalType.METRICS: "metrics_analyzer",
    SignalType.LOGS: "log_analyst",
    SignalType.ALERTS: "alert_analyst",
}


def is_greeting_or_conversational(query: str) -> bool:
    """Check whether a query is a greeting or simple conversational message.

    These queries don't require any tool calls and should be answered
    directly with a lightweight prompt for minimal latency.

    Heuristics:
    1. Contains greeting or conversational keywords.
    2. Is short (< 40 characters) and has NO signal-type keywords
       (i.e. the user isn't asking about traces, metrics, logs, or alerts).

    Args:
        query: The user's query string.

    Returns:
        True if the query is a greeting or simple conversation.
    """
    query_lower = query.lower().strip()

    if not query_lower:
        return False

    # Strip trailing punctuation for cleaner matching ("Hello!" -> "hello")
    query_clean = query_lower.rstrip("!?.,;:")

    # Exact-match very short greetings (≤ 20 chars) that are obviously greetings
    if len(query_clean) <= 20 and _has_keyword_match(query_clean, "greeting"):
        return True

    # Conversational keywords at any length
    if _has_keyword_match(query_clean, "conversational"):
        # But only if there are no SRE-signal keywords mixed in
        has_signal = any(
            _has_keyword_match(query_clean, cat)
            for cat in ("trace", "metrics", "logs", "alerts")
        )
        if not has_signal:
            return True

    # Short messages with greeting keywords (up to 60 chars for things like
    # "hey there, what can you do?" or "good morning team")
    if len(query_clean) < 60 and _has_keyword_match(query_clean, "greeting"):
        has_signal = any(
            _has_keyword_match(query_clean, cat)
            for cat in ("trace", "metrics", "logs", "alerts", "debate", "analysis")
        )
        if not has_signal:
            return True

    return False


def classify_routing(query: str) -> RoutingResult:
    """Classify a user query into a routing decision.

    Determines whether a query should be handled by:
    - GREETING: Greetings/conversational — respond directly, no tools
    - DIRECT: Individual tools for simple data retrieval
    - SUB_AGENT: Specialist sub-agents for focused analysis
    - COUNCIL: Council meeting for complex multi-signal investigation

    Rules (applied in priority order):
    0. Greeting/conversational (hi, thanks, help, etc.) -> GREETING
    1. Council keywords/patterns (root cause, incident, etc.) -> COUNCIL
    2. Analysis keywords/patterns (analyze, detect, compare, etc.) -> SUB_AGENT
    3. Direct retrieval keywords/patterns (show, list, get, etc.) -> DIRECT
    4. Default -> SUB_AGENT (analysis is a safe default)

    Args:
        query: The user's query string.

    Returns:
        RoutingResult with decision, signal_type, and routing guidance.
    """
    query_lower = query.lower().strip()

    # 0. Check for greetings/conversational (highest priority — zero-tool fast path)
    if is_greeting_or_conversational(query):
        return RoutingResult(
            decision=RoutingDecision.GREETING,
        )

    signal_type = _detect_signal_type(query_lower)

    # 1. Check for council-level queries (highest priority — complex investigations)
    # Reuse classify_intent_with_signal to avoid duplicate keyword checks.
    intent = classify_intent_with_signal(query)
    if intent.mode == InvestigationMode.DEBATE:
        return RoutingResult(
            decision=RoutingDecision.COUNCIL,
            signal_type=signal_type,
            investigation_mode=intent.mode,
        )

    # 1b. Standard multi-signal council — holistic service-health and cross-signal
    #     queries that don't reach DEBATE threshold but benefit from all 5 panels.
    for pattern in _STANDARD_COUNCIL_PATTERNS:
        if pattern.search(query_lower):
            return RoutingResult(
                decision=RoutingDecision.COUNCIL,
                signal_type=signal_type,
                investigation_mode=InvestigationMode.STANDARD,
            )

    # 2. Check for analysis queries (SUB_AGENT tier)
    if _has_keyword_match(query_lower, "analysis"):
        return RoutingResult(
            decision=RoutingDecision.SUB_AGENT,
            signal_type=signal_type,
            suggested_agent=_SIGNAL_TO_AGENT.get(signal_type, "trace_analyst"),
        )

    for pattern in _ANALYSIS_PATTERNS:
        if pattern.search(query_lower):
            return RoutingResult(
                decision=RoutingDecision.SUB_AGENT,
                signal_type=signal_type,
                suggested_agent=_SIGNAL_TO_AGENT.get(signal_type, "trace_analyst"),
            )

    # 3. Check for direct retrieval queries (keyword + pattern, or pattern alone)
    for pattern in _DIRECT_PATTERNS:
        if pattern.search(query_lower):
            return RoutingResult(
                decision=RoutingDecision.DIRECT,
                signal_type=signal_type,
                suggested_tools=_SIGNAL_TO_TOOLS.get(
                    signal_type, ("fetch_trace", "list_traces")
                ),
            )

    # 4. Default: SUB_AGENT (analysis is the safest default for an SRE agent)
    return RoutingResult(
        decision=RoutingDecision.SUB_AGENT,
        signal_type=signal_type,
        suggested_agent=_SIGNAL_TO_AGENT.get(signal_type, "trace_analyst"),
    )
