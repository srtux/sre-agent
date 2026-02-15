"""Integration test: verify all playbooks load correctly with unique IDs.

Ensures the playbook registry can load all registered playbooks without
errors and that there are no duplicate playbook or issue IDs.
"""

from sre_agent.tools.playbooks.registry import get_playbook_registry
from sre_agent.tools.playbooks.schemas import Playbook


class TestPlaybookDataIntegrity:
    """Verify playbook registry loads all playbooks without errors."""

    def test_registry_loads_all_playbooks(self) -> None:
        """All playbooks must load without exceptions."""
        registry = get_playbook_registry()
        playbooks = registry.list_all()
        assert len(playbooks) > 0, "No playbooks found in registry"

    def test_all_playbooks_are_valid(self) -> None:
        """Each entry must be a Playbook instance."""
        registry = get_playbook_registry()
        for playbook in registry.list_all():
            assert isinstance(playbook, Playbook), (
                f"Expected Playbook, got {type(playbook).__name__}"
            )

    def test_playbook_ids_are_unique(self) -> None:
        """No two playbooks should share the same playbook_id."""
        registry = get_playbook_registry()
        ids = [p.playbook_id for p in registry.list_all()]
        assert len(ids) == len(set(ids)), (
            f"Duplicate playbook IDs found: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_issue_ids_are_globally_unique(self) -> None:
        """Issue IDs should be unique across all playbooks."""
        registry = get_playbook_registry()
        all_issue_ids: list[str] = []
        for playbook in registry.list_all():
            for issue in playbook.issues:
                all_issue_ids.append(issue.issue_id)
        assert len(all_issue_ids) == len(set(all_issue_ids)), (
            f"Duplicate issue IDs found: "
            f"{[x for x in all_issue_ids if all_issue_ids.count(x) > 1]}"
        )

    def test_each_playbook_has_issues(self) -> None:
        """Every playbook must define at least one issue."""
        registry = get_playbook_registry()
        for playbook in registry.list_all():
            assert len(playbook.issues) > 0, (
                f"Playbook '{playbook.playbook_id}' has no issues defined"
            )

    def test_at_least_some_playbooks_have_diagnostic_steps(self) -> None:
        """At least some playbooks should define general diagnostic steps.

        The general_diagnostic_steps field is optional (default_factory=list),
        so not every playbook is required to have them. But we verify at least
        one does to catch registry-wide regressions.
        """
        registry = get_playbook_registry()
        with_steps = [
            p for p in registry.list_all() if len(p.general_diagnostic_steps) > 0
        ]
        assert len(with_steps) > 0, "No playbooks have general diagnostic steps"

    def test_playbook_service_names_are_unique(self) -> None:
        """Each playbook should cover a different service."""
        registry = get_playbook_registry()
        services = [p.service_name for p in registry.list_all()]
        assert len(services) == len(set(services)), (
            f"Duplicate service names: {[x for x in services if services.count(x) > 1]}"
        )
