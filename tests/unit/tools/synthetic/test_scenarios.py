"""Tests for synthetic scenario constants validation.

Validates that all synthetic scenario data constants have the expected
structure and types, serving as a regression gate for the demo data.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields

from sre_agent.tools.synthetic.scenarios import (
    ALERT_DEFS,
    ALERT_POLICIES,
    DEMO_CLUSTER_LOCATION,
    DEMO_CLUSTER_NAME,
    DEMO_PROJECT_ID,
    DEMO_REGION,
    LOG_TEMPLATES,
    METRIC_DESCRIPTORS,
    POD_NAMES,
    SERVICES,
    TRACE_IDS,
    ServiceDef,
)

# ---------------------------------------------------------------------------
# Demo project constants
# ---------------------------------------------------------------------------


class TestDemoConstants:
    """Validate demo project constants."""

    def test_demo_project_id_is_non_empty_string(self) -> None:
        assert isinstance(DEMO_PROJECT_ID, str)
        assert len(DEMO_PROJECT_ID) > 0

    def test_demo_cluster_name_is_non_empty_string(self) -> None:
        assert isinstance(DEMO_CLUSTER_NAME, str)
        assert len(DEMO_CLUSTER_NAME) > 0

    def test_demo_cluster_location_is_non_empty_string(self) -> None:
        assert isinstance(DEMO_CLUSTER_LOCATION, str)
        assert len(DEMO_CLUSTER_LOCATION) > 0

    def test_demo_region_is_non_empty_string(self) -> None:
        assert isinstance(DEMO_REGION, str)
        assert len(DEMO_REGION) > 0

    def test_demo_region_matches_cluster_location(self) -> None:
        assert DEMO_REGION == DEMO_CLUSTER_LOCATION


# ---------------------------------------------------------------------------
# ServiceDef dataclass
# ---------------------------------------------------------------------------


class TestServiceDef:
    """Validate ServiceDef dataclass structure."""

    def test_servicedef_is_frozen_dataclass(self) -> None:
        svc = ServiceDef(
            name="test",
            display_name="Test",
            resource_type="k8s_container",
            health="healthy",
        )
        assert svc.name == "test"
        # Frozen dataclass should raise on attribute assignment
        try:
            svc.name = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass

    def test_servicedef_has_required_fields(self) -> None:
        field_names = {f.name for f in dataclass_fields(ServiceDef)}
        required = {
            "name",
            "display_name",
            "resource_type",
            "health",
            "namespace",
            "replicas",
            "latency_ms_p50",
            "latency_ms_p99",
            "error_rate",
            "rps",
            "connections",
        }
        assert required.issubset(field_names)

    def test_servicedef_defaults(self) -> None:
        svc = ServiceDef(
            name="t",
            display_name="T",
            resource_type="k8s_container",
            health="healthy",
        )
        assert svc.namespace == "default"
        assert svc.replicas == 3
        assert svc.latency_ms_p50 == 25.0
        assert svc.latency_ms_p99 == 80.0
        assert svc.error_rate == 0.001
        assert svc.rps == 500.0
        assert svc.connections == []


# ---------------------------------------------------------------------------
# SERVICES dict
# ---------------------------------------------------------------------------

VALID_RESOURCE_TYPES = {
    "k8s_container",
    "cloud_run_revision",
    "cloudsql_database",
    "redis_instance",
}

VALID_HEALTH_STATES = {"healthy", "degraded", "unhealthy"}


class TestServices:
    """Validate SERVICES dictionary."""

    def test_services_is_non_empty_dict(self) -> None:
        assert isinstance(SERVICES, dict)
        assert len(SERVICES) > 0

    def test_service_keys_match_service_names(self) -> None:
        for key, svc in SERVICES.items():
            assert key == svc.name, f"Key '{key}' != service name '{svc.name}'"

    def test_all_services_are_servicedef_instances(self) -> None:
        for key, svc in SERVICES.items():
            assert isinstance(svc, ServiceDef), f"{key} is not a ServiceDef"

    def test_service_display_names_are_non_empty(self) -> None:
        for key, svc in SERVICES.items():
            assert len(svc.display_name) > 0, f"{key} has empty display_name"

    def test_service_resource_types_are_valid(self) -> None:
        for key, svc in SERVICES.items():
            assert svc.resource_type in VALID_RESOURCE_TYPES, (
                f"{key} has invalid resource_type '{svc.resource_type}'"
            )

    def test_service_health_states_are_valid(self) -> None:
        for key, svc in SERVICES.items():
            assert svc.health in VALID_HEALTH_STATES, (
                f"{key} has invalid health '{svc.health}'"
            )

    def test_service_latency_p50_less_than_p99(self) -> None:
        for key, svc in SERVICES.items():
            assert svc.latency_ms_p50 <= svc.latency_ms_p99, (
                f"{key}: p50 ({svc.latency_ms_p50}) > p99 ({svc.latency_ms_p99})"
            )

    def test_service_numeric_fields_non_negative(self) -> None:
        for key, svc in SERVICES.items():
            assert svc.latency_ms_p50 >= 0, f"{key}: negative p50"
            assert svc.latency_ms_p99 >= 0, f"{key}: negative p99"
            assert svc.error_rate >= 0, f"{key}: negative error_rate"
            assert svc.rps >= 0, f"{key}: negative rps"
            assert svc.replicas >= 0, f"{key}: negative replicas"

    def test_service_connections_reference_known_services(self) -> None:
        all_service_names = set(SERVICES.keys())
        for key, svc in SERVICES.items():
            for conn in svc.connections:
                assert conn in all_service_names, (
                    f"{key} references unknown service '{conn}'"
                )

    def test_no_duplicate_display_names(self) -> None:
        display_names = [svc.display_name for svc in SERVICES.values()]
        assert len(display_names) == len(set(display_names))

    def test_at_least_one_degraded_service_exists(self) -> None:
        degraded = [k for k, s in SERVICES.items() if s.health != "healthy"]
        assert len(degraded) > 0, "Scenario requires at least one unhealthy service"


# ---------------------------------------------------------------------------
# POD_NAMES
# ---------------------------------------------------------------------------


class TestPodNames:
    """Validate POD_NAMES dictionary."""

    def test_pod_names_is_non_empty_dict(self) -> None:
        assert isinstance(POD_NAMES, dict)
        assert len(POD_NAMES) > 0

    def test_pod_name_keys_are_known_services(self) -> None:
        for key in POD_NAMES:
            assert key in SERVICES, f"Pod key '{key}' not in SERVICES"

    def test_pod_name_values_are_non_empty_lists(self) -> None:
        for key, pods in POD_NAMES.items():
            assert isinstance(pods, list), f"{key}: expected list"
            assert len(pods) > 0, f"{key}: pod list is empty"

    def test_pod_names_are_non_empty_strings(self) -> None:
        for key, pods in POD_NAMES.items():
            for pod in pods:
                assert isinstance(pod, str), f"{key}: pod name is not str"
                assert len(pod) > 0, f"{key}: empty pod name"

    def test_no_duplicate_pod_names_across_services(self) -> None:
        all_pods: list[str] = []
        for pods in POD_NAMES.values():
            all_pods.extend(pods)
        assert len(all_pods) == len(set(all_pods)), "Duplicate pod names found"

    def test_pod_names_contain_service_prefix(self) -> None:
        for key, pods in POD_NAMES.items():
            for pod in pods:
                # Pod name should start with service name or an abbreviation
                prefix = key.split("-")[0]
                assert prefix in pod, f"Pod '{pod}' missing service prefix for '{key}'"


# ---------------------------------------------------------------------------
# TRACE_IDS
# ---------------------------------------------------------------------------


class TestTraceIds:
    """Validate TRACE_IDS constants."""

    def test_trace_ids_is_non_empty_dict(self) -> None:
        assert isinstance(TRACE_IDS, dict)
        assert len(TRACE_IDS) > 0

    def test_trace_id_keys_are_strings(self) -> None:
        for key in TRACE_IDS:
            assert isinstance(key, str)

    def test_trace_id_values_are_hex_strings(self) -> None:
        for key, value in TRACE_IDS.items():
            assert isinstance(value, str), f"Value for {key} is not a string"
            int(value, 16)  # Raises ValueError if not valid hex

    def test_trace_id_values_have_valid_length(self) -> None:
        for key, value in TRACE_IDS.items():
            assert 16 <= len(value) <= 64, (
                f"Trace ID '{key}' has length {len(value)}, expected 16-64"
            )

    def test_trace_id_keys_are_descriptive(self) -> None:
        for key in TRACE_IDS:
            assert len(key) > 3, f"Key '{key}' is too short to be descriptive"

    def test_no_duplicate_trace_id_values(self) -> None:
        values = list(TRACE_IDS.values())
        assert len(values) == len(set(values)), "Duplicate trace ID values found"


# ---------------------------------------------------------------------------
# ALERT_DEFS
# ---------------------------------------------------------------------------

ALERT_DEF_REQUIRED_KEYS = {"name", "policy", "state", "severity", "resource", "metric"}
VALID_ALERT_STATES = {"OPEN", "ACKNOWLEDGED", "CLOSED"}
VALID_ALERT_SEVERITIES = {"CRITICAL", "ERROR", "WARNING", "INFO"}


class TestAlertDefs:
    """Validate ALERT_DEFS list."""

    def test_alert_defs_is_non_empty_list(self) -> None:
        assert isinstance(ALERT_DEFS, list)
        assert len(ALERT_DEFS) > 0

    def test_alert_defs_have_required_keys(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            assert isinstance(alert, dict), f"Alert[{i}] is not a dict"
            missing = ALERT_DEF_REQUIRED_KEYS - alert.keys()
            assert not missing, f"Alert[{i}] missing keys: {missing}"

    def test_alert_def_names_contain_project_id(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            assert DEMO_PROJECT_ID in alert["name"], (
                f"Alert[{i}] name missing project ID"
            )

    def test_alert_def_states_are_valid(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            assert alert["state"] in VALID_ALERT_STATES, (
                f"Alert[{i}] invalid state '{alert['state']}'"
            )

    def test_alert_def_severities_are_valid(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            assert alert["severity"] in VALID_ALERT_SEVERITIES, (
                f"Alert[{i}] invalid severity '{alert['severity']}'"
            )

    def test_alert_def_policy_has_name_and_display(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            policy = alert["policy"]
            assert "name" in policy, f"Alert[{i}] policy missing 'name'"
            assert "displayName" in policy, f"Alert[{i}] policy missing 'displayName'"

    def test_alert_def_resource_has_type_and_labels(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            resource = alert["resource"]
            assert "type" in resource, f"Alert[{i}] resource missing 'type'"
            assert "labels" in resource, f"Alert[{i}] resource missing 'labels'"
            assert isinstance(resource["labels"], dict)

    def test_alert_def_metric_has_type(self) -> None:
        for i, alert in enumerate(ALERT_DEFS):
            metric = alert["metric"]
            assert "type" in metric, f"Alert[{i}] metric missing 'type'"

    def test_no_duplicate_alert_names(self) -> None:
        names = [a["name"] for a in ALERT_DEFS]
        assert len(names) == len(set(names)), "Duplicate alert names found"


# ---------------------------------------------------------------------------
# ALERT_POLICIES
# ---------------------------------------------------------------------------

ALERT_POLICY_REQUIRED_KEYS = {
    "name",
    "display_name",
    "documentation",
    "conditions",
    "enabled",
}


class TestAlertPolicies:
    """Validate ALERT_POLICIES list."""

    def test_alert_policies_is_non_empty_list(self) -> None:
        assert isinstance(ALERT_POLICIES, list)
        assert len(ALERT_POLICIES) > 0

    def test_alert_policies_have_required_keys(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            assert isinstance(policy, dict), f"Policy[{i}] is not a dict"
            missing = ALERT_POLICY_REQUIRED_KEYS - policy.keys()
            assert not missing, f"Policy[{i}] missing keys: {missing}"

    def test_alert_policy_names_contain_project_id(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            assert DEMO_PROJECT_ID in policy["name"], (
                f"Policy[{i}] name missing project ID"
            )

    def test_alert_policy_documentation_has_content(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            doc = policy["documentation"]
            assert "content" in doc, f"Policy[{i}] doc missing 'content'"
            assert "mime_type" in doc, f"Policy[{i}] doc missing 'mime_type'"
            assert len(doc["content"]) > 0

    def test_alert_policy_conditions_non_empty(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            conditions = policy["conditions"]
            assert isinstance(conditions, list)
            assert len(conditions) > 0, f"Policy[{i}] has no conditions"

    def test_alert_policy_condition_has_name_and_display(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            for j, cond in enumerate(policy["conditions"]):
                assert "name" in cond, f"Policy[{i}] cond[{j}] missing 'name'"
                assert "display_name" in cond, (
                    f"Policy[{i}] cond[{j}] missing 'display_name'"
                )

    def test_alert_policy_enabled_is_bool(self) -> None:
        for i, policy in enumerate(ALERT_POLICIES):
            assert isinstance(policy["enabled"], bool), (
                f"Policy[{i}] 'enabled' is not bool"
            )

    def test_no_duplicate_policy_names(self) -> None:
        names = [p["name"] for p in ALERT_POLICIES]
        assert len(names) == len(set(names)), "Duplicate policy names found"

    def test_policies_match_alert_defs(self) -> None:
        """Each alert def references a policy that exists in ALERT_POLICIES."""
        policy_names = {p["name"] for p in ALERT_POLICIES}
        for i, alert in enumerate(ALERT_DEFS):
            ref = alert["policy"]["name"]
            assert ref in policy_names, f"Alert[{i}] references unknown policy '{ref}'"


# ---------------------------------------------------------------------------
# LOG_TEMPLATES
# ---------------------------------------------------------------------------

LOG_TEMPLATE_REQUIRED_KEYS = {"severity", "payload", "service"}
VALID_LOG_SEVERITIES = {"DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL"}


class TestLogTemplates:
    """Validate LOG_TEMPLATES dictionary."""

    def test_log_templates_is_non_empty_dict(self) -> None:
        assert isinstance(LOG_TEMPLATES, dict)
        assert len(LOG_TEMPLATES) > 0

    def test_log_template_keys_are_descriptive(self) -> None:
        for key in LOG_TEMPLATES:
            assert isinstance(key, str)
            assert len(key) > 3, f"Log template key '{key}' is too short"

    def test_log_template_values_are_non_empty_lists(self) -> None:
        for key, entries in LOG_TEMPLATES.items():
            assert isinstance(entries, list), f"{key}: expected list"
            assert len(entries) > 0, f"{key}: empty template list"

    def test_log_entries_have_required_keys(self) -> None:
        for key, entries in LOG_TEMPLATES.items():
            for i, entry in enumerate(entries):
                assert isinstance(entry, dict), f"{key}[{i}] is not a dict"
                missing = LOG_TEMPLATE_REQUIRED_KEYS - entry.keys()
                assert not missing, f"{key}[{i}] missing keys: {missing}"

    def test_log_entry_severities_are_valid(self) -> None:
        for key, entries in LOG_TEMPLATES.items():
            for i, entry in enumerate(entries):
                assert entry["severity"] in VALID_LOG_SEVERITIES, (
                    f"{key}[{i}] invalid severity '{entry['severity']}'"
                )

    def test_log_entry_payload_is_non_empty(self) -> None:
        for key, entries in LOG_TEMPLATES.items():
            for i, entry in enumerate(entries):
                payload = entry["payload"]
                if isinstance(payload, str):
                    assert len(payload) > 0, f"{key}[{i}] empty string payload"
                elif isinstance(payload, dict):
                    assert len(payload) > 0, f"{key}[{i}] empty dict payload"
                    assert "message" in payload, (
                        f"{key}[{i}] dict payload missing 'message'"
                    )
                else:
                    raise AssertionError(f"{key}[{i}] payload is neither str nor dict")

    def test_log_entry_services_are_known(self) -> None:
        for key, entries in LOG_TEMPLATES.items():
            for i, entry in enumerate(entries):
                assert entry["service"] in SERVICES, (
                    f"{key}[{i}] references unknown service '{entry['service']}'"
                )

    def test_log_entry_pod_index_in_range(self) -> None:
        for _key, entries in LOG_TEMPLATES.items():
            for _i, entry in enumerate(entries):
                if "pod_index" in entry:
                    assert isinstance(entry["pod_index"], int)
                    assert entry["pod_index"] >= 0


# ---------------------------------------------------------------------------
# METRIC_DESCRIPTORS
# ---------------------------------------------------------------------------

METRIC_DESCRIPTOR_REQUIRED_KEYS = {
    "name",
    "type",
    "metric_kind",
    "value_type",
    "unit",
    "description",
    "display_name",
    "labels",
}

VALID_METRIC_KINDS = {"GAUGE", "DELTA", "CUMULATIVE"}
VALID_VALUE_TYPES = {"BOOL", "INT64", "DOUBLE", "STRING", "DISTRIBUTION"}


class TestMetricDescriptors:
    """Validate METRIC_DESCRIPTORS list."""

    def test_metric_descriptors_is_non_empty_list(self) -> None:
        assert isinstance(METRIC_DESCRIPTORS, list)
        assert len(METRIC_DESCRIPTORS) > 0

    def test_metric_descriptors_have_required_keys(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert isinstance(md, dict), f"Descriptor[{i}] is not a dict"
            missing = METRIC_DESCRIPTOR_REQUIRED_KEYS - md.keys()
            assert not missing, f"Descriptor[{i}] missing keys: {missing}"

    def test_metric_descriptor_names_contain_project_id(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert DEMO_PROJECT_ID in md["name"], (
                f"Descriptor[{i}] name missing project ID"
            )

    def test_metric_descriptor_kinds_are_valid(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert md["metric_kind"] in VALID_METRIC_KINDS, (
                f"Descriptor[{i}] invalid metric_kind '{md['metric_kind']}'"
            )

    def test_metric_descriptor_value_types_are_valid(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert md["value_type"] in VALID_VALUE_TYPES, (
                f"Descriptor[{i}] invalid value_type '{md['value_type']}'"
            )

    def test_metric_descriptor_unit_is_non_empty(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert isinstance(md["unit"], str)
            assert len(md["unit"]) > 0, f"Descriptor[{i}] has empty unit"

    def test_metric_descriptor_labels_are_list(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert isinstance(md["labels"], list), (
                f"Descriptor[{i}] labels is not a list"
            )

    def test_metric_descriptor_labels_have_key(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            for j, label in enumerate(md["labels"]):
                assert isinstance(label, dict)
                assert "key" in label, f"Descriptor[{i}] label[{j}] missing 'key'"

    def test_no_duplicate_metric_descriptor_names(self) -> None:
        names = [md["name"] for md in METRIC_DESCRIPTORS]
        assert len(names) == len(set(names)), "Duplicate metric descriptor names"

    def test_no_duplicate_metric_descriptor_types(self) -> None:
        types = [md["type"] for md in METRIC_DESCRIPTORS]
        assert len(types) == len(set(types)), "Duplicate metric descriptor types"

    def test_metric_descriptor_description_non_empty(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert isinstance(md["description"], str)
            assert len(md["description"]) > 0, f"Descriptor[{i}] has empty description"

    def test_metric_descriptor_display_name_non_empty(self) -> None:
        for i, md in enumerate(METRIC_DESCRIPTORS):
            assert isinstance(md["display_name"], str)
            assert len(md["display_name"]) > 0, (
                f"Descriptor[{i}] has empty display_name"
            )


# ---------------------------------------------------------------------------
# Cross-collection consistency
# ---------------------------------------------------------------------------


class TestCrossCollectionConsistency:
    """Validate consistency across all scenario collections."""

    def test_all_alert_resource_types_are_in_services(self) -> None:
        service_resource_types = {s.resource_type for s in SERVICES.values()}
        for i, alert in enumerate(ALERT_DEFS):
            rt = alert["resource"]["type"]
            assert rt in service_resource_types, (
                f"Alert[{i}] resource type '{rt}' not in SERVICES"
            )

    def test_all_alert_def_names_are_unique_globally(self) -> None:
        alert_names = [a["name"] for a in ALERT_DEFS]
        policy_names = [p["name"] for p in ALERT_POLICIES]
        # Alert names and policy names should not overlap
        overlap = set(alert_names) & set(policy_names)
        assert not overlap, f"Overlap between alert and policy names: {overlap}"

    def test_log_template_services_subset_of_services(self) -> None:
        referenced = set()
        for entries in LOG_TEMPLATES.values():
            for entry in entries:
                referenced.add(entry["service"])
        unknown = referenced - set(SERVICES.keys())
        assert not unknown, f"Log templates reference unknown services: {unknown}"

    def test_scenario_has_incident_signals(self) -> None:
        """The demo scenario should include degraded services, alerts, and error logs."""
        has_degraded = any(s.health != "healthy" for s in SERVICES.values())
        has_alerts = len(ALERT_DEFS) > 0
        has_error_logs = any(
            any(e["severity"] in ("ERROR", "CRITICAL") for e in entries)
            for entries in LOG_TEMPLATES.values()
        )
        assert has_degraded, "Scenario missing degraded services"
        assert has_alerts, "Scenario missing alerts"
        assert has_error_logs, "Scenario missing error logs"
