# Evaluation Guide

This guide explains how to benchmark the SRE Agent's performance using the evaluation harness.

## Running Evaluations

The project uses a custom evaluation script `deploy/run_eval.py` that executes test cases against the agent and scores the results.

```bash
uv run poe eval
```

## Creating Test Cases

Test cases are JSON files located in `eval/`.

**Structure:**
```json
{
  "id": "e2e_latency_analysis",
  "name": "E2E Latency Analysis",
  "query": "Analyze the latency spike in the checkout service",
  "expected_steps": [
    "analyze_aggregate_metrics",
    "find_exemplar_traces",
    "analyze_trace_comprehensive"
  ],
  "success_criteria": {
    "output_contains": ["checkout-service", "db-proxy"],
    "has_ui_event": "show_trace_waterfall"
  }
}
```

## Metrics

The evaluation harness reports:
*   **Success Rate**: Percentage of test cases passing all criteria.
*   **Tool Usage**: Accuracy of tool selection.
*   **Latency**: Time to completion.
*   **Cost**: Token usage (if available).
