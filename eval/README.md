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
- **Tool**: `vertexai.Client().evals` API (via `uv run poe eval --sync`)
- **Purpose**: Long-term tracking and historical analysis in GCP Console
- **Agent Metrics**: `FINAL_RESPONSE_QUALITY`, `TOOL_USE_QUALITY`, `HALLUCINATION`, `SAFETY`
- **Fallback**: Legacy `vertexai.preview.evaluation.EvalTask` if the new SDK is unavailable

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
| `kubernetes_debugging.test.json` | 3 | GKE | Pod crashloops, node pressure, HPA scaling failures |
| `slo_burn_rate.test.json` | 2 | SLO | Error budget exhaustion, multi-window SLO violations |
| `failure_modes.test.json` | 4 | Edge Cases | Invalid projects, hallucination resistance, rate limits, cascading failures |

**Total: 20 evaluation cases** across 9 categories covering the full investigation lifecycle.

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
# Run all evaluations via deploy script (uses adk eval CLI)
uv run poe eval

# Run all pytest eval tests
uv run pytest eval/test_evaluate.py -v

# Run a specific eval test
uv run pytest eval/test_evaluate.py::test_agent_capabilities -v

# Run with detailed output
uv run pytest eval/test_evaluate.py -v -s
```

### Vertex AI Sync

```bash
# Sync results to Vertex AI Evaluation Service for historical tracking
uv run poe eval --sync
```

View results in **GCP Console > Vertex AI > Evaluations**.

---

## Test Structure

### `conftest.py` — Shared Eval Fixtures

The `conftest.py` module provides shared utilities:

- `has_eval_credentials()` — credential detection
- `requires_credentials` — pytest skip marker
- `load_eval_set(file_name)` — load and parse eval JSON with project ID replacement
- `load_eval_config()` — load shared criteria from `test_config.json`
- `make_tool_trajectory_config()` — create config focused on tool selection
- `make_full_config()` — create config with all quality criteria

### `test_evaluate.py` — Pytest Entry Points

All 10 test files are wired into dedicated test functions:

| Test Function | Eval File | Focus |
|---------------|-----------|-------|
| `test_agent_capabilities` | `basic_capabilities.test.json` | Response quality |
| `test_tool_selection` | `tool_selection.test.json` | Tool trajectory |
| `test_metrics_analysis` | `metrics_analysis.test.json` | Tool trajectory |
| `test_incident_investigation` | `incident_investigation.test.json` | Tool trajectory |
| `test_error_diagnosis` | `error_diagnosis.test.json` | Full rubric suite |
| `test_multi_signal_correlation` | `multi_signal_correlation.test.json` | Full rubric suite |
| `test_kubernetes_debugging` | `kubernetes_debugging.test.json` | Tool trajectory |
| `test_slo_burn_rate` | `slo_burn_rate.test.json` | Tool trajectory |
| `test_failure_modes` | `failure_modes.test.json` | Response + safety |

---

## CI/CD Integration

Evaluations are integrated into `cloudbuild.yaml` as a post-deployment quality check:

- **Step**: `run-evals` (runs after frontend deployment)
- **Policy**: `allowFailure: true` — does not block the release but surfaces regressions
- **Identity**: Cloud Build Service Account needs the IAM roles listed below

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
      "session_input": {
        "app_name": "sre_agent",
        "user_id": "test_user"
      },
      "conversation": [
        {
          "invocation_id": "inv_001",
          "user_content": {
            "role": "user",
            "parts": [{ "text": "User query to the agent" }]
          },
          "intermediate_data": {
            "tool_uses": [
              { "name": "expected_tool_1" },
              { "name": "expected_tool_2" }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "Gold standard response for semantic matching" }]
          }
        }
      ]
    }
  ]
}
```

### Checklist for New Eval Cases

1. Include `session_input` with `app_name` and `user_id` on every eval case
2. Use `TEST_PROJECT_ID` as the placeholder for GCP project IDs
3. List expected tools in `intermediate_data.tool_uses` in call order
4. Write a detailed `final_response` as the gold standard reference
5. Add the test file to the corresponding test function in `test_evaluate.py`
6. Run `uv run pytest eval/test_evaluate.py -v` to verify

### Guidelines

- **Be specific**: Include project IDs, service names, time windows, and error details
- **Cover the tool trajectory**: List expected tools in the order they should be called
- **Write detailed references**: The gold standard should be a complete diagnostic report
- **Test failure modes**: Include scenarios where the agent should ask for clarification
- **Reflect real incidents**: Base scenarios on real SRE incident patterns

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

### Vertex AI Evaluation Service

Results are synced to GCS and visualized in Vertex AI:

1. Set `EVAL_STORAGE_URI="gs://YOUR_BUCKET/sre-agent-evals"` in `.env`
2. Run `uv run poe eval --sync`
3. Navigate to **Vertex AI > Evaluations** in GCP Console

### Metrics Tracked Over Time

- Tool trajectory exact match rate
- Rubric scores per dimension (technical precision, causality, actionability)
- Final response quality
- Tool use quality
- Hallucination rate
- Safety score

For the full evaluation standards, see [docs/EVALUATIONS.md](../docs/EVALUATIONS.md).
