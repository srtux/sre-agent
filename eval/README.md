# 🏆 World-Class SRE Agent Evaluations

This directory contains the "Award-Winning" evaluation framework for the SRE Agent. It uses the **Vertex AI Agent Development Kit (ADK)** to verify both the final responses and the internal reasoning trajectories against a "Golden Dataset."

## 🏛️ Architecture: The Quality Gate
We follow an **Evaluation-Driven Development (EDD)** model. Every release must pass a suite of semantic and structural tests before it can be deployed to production.

### 1. Model-Based Evaluation (LLM-as-a-Judge)
We use `gemini-2.5-flash` as a "Teacher Model" to evaluate the agent's "Student" responses.
*   **Metric**: `rubric_based_final_response_quality_v1`
*   **Dimensions**: Technical Precision, Root Cause Causality, and Actionability.

### 2. Trajectory Score (Tool-Use Integrity)
We don't just care about what the agent says; we care about **how it got there**.
*   **Metric**: `tool_trajectory_avg_score`
*   **Goal**: Ensure the agent follows the 3-Stage Analysis Pipeline (Aggregate -> Triage -> Deep Dive).

## 🚀 Running Evaluations

To run the local evaluation suite:

```bash
uv run poe eval
```

This script (located at `deploy/run_eval.py`):
1.  Cleans and prepares the Golden Dataset (`eval/*.test.json`).
2.  Injects your current `GOOGLE_CLOUD_PROJECT` for live tool-connectivity checks.
3.  Executes `adk eval` with the `test_config.json` requirements.

## 📂 The Golden Dataset

Each test set is a collection of "Ideal Investigations":

*   **`incident_investigation.test.json`**: (NEW) Complex, multi-stage investigation scenarios.
*   **`metrics_analysis.test.json`**: Precision PromQL and anomaly detection.
*   **`tool_selection.test.json`**: Structural checks for tool routing.
*   **`basic_capabilities.test.json`**: Sanity checks for the agent's "personality" and time awareness.

## 🌉 CI/CD Integration

This suite is integrated into `cloudbuild.yaml` as a **Mandatory Quality Gate**.
*   **Step**: `run-evals`
*   **Impact**: If the `trajectory_score` falls below 100% or the `rubric_score` falls below 80%, the build fails and deployment is blocked.

### 🔑 IAM Setup
To run evaluations (either locally or in CI/CD), the executing identity must have permissions for observability data and Vertex AI.

#### 1. Cloud Build Setup (CI/CD)
Run this command to configure the build service account:

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CB_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Grant necessary roles for agent analysis, MCP discovery, and model-based evaluation
for ROLE in aiplatform.user aiplatform.viewer logging.viewer monitoring.viewer \
            cloudtrace.user bigquery.jobUser bigquery.dataViewer \
            cloudapiregistry.viewer resourcemanager.projectViewer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CB_SA" \
    --role="roles/$ROLE" \
    --condition=None
done
```

#### 2. Local Developer Setup
Ensure your local identity (`gcloud auth application-default login`) has these roles:

```bash
# Replace with your email
USER_EMAIL="user@google.com"

for ROLE in aiplatform.user aiplatform.viewer cloudapiregistry.viewer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="roles/$ROLE" \
    --condition=None
done
```

## � Monitoring & Historical Tracking

### Vertex AI Experiments
To track historic pass/fail rates and compare evaluation scores across different model versions or logic updates, we use **Vertex AI Experiments** integration.

1.  **Storage**: Evaluation results are stored in Google Cloud Storage.
2.  **Configuration**: Set the `EVAL_STORAGE_URI` environment variable in your `.env` or CI/CD pipeline:
    ```bash
    EVAL_STORAGE_URI="gs://YOUR_PROJECT_EVALS_BUCKET/sre-agent-evals"
    ```
3.  **Visualization**:
    *   Navigate to **Vertex AI > Experiments** in the Google Cloud Console.
    *   Select your project and look for experiment runs starting with "sre-agent". You'll see a timeline of trajectory scores and LLM-judge rubrics.

### Latest Features (GenAI Evaluation)
Your setup uses the latest **Vertex AI GenAI Evaluation Service** capabilities (announced Jan 2026):
*   **Dual-Layer Evaluation**:
    *   **Locally**: You use `adk eval` (ADK/Agent SDK) for rapid dev loops and blocking the build.
    *   **Cloud-Native**: `run_eval.py` automatically triggers the `EvalTask` SDK (GenAI Evaluation Service). This syncs your runs to the **Vertex AI > Evaluations** tab in the console.
*   **Agent-Specific Metrics**: Includes `trajectory_exact_match` and `trajectory_precision` to grade the tool-use quality of your SRE investigations.
*   **Semantic Rubrics**: Uses `gemini-2.5-flash` as the grading engine (Auto-SxS equivalent), supporting nuanced reasoning checks.
*   **Quality Gates**: Automatically blocks deployments via `cloudbuild.yaml` if the agent fails the defined rubrics.

For a deep dive into the technical architecture and "World-Class" standards, see [docs/EVALUATIONS.md](../docs/EVALUATIONS.md).

## �📝 Defining New Tests

To define a new "Award-Winning" test case, add it to one of the `.test.json` files using the `eval_cases` format. Focus on defining the `tool_uses` in the `intermediate_data` to ensure the agent doesn't "skip steps" or halluncinate tool results.
