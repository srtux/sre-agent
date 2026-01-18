from sre_agent.tools.analysis.genui_adapter import (
    transform_log_entries,
    transform_metrics,
    transform_remediation,
    transform_trace,
)


def test_transform_trace():
    raw_trace = {
        "trace_id": "test-trace-123",
        "spans": [
            {
                "span_id": "span-1",
                "labels": {"/http/status_code": "200", "component": "proxy"},
            },
            {
                "span_id": "span-2",
                "labels": {"/http/status_code": "500", "error": "true"},
            },
        ],
    }

    transformed = transform_trace(raw_trace)

    assert transformed["trace_id"] == "test-trace-123"
    assert len(transformed["spans"]) == 2
    assert transformed["spans"][0]["trace_id"] == "test-trace-123"
    assert transformed["spans"][0]["status"] == "OK"
    assert transformed["spans"][0]["attributes"]["component"] == "proxy"
    assert transformed["spans"][1]["status"] == "ERROR"


def test_transform_metrics_list():
    raw_metrics = [
        {
            "metric": {
                "type": "compute.googleapis.com/instance/cpu/utilization",
                "labels": {"instance_name": "vm1"},
            },
            "resource": {"type": "gce_instance", "labels": {"project_id": "p1"}},
            "points": [{"value": 0.5, "timestamp": "2023-01-01T00:00:00Z"}],
        }
    ]

    transformed = transform_metrics(raw_metrics)

    assert (
        transformed["metric_name"] == "compute.googleapis.com/instance/cpu/utilization"
    )
    assert len(transformed["points"]) == 1
    assert transformed["labels"]["instance_name"] == "vm1"
    assert transformed["labels"]["project_id"] == "p1"


def test_transform_remediation():
    raw_remediation = {
        "finding_summary": "High Latency in Frontend",
        "suggestions": [
            {
                "action": "Scale Up",
                "description": "Increase replicas for frontend",
                "steps": ["gcloud compute instance-groups managed resize ..."],
                "risk": "low",
            }
        ],
    }

    transformed = transform_remediation(raw_remediation)

    assert transformed["issue"] == "High Latency in Frontend"
    assert len(transformed["steps"]) == 1
    assert (
        transformed["steps"][0]["description"]
        == "gcloud compute instance-groups managed resize ..."
    )
    assert transformed["steps"][0]["command"] == "Scale Up"


def test_transform_log_entries():
    raw_logs = {
        "entries": [
            {
                "insertId": "log-1",
                "timestamp": "2023-01-01T00:00:00Z",
                "severity": "ERROR",
                "jsonPayload": {"message": "Something went wrong"},
                "resource": {
                    "type": "k8s_container",
                    "labels": {"pod_name": "pod-1", "namespace_name": "default"},
                },
                "trace": "projects/p1/traces/trace-123",
            }
        ],
        "filter": 'severity="ERROR"',
        "project_id": "test-project",
    }

    transformed = transform_log_entries(raw_logs)

    assert len(transformed["entries"]) == 1
    entry = transformed["entries"][0]

    # Check flattening and mapping
    assert entry["insert_id"] == "log-1"
    assert entry["timestamp"] == "2023-01-01T00:00:00Z"
    assert entry["severity"] == "ERROR"
    assert entry["payload"] == {"message": "Something went wrong"}

    # Check resource flattening (Critical for Frontend)
    assert entry["resource_type"] == "k8s_container"
    assert entry["resource_labels"]["pod_name"] == "pod-1"
    assert entry["resource_labels"]["namespace_name"] == "default"

    # Check trace extraction
    assert entry["trace_id"] == "trace-123"

    # Check metadata
    assert transformed["filter"] == 'severity="ERROR"'
    assert transformed["project_id"] == "test-project"
