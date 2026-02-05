"""Unit tests for playbook schemas."""

import pytest
from pydantic import ValidationError

from sre_agent.tools.playbooks.schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSearchResult,
    PlaybookSeverity,
    TroubleshootingIssue,
)


class TestDiagnosticStep:
    """Tests for DiagnosticStep schema."""

    def test_create_minimal_step(self):
        """Test creating a step with minimal required fields."""
        step = DiagnosticStep(
            step_number=1,
            title="Check Status",
            description="Verify the service is running",
        )
        assert step.step_number == 1
        assert step.title == "Check Status"
        assert step.command is None
        assert step.tool_name is None

    def test_create_full_step(self):
        """Test creating a step with all fields."""
        step = DiagnosticStep(
            step_number=1,
            title="Check Logs",
            description="Review application logs",
            command="kubectl logs -n default my-pod",
            tool_name="list_log_entries",
            tool_params={"filter_str": "severity>=ERROR"},
            expected_outcome="Logs retrieved",
            failure_action="Check pod exists",
            documentation_url="https://example.com/docs",
        )
        assert step.command == "kubectl logs -n default my-pod"
        assert step.tool_name == "list_log_entries"
        assert step.tool_params == {"filter_str": "severity>=ERROR"}

    def test_step_is_frozen(self):
        """Test that steps are immutable."""
        step = DiagnosticStep(
            step_number=1,
            title="Test",
            description="Test step",
        )
        with pytest.raises(ValidationError):
            step.title = "Modified"  # type: ignore


class TestTroubleshootingIssue:
    """Tests for TroubleshootingIssue schema."""

    def test_create_issue(self):
        """Test creating a troubleshooting issue."""
        issue = TroubleshootingIssue(
            issue_id="test-issue-001",
            title="Test Issue",
            description="A test issue for unit testing",
            symptoms=["Symptom 1", "Symptom 2"],
            root_causes=["Cause 1"],
            severity=PlaybookSeverity.HIGH,
            diagnostic_steps=[
                DiagnosticStep(
                    step_number=1,
                    title="Step 1",
                    description="First step",
                )
            ],
            remediation_steps=[
                DiagnosticStep(
                    step_number=1,
                    title="Fix 1",
                    description="First fix",
                )
            ],
        )
        assert issue.issue_id == "test-issue-001"
        assert len(issue.symptoms) == 2
        assert issue.severity == PlaybookSeverity.HIGH

    def test_issue_with_optional_fields(self):
        """Test issue with all optional fields."""
        issue = TroubleshootingIssue(
            issue_id="test-002",
            title="Full Issue",
            description="Issue with all fields",
            symptoms=["S1"],
            root_causes=["C1"],
            severity=PlaybookSeverity.CRITICAL,
            diagnostic_steps=[],
            remediation_steps=[],
            prevention_tips=["Tip 1"],
            related_metrics=["metric.type/name"],
            related_logs=["resource.type=k8s"],
            error_codes=["E001", "E002"],
            documentation_urls=["https://docs.example.com"],
        )
        assert len(issue.prevention_tips) == 1
        assert len(issue.error_codes) == 2


class TestPlaybook:
    """Tests for Playbook schema."""

    def test_create_playbook(self):
        """Test creating a complete playbook."""
        playbook = Playbook(
            playbook_id="test-playbook",
            service_name="TestService",
            display_name="Test Service",
            category=PlaybookCategory.COMPUTE,
            description="A test playbook",
            issues=[
                TroubleshootingIssue(
                    issue_id="issue-1",
                    title="Issue 1",
                    description="First issue",
                    symptoms=["S1"],
                    root_causes=["C1"],
                    severity=PlaybookSeverity.MEDIUM,
                    diagnostic_steps=[],
                    remediation_steps=[],
                )
            ],
        )
        assert playbook.playbook_id == "test-playbook"
        assert playbook.category == PlaybookCategory.COMPUTE
        assert len(playbook.issues) == 1
        assert playbook.version == "1.0.0"

    def test_playbook_categories(self):
        """Test all playbook categories."""
        categories = [
            PlaybookCategory.COMPUTE,
            PlaybookCategory.DATA,
            PlaybookCategory.STORAGE,
            PlaybookCategory.MESSAGING,
            PlaybookCategory.AI_ML,
            PlaybookCategory.OBSERVABILITY,
            PlaybookCategory.SECURITY,
            PlaybookCategory.NETWORKING,
            PlaybookCategory.MANAGEMENT,
        ]
        for cat in categories:
            assert cat.value is not None


class TestPlaybookSearchResult:
    """Tests for PlaybookSearchResult schema."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = PlaybookSearchResult(
            playbook_id="pb-001",
            service_name="GKE",
            relevance_score=0.85,
            match_reason="Matched symptom: Pod crash",
        )
        assert result.playbook_id == "pb-001"
        assert result.relevance_score == 0.85
        assert result.issue_id is None

    def test_search_result_with_issue(self):
        """Test search result with issue match."""
        result = PlaybookSearchResult(
            playbook_id="pb-001",
            service_name="GKE",
            issue_id="issue-001",
            issue_title="Pod CrashLoopBackOff",
            relevance_score=0.95,
            match_reason="Matched issue title",
        )
        assert result.issue_id == "issue-001"
        assert result.issue_title == "Pod CrashLoopBackOff"

    def test_relevance_score_bounds(self):
        """Test that relevance score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            PlaybookSearchResult(
                playbook_id="pb-001",
                service_name="GKE",
                relevance_score=1.5,  # Invalid: > 1.0
                match_reason="Test",
            )

        with pytest.raises(ValidationError):
            PlaybookSearchResult(
                playbook_id="pb-001",
                service_name="GKE",
                relevance_score=-0.1,  # Invalid: < 0.0
                match_reason="Test",
            )
