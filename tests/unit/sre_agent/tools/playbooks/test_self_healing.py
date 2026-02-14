"""Tests for the self-healing agent playbook.

Validates playbook structure, issue definitions, diagnostic steps,
and integration with the playbook registry.
"""

import pytest

from sre_agent.tools.playbooks.schemas import (
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
)
from sre_agent.tools.playbooks.self_healing import get_playbook


class TestSelfHealingPlaybook:
    """Tests for get_playbook() return value."""

    @pytest.fixture
    def playbook(self) -> Playbook:
        return get_playbook()

    def test_returns_playbook_instance(self, playbook: Playbook) -> None:
        assert isinstance(playbook, Playbook)

    def test_playbook_id(self, playbook: Playbook) -> None:
        assert playbook.playbook_id == "agent-self-healing"

    def test_category_is_observability(self, playbook: Playbook) -> None:
        assert playbook.category == PlaybookCategory.OBSERVABILITY

    def test_service_name(self, playbook: Playbook) -> None:
        assert playbook.service_name == "AutoSRE Agent"

    def test_has_issues(self, playbook: Playbook) -> None:
        assert len(playbook.issues) == 4

    def test_has_general_diagnostic_steps(self, playbook: Playbook) -> None:
        assert len(playbook.general_diagnostic_steps) >= 5

    def test_has_best_practices(self, playbook: Playbook) -> None:
        assert len(playbook.best_practices) > 0

    def test_has_key_metrics(self, playbook: Playbook) -> None:
        assert len(playbook.key_metrics) > 0

    def test_has_documentation_urls(self, playbook: Playbook) -> None:
        assert len(playbook.documentation_urls) > 0

    def test_diagnostic_steps_are_ordered(self, playbook: Playbook) -> None:
        steps = playbook.general_diagnostic_steps
        for i, step in enumerate(steps):
            assert step.step_number == i + 1

    def test_diagnostic_steps_have_tool_references(self, playbook: Playbook) -> None:
        for step in playbook.general_diagnostic_steps:
            assert step.tool_name is not None
            assert len(step.tool_name) > 0


class TestExcessiveRetriesIssue:
    """Tests for the excessive retries issue."""

    @pytest.fixture
    def issue(self) -> None:
        playbook = get_playbook()
        return next(
            i for i in playbook.issues if i.issue_id == "agent-excessive-retries"
        )

    def test_issue_exists(self, issue) -> None:
        assert issue is not None

    def test_severity_is_high(self, issue) -> None:
        assert issue.severity == PlaybookSeverity.HIGH

    def test_has_symptoms(self, issue) -> None:
        assert len(issue.symptoms) >= 2

    def test_has_root_causes(self, issue) -> None:
        assert len(issue.root_causes) >= 2

    def test_has_diagnostic_steps(self, issue) -> None:
        assert len(issue.diagnostic_steps) >= 1

    def test_has_remediation_steps(self, issue) -> None:
        assert len(issue.remediation_steps) >= 1

    def test_has_prevention_tips(self, issue) -> None:
        assert len(issue.prevention_tips) >= 1


class TestTokenWasteIssue:
    """Tests for the token waste issue."""

    @pytest.fixture
    def issue(self) -> None:
        playbook = get_playbook()
        return next(i for i in playbook.issues if i.issue_id == "agent-token-waste")

    def test_severity_is_medium(self, issue) -> None:
        assert issue.severity == PlaybookSeverity.MEDIUM

    def test_has_symptoms(self, issue) -> None:
        assert len(issue.symptoms) >= 2


class TestToolSyntaxErrorsIssue:
    """Tests for the tool syntax errors issue."""

    @pytest.fixture
    def issue(self) -> None:
        playbook = get_playbook()
        return next(
            i for i in playbook.issues if i.issue_id == "agent-tool-syntax-errors"
        )

    def test_severity_is_high(self, issue) -> None:
        assert issue.severity == PlaybookSeverity.HIGH

    def test_references_search_google(self, issue) -> None:
        tool_names = [step.tool_name for step in issue.diagnostic_steps]
        assert "search_google" in tool_names


class TestSlowInvestigationIssue:
    """Tests for the slow investigation issue."""

    @pytest.fixture
    def issue(self) -> None:
        playbook = get_playbook()
        return next(
            i for i in playbook.issues if i.issue_id == "agent-slow-investigation"
        )

    def test_severity_is_medium(self, issue) -> None:
        assert issue.severity == PlaybookSeverity.MEDIUM

    def test_has_diagnostic_steps(self, issue) -> None:
        assert len(issue.diagnostic_steps) >= 2


class TestPlaybookRegistryIntegration:
    """Test that the self-healing playbook loads into the registry."""

    def test_loads_in_registry(self) -> None:
        from sre_agent.tools.playbooks.registry import PlaybookRegistry

        registry = PlaybookRegistry()
        registry.load_all_playbooks()

        pb = registry.get("agent-self-healing")
        assert pb is not None
        assert pb.service_name == "AutoSRE Agent"

    def test_searchable_by_category(self) -> None:
        from sre_agent.tools.playbooks.registry import PlaybookRegistry

        registry = PlaybookRegistry()
        registry.load_all_playbooks()

        results = registry.get_by_category(PlaybookCategory.OBSERVABILITY)
        ids = [p.playbook_id for p in results]
        assert "agent-self-healing" in ids

    def test_issue_retrieval(self) -> None:
        from sre_agent.tools.playbooks.registry import PlaybookRegistry

        registry = PlaybookRegistry()
        registry.load_all_playbooks()

        issue = registry.get_issue("agent-self-healing", "agent-excessive-retries")
        assert issue is not None
        assert issue.title == "Agent Excessive Tool Retries"
