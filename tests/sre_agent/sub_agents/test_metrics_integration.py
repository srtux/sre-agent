from sre_agent.sub_agents.metrics import COMMON_GCP_METRICS, METRICS_ANALYZER_PROMPT


def test_metrics_prompt_integration():
    """Verify that common GCP metrics are integrated into the metrics prompt."""
    assert "Knowledge Base (GCP Metrics)" in METRICS_ANALYZER_PROMPT
    assert "kubernetes.io/container/cpu/core_usage_time" in METRICS_ANALYZER_PROMPT
    assert "run.googleapis.com/request_count" in METRICS_ANALYZER_PROMPT
    assert (
        "aiplatform.googleapis.com/ReasoningEngine/request_count"
        in METRICS_ANALYZER_PROMPT
    )
    assert "logging.googleapis.com/log_entry_count" in METRICS_ANALYZER_PROMPT

    # Verify strict hierarchy is preserved
    assert "Tool Strategy (STRICT HIERARCHY):" in METRICS_ANALYZER_PROMPT
    assert "PromQL (Primary)" in METRICS_ANALYZER_PROMPT


def test_common_gcp_metrics_structure():
    """Verify the structure of the common GCP metrics resource."""
    assert "GKE" in COMMON_GCP_METRICS
    assert "Cloud Run" in COMMON_GCP_METRICS
    assert "Compute Engine" in COMMON_GCP_METRICS
    assert "Vertex AI" in COMMON_GCP_METRICS
    assert "BigQuery" in COMMON_GCP_METRICS
    assert "Cloud Logging" in COMMON_GCP_METRICS

    assert isinstance(COMMON_GCP_METRICS["GKE"], list)
    assert len(COMMON_GCP_METRICS["GKE"]) > 0
