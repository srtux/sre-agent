"""Tests for remediation suggestions."""

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.remediation.suggestions import (
    estimate_remediation_risk,
    find_similar_past_incidents,
    generate_remediation_suggestions,
    get_gcloud_commands,
)


def test_generate_remediation_suggestions_patterns():
    # Test OOM
    res = generate_remediation_suggestions("OOMKilled detected")
    assert res["status"] == ToolStatus.SUCCESS
    assert "oom_killed" in res["result"]["matched_patterns"]
    assert any(
        s["action"] == "Increase memory limits" for s in res["result"]["suggestions"]
    )

    # Test CPU
    res = generate_remediation_suggestions("cpu saturation")
    assert "cpu_throttling" in res["result"]["matched_patterns"]

    # Test connection pool
    res = generate_remediation_suggestions("connection pool exhausted")
    assert "connection_pool" in res["result"]["matched_patterns"]

    # Test high latency
    res = generate_remediation_suggestions("p99 spike")
    assert "high_latency" in res["result"]["matched_patterns"]

    # Test error spike
    res = generate_remediation_suggestions("500 error rate")
    assert "error_spike" in res["result"]["matched_patterns"]

    # Test cold start
    res = generate_remediation_suggestions("cold start detected")
    assert "cold_start" in res["result"]["matched_patterns"]

    # Test scheduling
    res = generate_remediation_suggestions("insufficient resources to schedule")
    assert "scheduling" in res["result"]["matched_patterns"]

    # Test pubsub
    res = generate_remediation_suggestions("message backlog")
    assert "pubsub_backlog" in res["result"]["matched_patterns"]

    # Test disk
    res = generate_remediation_suggestions("disk pressure")
    assert "disk_pressure" in res["result"]["matched_patterns"]


def test_generate_remediation_suggestions_no_match():
    res = generate_remediation_suggestions("mystery issue")
    assert res["status"] == ToolStatus.SUCCESS
    assert res["result"]["matched_patterns"] == []
    assert len(res["result"]["suggestions"]) == 2


def test_get_gcloud_commands_all_types():
    base_args = {"resource_name": "r1", "project_id": "p1", "region": "us-c1"}

    # rollback
    res = get_gcloud_commands("rollback", **base_args)
    assert any(
        "rollback" in c["description"].lower() for c in res["result"]["commands"]
    )

    # increase_memory
    res = get_gcloud_commands("increase_memory", **base_args)
    assert any("memory" in c["description"].lower() for c in res["result"]["commands"])

    # scale_gke_nodepool
    res = get_gcloud_commands("scale_gke_nodepool", cluster="c1", **base_args)
    assert "container clusters update" in res["result"]["commands"][0]["command"]

    # increase_sql_connections
    res = get_gcloud_commands("increase_sql_connections", **base_args)
    assert "sql instances patch" in res["result"]["commands"][0]["command"]

    # enable_min_instances
    res = get_gcloud_commands("enable_min_instances", **base_args)
    assert "--min-instances" in res["result"]["commands"][0]["command"]

    # update_hpa
    res = get_gcloud_commands("update_hpa", **base_args)
    assert "kubectl patch hpa" in res["result"]["commands"][0]["command"]

    # unknown
    res = get_gcloud_commands("unknown", **base_args)
    assert res["status"] == ToolStatus.ERROR


def test_estimate_remediation_risk_scenarios():
    # Low risk
    res = estimate_remediation_risk("scale up", "service", "add 2 replicas")
    assert res["result"]["risk_assessment"]["level"] == "low"

    # High risk
    res = estimate_remediation_risk("delete node pool", "service", "destroy nodes")
    assert res["result"]["risk_assessment"]["level"] == "high"

    # Database
    res = estimate_remediation_risk("sql update", "service", "patch db")
    assert any("Database" in f for f in res["result"]["risk_assessment"]["factors"])

    # Rollback
    res = estimate_remediation_risk("rollback", "service", "back to v1")
    assert any("Rollback" in f for f in res["result"]["risk_assessment"]["factors"])

    # Restart
    res = estimate_remediation_risk("restart", "service", "reboot")
    assert any("Restart" in f for f in res["result"]["risk_assessment"]["factors"])

    # Config
    res = estimate_remediation_risk("config change", "service", "tweak params")
    assert any(
        "Configuration" in f for f in res["result"]["risk_assessment"]["factors"]
    )

    # Scale down
    res = estimate_remediation_risk("scale down", "service", "remove nodes")
    assert any("capacity" in f for f in res["result"]["risk_assessment"]["factors"])


def test_find_similar_past_incidents_search():
    # Direct match
    res = find_similar_past_incidents("OOM")
    assert res["result"]["matches_found"] > 0
    assert "key_learnings" in res["result"]

    # Service filter
    res = find_similar_past_incidents("OOM", service_name="frontend")
    assert res["result"]["matches_found"] == 1

    # Partial match
    res = find_similar_past_incidents("flash sale")
    assert res["result"]["matches_found"] > 0

    # No match
    res = find_similar_past_incidents("alien abduction")
    assert res["result"]["matches_found"] == 0
    assert "note" in res["result"]
