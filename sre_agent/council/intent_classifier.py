"""Rule-based intent classifier for investigation mode selection.

Classifies user queries into investigation modes without an LLM call:
- FAST: Quick status checks, single-service queries
- STANDARD: Multi-signal investigation, general analysis
- DEBATE: Deep dive, root cause analysis, production incidents

Also determines the best signal type for FAST mode panel selection,
so the orchestrator routes to the most relevant panel (trace, metrics,
logs, or alerts) rather than always defaulting to traces.
"""

import re
from dataclasses import dataclass
from enum import Enum

from .schemas import InvestigationMode

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

    Counts keyword matches for each signal type and returns the
    one with the most hits. Defaults to TRACE if no signal-specific
    keywords are found.

    Args:
        query_lower: Lowercased user query.

    Returns:
        The best-fit signal type.
    """
    scores: dict[SignalType, int] = {
        SignalType.TRACE: 0,
        SignalType.METRICS: 0,
        SignalType.LOGS: 0,
        SignalType.ALERTS: 0,
    }

    for keyword in _TRACE_KEYWORDS:
        if keyword in query_lower:
            scores[SignalType.TRACE] += 1

    for keyword in _METRICS_KEYWORDS:
        if keyword in query_lower:
            scores[SignalType.METRICS] += 1

    for keyword in _LOGS_KEYWORDS:
        if keyword in query_lower:
            scores[SignalType.LOGS] += 1

    for keyword in _ALERTS_KEYWORDS:
        if keyword in query_lower:
            scores[SignalType.ALERTS] += 1

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
    for keyword in _DEBATE_KEYWORDS:
        if keyword in query_lower:
            return ClassificationResult(mode=InvestigationMode.DEBATE)

    for pattern in _DEBATE_PATTERNS:
        if pattern.search(query_lower):
            return ClassificationResult(mode=InvestigationMode.DEBATE)

    # Check for fast mode (short queries with status-like keywords)
    query_words = set(re.findall(r"\b\w+\b", query_lower))
    if query_words & _FAST_KEYWORDS and len(query_lower) < 100:
        signal_type = _detect_signal_type(query_lower)
        return ClassificationResult(
            mode=InvestigationMode.FAST,
            signal_type=signal_type,
        )

    # Default to standard
    return ClassificationResult(mode=InvestigationMode.STANDARD)
