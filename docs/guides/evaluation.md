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

### Vertex AI Synchronization
To sync local evaluation results with the **Vertex AI GenAI Evaluation Service** (Rapid Eval), use:

```bash
uv run poe eval --sync
```
*   **Benefits**: Visualize historical quality trends, compare versions, and use standard Rubric-based grading in the GCP console.

## 🌉 CI/CD Quality Gate
This suite is integrated into our `cloudbuild.yaml`. Every deployment is blocked until it passes:
*   **Trajectory Integrity**: Verified via `TrajectorEvaluator` to ensure correct tool sequence.
*   **Technical Quality**: Graded via **Rubrics** using `gemini-1.5-pro` as the evaluator model, with optional sync to Vertex AI Experiments.

## 📈 Monitoring
Results are exported to GCS and visualized in **Vertex AI Experiments**. See the [Monitoring Section](../../eval/README.md#📈-monitoring--historical-tracking) for details.
