# Agent Evaluation Framework

This directory contains the evaluation framework for measuring the SRE Agent's
reasoning quality, tool-use precision, and response actionability.

For the high-level evaluation standards (rubrics, anti-hallucination rules, CI/CD
setup), see [`docs/EVALUATIONS.md`](../docs/EVALUATIONS.md).

## Architecture: Dual-Layer Quality Gate

We follow an **Evaluation-Driven Development (EDD)** model. Every release must
pass a suite of semantic and structural tests before deployment.

### Layer 1: Local/CI Quality Gate (pytest)

- **Tool**: ADK `AgentEvaluator.evaluate_eval_set()` called from pytest (`eval/test_evaluate.py`)
- **CLI alternative**: `adk eval` CLI called from `deploy/run_eval.py` (`uv run poe eval`)
- **Purpose**: Rapid iteration and blocking CI/CD on regressions
- **Key Metrics**: `tool_trajectory_avg_score`, `response_match_score`, `rubric_based_final_response_quality_v1`, `hallucinations_v1`, `safety_v1`

### Layer 2: Cloud-Native Vertex AI Sync

- **Tool**: `vertexai.Client().evals` API (via `uv run poe eval --sync`)
- **Fallback**: Legacy `vertexai.preview.evaluation.EvalTask` if the new SDK is unavailable
- **Purpose**: Long-term tracking and historical analysis in GCP Console
- **Agent Metrics**: `FINAL_RESPONSE_QUALITY`, `TOOL_USE_QUALITY`, `HALLUCINATION`, `SAFETY`
- **Prerequisite**: Set `EVAL_STORAGE_URI` to a GCS bucket URI (required by the new API)

---

## Directory Contents

```
eval/
├── conftest.py                          # Shared pytest fixtures and config loaders
├── test_evaluate.py                     # 9 pytest test functions (entry points)
├── test_config.json                     # Shared evaluation criteria and rubrics
├── basic_capabilities.test.json         # 1 case  — Sanity check
├── tool_selection.test.json             # 3 cases — Tool routing
├── metrics_analysis.test.json           # 1 case  — Metric analysis
├── incident_investigation.test.json     # 1 case  — E2E investigation
├── error_diagnosis.test.json            # 3 cases — Error diagnosis
├── multi_signal_correlation.test.json   # 2 cases — Cross-signal correlation
├── kubernetes_debugging.test.json       # 3 cases — GKE debugging
├── slo_burn_rate.test.json              # 2 cases — SLO burn rate analysis
├── failure_modes.test.json              # 4 cases — Edge cases and failure modes
└── README.md                            # This file
```

---

## Evaluation Datasets

| File | Cases | Category | Eval IDs |
|------|-------|----------|----------|
| `basic_capabilities.test.json` | 1 | Sanity | `capability_check` |
| `tool_selection.test.json` | 3 | Routing | `fetch_trace_selection`, `log_analysis_selection`, `metric_query_selection` |
| `metrics_analysis.test.json` | 1 | Analysis | `metrics_analysis_cpu` |
| `incident_investigation.test.json` | 1 | E2E | `latency_investigation_checkout` |
| `error_diagnosis.test.json` | 3 | Diagnosis | `database_connection_pool_exhaustion`, `cascading_timeout_failure`, `memory_leak_oom_kill` |
| `multi_signal_correlation.test.json` | 2 | Correlation | `correlated_deploy_regression`, `gradual_degradation_detection` |
| `kubernetes_debugging.test.json` | 3 | GKE | `pod_crashloop_investigation`, `node_pressure_investigation`, `hpa_scaling_failure` |
| `slo_burn_rate.test.json` | 2 | SLO | `error_budget_exhaustion`, `multi_window_slo_violation` |
| `failure_modes.test.json` | 4 | Edge Cases | `invalid_project_graceful_handling`, `hallucination_resistance_fake_metric`, `rate_limit_recovery`, `cascading_failure_multi_service` |

**Total: 20 evaluation cases** across 9 categories covering the full investigation lifecycle.

---

## Quality Criteria

### Shared Criteria (`test_config.json`)

The `test_config.json` file defines the full shared criteria used by tests that require comprehensive evaluation:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| `tool_trajectory_avg_score` | 1.0 | Correct tool sequence (Aggregate > Triage > Deep Dive) |
| `rubric_based_final_response_quality_v1` | 0.8 | Technical precision, causality, actionability (judged by Gemini 2.5 Flash) |
| `final_response_match_v2` | 0.6 | Semantic match with gold standard reference |
| `hallucinations_v1` | 0.0 | Zero tolerance for hallucinated claims |
| `safety_v1` | 0.0 | Zero tolerance for unsafe outputs |

### Per-Test Criteria Overrides

Not every test uses the full criteria. Each test function in `test_evaluate.py` applies the appropriate config:

| Test Function | Config Source | What It Checks |
|---------------|--------------|----------------|
| `test_agent_capabilities` | Inline: `response_match_score >= 0.6` | Response quality only |
| `test_tool_selection` | `make_tool_trajectory_config(0.8)` | Tool trajectory (marked `xfail`) |
| `test_metrics_analysis` | `make_tool_trajectory_config(0.8)` | Tool trajectory |
| `test_incident_investigation` | `make_tool_trajectory_config(0.8)` | Tool trajectory |
| `test_error_diagnosis` | `make_full_config()` (all `test_config.json`) | Full rubric suite |
| `test_multi_signal_correlation` | `make_full_config()` (all `test_config.json`) | Full rubric suite |
| `test_kubernetes_debugging` | `make_tool_trajectory_config(0.8)` | Tool trajectory |
| `test_slo_burn_rate` | `make_tool_trajectory_config(0.8)` | Tool trajectory |
| `test_failure_modes` | Inline: `response_match >= 0.5, hallucinations = 0, safety = 0` | Graceful degradation + safety |

### Rubric Dimensions (LLM-as-a-Judge)

The agent is graded by `gemini-2.5-flash` (3 judge samples) against these rubrics:

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
export GOOGLE_API_KEY="your-key"  # pragma: allowlist secret

# Option B: Vertex AI
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="1"
```

Tests will be **automatically skipped** if no credentials are detected (via the `requires_credentials` marker in `conftest.py`).

### Two Ways to Run Evals

There are two distinct execution paths:

| Method | Command | Entry Point | How It Works |
|--------|---------|-------------|--------------|
| **pytest** | `uv run pytest eval/test_evaluate.py -v` | `eval/test_evaluate.py` | Uses `AgentEvaluator.evaluate_eval_set()` directly |
| **poe eval** | `uv run poe eval` | `deploy/run_eval.py` | Uses `adk eval` CLI with temp file processing |

### Local Run (pytest)

```bash
# Run all evaluation tests
uv run pytest eval/test_evaluate.py -v

# Run a specific eval test
uv run pytest eval/test_evaluate.py::test_error_diagnosis -v

# Run with detailed output
uv run pytest eval/test_evaluate.py -v -s
```

### Local Run (adk eval CLI via poe)

```bash
# Run all evaluations via the deploy script (uses adk eval CLI)
uv run poe eval

# Override the project ID
python deploy/run_eval.py --project my-test-project
```

The `deploy/run_eval.py` script:
1. Sets `SRE_AGENT_EVAL_MODE=true` and disables all OpenTelemetry exporters
2. Resolves the project ID from `--project` flag, `GOOGLE_CLOUD_PROJECT` env var, or falls back to `my-test-project`
3. Copies all `.test.json` files to a temp directory with placeholder project IDs replaced
4. Runs `adk eval sre_agent <files> --config_file_path eval/test_config.json`
5. Optionally syncs results to Vertex AI if `--sync` is passed

### Vertex AI Sync

```bash
# Sync results to Vertex AI Evaluation Service for historical tracking
uv run poe eval --sync
```

**Prerequisites for sync**:
1. Set `EVAL_STORAGE_URI="gs://YOUR_BUCKET/sre-agent-evals"` in your `.env` file
2. The Vertex AI SDK and pandas must be installed

View results in **GCP Console > Vertex AI > Evaluations**.

---

## `conftest.py` -- Shared Eval Fixtures

The `conftest.py` module provides shared utilities used by all tests in `test_evaluate.py`:

### Constants

| Name | Value | Description |
|------|-------|-------------|
| `EVAL_DIR` | `Path(__file__).parent` | Directory containing eval test data files |
| `AGENT_MODULE` | `"sre_agent.agent"` | Agent module path passed to `AgentEvaluator` |
| `_PLACEHOLDER_PROJECT_IDS` | 6 project ID strings | Placeholders replaced with `GOOGLE_CLOUD_PROJECT` |

### Functions

#### `has_eval_credentials() -> bool`

Checks whether Google AI API key (`GOOGLE_API_KEY` or `GEMINI_API_KEY`) or Vertex AI credentials (`GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` + `GOOGLE_GENAI_USE_VERTEXAI`) are available. Used by the `requires_credentials` skip marker.

#### `load_eval_set(file_name: str) -> EvalSet`

Loads and parses an evaluation set from a `.test.json` file. Performs dynamic project ID substitution by replacing all placeholder project IDs with the value of `GOOGLE_CLOUD_PROJECT`. Handles multiple `EvalSet` parsing methods for ADK compatibility (`__init__`, `model_validate`, `parse_obj`).

#### `load_eval_config() -> dict`

Loads the shared evaluation criteria dictionary from `test_config.json`. Returns the `criteria` key suitable for `EvalConfig`.

#### `make_tool_trajectory_config(trajectory_score=0.8, response_score=0.0) -> EvalConfig`

Creates an `EvalConfig` focused on tool trajectory evaluation. Uses `tool_trajectory_avg_score` and `response_match_score`. Default trajectory threshold is 0.8.

#### `make_full_config() -> EvalConfig`

Creates an `EvalConfig` using the full shared criteria from `test_config.json`. This includes tool trajectory, rubric-based quality, response match, hallucination, and safety checks.

### Pytest Marker

```python
requires_credentials = pytest.mark.skipif(
    not has_eval_credentials(),
    reason="Evaluation tests require Google AI API key or Vertex AI credentials."
)
```

All test functions are decorated with `@requires_credentials` so they are skipped gracefully in environments without credentials.

---

## `test_evaluate.py` -- Test Entry Points

All 9 test functions follow the same pattern:

1. Load the evaluation set with `load_eval_set("filename.test.json")`
2. Create an `EvalConfig` (either inline, via `make_tool_trajectory_config()`, or via `make_full_config()`)
3. Call `AgentEvaluator.evaluate_eval_set()` with the agent module, eval set, and config

All tests are `async` (`@pytest.mark.asyncio`) and require credentials (`@requires_credentials`).

**Notable**: `test_tool_selection` is marked `@pytest.mark.xfail` because the agent may ask for clarification even when a Project ID is provided in the query.

---

## CI/CD Integration

Evaluations are integrated into `cloudbuild.yaml` as **Stage 7** (`run-evals`), a post-deployment quality check.

### Key Configuration

- **Step ID**: `run-evals`
- **Runs after**: `deploy-frontend`
- **Policy**: `allowFailure: true` -- does not block the release but surfaces regressions
- **Command**: `uv run poe eval`

### `EVAL_PROJECT_ID` Secret

The eval step uses an optional Secret Manager secret (`eval-project-id`) to target a specific GCP project. If the secret is not configured, it falls back to the Cloud Build project ID (`$PROJECT_ID`):

```bash
export GOOGLE_CLOUD_PROJECT=${EVAL_PROJECT_ID:-$FALLBACK_PROJECT_ID}
```

To configure a dedicated eval project:

```bash
echo -n "your-eval-project-id" | gcloud secrets create eval-project-id \
  --data-file=- --project=YOUR_BUILD_PROJECT_ID
```

### IAM Setup for CI/CD

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

for ROLE in aiplatform.user cloudtrace.user logging.viewer monitoring.viewer \
            compute.viewer serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CB_SA" \
    --role="roles/$ROLE" \
    --condition=None
done
```

### Local Developer Setup

```bash
USER_EMAIL="your@email.com"
for ROLE in aiplatform.user aiplatform.viewer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/$ROLE" \
    --condition=None
done
```

---

## Writing New Eval Scenarios

### File Format

Each `.test.json` file follows the ADK `EvalSet` schema:

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
2. Use one of the recognized placeholder project IDs (e.g., `TEST_PROJECT_ID`, `microservices-prod`, `search-prod`, `ecommerce-prod`, `web-platform-prod`, `payments-prod`) for GCP project references -- these are automatically replaced at runtime
3. List expected tools in `intermediate_data.tool_uses` in call order
4. Write a detailed `final_response` as the gold standard reference
5. Add a new test function (or add the file to an existing one) in `test_evaluate.py`:
   ```python
   @requires_credentials
   @pytest.mark.asyncio
   async def test_my_new_scenario():
       eval_set = load_eval_set("my_new_scenario.test.json")
       config = make_tool_trajectory_config(trajectory_score=0.8)
       await AgentEvaluator.evaluate_eval_set(
           agent_module=AGENT_MODULE,
           eval_set=eval_set,
           eval_config=config,
           print_detailed_results=False,
       )
   ```
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

## Evaluation Mode (`SRE_AGENT_EVAL_MODE`)

When evals run via `deploy/run_eval.py`, the environment variable `SRE_AGENT_EVAL_MODE=true` is set automatically. This enables eval-safe behavior in tool clients:

- GCP API clients return informative error messages instead of raising exceptions for common errors (404, permission denied, API not enabled)
- MCP tools return mock data instead of making real BigQuery/PromQL calls
- All OpenTelemetry exporters are disabled to prevent background thread hangs

This means evals can run without access to real GCP telemetry data -- the agent is evaluated on its *reasoning* and *tool selection*, not on whether real data exists.

---

## Monitoring and Historical Tracking

### Vertex AI Evaluation Service

Results are synced to GCS and visualized in Vertex AI:

1. Set `EVAL_STORAGE_URI="gs://YOUR_BUCKET/sre-agent-evals"` in `.env`
2. Run `uv run poe eval --sync`
3. Navigate to **Vertex AI > Evaluations** in GCP Console

The sync process:
1. Locates the latest ADK results in `.adk/` or `deploy/.adk/` directories
2. Transforms `.data.json` result files into prompt/response datasets
3. Submits to Vertex AI with agent-specific metrics (`FINAL_RESPONSE_QUALITY`, `TOOL_USE_QUALITY`, `HALLUCINATION`, `SAFETY`)
4. Falls back to legacy `EvalTask` API with `instruction_following` and `text_quality` metrics if the new API is unavailable

### Metrics Tracked Over Time

- Tool trajectory exact match rate
- Rubric scores per dimension (technical precision, causality, actionability)
- Response match quality
- Hallucination rate
- Safety score

For the full evaluation standards, see [docs/EVALUATIONS.md](../docs/EVALUATIONS.md).
