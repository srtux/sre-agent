# Agent Evaluation Framework

This directory contains the evaluation framework for measuring the SRE Agent's
reasoning quality, tool-use precision, and response actionability.

## Architecture: Dual-Layer Quality Gate

We follow an **Evaluation-Driven Development (EDD)** model. Every release must
pass a suite of semantic and structural tests before deployment.

### Layer 1: Local/CI Quality Gate
- **Tool**: `adk eval` (triggered via `uv run poe eval`)
- **Purpose**: Rapid iteration and blocking CI/CD on regressions
- **Key Metrics**: `tool_trajectory_avg_score`, `rubric_based_final_response_quality_v1`

### Layer 2: Cloud-Native Vertex AI Sync
- **Tool**: `vertexai.preview.evaluation.EvalTask` (via `uv run poe eval --sync`)
- **Purpose**: Long-term tracking and historical analysis in GCP Console
- **Advanced Metrics**: `trajectory_exact_match`, `trajectory_precision`, `groundedness`

---

## Evaluation Datasets

| File | Cases | Category | Description |
|------|-------|----------|-------------|
| `basic_capabilities.test.json` | 1 | Sanity | Agent self-description and capability check |
| `tool_selection.test.json` | 3 | Routing | Correct tool selection (trace, logs, metrics) |
| `metrics_analysis.test.json` | 1 | Analysis | PromQL metric analysis and anomaly detection |
| `incident_investigation.test.json` | 1 | E2E | Multi-stage latency investigation |
| `error_diagnosis.test.json` | 3 | Diagnosis | DB pool exhaustion, cascading timeouts, OOM kills |
| `multi_signal_correlation.test.json` | 2 | Correlation | Deploy regressions, gradual SLO degradation |

**Total: 11 evaluation scenarios** covering the full investigation lifecycle.

---

## Quality Criteria (`test_config.json`)

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `tool_trajectory_avg_score` | 1.0 | Correct tool sequence (Aggregate > Triage > Deep Dive) |
| `rubric_based_final_response_quality_v1` | 0.8 | Technical precision, causality, actionability |
| `final_response_match_v2` | 0.6 | Semantic match with gold standard reference |
| `hallucinations_v1` | 0.0 | Zero tolerance for hallucinated claims |
| `safety_v1` | 0.0 | Zero tolerance for unsafe outputs |

### Rubric Dimensions (LLM-as-a-Judge)

The agent is graded by `gemini-2.5-flash` against these rubrics:

| Dimension | What It Measures |
|-----------|-----------------|
| **Technical Precision** | Identifies specific GCP signals (Traces, Logs, Metrics) with quantitative evidence |
| **Root Cause Causality** | Explains WHY an issue happened (cascading failures), not just WHAT happened |
| **Actionability** | Provides clear recommendations or specific `gcloud` commands for remediation |

---

## Running Evaluations

### Prerequisites

Set one of these credential configurations:

```bash
# Option A: Google AI API key
export GOOGLE_API_KEY="your-key"

# Option B: Vertex AI
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="1"
```

### Local Run

```bash
# Run all evaluations via deploy script
uv run poe eval

# Run specific eval test directly
uv run pytest eval/test_evaluate.py::test_agent_capabilities -v

# Run with detailed output
uv run pytest eval/test_evaluate.py -v -s
```

### Vertex AI Sync

```bash
# Sync results to Vertex AI Experiments for historical tracking
uv run poe eval --sync
```

View results in **GCP Console > Vertex AI > Evaluations**.

---

## CI/CD Integration

Evaluations are integrated into `cloudbuild.yaml` as a mandatory quality gate:

- **Step**: `run-evals`
- **Blocking**: If trajectory score < 100% or rubric score < 80%, deployment is blocked
- **Identity**: Cloud Build Service Account needs `roles/aiplatform.user` and observability roles

### IAM Setup for CI/CD

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

for ROLE in aiplatform.user aiplatform.viewer logging.viewer monitoring.viewer \
            cloudtrace.user bigquery.jobUser bigquery.dataViewer \
            cloudapiregistry.viewer resourcemanager.projectViewer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CB_SA" \
    --role="roles/$ROLE" \
    --condition=None
done
```

### Local Developer Setup

```bash
USER_EMAIL="your@email.com"
for ROLE in aiplatform.user aiplatform.viewer cloudapiregistry.viewer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/$ROLE" \
    --condition=None
done
```

---

## Writing New Eval Scenarios

### File Format

Each `.test.json` file follows the ADK EvalSet schema:

```json
{
  "eval_set_id": "unique_id",
  "name": "Human-readable name",
  "description": "What this eval suite tests",
  "eval_cases": [
    {
      "eval_id": "case_unique_id",
      "conversation": [
        {
          "invocation_id": "inv_001",
          "user_content": "User query to the agent",
          "expected_tool_use": [
            {"tool_name": "expected_tool_1"},
            {"tool_name": "expected_tool_2"}
          ],
          "expected_intermediate_agent_responses": [
            "keyword1", "keyword2"
          ],
          "reference": "Gold standard response for semantic matching"
        }
      ]
    }
  ]
}
```

### Guidelines for Writing Good Eval Cases

1. **Be specific**: Include project IDs, service names, time windows, and error details
2. **Cover the tool trajectory**: List expected tools in the order they should be called
3. **Include intermediate keywords**: These verify the agent's reasoning path
4. **Write detailed references**: The gold standard should be a complete diagnostic report
5. **Test failure modes**: Include scenarios where the agent should ask for clarification
6. **Reflect real incidents**: Base scenarios on real SRE incident patterns

### Recommended Eval Scenario Categories

| Category | Example Scenarios | Tools Expected |
|----------|-------------------|----------------|
| **Latency Investigation** | P99 spikes, slow DB queries, network hops | `fetch_trace`, `list_time_series`, `list_log_entries` |
| **Error Diagnosis** | 5xx surges, connection failures, OOM kills | `list_log_entries`, `list_time_series`, `list_alert_policies` |
| **Availability/SLO** | SLO burn, partial outages, failover | `list_time_series`, `list_alert_policies` |
| **Correlation** | Deploy regressions, config changes, dependency failures | All tools + `run_cross_signal_correlation` |
| **Proactive Detection** | Gradual degradation, capacity planning | `list_time_series`, `run_anomaly_detection` |
| **GKE/Infrastructure** | Pod crashes, node pressure, resource limits | `list_gke_clusters`, `list_time_series`, `list_log_entries` |

---

## Monitoring & Historical Tracking

### Vertex AI Experiments

Results are stored in GCS and visualized in Vertex AI Experiments:

1. Set `EVAL_STORAGE_URI="gs://YOUR_BUCKET/sre-agent-evals"` in `.env`
2. Navigate to **Vertex AI > Experiments** in GCP Console
3. Look for experiment runs starting with "sre-agent"

### Metrics Tracked Over Time

- Trajectory exact match rate
- Trajectory precision and recall
- Rubric scores per dimension
- Hallucination rate
- Response match score

For the full evaluation standards, see [docs/EVALUATIONS.md](../docs/EVALUATIONS.md).
