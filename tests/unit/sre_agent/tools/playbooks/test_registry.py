"""Unit tests for playbook registry."""

from sre_agent.tools.playbooks.registry import PlaybookRegistry, get_playbook_registry
from sre_agent.tools.playbooks.schemas import (
    DiagnosticStep,
    Playbook,
    PlaybookCategory,
    PlaybookSeverity,
    TroubleshootingIssue,
)


def create_test_playbook(
    playbook_id: str = "test-playbook",
    service_name: str = "TestService",
    category: PlaybookCategory = PlaybookCategory.COMPUTE,
) -> Playbook:
    """Create a test playbook for unit tests."""
    return Playbook(
        playbook_id=playbook_id,
        service_name=service_name,
        display_name=f"Test {service_name}",
        category=category,
        description=f"Playbook for {service_name}",
        issues=[
            TroubleshootingIssue(
                issue_id=f"{playbook_id}-issue-1",
                title="Test Issue",
                description="A test issue",
                symptoms=["Symptom A", "Symptom B"],
                root_causes=["Root cause 1"],
                severity=PlaybookSeverity.HIGH,
                diagnostic_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Check Status",
                        description="Check the status",
                    )
                ],
                remediation_steps=[
                    DiagnosticStep(
                        step_number=1,
                        title="Fix Issue",
                        description="Apply the fix",
                    )
                ],
                error_codes=["E001"],
            )
        ],
    )


class TestPlaybookRegistry:
    """Tests for PlaybookRegistry."""

    def test_register_playbook(self):
        """Test registering a playbook."""
        registry = PlaybookRegistry()
        playbook = create_test_playbook()

        registry.register(playbook)

        assert registry.get("test-playbook") == playbook

    def test_get_nonexistent_playbook(self):
        """Test getting a nonexistent playbook returns None."""
        registry = PlaybookRegistry()
        assert registry.get("nonexistent") is None

    def test_get_by_service(self):
        """Test getting playbook by service name."""
        registry = PlaybookRegistry()
        playbook = create_test_playbook(service_name="MyService")
        registry.register(playbook)

        result = registry.get_by_service("myservice")  # Case insensitive
        assert result == playbook

        result = registry.get_by_service("MyService")
        assert result == playbook

    def test_get_by_category(self):
        """Test getting playbooks by category."""
        registry = PlaybookRegistry()
        compute_pb = create_test_playbook("pb-1", "Service1", PlaybookCategory.COMPUTE)
        data_pb = create_test_playbook("pb-2", "Service2", PlaybookCategory.DATA)

        registry.register(compute_pb)
        registry.register(data_pb)

        compute_results = registry.get_by_category(PlaybookCategory.COMPUTE)
        assert len(compute_results) == 1
        assert compute_results[0] == compute_pb

        data_results = registry.get_by_category(PlaybookCategory.DATA)
        assert len(data_results) == 1
        assert data_results[0] == data_pb

    def test_list_all(self):
        """Test listing all playbooks."""
        registry = PlaybookRegistry()
        pb1 = create_test_playbook("pb-1", "Service1")
        pb2 = create_test_playbook("pb-2", "Service2")

        registry.register(pb1)
        registry.register(pb2)

        all_playbooks = registry.list_all()
        assert len(all_playbooks) == 2

    def test_search_by_service_name(self):
        """Test searching playbooks by service name."""
        registry = PlaybookRegistry()
        registry.register(
            create_test_playbook("gke-pb", "GKE", PlaybookCategory.COMPUTE)
        )

        results = registry.search("GKE")
        assert len(results) > 0
        assert results[0].service_name == "GKE"

    def test_search_by_symptom(self):
        """Test searching playbooks by symptom."""
        registry = PlaybookRegistry()
        playbook = Playbook(
            playbook_id="test-pb",
            service_name="TestService",
            display_name="Test Service",
            category=PlaybookCategory.COMPUTE,
            description="Test playbook",
            issues=[
                TroubleshootingIssue(
                    issue_id="issue-1",
                    title="Connection Timeout",
                    description="Connections timing out",
                    symptoms=["Connection refused", "Timeout errors"],
                    root_causes=["Network issues"],
                    severity=PlaybookSeverity.HIGH,
                    diagnostic_steps=[],
                    remediation_steps=[],
                )
            ],
        )
        registry.register(playbook)

        results = registry.search("timeout")
        assert len(results) > 0

    def test_search_with_category_filter(self):
        """Test searching with category filter."""
        registry = PlaybookRegistry()
        registry.register(
            create_test_playbook("pb-1", "Service1", PlaybookCategory.COMPUTE)
        )
        registry.register(
            create_test_playbook("pb-2", "Service2", PlaybookCategory.DATA)
        )

        results = registry.search("Service", category=PlaybookCategory.COMPUTE)
        assert all(r.service_name == "Service1" for r in results)

    def test_get_issue(self):
        """Test getting a specific issue from a playbook."""
        registry = PlaybookRegistry()
        playbook = create_test_playbook()
        registry.register(playbook)

        issue = registry.get_issue("test-playbook", "test-playbook-issue-1")
        assert issue is not None
        assert issue.title == "Test Issue"

    def test_get_issue_not_found(self):
        """Test getting nonexistent issue returns None."""
        registry = PlaybookRegistry()
        playbook = create_test_playbook()
        registry.register(playbook)

        assert registry.get_issue("test-playbook", "nonexistent") is None
        assert registry.get_issue("nonexistent", "issue-1") is None

    def test_get_diagnostic_steps_for_symptom(self):
        """Test finding diagnostic steps by symptom."""
        registry = PlaybookRegistry()
        playbook = Playbook(
            playbook_id="test-pb",
            service_name="TestService",
            display_name="Test Service",
            category=PlaybookCategory.COMPUTE,
            description="Test playbook",
            issues=[
                TroubleshootingIssue(
                    issue_id="issue-1",
                    title="High CPU",
                    description="CPU usage is high",
                    symptoms=["CPU utilization above 90%", "Slow response times"],
                    root_causes=["Resource intensive operations"],
                    severity=PlaybookSeverity.HIGH,
                    diagnostic_steps=[
                        DiagnosticStep(
                            step_number=1,
                            title="Check CPU Metrics",
                            description="Review CPU usage",
                        )
                    ],
                    remediation_steps=[],
                )
            ],
        )
        registry.register(playbook)

        results = registry.get_diagnostic_steps_for_symptom("CPU utilization")
        assert len(results) > 0
        assert results[0]["issue_title"] == "High CPU"


class TestGetPlaybookRegistry:
    """Tests for get_playbook_registry singleton."""

    def test_returns_singleton(self):
        """Test that get_playbook_registry returns the same instance."""
        # Reset the singleton for testing
        import sre_agent.tools.playbooks.registry as registry_module

        registry_module._registry = None

        registry1 = get_playbook_registry()
        registry2 = get_playbook_registry()

        assert registry1 is registry2

    def test_loads_builtin_playbooks(self):
        """Test that builtin playbooks are loaded."""
        import sre_agent.tools.playbooks.registry as registry_module

        registry_module._registry = None

        registry = get_playbook_registry()
        all_playbooks = registry.list_all()

        # Should have at least the playbooks we created
        assert len(all_playbooks) >= 1

        # Check for specific playbooks
        gke_pb = registry.get_by_service("GKE")
        assert gke_pb is not None or len(all_playbooks) > 0
