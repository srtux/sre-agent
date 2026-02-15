# Agent Evaluation: World-Class Quality Framework

This guide explains how to benchmark the SRE Agent's reasoning quality and tool-use precision using our **Evaluation-Driven Development (EDD)** framework.

## Philosophy: The Reasoning Pipeline

Unlike standard software, an SRE Agent's "correctness" is subjective. We evaluate it on two layers:
1.  **Trajectory Integrity**: Did it call the right tools in the right order? (Aggregate > Triage > Deep Dive).
2.  **Response Quality**: Is the final answer technically precise, causal, and actionable?

## Running Evaluations

For detailed instructions on defining test cases, configuring metrics, and understanding the `conftest.py` fixtures, see the **[Evaluation README](../../eval/README.md)**.

### Two Execution Paths

| Method | Command | Entry Point | How It Works |
|--------|---------|-------------|--------------|
| **pytest** | `uv run pytest eval/test_evaluate.py -v` | `eval/test_evaluate.py` | Uses `AgentEvaluator.evaluate_eval_set()` directly |
| **poe eval** | `uv run poe eval` | `deploy/run_eval.py` | Uses `adk eval` CLI with temp file processing |

### Local Developer Loop

Use the `poe` task to run the full suite via the `adk eval` CLI:

```bash
uv run poe eval
```

Or run specific test categories via pytest:

```bash
uv run pytest eval/test_evaluate.py::test_error_diagnosis -v
```

Or run all pytest eval tests:

```bash
uv run pytest eval/test_evaluate.py -v -s
```

### Vertex AI Synchronization

To sync local evaluation results with the **Vertex AI GenAI Evaluation Service**, use:

```bash
uv run poe eval --sync
```

*   **Prerequisites**: Set `EVAL_STORAGE_URI="gs://YOUR_BUCKET/sre-agent-evals"` in `.env`
*   **Benefits**: Visualize historical quality trends, compare versions, and use agent-specific rubric metrics (`FINAL_RESPONSE_QUALITY`, `TOOL_USE_QUALITY`, `HALLUCINATION`, `SAFETY`) in the GCP console.

## Evaluation Mode

When evals run via `deploy/run_eval.py`, the environment variable `SRE_AGENT_EVAL_MODE=true` is set automatically. This enables eval-safe behavior: GCP API clients return informative error messages instead of raising exceptions, MCP tools return mock data, and all OpenTelemetry exporters are disabled. This means evals can run without access to real GCP telemetry data.

## CI/CD Quality Gate

This suite is integrated into `cloudbuild.yaml` as **Stage 7** (`run-evals`). Evaluations run as a post-deployment quality check with `allowFailure: true` (does not block the release but surfaces regressions).

*   **Trajectory Integrity**: Verified via ADK `AgentEvaluator` to ensure correct tool sequence.
*   **Technical Quality**: Graded via **Rubrics** using `gemini-2.5-flash` as the evaluator model (3 judge samples), with optional sync to Vertex AI Evaluations.
*   **Project targeting**: Uses the `EVAL_PROJECT_ID` secret from Secret Manager if configured, otherwise falls back to the build project ID.

For full CI/CD setup instructions (IAM roles, `EVAL_PROJECT_ID` secret, environment variables), see [docs/EVALUATIONS.md](../EVALUATIONS.md#6-cicd-setup-cloud-build).

## Monitoring

Results are exported to GCS and visualized in **Vertex AI Evaluations**. See the [Monitoring Section](../../eval/README.md#monitoring-and-historical-tracking) for details.
