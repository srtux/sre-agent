# 🏆 Agent Evaluation: World-Class Quality Framework

This guide explains how to benchmark the SRE Agent's reasoning quality and tool-use precision using our **Evaluation-Driven Development (EDD)** framework.

## 🏛️ Philosophy: The Reasoning Pipeline
Unlike standard software, an SRE Agent's "correctness" is subjective. We evaluate it on two layers:
1.  **Trajectory Integrity**: Did it call the right tools in the right order? (Aggregate -> Triage -> Deep Dive).
2.  **Response Quality**: Is the final answer technically precise, causal, and actionable?

## 🚀 Running Evaluations

For detailed instructions on defining test cases and configuring metrics, see the **[Evaluation README](../../eval/README.md)**.

### Local Developer Loop
Use the `poe` task to run the suite against your current local changes:

```bash
uv run poe eval
```

## 🌉 CI/CD Quality Gate
This suite is integrated into our `cloudbuild.yaml`. Every deployment is blocked until it passes:
*   **100% Trajectory Score**: Ensures no regressions in the agent's diagnostic logic.
*   **80%+ Rubric Score**: Uses `gemini-1.5-pro` as a "Teacher Model" to grade the technical quality of the response.

## 📈 Monitoring
Results are exported to GCS and visualized in **Vertex AI Experiments**. See the [Monitoring Section](../../eval/README.md#📈-monitoring--historical-tracking) for details.
