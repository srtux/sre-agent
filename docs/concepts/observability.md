# Observability and OpenTelemetry Concepts

This guide provides a foundational understanding of Observability and OpenTelemetry (OTel), which are the core pillars powering the **SRE Agent**. Understanding these concepts is crucial for interpreting the agent's findings and leveraging its full capabilities.

## What is Observability?

Observability is a measure of how well you can understand the internal state of a system simply by looking at its external outputs. In distributed systems, it is about answering the question: *"Why is my system behaving this way?"*

Unlike traditional **Monitoring** (which tells you *that* something is wrong), **Observability** gives you the granularity to understand *why* it is wrong, even for novel, "unknown-unknown" issues.

### The Four Pillars of Observability

In addition to the traditional three pillars, the SRE Agent treats **Changes** as a first-class citizen of observability.

1.  **Traces**: The "narrative" of a request.
    *   **Context**: A single request often touches dozens of microservices. Tracing stitches these interactions into a single coherent story.
    *   **Value**: Essential for identifying latency bottlenecks, critical paths, and understanding service dependencies.
    *   **SRE Agent Tools**: `sre_agent/tools/analysis/trace/` analyzers -- `analyze_trace_comprehensive` (Mega-Tool combining latency, error, structure, and resiliency analysis), `analyze_critical_path`, `compare_span_timings`, `detect_all_sre_patterns`.

2.  **Logs**: The "discrete events."
    *   **Context**: Textual records of specific events (e.g., "Payment processed", "Database connection failed").
    *   **Value**: Provides the fine-grained details and error messages needed for root cause forensics.
    *   **SRE Agent Tools**: `sre_agent/tools/analysis/logs/` -- `extract_log_patterns` (Drain3 streaming log template mining), `analyze_log_anomalies`, `analyze_bigquery_log_patterns`.

3.  **Metrics**: The "aggregates."
    *   **Context**: Numerical data measured over time (e.g., CPU load, memory usage, request rate).
    *   **Value**: Excellent for spotting trends, setting alerts, and understanding overall system health at a glance.
    *   **SRE Agent Tools**: `sre_agent/tools/analysis/metrics/` -- `detect_metric_anomalies`, `compare_metric_windows`, `query_promql`; `sre_agent/tools/analysis/slo/burn_rate.py` -- `analyze_error_budget_burn` (Multi-Window Burn Rate).

4.  **Changes**: The "root cause."
    *   **Context**: Intentional modifications to the system (Deployments, Config changes, Feature flags).
    *   **Value**: Most incidents are preceded by a change. Correlating these temporally is the fastest path to root cause.
    *   **SRE Agent Tools**: `sre_agent/tools/analysis/correlation/` -- `correlate_changes_with_incident`, `perform_causal_analysis`, `build_cross_signal_timeline`.

---

## Resilience and Reliability Patterns

The SRE Agent is built with engineering-grade resilience patterns to protect both target systems and the agent itself:

### 1. Circuit Breaker Pattern

The agent implements a **three-state Circuit Breaker** (`sre_agent/core/circuit_breaker.py`) to protect production GCP APIs and the agent's reasoning budget:

```
CLOSED (normal) --[failures >= threshold]--> OPEN (fail fast)
OPEN --[recovery timeout elapsed]--> HALF_OPEN (testing)
HALF_OPEN --[success >= threshold]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

Configuration via `CircuitBreakerConfig`:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `failure_threshold` | 5 | Failures before opening the circuit |
| `recovery_timeout_seconds` | 60.0 | Wait time before testing recovery |
| `half_open_max_calls` | 1 | Max calls allowed in HALF_OPEN state |
| `success_threshold` | 2 | Successes needed to close the circuit |

The circuit breaker tracks per-tool state via `CircuitBreakerState` (state, failure/success counts, last failure time, total calls). When tripped, tool calls receive an immediate error response without executing, preventing cascading failures and "panic-mode" token consumption during GCP outages.

### 2. Multi-Window SLO Burn Rate

Standard alerting is noisy. The agent uses Google's recommended **Multi-Window, Multi-Burn Rate** strategy (`sre_agent/tools/analysis/slo/burn_rate.py`). It distinguishes between:
- **Fast Burn** (needs a page now): High error rate in short windows (1h, 6h)
- **Slow Burn** (create a ticket for tomorrow): Gradual budget erosion across longer windows (1d, 3d)

By analyzing error budget consumption across multiple lookback windows simultaneously, the agent avoids both false alarms and missed incidents.

### 3. Model Callbacks (Cost & Budget Enforcement)

The `sre_agent/core/model_callbacks.py` module provides `before_model_callback` and `after_model_callback` functions that:
- Track input/output token counts per LLM call
- Accumulate cost estimates across the session
- Enforce `SRE_AGENT_TOKEN_BUDGET` limits (halt execution if exceeded)
- Record model call duration for latency monitoring

### 4. Tool Callbacks (Output Management)

The `sre_agent/core/tool_callbacks.py` module handles:
- Tool output truncation to prevent context overflow
- Post-processing of tool results (normalization, summarization)
- Large payload detection and offload to sandbox (`sre_agent/core/large_payload_handler.py`)

---

## What is OpenTelemetry (OTel)?

[OpenTelemetry](https://opentelemetry.io/) is an open-source observability framework that provides a standard way to generate, collect, and export telemetry data (metrics, logs, and traces). It is the industry standard and is vendor-neutral, meaning you can send OTel data to Google Cloud, Prometheus, Splunk, or any other backend.

### Key OTel Concepts in SRE Agent

#### 1. Trace Structure
*   **Trace**: Represents an entire transaction (e.g., "Checkout"). Defined by a unique `Trace ID`.
*   **Span**: A single operation within a trace (e.g., "SQL Query", "HTTP GET /cart"). Defined by a `Span ID`.
    *   **Parent/Child Relationship**: Spans are nested. A parent span (e.g., "API Request") waits for its children (e.g., "Auth Check", "DB Query") to complete.
    *   **Attributes (Labels)**: Key-value pairs attached to a span (e.g., `http.status_code=500`, `db.statement="SELECT * FROM..."`). SRE Agent heavily uses these attributes to diagnose errors.

#### 2. Context Propagation
OTel ensures that a `Trace ID` is passed ("propagated") from service A to service B. This is what allows SRE Agent to build a complete `Call Graph` across distributed boundaries. Broken context propagation leads to "orphaned spans" (traces that seem to stop abruptly), which the agent's `Structure Analyzer` can often identify as a missing link.

#### 3. Instrumentation
*   **Auto-Instrumentation**: Many libraries (like standard OTel for Python/Java) automatically generate spans for standard HTTP/GRPC calls.
*   **Manual Instrumentation**: Developers add custom spans to measure specific blocks of code (e.g., `with tracer.start_as_current_span("calculate_tax"): ...`).

---

## How SRE Agent Uses OTel Data

The SRE Agent is designed to "speak OTel natively." It interprets the semantic conventions defined by OTel to make intelligent deductions about **target systems** it is investigating:

*   **Error Detection**: It checks spans for `status.code != OK` and standard error attributes like `exception.message`.
*   **Latency Analysis**: It calculates duration by subtracting `start_time` from `end_time` for spans and comparing them against historical baselines.
*   **Service Dependency Mapping**: By traversing the Parent -> Child links in trace data, the agent automatically reconstructs your architecture diagram via `GraphService` (`sre_agent/core/graph_service.py`).
*   **SRE Anti-Pattern Detection**: `detect_all_sre_patterns` identifies retry storms, cascading timeouts, connection pool saturation, and circular dependencies directly from trace structure.

### Internal Agent Instrumentation
While the agent *analyzes* target OTel data manually, its **own internal observability** is handled automatically. The agent relies on [Google ADK](https://github.com/google/adk-python) native instrumentation, ensuring its reasoning steps, tool calls, and LLM prompts are captured in Cloud Trace without manual boilerplate code.

The telemetry setup (`sre_agent/tools/common/telemetry.py`) is initialized at import time in `sre_agent/agent.py` (before other modules) to ensure OTel instrumentation correctly patches ADK and other libraries. It can be disabled with the `DISABLE_TELEMETRY=true` environment variable.

### Agent Self-Analysis Tools

The agent includes tools specifically for analyzing its own execution traces (`sre_agent/tools/analysis/agent_trace/`):

| Tool | Purpose |
| :--- | :--- |
| `analyze_and_learn_from_traces` | Generate SQL to find agent traces in BigQuery |
| `detect_agent_anti_patterns` | Identify inefficiencies in agent execution |
| `list_agent_traces` | List past agent execution traces |
| `reconstruct_agent_interaction` | Rebuild the agent's decision tree from trace data |
| `analyze_agent_token_usage` | Break down token consumption per tool/LLM call |

These tools enable the self-healing loop described in [Online Research & Self-Healing](online_research_and_self_healing.md).

### Example: The "N+1 Query" Anti-Pattern

An "N+1 Query" problem happens when an application makes a database call for *every item* in a list, rather than fetching them all at once.

**In OTel Data:**
*   You see one large parent span (e.g., `list_users`).
*   Nested underneath are 50 identical child spans (e.g., `SELECT * FROM user WHERE id = ?`), executed sequentially.
*   **SRE Agent Detection**: The `Structure Analyzer` spots this high "fan-out" and sequential pattern and flags it as a critical optimization opportunity.

---

## Dashboard Data Channel

The SRE Agent provides a real-time data channel for the frontend Mission Control UI. This is separate from the main chat/A2UI protocol and enables rich live panels.

### Architecture

```
Backend Tool Execution
        |
        v
emit_dashboard_event()          (sre_agent/api/helpers/tool_events.py)
        |
        v
NDJSON Stream                   {"type": "dashboard", "category": "...", "data": {...}}
        |
        v
Frontend dashboardStream        (Flutter: services/dashboard_state.dart)
        |
        v
Live Panel Widgets              (Flutter: widgets/dashboard/*.dart)
```

### Dashboard Event Categories

Tool results are automatically mapped to dashboard categories via `TOOL_WIDGET_MAP` (`sre_agent/api/helpers/__init__.py`):

| Category | Source Tools | Frontend Panel |
| :--- | :--- | :--- |
| `traces` | `fetch_trace`, `analyze_trace_comprehensive`, `compare_span_timings` | Trace visualization, critical path display |
| `metrics` | `query_promql`, `list_time_series`, `detect_metric_anomalies` | Metrics charts, anomaly markers |
| `logs` | `list_log_entries`, `extract_log_patterns` | Log stream, pattern clustering |
| `alerts` | `list_alerts`, `list_alert_policies`, `get_alert` | Alert timeline, severity indicators |
| `council` | Council panel findings, critic reports, synthesis | Council activity graph |

### Event Helpers

The `sre_agent/api/helpers/` module provides helper functions for creating dashboard events:

| Function | Purpose |
| :--- | :--- |
| `create_dashboard_event()` | Create a typed dashboard event from tool output |
| `create_tool_call_events()` | Emit events when a tool is called (for activity tracking) |
| `create_tool_response_events()` | Emit events when a tool returns results |
| `create_widget_events()` | Create widget-specific rendering events |
| `create_exploration_dashboard_events()` | Create events for health check exploration |
| `normalize_tool_args()` | Normalize tool arguments for consistent event format |

---

## Langfuse Integration (Development & Debugging)

For developers, the SRE Agent integrates with [Langfuse](https://langfuse.com/) to provide high-fidelity tracing of LLM reasoning, tool calls, and session flows. This is primarily used in **Local Development Mode** for debugging and performance tuning.

### Key Features
*   **Session Grouping**: Investigations are grouped into sessions in Langfuse using the `session_id`.
*   **Prompt Analytics**: View the exact system instructions and few-shot examples sent to the LLM.
*   **Tool Tracing**: See the latency and output of every tool called by the agent.
*   **Scores & Eval**: Send feedback scores to Langfuse for evaluations.

### Configuration
Run Langfuse locally via Docker, then set the following environment variables:
```bash
LANGFUSE_TRACING=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=http://localhost:3000  # Default for self-hosted
```

### Langfuse Context Utilities
The agent provides several utilities in `sre_agent/tools/common/telemetry.py` to enhance traces:
*   `set_langfuse_session(session_id)`: Groups all following traces into a single session.
*   `set_langfuse_user(user_id)`: Tags traces with the current user.
*   `add_langfuse_tags(tags)`: Adds custom labels for filtering.
*   `send_langfuse_score(...)`: Programmatically submits evaluation scores.

---

## Environment Variables for Observability

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `DISABLE_TELEMETRY` | Disable OTel telemetry setup | `false` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `SRE_AGENT_TOKEN_BUDGET` | Max token budget per request (model callbacks enforce) | Unset (unlimited) |
| `SRE_AGENT_CONTEXT_CACHING` | Enable Vertex AI context caching (OPT-10) | `false` |
| `LANGFUSE_TRACING` | Enable Langfuse tracing | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Unset |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Unset |
| `LANGFUSE_HOST` | Langfuse server URL | `http://localhost:3000` |

---

## Multi-Agent Observability

While the sections above describe observability for **target systems** that the SRE Agent investigates, the agent itself is a complex multi-agent system that requires its own observability. The Agent Graph, AgentOps Dashboard, and Agent Self-Analysis Tools provide three complementary surfaces for understanding agent behavior:

- **Agent Graph**: Aggregated topology and trajectory visualization across thousands of executions -- see [Agent Graph](agent_graph.md) for the full architecture
- **AgentOps Dashboard**: Fleet-wide KPIs, latency charts, model/tool performance tables, and agent log streams -- see [AgentOps Dashboard Guide](../agent_ops/dashboard.md)
- **Self-Analysis Tools**: Agent introspection for detecting anti-patterns and token waste -- see [Agent Self-Analysis](../reference/tools.md)

For the complete conceptual overview, see [Multi-Agent Observability](multi_agent_observability.md).

---

## Further Reading

*   [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
*   [Google Cloud Trace Concepts](https://cloud.google.com/trace/docs/overview)
*   [Google SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
*   [Langfuse - OpenTelemetry Integration](https://langfuse.com/integrations/native/opentelemetry)
*   [Multi-Agent Observability](multi_agent_observability.md) -- How the three observability surfaces work together
*   [AgentOps Dashboard Guide](../agent_ops/dashboard.md) -- Operational monitoring with KPIs and charts
*   [Memory Best Practices](memory.md) -- Memory event visibility system
*   [Agent Orchestration](agent_orchestration.md) -- Council activity graph for frontend

---

*Last verified: 2026-02-21
