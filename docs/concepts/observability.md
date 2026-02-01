# Observability and OpenTelemetry Concepts

This guide provides a foundational understanding of Observability and OpenTelemetry (OTel), which are the core pillars powering the **SRE Agent**. Understanding these concepts is crucial for interpreting the agent's findings and leveraging its full capabilities.

## What is Observability?

Observability is a measure of how well you can understand the internal state of a system simply by looking at its external outputs. In distributed systems, it's about answering the question: *"Why is my system behaving this way?"*

Unlike traditional **Monitoring** (which tells you *that* something is wrong), **Observability** gives you the granularity to understand *why* it's wrong, even for novel, "unknown-unknown" issues.

### The Three Pillars of Observability

1.  **Traces**: The "narrative" of a request.
    *   **Context**: A single request often touches dozens of microservices. Tracing stitches these interactions into a single coherent story.
    *   **Value**: Essential for identifying latency bottlenecks, critical paths, and understanding service dependencies.
    *   **SRE Agent Tool**: `sre_agent/tools/analysis/trace/` analyzers (Latency, Error, Structure, Critical Path).

2.  **Logs**: The "discrete events."
    *   **Context**: Textual records of specific events (e.g., "Payment processed", "Database connection failed").
    *   **Value**: Provides the fine-grained details and error messages needed for root cause forensics.
    *   **SRE Agent Tool**: `sre_agent/tools/analysis/logs/` (Log Pattern Extractor, Drain3).

3.  **Metrics**: The "aggregates."
    *   **Context**: Numerical data measured over time (e.g., CPU load, memory usage, request rate).
    *   **Value**: Excellent for spotting trends, setting alerts, and understanding overall system health at a glance.
    *   **SRE Agent Tool**: `sre_agent/tools/analysis/metrics/` (Anomaly Detection, PromQL).

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
*   **Service Dependency Mapping**: By traversing the Parent -> Child links in trace data, the agent automatically reconstructs your architecture diagram.

### Internal Agent Instrumentation
While the agent *analyzes* target OTel data manually, its **own internal observability** is handled automatically. The agent relies on [Google ADK](https://github.com/google/adk) native instrumentation, ensuring its reasoning steps, tool calls, and LLM prompts are captured in Cloud Trace without manual boilerplate code.

### Example: The "N+1 Query" Anti-Pattern

An "N+1 Query" problem happens when an application makes a database call for *every item* in a list, rather than fetching them all at once.

**In OTel Data:**
*   You see one large parent span (e.g., `list_users`).
*   Nested underneath are 50 identical child spans (e.g., `SELECT * FROM user WHERE id = ?`), executed sequentially.
*   **SRE Agent Detection**: The `Structure Analyzer` spots this high "fan-out" and sequential pattern and flags it as a critical optimization opportunity.

---

## LangSmith Integration (Development & Regression)

For developers, the SRE Agent integrates with [LangSmith](https://smith.langchain.com/) to provide high-fidelity tracing of LLM reasoning, tool calls, and session flows. This is primarily used in **Local Development Mode** for debugging and performance tuning.

### Key Features
*   **Thread Grouping**: Investigations are grouped into "Threads" in LangSmith using the `session_id`.
*   **Prompt Analytics**: View the exact system instructions and few-shot examples sent to the LLM.
*   **Tool Tracing**: See the latency and output of every tool called by the agent.
*   **Feedback & Eval**: Send "Thumbs Up/Down" feedback to LangSmith for online evaluation.

### Configuration
Enable LangSmith by setting the following environment variables:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
LANGSMITH_PROJECT=sre-agent  # Optional
```

### LangSmith Context Utilities
The agent provides several utilities in `sre_agent.tools.common.telemetry` to enhance traces:
*   `set_langsmith_session(session_id)`: Groups all following traces into a single thread.
*   `set_langsmith_user(user_id)`: Tags traces with the current user.
*   `add_langsmith_tags(tags)`: Adds custom labels for filtering.
*   `send_langsmith_feedback(...)`: Programmatically submits evaluation scores.

---

## Further Reading

*   [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
*   [Google Cloud Trace Concepts](https://cloud.google.com/trace/docs/overview)
*   [Google SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
*   [LangSmith - Trace with OpenTelemetry](https://docs.smith.langchain.com/how_to_guides/tracing/trace_with_otel)
