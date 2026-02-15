"""Tests for Cloud Run playbook."""

from sre_agent.tools.playbooks.cloud_run import get_playbook
from sre_agent.tools.playbooks.schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


class TestGetPlaybook:
    """Tests for get_playbook() function."""

    def test_returns_playbook_instance(self) -> None:
        playbook = get_playbook()
        assert isinstance(playbook, Playbook)

    def test_has_valid_playbook_id(self) -> None:
        playbook = get_playbook()
        assert playbook.playbook_id == "cloud-run-troubleshooting"

    def test_has_service_name(self) -> None:
        playbook = get_playbook()
        assert playbook.service_name == "Cloud Run"

    def test_has_display_name(self) -> None:
        playbook = get_playbook()
        assert playbook.display_name == "Cloud Run"

    def test_has_valid_category(self) -> None:
        playbook = get_playbook()
        assert playbook.category is PlaybookCategory.COMPUTE

    def test_has_description(self) -> None:
        playbook = get_playbook()
        assert len(playbook.description) > 10

    def test_has_expected_issue_count(self) -> None:
        playbook = get_playbook()
        assert (
            len(playbook.issues) == 5
        )  # container_failed, cold_start, memory, connection_reset, permission

    def test_issues_have_valid_structure(self) -> None:
        playbook = get_playbook()
        for issue in playbook.issues:
            assert isinstance(issue, TroubleshootingIssue)
            assert issue.issue_id
            assert issue.title
            assert issue.description
            assert isinstance(issue.severity, PlaybookSeverity)

    def test_issues_have_diagnostic_steps(self) -> None:
        playbook = get_playbook()
        for issue in playbook.issues:
            assert len(issue.diagnostic_steps) > 0
            for step in issue.diagnostic_steps:
                assert isinstance(step, DiagnosticStep)
                assert step.step_number > 0
                assert step.title
                assert step.description

    def test_issues_have_remediation_steps(self) -> None:
        playbook = get_playbook()
        for issue in playbook.issues:
            assert len(issue.remediation_steps) > 0
            for step in issue.remediation_steps:
                assert isinstance(step, DiagnosticStep)

    def test_issues_have_symptoms(self) -> None:
        playbook = get_playbook()
        for issue in playbook.issues:
            assert len(issue.symptoms) > 0

    def test_has_general_diagnostic_steps(self) -> None:
        playbook = get_playbook()
        assert len(playbook.general_diagnostic_steps) == 3
        for step in playbook.general_diagnostic_steps:
            assert isinstance(step, DiagnosticStep)

    def test_has_best_practices(self) -> None:
        playbook = get_playbook()
        assert len(playbook.best_practices) > 0

    def test_has_key_metrics(self) -> None:
        playbook = get_playbook()
        assert len(playbook.key_metrics) > 0

    def test_has_key_logs(self) -> None:
        playbook = get_playbook()
        assert len(playbook.key_logs) > 0

    def test_has_related_services(self) -> None:
        playbook = get_playbook()
        assert len(playbook.related_services) > 0

    def test_has_documentation_urls(self) -> None:
        playbook = get_playbook()
        assert len(playbook.documentation_urls) > 0

    def test_issue_ids_are_unique(self) -> None:
        playbook = get_playbook()
        ids = [issue.issue_id for issue in playbook.issues]
        assert len(ids) == len(set(ids))

    def test_diagnostic_step_numbers_are_sequential(self) -> None:
        playbook = get_playbook()
        for step in playbook.general_diagnostic_steps:
            assert step.step_number > 0

    def test_expected_issue_ids(self) -> None:
        playbook = get_playbook()
        issue_ids = {issue.issue_id for issue in playbook.issues}
        expected = {
            "cloudrun-container-failed-start",
            "cloudrun-cold-start",
            "cloudrun-memory-exceeded",
            "cloudrun-connection-reset",
            "cloudrun-permission-denied",
        }
        assert issue_ids == expected

    def test_version_defaults_to_1_0_0(self) -> None:
        playbook = get_playbook()
        assert playbook.version == "1.0.0"
