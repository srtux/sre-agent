"""Tests for the rule-based intent classifier.

Validates that queries are correctly classified into
investigation modes based on keyword and pattern matching,
and that greetings/conversational queries are detected.
"""

import pytest

from sre_agent.council.intent_classifier import (
    classify_intent,
    classify_routing,
    is_greeting_or_conversational,
)
from sre_agent.council.schemas import InvestigationMode, RoutingDecision


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


class TestGreetingDetection:
    """Tests for greeting and conversational query detection."""

    @pytest.mark.parametrize(
        "query",
        [
            "hi",
            "hello",
            "hey",
            "howdy",
            "Hi!",
            "Hello there",
            "hey there",
            "good morning",
            "Good afternoon!",
            "good evening",
            "hiya",
            "yo",
            "sup",
        ],
    )
    def test_greetings_detected(self, query: str) -> None:
        """Simple greetings should be detected."""
        assert is_greeting_or_conversational(query) is True

    @pytest.mark.parametrize(
        "query",
        [
            "thanks",
            "thank you",
            "thx",
            "bye",
            "goodbye",
            "who are you",
            "what can you do",
            "what are you",
            "help me",
            "how do you work",
            "introduce yourself",
        ],
    )
    def test_conversational_detected(self, query: str) -> None:
        """Conversational queries should be detected."""
        assert is_greeting_or_conversational(query) is True

    @pytest.mark.parametrize(
        "query",
        [
            "show me the logs for checkout-service",
            "analyze the trace for latency bottlenecks",
            "find the root cause of the latency spike",
            "check the status of payment-service",
            "list all alerts",
            "what metrics are available for CPU",
        ],
    )
    def test_sre_queries_not_greetings(self, query: str) -> None:
        """SRE-related queries should NOT be classified as greetings."""
        assert is_greeting_or_conversational(query) is False

    def test_empty_query_not_greeting(self) -> None:
        """Empty queries should not be classified as greetings."""
        assert is_greeting_or_conversational("") is False

    def test_greeting_with_sre_context_not_greeting(self) -> None:
        """Greeting combined with SRE keywords should not be a greeting."""
        assert (
            is_greeting_or_conversational("hi, show me the traces for payment-service")
            is False
        )

    def test_thanks_with_signal_not_greeting(self) -> None:
        """Conversational word with signal keywords should not be a greeting."""
        assert is_greeting_or_conversational("thanks, now analyze the metrics") is False


class TestGreetingRouting:
    """Tests that greeting queries are routed to the GREETING tier."""

    @pytest.mark.parametrize(
        "query",
        [
            "hi",
            "hello",
            "hey there",
            "good morning",
            "thanks",
            "who are you",
            "what can you do",
        ],
    )
    def test_greeting_routed_to_greeting_tier(self, query: str) -> None:
        """Greetings should route to GREETING tier."""
        result = classify_routing(query)
        assert result.decision == RoutingDecision.GREETING

    def test_greeting_tier_has_no_suggested_tools(self) -> None:
        """GREETING tier should have empty suggested_tools."""
        result = classify_routing("hello")
        assert result.suggested_tools == ()

    def test_greeting_tier_has_no_suggested_agent(self) -> None:
        """GREETING tier should have empty suggested_agent."""
        result = classify_routing("hey")
        assert result.suggested_agent == ""

    def test_sre_query_not_routed_to_greeting(self) -> None:
        """SRE queries should not be routed to GREETING tier."""
        result = classify_routing("show me the logs")
        assert result.decision != RoutingDecision.GREETING


class TestStandardCouncilRouting:
    """Tests for the STANDARD council routing tier."""

    @pytest.mark.parametrize(
        "query",
        [
            "what is happening with the checkout service",
            "what are the issues with the auth system",
            "the payment API is slow",
            "look into the health of the auth service",
            "end-to-end diagnostic of the pipeline",
            "how is the checkout service performing",
            "performance issue with the gateway",
            "health of the payment service",
            "service health for recommendation-service",
            "system health overview",
            "the checkout app is degraded",
            "figure out what is wrong with the api service",
        ],
    )
    def test_standard_council_queries(self, query: str) -> None:
        """Multi-signal service-health queries should route to COUNCIL + STANDARD."""
        from sre_agent.council.schemas import InvestigationMode

        result = classify_routing(query)
        assert result.decision == RoutingDecision.COUNCIL, (
            f"Expected COUNCIL but got {result.decision} for: {query!r}"
        )
        assert result.investigation_mode == InvestigationMode.STANDARD, (
            f"Expected STANDARD but got {result.investigation_mode} for: {query!r}"
        )

    def test_debate_still_wins_over_standard(self) -> None:
        """DEBATE-level queries must not be downgraded to STANDARD."""
        from sre_agent.council.schemas import InvestigationMode

        result = classify_routing("root cause of the payment service outage")
        assert result.decision == RoutingDecision.COUNCIL
        assert result.investigation_mode == InvestigationMode.DEBATE

    def test_direct_retrieval_not_upgraded_to_council(self) -> None:
        """Simple data-retrieval queries must not be upgraded to COUNCIL."""
        result = classify_routing("show me the logs for pod X")
        assert result.decision == RoutingDecision.DIRECT

    def test_single_signal_analysis_stays_sub_agent(self) -> None:
        """Focused single-signal analysis should remain SUB_AGENT."""
        result = classify_routing("analyze trace patterns for service Y")
        assert result.decision == RoutingDecision.SUB_AGENT
