"""
Goal: Verify the GenUI adapter correctly transforms raw tool data into frontend widget schemas.
Patterns: Schema Mapping Verification, Edge Case Coverage (Empty/Error data).
"""

from sre_agent.tools.analysis.genui_adapter import (
    create_demo_agent_activity,
    create_demo_incident_timeline,
    create_demo_log_entries,
    create_demo_service_topology,
    transform_agent_activity,
    transform_ai_reasoning,
    transform_alerts_to_timeline,
    transform_golden_signals,
    transform_incident_timeline,
    transform_log_entries,
    transform_log_patterns,
    transform_metrics,
    transform_metrics_dashboard,
    transform_remediation,
    transform_service_topology,
    transform_trace,
)


def test_transform_trace():
    trace_data = {
        "trace_id": "t1",
        "spans": [
            {
                "span_id": "s1",
                "name": "op1",
                "start_time_unix": 1000,
                "end_time_unix": 1001,
                "labels": {},
            }
        ],
        "duration_ms": 1000,
    }
    result = transform_trace(trace_data)
    # The functions return the data part directly, not wrapped in status/type/data
    assert result["trace_id"] == "t1"
    assert len(result["spans"]) == 1


def test_transform_metrics():
    # Simple metric data
    metric_data = {
        "metric_name": "m1",
        "points": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 10},
            {"timestamp": "2024-01-01T00:01:00Z", "value": 15},
        ],
    }
    result = transform_metrics(metric_data)
    assert result["metric_name"] == "m1"
    assert len(result["points"]) == 2


def test_transform_remediation():
    remediation_data = {
        "finding_summary": "Fix it",
        "suggestions": [
            {"action": "redeploy", "description": "restart", "steps": ["Step 1"]}
        ],
    }
    result = transform_remediation(remediation_data)
    assert result["issue"] == "Fix it"
    assert len(result["steps"]) == 1


def test_transform_agent_activity():
    activity_data = {
        "nodes": [{"id": "n1", "name": "Start"}],
        "current_phase": "triage",
    }
    result = transform_agent_activity(activity_data)
    assert result["current_phase"] == "triage"
    assert result["nodes"][0]["id"] == "n1"


def test_transform_service_topology():
    topology_data = {"services": [{"id": "s1", "name": "Frontend"}]}
    result = transform_service_topology(topology_data)
    assert len(result["services"]) == 1


def test_transform_incident_timeline():
    incident_data = {
        "title": "Outage",
        "events": [{"id": "e1", "time": "2024-01-01T00:00:00Z", "title": "Down"}],
    }
    result = transform_incident_timeline(incident_data)
    assert result["title"] == "Outage"
    assert len(result["events"]) == 1


def test_transform_metrics_dashboard():
    dashboard_data = {
        "title": "Perf",
        "metrics": [{"id": "m1", "name": "CPU", "current_value": 50}],
    }
    result = transform_metrics_dashboard(dashboard_data)
    assert result["title"] == "Perf"
    assert len(result["metrics"]) == 1


def test_transform_golden_signals():
    data = {
        "service_name": "app",
        "signals": {
            "latency": {"value_ms": 100, "status": "GOOD"},
            "traffic": {"requests_per_second": 10, "status": "OK"},
            "errors": {"error_rate_percent": 0.1, "status": "GOOD"},
            "saturation": {"cpu_utilization_avg_percent": 50, "status": "GOOD"},
        },
    }
    result = transform_golden_signals(data)
    assert result["service_name"] == "app"
    assert len(result["metrics"]) == 4


def test_transform_ai_reasoning():
    reasoning_data = {
        "agent_name": "TriageAgent",
        "steps": [{"content": "Thinking..."}],
    }
    result = transform_ai_reasoning(reasoning_data)
    assert result["agent_name"] == "TriageAgent"
    assert len(result["steps"]) == 1


def test_transform_log_entries():
    log_data = {"entries": [{"timestamp": "2024-01-01T00:00:00Z", "payload": "Error"}]}
    result = transform_log_entries(log_data)
    assert len(result["entries"]) == 1


def test_transform_log_patterns():
    # Test dictionary input (Summary format)
    pattern_data = {
        "top_patterns": [{"pattern_id": "p1", "template": "abc", "count": 10}]
    }
    result = transform_log_patterns(pattern_data)
    assert isinstance(result, dict)
    assert "patterns" in result
    assert result["count"] == 1
    assert result["patterns"][0]["pattern_id"] == "p1"

    # Test comparison format
    comparison_data = {
        "anomalies": {
            "new_patterns": [{"pattern_id": "new1", "template": "new", "count": 5}],
            "increased_patterns": [
                {
                    "pattern": {"pattern_id": "inc1", "template": "inc", "count": 20},
                    "increase_pct": 200,
                }
            ],
        }
    }
    result_comp = transform_log_patterns(comparison_data)
    assert result_comp["count"] == 2
    assert any(p["pattern_id"] == "new1" for p in result_comp["patterns"])
    assert any(p["pattern_id"] == "inc1" for p in result_comp["patterns"])

    # Test raw list input
    list_data = [{"pattern_id": "list1", "template": "list", "count": 1}]
    result_list = transform_log_patterns(list_data)
    assert result_list["count"] == 1
    assert result_list["patterns"][0]["pattern_id"] == "list1"


def test_demo_functions():
    assert "nodes" in create_demo_agent_activity()
    assert "services" in create_demo_service_topology()
    assert "events" in create_demo_incident_timeline()
    assert "entries" in create_demo_log_entries()


def test_transform_alerts_to_timeline():
    alerts_data = [
        {
            "name": "projects/p1/alertPolicies/a1",
            "state": "OPEN",
            "severity": "CRITICAL",
            "openTime": "2024-01-01T10:00:00Z",
            "policy": {"displayName": "High CPU"},
            "resource": {"type": "gce_instance", "labels": {"service_name": "worker"}},
            "metric": {"type": "compute.googleapis.com/instance/cpu/utilization"},
        }
    ]
    result = transform_alerts_to_timeline(alerts_data)
    assert result["title"] == "Active Alerts Timeline"
    assert result["status"] == "ongoing"
    assert len(result["events"]) == 1
    assert result["events"][0]["severity"] == "critical"
    assert "worker" in result["events"][0]["description"]

    # Test empty list
    result_empty = transform_alerts_to_timeline([])
    assert result_empty["title"] == "No Active Alerts"
    assert result_empty["status"] == "resolved"
