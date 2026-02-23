# Online GenAI Evaluation Service

## Overview

The Online GenAI Evaluation Service enables continuous, automated quality assessment of LLM interactions within AutoSRE. Instead of dynamically provisioning infrastructure per agent, it uses a **"Single Worker, Dynamic Config"** architecture: users toggle evaluations on/off per agent via API, and a scheduled worker evaluates un-assessed traces.

## Architecture

```
┌─────────────┐   POST /api/v1/evals/config/{agent}   ┌──────────────────┐
│  UI / API   │ ─────────────────────────────────────► │  EvalConfig DB   │
│  Client     │                                        │  (StorageService)│
└─────────────┘                                        └────────┬─────────┘
                                                                │
                              ┌─────────────────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Eval Worker     │  (Cloud Scheduler trigger)
                    │  (eval_worker.py)│
                    └──┬───────┬───────┘
                       │       │
              ┌────────┘       └────────┐
              ▼                         ▼
    ┌──────────────────┐     ┌──────────────────┐
    │  BigQuery        │     │  Vertex AI       │
    │  (un-evaluated   │     │  Batch Eval      │
    │   GenAI spans)   │     │  (EvalTask)      │
    └──────────────────┘     └────────┬─────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  OTel Events     │
                            │  (gen_ai.eval    │
                            │   .result)       │
                            └──────────────────┘
```

## Components

### 1. EvalConfig API (`sre_agent/api/routers/evals.py`)

CRUD endpoints for managing per-agent evaluation configurations.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/evals/config` | List all eval configs |
| `POST` | `/api/v1/evals/config/{agent_name}` | Create or update a config |
| `GET` | `/api/v1/evals/config/{agent_name}` | Get a single config |
| `DELETE` | `/api/v1/evals/config/{agent_name}` | Delete a config |

**EvalConfig fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_name` | `str` | required | Agent identifier (PK) |
| `is_enabled` | `bool` | `false` | Whether evaluation is active |
| `sampling_rate` | `float` | `1.0` | Fraction of traces to evaluate (0.0–1.0) |
| `metrics` | `list[str]` | `[]` | Vertex AI metric names (e.g. `["coherence", "fluency"]`) |
| `last_eval_timestamp` | `datetime?` | `null` | Timestamp of last evaluated span |

**Example — enable evaluation for an agent:**
```bash
curl -X POST http://localhost:8001/api/v1/evals/config/sre-agent \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true, "sampling_rate": 0.5, "metrics": ["coherence", "fluency"]}'
```

### 2. OTel Eval Logger (`sre_agent/tools/common/telemetry.py`)

The `log_evaluation_result()` function logs evaluation scores as OpenTelemetry events following the [GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/#event-gen_aievaluationresult).

- Creates a `SpanContext` linked to the original LLM trace via `trace_id`/`span_id`
- Starts a child span named `gen_ai.evaluation`
- Emits `gen_ai.evaluation.result` events with attributes:
  - `gen_ai.evaluation.metric.name`
  - `gen_ai.evaluation.score`
  - `gen_ai.evaluation.explanation`

### 3. Batch Evaluation Worker (`sre_agent/services/eval_worker.py`)

The core worker orchestrates the evaluation pipeline:

1. **Read configs** — fetch all enabled `EvalConfig` entries
2. **Query BigQuery** — find GenAI spans not yet evaluated (LEFT JOIN against `gen_ai.evaluation` spans)
3. **Apply sampling** — filter spans by `sampling_rate`
4. **Run Vertex AI eval** — `EvalTask` with configured metrics
5. **Log results** — emit OTel events via `log_evaluation_result()`
6. **Update cursor** — advance `last_eval_timestamp` to avoid re-processing

**Running the worker:**
```bash
# Direct CLI
uv run python -m sre_agent.services.eval_worker

# Or import and call
from sre_agent.services.eval_worker import run_scheduled_evaluations
result = await run_scheduled_evaluations()
```

**Environment variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project for BigQuery queries | required |
| `SRE_AGENT_EVAL_BQ_DATASET` | BigQuery dataset with OTel exports | `otel_export` |

### BigQuery Dataset Discovery

The evaluation service automatically attempts to discover the correct BigQuery dataset for a project if `SRE_AGENT_EVAL_BQ_DATASET` is not set. It uses the following priority:

1.  **Managed Trace Link**: Queries the Cloud Observability API for any bucket linked to the `Spans` (trace) dataset.
2.  **Environment Variable**: Falls back to the value of `SRE_AGENT_EVAL_BQ_DATASET` (defaults to `otel_export`).

This discovery ensures that traces stored in dedicated Observability buckets are correctly identified even if they differ from the default log bucket.

## Supported Metrics

The worker resolves metric names against `vertexai.evaluation.MetricPromptTemplateExamples.Pointwise`. Common metrics:

- `coherence` — Logical consistency of the response
- `fluency` — Grammatical and linguistic quality
- `groundedness` — Factual accuracy against provided context
- `safety` — Absence of harmful content
- `fulfillment` — How well the response addresses the prompt

## Testing

```bash
# Run all eval service tests (56 tests)
uv run poe test-fast -- tests/unit/sre_agent/api/routers/test_evals.py \
  tests/unit/sre_agent/tools/common/test_telemetry_eval.py \
  tests/unit/sre_agent/services/test_eval_worker.py
```

## Future Work (Phase 2+)

- Frontend UI toggle for enabling/disabling evaluations per agent
- Dashboard visualization of evaluation scores over time
- Alerting on evaluation score degradation
- Custom metric prompt templates
- Cost tracking and budget controls for Vertex AI evaluations
