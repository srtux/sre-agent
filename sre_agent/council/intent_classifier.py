"""Rule-based intent classifier for investigation mode selection.

Classifies user queries into investigation modes without an LLM call:
- FAST: Quick status checks, single-service queries
- STANDARD: Multi-signal investigation, general analysis
- DEBATE: Deep dive, root cause analysis, production incidents
"""

import re

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


def classify_intent(query: str) -> InvestigationMode:
    """Classify a user query into an investigation mode.

    Uses keyword matching and pattern rules to determine the
    appropriate depth of investigation. No LLM call is made.

    Rules (applied in priority order):
    1. If query contains debate keywords/patterns → DEBATE
    2. If query contains fast keywords and is short → FAST
    3. Otherwise → STANDARD

    Args:
        query: The user's investigation query.

    Returns:
        The recommended InvestigationMode.
    """
    query_lower = query.lower().strip()

    # Check for debate mode first (highest priority)
    for keyword in _DEBATE_KEYWORDS:
        if keyword in query_lower:
            return InvestigationMode.DEBATE

    for pattern in _DEBATE_PATTERNS:
        if pattern.search(query_lower):
            return InvestigationMode.DEBATE

    # Check for fast mode (short queries with status-like keywords)
    query_words = set(re.findall(r"\b\w+\b", query_lower))
    if query_words & _FAST_KEYWORDS and len(query_lower) < 100:
        return InvestigationMode.FAST

    # Default to standard
    return InvestigationMode.STANDARD
