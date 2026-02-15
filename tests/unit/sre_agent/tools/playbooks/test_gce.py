"""Tests for GCE (Compute Engine) playbook."""

from sre_agent.tools.playbooks.gce import get_playbook
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
        assert playbook.playbook_id == "gce-troubleshooting"

    def test_has_service_name(self) -> None:
        playbook = get_playbook()
        assert playbook.service_name == "Compute Engine"

    def test_has_display_name(self) -> None:
        playbook = get_playbook()
        assert playbook.display_name == "Compute Engine"

    def test_has_valid_category(self) -> None:
        playbook = get_playbook()
        assert playbook.category is PlaybookCategory.COMPUTE

    def test_has_description(self) -> None:
        playbook = get_playbook()
        assert len(playbook.description) > 10

    def test_has_expected_issue_count(self) -> None:
        playbook = get_playbook()
        assert len(playbook.issues) == 3  # vm_not_starting, ssh_failure, high_cpu

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

    def test_no_general_diagnostic_steps(self) -> None:
        playbook = get_playbook()
        assert len(playbook.general_diagnostic_steps) == 0

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

    def test_expected_issue_ids(self) -> None:
        playbook = get_playbook()
        issue_ids = {issue.issue_id for issue in playbook.issues}
        expected = {
            "gce-vm-not-starting",
            "gce-ssh-failure",
            "gce-high-cpu",
        }
        assert issue_ids == expected

    def test_version_defaults_to_1_0_0(self) -> None:
        playbook = get_playbook()
        assert playbook.version == "1.0.0"
