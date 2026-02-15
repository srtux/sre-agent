# SRE Agent Evaluation Standards

This document defines the "World-Class" evaluation standards for the SRE Agent, ensuring high-fidelity reasoning, reliable tool usage, and actionable reporting.

## 1. Dual-Layer Evaluation Architecture

The SRE Agent uses a hybrid approach to balance developer velocity with production-grade auditing.

### Layer 1: Local / CI Quality Gate
*   **Tool**: `adk eval` (triggered via `uv run poe eval`)
*   **Purpose**: Rapid iteration and blocking the CI/CD pipeline on regressions.
*   **Configuration**: `eval/test_config.json`
*   **Key Metrics**:
    *   `tool_trajectory_avg_score`: Ensures the agent uses the correct sequence of SRE tools (Aggregate -> Triage -> Deep Dive).
    *   `rubric_based_final_response_quality_v1`: Gradual quality check for Technical Precision, Causality, and Actionability.
    *   `final_response_match_v2`: Semantic match against "Gold Standard" diagnostic reports.

### Layer 2: Cloud-Native Vertex AI Sync
*   **Tool**: `vertexai.preview.evaluation.EvalTask` (triggered via `uv run poe eval --sync`)
*   **Purpose**: Long-term tracking, auditing, and historical analysis in the Google Cloud Console.
*   **Platform**: Syncs to the **Vertex AI > Evaluations** and **Experiments** tabs.
*   **Advanced Metrics**:
    *   `trajectory_exact_match`
    *   `trajectory_precision` / `trajectory_recall`
    *   `groundedness` (Ensures responses are strictly based on tool outputs).

## 2. Evaluation Rubrics

The agent is judged by a "Teacher Model" (**Gemini 2.5 Flash**) against the following official SRE rubrics:

| Dimension | Description |
| :--- | :--- |
| **Technical Precision** | Identifies specific GCP signals (Traces, Logs, Metrics) with quantitative evidence. |
| **Root Cause Causality** | Explains the *WHY* (cascading failures), not just the *WHAT*. |
| **Actionability** | Provides clear recommendations or specific `gcloud` commands for remediation. |

## 3. Tool Usage Best Practices (Anti-Hallucination)

To pass the `tool_trajectory` metrics, the agent must adhere to strict syntax rules implemented in its sub-agent prompts:

*   **PromQL ONLY**: The `query_promql` tool does NOT support MQL (Monitoring Query Language). Hallucinating `fetch` or `::` syntax results in immediate failure.
*   **Resource Labeling**: For GKE and GCE, resource labels must be precise (e.g., `resource.labels.container_name` vs `container_name`).
*   **Verify-then-Query**: The agent is instructed to use `list_metric_descriptors` before querying unknown metrics to prevent hallucinated metric names (e.g., `core_usage_time` vs `usage_time`).

## 5. CI/CD Setup (Cloud Build)

To run evaluations successfully in Cloud Build, follow these steps:

### 1. Grant IAM Roles
Grant the following roles to your Cloud Build Service Account (`PROJECT_NUMBER@cloudbuild.gserviceaccount.com`):
*   `roles/cloudtrace.user`
*   `roles/logging.viewer`
*   `roles/monitoring.viewer`
*   `roles/aiplatform.user`
*   `roles/compute.viewer`
*   `roles/serviceusage.serviceUsageConsumer`

You can use the provided script:
```bash
python deploy/grant_permissions.py --project-id YOUR_PROJECT_ID --service-account PROJECT_NUMBER@cloudbuild.gserviceaccount.com
```

### 2. Configure Secrets (Optional)
By default, evals run against the project currently being built (`$PROJECT_ID`). If you want to run evals against a *different* project (e.g., a stable test project), create a secret in Secret Manager:
*   **Secret Name**: `eval-project-id`
*   **Value**: The target GCP Project ID.

The `cloudbuild.yaml` is configured to automatically pick up this secret if it exists.

---
*Last verified: 2026-02-02 — Auto SRE Team*
