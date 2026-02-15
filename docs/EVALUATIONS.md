# SRE Agent Evaluation Standards

This document defines the evaluation standards for the SRE Agent, ensuring high-fidelity reasoning, reliable tool usage, and actionable reporting.

For instructions on writing new eval scenarios and running the framework, see [`eval/README.md`](../eval/README.md).

## 1. Dual-Layer Evaluation Architecture

The SRE Agent uses a hybrid approach to balance developer velocity with production-grade auditing.

### Layer 1: Local / CI Quality Gate

*   **Tool**: ADK `AgentEvaluator` (via `uv run pytest eval/test_evaluate.py`) or `adk eval` CLI (via `uv run poe eval`)
*   **Purpose**: Rapid iteration and surfacing regressions in CI/CD.
*   **Configuration**: `eval/test_config.json` (shared criteria) and per-test overrides in `eval/test_evaluate.py`.
*   **Key Metrics**:
    *   `tool_trajectory_avg_score`: Ensures the agent uses the correct sequence of SRE tools (Aggregate > Triage > Deep Dive).
    *   `response_match_score`: Semantic match against gold standard diagnostic reports.
    *   `rubric_based_final_response_quality_v1`: LLM-as-a-Judge quality check for Technical Precision, Causality, and Actionability.
    *   `hallucinations_v1`: Zero tolerance for fabricated claims.
    *   `safety_v1`: Zero tolerance for unsafe outputs.

### Layer 2: Cloud-Native Vertex AI Sync

*   **Tool**: `vertexai.Client().evals` API (triggered via `uv run poe eval --sync`).
*   **Fallback**: Legacy `vertexai.preview.evaluation.EvalTask` when the new SDK is unavailable.
*   **Purpose**: Long-term tracking, auditing, and historical analysis in the Google Cloud Console.
*   **Platform**: Syncs to **Vertex AI > Evaluations** in GCP Console.
*   **Agent Metrics**:
    *   `FINAL_RESPONSE_QUALITY`: Response appropriateness and completeness
    *   `TOOL_USE_QUALITY`: Tool selection and invocation accuracy
    *   `HALLUCINATION`: Factual accuracy assessment
    *   `SAFETY`: Safety compliance evaluation

## 2. Evaluation Rubrics

The agent is judged by a "Teacher Model" (**Gemini 2.5 Flash**) against the following official SRE rubrics, defined in `eval/test_config.json`:

| Dimension | Description |
| :--- | :--- |
| **Technical Precision** | Identifies specific GCP signals (Traces, Logs, Metrics) with quantitative evidence. |
| **Root Cause Causality** | Explains the *WHY* (cascading failures), not just the *WHAT*. |
| **Actionability** | Provides clear recommendations or specific `gcloud` commands for remediation. |

The rubric evaluation uses 3 judge samples (`num_samples: 3`) and requires a minimum threshold of 0.8.

## 3. Tool Usage Best Practices (Anti-Hallucination)

To pass the `tool_trajectory` metrics, the agent must adhere to strict syntax rules implemented in its sub-agent prompts:

*   **PromQL ONLY**: The `query_promql` tool does NOT support MQL (Monitoring Query Language). Hallucinating `fetch` or `::` syntax results in immediate failure.
*   **Resource Labeling**: For GKE and GCE, resource labels must be precise (e.g., `resource.labels.container_name` vs `container_name`).
*   **Verify-then-Query**: The agent is instructed to use `list_metric_descriptors` before querying unknown metrics to prevent hallucinated metric names (e.g., `core_usage_time` vs `usage_time`).

## 4. Evaluation Mode (`SRE_AGENT_EVAL_MODE`)

When evaluations run via `deploy/run_eval.py`, the environment variable `SRE_AGENT_EVAL_MODE=true` is set. This affects agent behavior in several ways:

*   **Graceful error handling**: GCP API clients (trace, logging, monitoring, alerts) return informative error messages instead of raising exceptions for common errors like 404s, permission denied, or API not enabled. This allows the agent to demonstrate its reasoning even without real GCP data.
*   **MCP mock fallback**: When `SRE_AGENT_EVAL_MODE=true`, MCP tools return mock data instead of making real BigQuery/PromQL calls.
*   **Telemetry disabled**: OpenTelemetry exporters are set to `none` to prevent background thread hangs during eval runs.

The following environment variables are automatically set by `run_eval.py`:

| Variable | Value | Purpose |
| :--- | :--- | :--- |
| `SRE_AGENT_EVAL_MODE` | `true` | Enables eval-safe error handling in tool clients |
| `OTEL_SDK_DISABLED` | `true` | Disables OpenTelemetry SDK |
| `DISABLE_TELEMETRY` | `true` | Disables project telemetry |
| `OTEL_TRACES_EXPORTER` | `none` | Prevents trace export |
| `OTEL_METRICS_EXPORTER` | `none` | Prevents metrics export |
| `OTEL_LOGS_EXPORTER` | `none` | Prevents log export |

## 5. Test Coverage

The eval suite covers **20 test cases** across 9 categories in 9 `.test.json` files:

| Category | File | Cases | What It Tests |
| :--- | :--- | :--- | :--- |
| Sanity | `basic_capabilities.test.json` | 1 | Agent self-description (`capability_check`) |
| Tool Routing | `tool_selection.test.json` | 3 | Correct tool selection: trace, logs, metrics |
| Analysis | `metrics_analysis.test.json` | 1 | PromQL metric analysis, CPU anomaly detection |
| E2E Investigation | `incident_investigation.test.json` | 1 | Multi-stage latency investigation (checkout) |
| Error Diagnosis | `error_diagnosis.test.json` | 3 | DB pool exhaustion, cascading timeouts, OOM kills |
| Multi-Signal Correlation | `multi_signal_correlation.test.json` | 2 | Deploy regressions, gradual SLO degradation |
| GKE Debugging | `kubernetes_debugging.test.json` | 3 | Pod crashloops, node pressure, HPA scaling failures |
| SLO Analysis | `slo_burn_rate.test.json` | 2 | Error budget exhaustion, multi-window SLO violations |
| Failure Modes | `failure_modes.test.json` | 4 | Invalid projects, hallucination resistance, rate limits, cascading failures |

### Quality Criteria per Test Category

Each test function in `test_evaluate.py` uses a different evaluation configuration:

| Test Function | Eval Config | Criteria Focus |
| :--- | :--- | :--- |
| `test_agent_capabilities` | `response_match_score >= 0.6` | Response quality only |
| `test_tool_selection` | `tool_trajectory >= 0.8` | Tool trajectory (xfail: may ask for clarification) |
| `test_metrics_analysis` | `tool_trajectory >= 0.8` | Tool trajectory |
| `test_incident_investigation` | `tool_trajectory >= 0.8` | Tool trajectory |
| `test_error_diagnosis` | Full `test_config.json` criteria | All rubrics + trajectory + hallucination + safety |
| `test_multi_signal_correlation` | Full `test_config.json` criteria | All rubrics + trajectory + hallucination + safety |
| `test_kubernetes_debugging` | `tool_trajectory >= 0.8` | Tool trajectory |
| `test_slo_burn_rate` | `tool_trajectory >= 0.8` | Tool trajectory |
| `test_failure_modes` | `response_match >= 0.5, hallucinations_v1 = 0.0, safety_v1 = 0.0` | Graceful degradation + safety |

## 6. CI/CD Setup (Cloud Build)

Evaluations run as **Stage 7** in the Cloud Build pipeline (`cloudbuild.yaml`), after frontend deployment.

### Pipeline Configuration

```yaml
# Stage 7: run-evals
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'run-evals'
  allowFailure: true              # Does not block the release
  waitFor: ['deploy-frontend']    # Runs after deployment
```

**Key behavior**: `allowFailure: true` means eval failures surface regressions but do not block the deployment pipeline.

### Project ID Resolution

The eval step resolves the GCP project ID in this order:

1. `EVAL_PROJECT_ID` secret from Secret Manager (if configured)
2. `FALLBACK_PROJECT_ID` (set to `$PROJECT_ID`, the Cloud Build project)

```bash
export GOOGLE_CLOUD_PROJECT=${EVAL_PROJECT_ID:-$FALLBACK_PROJECT_ID}
```

### Setting Up `EVAL_PROJECT_ID` (Optional)

If you want evals to run against a different project than the build project (for example, a stable test project with known telemetry data):

1. Create a secret in Secret Manager:
   ```bash
   echo -n "your-eval-project-id" | gcloud secrets create eval-project-id \
     --data-file=- --project=YOUR_BUILD_PROJECT_ID
   ```

2. The `cloudbuild.yaml` is already configured to pick up this secret:
   ```yaml
   availableSecrets:
     secretManager:
     - versionName: projects/$PROJECT_ID/secrets/eval-project-id/versions/latest
       env: 'EVAL_PROJECT_ID'
   ```

### IAM Roles for Cloud Build

Grant the following roles to your Cloud Build Service Account (`PROJECT_NUMBER@cloudbuild.gserviceaccount.com`):

*   `roles/cloudtrace.user`
*   `roles/logging.viewer`
*   `roles/monitoring.viewer`
*   `roles/aiplatform.user`
*   `roles/compute.viewer`
*   `roles/serviceusage.serviceUsageConsumer`

You can use the provided script:
```bash
python deploy/grant_permissions.py \
  --project-id YOUR_PROJECT_ID \
  --service-account PROJECT_NUMBER@cloudbuild.gserviceaccount.com
```

### Environment Variables in CI

The eval step in Cloud Build sets these environment variables:

| Variable | Value | Purpose |
| :--- | :--- | :--- |
| `FALLBACK_PROJECT_ID` | `$PROJECT_ID` | Build project as default |
| `GOOGLE_CLOUD_LOCATION` | `$_LOCATION` (default `us-central1`) | GCP region |
| `RUNNING_IN_AGENT_ENGINE` | `true` | Indicates cloud execution |
| `STRICT_EUC_ENFORCEMENT` | `false` | Allows ADC fallback |
| `SRE_AGENT_ENFORCE_POLICY` | `false` | Disables policy enforcement |

## 7. Project ID Placeholder Substitution

Both `conftest.py` (pytest path) and `deploy/run_eval.py` (CLI path) replace placeholder project IDs in `.test.json` files with the actual `GOOGLE_CLOUD_PROJECT` value. The following placeholders are substituted:

*   `TEST_PROJECT_ID`
*   `microservices-prod`
*   `search-prod`
*   `ecommerce-prod`
*   `web-platform-prod`
*   `payments-prod`

This allows test scenarios to use realistic project names while running against any GCP project.

---
*Last verified: 2026-02-15 -- Auto SRE Team*
