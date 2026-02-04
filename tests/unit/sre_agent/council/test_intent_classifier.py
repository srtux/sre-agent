"""Tests for the rule-based intent classifier.

Validates that queries are correctly classified into
investigation modes based on keyword and pattern matching.
"""

import pytest

from sre_agent.council.intent_classifier import classify_intent
from sre_agent.council.schemas import InvestigationMode


class TestFastModeClassification:
    """Tests for FAST mode classification."""

    @pytest.mark.parametrize(
        "query",
        [
            "check the status of payment-service",
            "is the API up?",
            "quick health check",
            "current status overview",
            "brief summary of the system",
            "glance at checkout service",
        ],
    )
    def test_fast_keywords(self, query: str) -> None:
        """Queries with fast keywords should classify as FAST."""
        assert classify_intent(query) == InvestigationMode.FAST

    def test_long_query_not_fast(self) -> None:
        """Long queries with fast keywords should NOT classify as FAST."""
        long_query = (
            "Can you give me a quick status check on all the microservices including the payment gateway, authentication service, inventory system, and the notification service? "
            * 2
        )
        assert classify_intent(long_query) != InvestigationMode.FAST


class TestDebateModeClassification:
    """Tests for DEBATE mode classification."""

    @pytest.mark.parametrize(
        "query",
        [
            "find the root cause of the latency spike",
            "deep dive into the checkout failure",
            "we have a production incident on payment-service",
            "this is a P0 — payments are failing",
            "sev1 alert on the API gateway",
            "what caused the outage at 2pm?",
            "why is the service failing?",
            "investigate the error rate spike",
            "comprehensive analysis of the system",
            "run all panels and cross-examine the findings",
            "emergency — database connections exhausted",
            "blast radius of the auth-service failure",
            "do a thorough analysis of the latency",
            "we need a postmortem on yesterday's incident",
        ],
    )
    def test_debate_keywords(self, query: str) -> None:
        """Queries with debate keywords should classify as DEBATE."""
        assert classify_intent(query) == InvestigationMode.DEBATE

    def test_debate_takes_priority_over_fast(self) -> None:
        """If both fast and debate keywords present, DEBATE wins."""
        query = "quick check on the root cause of the incident"
        assert classify_intent(query) == InvestigationMode.DEBATE


class TestStandardModeClassification:
    """Tests for STANDARD mode (default) classification."""

    @pytest.mark.parametrize(
        "query",
        [
            "analyze the latency for checkout-service in the last hour",
            "show me the error rates across services",
            "compare traces from yesterday vs today",
            "what's happening with the API response times?",
            "look at the metrics for the database",
            "find traces with high latency",
        ],
    )
    def test_standard_default(self, query: str) -> None:
        """General analysis queries should classify as STANDARD."""
        assert classify_intent(query) == InvestigationMode.STANDARD

    def test_empty_query(self) -> None:
        """Empty query should default to STANDARD."""
        assert classify_intent("") == InvestigationMode.STANDARD

    def test_generic_question(self) -> None:
        """Generic technical question should default to STANDARD."""
        assert (
            classify_intent("how are the services performing today?")
            == InvestigationMode.STANDARD
        )
