from sre_agent.tools.analysis.genui_adapter import (
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
