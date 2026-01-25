"""Tests for the Prompt Composer."""

import pytest

from sre_agent.core.prompt_composer import (
    DomainContext,
    PromptComposer,
    PromptRole,
    SessionSummary,
    get_prompt_composer,
)


class TestPromptRole:
    """Tests for PromptRole enum."""

    def test_prompt_roles(self) -> None:
        """Test prompt role values."""
        assert PromptRole.SYSTEM.value == "system"
        assert PromptRole.DEVELOPER.value == "developer"
        assert PromptRole.USER.value == "user"


class TestDomainContext:
    """Tests for DomainContext dataclass."""

    def test_create_domain_context(self) -> None:
        """Test creating a domain context."""
        context = DomainContext(
            project_id="my-project",
            active_alerts=["Alert 1", "Alert 2"],
            runbook_content="Steps to follow...",
            investigation_phase="TRIAGE",
            custom_constraints=["Don't restart pods"],
        )

        assert context.project_id == "my-project"
        assert len(context.active_alerts) == 2
        assert context.runbook_content == "Steps to follow..."
        assert context.investigation_phase == "TRIAGE"

    def test_empty_domain_context(self) -> None:
        """Test empty domain context."""
        context = DomainContext()

        assert context.project_id is None
        assert len(context.active_alerts) == 0
        assert context.runbook_content is None


class TestSessionSummary:
    """Tests for SessionSummary dataclass."""

    def test_create_session_summary(self) -> None:
        """Test creating a session summary."""
        summary = SessionSummary(
            summary_text="Investigation of checkout latency",
            key_findings=["Bottleneck in db-service"],
            tools_used=["fetch_trace", "query_promql"],
            last_compaction_turn=10,
        )

        assert "checkout" in summary.summary_text.lower()
        assert len(summary.key_findings) == 1
        assert len(summary.tools_used) == 2
        assert summary.last_compaction_turn == 10


class TestPromptComposer:
    """Tests for PromptComposer."""

    @pytest.fixture
    def composer(self) -> PromptComposer:
        """Create a prompt composer for testing."""
        return PromptComposer()

    def test_compose_system_role(self, composer: PromptComposer) -> None:
        """Test composing system role content."""
        content = composer.compose_system_role()

        assert content.role == "user"
        assert len(content.parts) == 1

        text = content.parts[0].text
        assert "SRE Agent" in text
        assert "SANDBOXED" in text
        assert "READ-ONLY" in text

    def test_compose_developer_role_empty(self, composer: PromptComposer) -> None:
        """Test composing developer role without context."""
        content = composer.compose_developer_role()

        assert content.role == "user"
        text = content.parts[0].text
        assert "Hard Constraints" in text
        assert "OODA" in text
        assert "Current Time" in text

    def test_compose_developer_role_with_project(
        self, composer: PromptComposer
    ) -> None:
        """Test composing developer role with project context."""
        domain_context = DomainContext(project_id="my-project-123")
        content = composer.compose_developer_role(domain_context)

        text = content.parts[0].text
        assert "my-project-123" in text
        assert "CURRENT PROJECT" in text

    def test_compose_developer_role_with_alerts(
        self, composer: PromptComposer
    ) -> None:
        """Test composing developer role with active alerts."""
        domain_context = DomainContext(
            active_alerts=["High CPU on frontend", "Database connection errors"]
        )
        content = composer.compose_developer_role(domain_context)

        text = content.parts[0].text
        assert "Active Alerts" in text
        assert "High CPU" in text

    def test_compose_developer_role_with_phase(
        self, composer: PromptComposer
    ) -> None:
        """Test composing developer role with investigation phase."""
        domain_context = DomainContext(investigation_phase="DEEP_DIVE")
        content = composer.compose_developer_role(domain_context)

        text = content.parts[0].text
        assert "DEEP_DIVE" in text
        assert "Investigation Phase" in text

    def test_compose_developer_role_with_runbook(
        self, composer: PromptComposer
    ) -> None:
        """Test composing developer role with runbook content."""
        domain_context = DomainContext(
            runbook_content="1. Check logs\n2. Restart service"
        )
        content = composer.compose_developer_role(domain_context)

        text = content.parts[0].text
        assert "Runbook Context" in text
        assert "Check logs" in text

    def test_compose_developer_role_with_constraints(
        self, composer: PromptComposer
    ) -> None:
        """Test composing developer role with custom constraints."""
        domain_context = DomainContext(
            custom_constraints=["Don't restart production pods"]
        )
        content = composer.compose_developer_role(domain_context)

        text = content.parts[0].text
        assert "Custom Constraints" in text
        assert "production pods" in text

    def test_compose_user_role_simple(self, composer: PromptComposer) -> None:
        """Test composing user role with simple message."""
        content = composer.compose_user_role(
            user_message="What's causing the latency spike?"
        )

        assert content.role == "user"
        text = content.parts[0].text
        assert "Current Request" in text
        assert "latency spike" in text

    def test_compose_user_role_with_summary(self, composer: PromptComposer) -> None:
        """Test composing user role with session summary."""
        summary = SessionSummary(
            summary_text="Previous investigation found db issues",
            key_findings=["Database bottleneck"],
            tools_used=["fetch_trace"],
        )
        content = composer.compose_user_role(
            user_message="Continue investigating",
            session_summary=summary,
        )

        text = content.parts[0].text
        assert "Session Summary" in text
        assert "db issues" in text
        assert "Database bottleneck" in text
        assert "fetch_trace" in text

    def test_compose_user_role_with_recent_events(
        self, composer: PromptComposer
    ) -> None:
        """Test composing user role with recent events."""
        events = [
            {"type": "tool_call", "content": "Calling fetch_trace", "timestamp": "T1"},
            {
                "type": "tool_output",
                "content": "Found 10 spans",
                "timestamp": "T2",
            },
        ]
        content = composer.compose_user_role(
            user_message="What next?",
            recent_events=events,
        )

        text = content.parts[0].text
        assert "Recent Events" in text
        assert "tool_call" in text
        assert "10 spans" in text

    def test_compose_full_prompt(self, composer: PromptComposer) -> None:
        """Test composing full three-tier prompt."""
        domain_context = DomainContext(
            project_id="test-project",
            investigation_phase="TRIAGE",
        )
        summary = SessionSummary(
            summary_text="Started investigating",
            key_findings=[],
            tools_used=[],
        )

        contents = composer.compose_full_prompt(
            user_message="Find the root cause",
            domain_context=domain_context,
            session_summary=summary,
        )

        assert len(contents) == 3  # System, Developer, User

        # Verify each tier is present
        combined = "".join(c.parts[0].text for c in contents)
        assert "SRE Agent" in combined  # System
        assert "test-project" in combined  # Developer
        assert "root cause" in combined  # User

    def test_add_system_capability(self, composer: PromptComposer) -> None:
        """Test adding custom capability to system role."""
        composer.add_system_capability("Can analyze Kubernetes HPA events")

        content = composer.compose_system_role()
        text = content.parts[0].text

        assert "Additional Capabilities" in text
        assert "Kubernetes HPA" in text

    def test_create_tool_guidance(self, composer: PromptComposer) -> None:
        """Test creating tool guidance text."""
        guidance = composer.create_tool_guidance(
            tool_name="fetch_trace",
            context="Investigating latency in checkout service",
        )

        assert "fetch_trace" in guidance
        assert "checkout service" in guidance
        assert "Remember" in guidance

    def test_format_recent_events_truncation(self, composer: PromptComposer) -> None:
        """Test that recent events are truncated if too long."""
        events = [{"type": "tool_output", "content": "x" * 1000, "timestamp": "T1"}]

        formatted = composer._format_recent_events(events)

        assert len(formatted) < 1000
        assert "truncated" in formatted

    def test_format_recent_events_limit(self, composer: PromptComposer) -> None:
        """Test that recent events are limited."""
        events = [{"type": "test", "content": f"Event {i}", "timestamp": f"T{i}"} for i in range(10)]

        formatted = composer._format_recent_events(events, max_events=3)

        # Should only have last 3 events
        assert "Event 7" in formatted
        assert "Event 8" in formatted
        assert "Event 9" in formatted
        assert "Event 0" not in formatted


class TestPromptComposerSingleton:
    """Tests for singleton access."""

    def test_get_prompt_composer_singleton(self) -> None:
        """Test that get_prompt_composer returns singleton."""
        composer1 = get_prompt_composer()
        composer2 = get_prompt_composer()

        assert composer1 is composer2
