# Online GenAI Evaluation Service

## Overview

The Online GenAI Evaluation Service enables continuous, automated quality assessment of LLM interactions within AutoSRE. It uses a **"Single Worker, Dynamic Config"** architecture: users toggle evaluations on/off per agent via the AgentOps UI (Evals tab), and a worker evaluates un-assessed **production traces** from BigQuery using the [Vertex AI Gen AI Evaluation Service](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-agents).

This is separate from the offline ADK-based eval suite in `eval/` (which is a CI/CD gate for tool trajectory and rubric scoring). The online eval service operates on **real production data**.

## Architecture

```
┌───────────────┐  POST /api/v1/evals/config/{agent}   ┌──────────────────┐
│  AgentOps UI  │ ──────────────────────────────────── ►│  EvalConfig DB   │
│  (Evals Tab)  │                                       │  (StorageService)│
└──────┬────────┘                                       └────────┬─────────┘
       │                                                         │
       │ POST /api/v1/evals/run                                  │
       │ (on-demand trigger)        ┌────────────────────────────┘
       │                            ▼
       │               ┌──────────────────────┐
       └──────────────►│  Eval Worker         │  (API trigger or Cloud Scheduler)
                       │  (eval_worker.py)    │
                       └──┬───────┬───────────┘
                          │       │
                 ┌────────┘       └────────┐
                 ▼                         ▼
       ┌──────────────────┐     ┌──────────────────────────┐
       │  BigQuery        │     │  Vertex AI Gen AI        │
       │  (_AllSpans)     │     │  Evaluation Service      │
       │  Production      │     │  (EvalTask + Pointwise   │
       │  GenAI traces    │     │   metric templates)      │
       └──────────────────┘     └────────┬─────────────────┘
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  OTel Events     │
                               │  gen_ai.evalua-  │
                               │  tion.result     │
                               └────────┬─────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │  AgentOps UI      │
                              │  (Eval charts &   │
                              │   score trends)   │
                              └───────────────────┘
```

## Components

### 1. EvalConfig API (`sre_agent/api/routers/evals.py`)

CRUD endpoints for managing per-agent evaluation configurations, plus an on-demand run trigger.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/evals/config` | List all eval configs |
| `POST` | `/api/v1/evals/config/{agent_name}` | Create or update a config |
| `GET` | `/api/v1/evals/config/{agent_name}` | Get a single config |
| `DELETE` | `/api/v1/evals/config/{agent_name}` | Delete a config |
| `POST` | `/api/v1/evals/run` | Trigger an on-demand evaluation run |
| `GET` | `/api/v1/evals/metrics/aggregate` | Aggregate eval metrics from BigQuery |

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

**Example — trigger an evaluation run:**
```bash
curl -X POST http://localhost:8001/api/v1/evals/run
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

The core worker orchestrates the evaluation pipeline using **production traces**:

1. **Read configs** — fetch all enabled `EvalConfig` entries from storage
2. **Query BigQuery** — find GenAI spans not yet evaluated (LEFT JOIN against `gen_ai.evaluation` spans). The SQL supports both modern (`gen_ai.input.messages` / `gen_ai.output.messages`) and legacy (`gen_ai.prompt` / `gen_ai.completion`) OTel GenAI attribute formats, as well as event-based content (`gen_ai.user.message` / `gen_ai.choice` events).
3. **Extract text** — parse structured JSON message attributes into plain text for evaluation
4. **Apply sampling** — filter spans by `sampling_rate`
5. **Run Vertex AI eval** — `vertexai.evaluation.EvalTask` with `MetricPromptTemplateExamples.Pointwise` metric templates
6. **Log results** — emit OTel events via `log_evaluation_result()`
7. **Update cursor** — advance `last_eval_timestamp` to avoid re-processing

**Triggering the worker:**
```bash
# Via the API (preferred — used by AgentOps UI)
curl -X POST http://localhost:8001/api/v1/evals/run

# Direct CLI
uv run python -m sre_agent.services.eval_worker

# Programmatically
from sre_agent.services.eval_worker import run_scheduled_evaluations
result = await run_scheduled_evaluations()
```

**Environment variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project for BigQuery queries | required |
| `SRE_AGENT_EVAL_BQ_DATASET` | BigQuery dataset with OTel exports | `otel_export` |

### BigQuery Span Extraction

The worker's SQL query (`_UNEVALUATED_SPANS_SQL`) extracts prompt/response text from production traces using a multi-fallback strategy:

| Priority | Input Attribute | Output Attribute | Source |
|----------|----------------|-----------------|--------|
| 1 | `gen_ai.input.messages` | `gen_ai.output.messages` | Modern OTel GenAI semconv (JSON arrays) |
| 2 | `gen_ai.prompt` | `gen_ai.completion` | Legacy OTel attribute names |
| 3 | `gen_ai.user.message` event | `gen_ai.choice` event | OTel span events |

This ensures compatibility regardless of which OpenTelemetry instrumentation library wrote the trace data.

### BigQuery Dataset Discovery

The evaluation service automatically attempts to discover the correct BigQuery dataset for a project if `SRE_AGENT_EVAL_BQ_DATASET` is not set. It uses the following priority:

1. **Logging API scan** — check Cloud Logging buckets for trace/span linked datasets
2. **Cloud Observability API** — query for `Spans` dataset in observability buckets
3. **BigQuery fallback** — check for common dataset names (`traces`, `obs_bucket_spans`)
4. **Environment variable** — fall back to `SRE_AGENT_EVAL_BQ_DATASET` (defaults to `otel_export`)

## Supported Metrics

The worker resolves metric names against `vertexai.evaluation.MetricPromptTemplateExamples.Pointwise`. Supported metrics:

- `coherence` — Logical consistency of the response
- `fluency` — Grammatical and linguistic quality
- `groundedness` — Factual accuracy against provided context
- `safety` — Absence of harmful content
- `fulfillment` — How well the response addresses the prompt

## AgentOps UI Integration

The Evals tab in the AgentOps UI provides a visual interface for managing evaluations:

- **EvalSetupWizard** — 2-step flow to configure agent name, metrics, and sampling rate
- **EvalAgentCard** — summary card showing enabled status, metric chips, sampling %
- **EvalDetailView** — time-series chart of evaluation scores per metric
- **EvalMetricsPanel** — dashboard widget embedded in the main dashboard

React hooks: `useEvalConfigs()`, `useEvalMetrics()`, `useUpsertEvalConfig()`, `useDeleteEvalConfig()`

## Testing

```bash
# Run all online eval service tests
uv run poe test-fast -- tests/unit/sre_agent/api/routers/test_evals.py \
  tests/unit/sre_agent/tools/common/test_telemetry_eval.py \
  tests/unit/sre_agent/services/test_eval_worker.py
```

## Comparison: Online vs Offline Evals

| Aspect | Offline Evals (`eval/`) | Online Evals (this service) |
|--------|------------------------|----------------------------|
| Data source | Synthetic scenarios (JSON files) | Production traces (BigQuery) |
| Trigger | `uv run poe eval` / CI pipeline | API endpoint or Cloud Scheduler |
| Metrics | Tool trajectory, rubric scoring, hallucination, safety | Pointwise: coherence, groundedness, fluency, safety |
| Judge | ADK AgentEvaluator + Gemini Flash | Vertex AI Gen AI Evaluation Service |
| Purpose | Pre-deployment gate | Continuous quality monitoring |
| UI | CLI / CI logs | AgentOps Evals tab |
