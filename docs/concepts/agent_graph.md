# Agent Graph: Multi-Agent Observability for Reasoning Systems

## Abstract

As AI agents evolve from single-prompt models into multi-agent orchestration systems — where a root agent delegates to specialist sub-agents, each invoking tools, LLMs, and further sub-agents — the need for structural observability becomes critical. Individual trace waterfalls show *what happened* in a single execution. The **Agent Graph** reveals *how the system behaves* across thousands of executions: which reasoning paths are dominant, where tokens and cost concentrate, which tool calls fail, and how the agent hierarchy actually operates in production.

This document describes the theory, strategy, and implementation of Auto SRE's Agent Graph — a property graph visualization built on BigQuery GRAPH_TABLE that aggregates multi-trace telemetry into an interactive, explorable topology of agent behavior.

---

## 1. The Problem: Observability Gaps in Multi-Agent Systems

### 1.1 Single-Agent Observability is Solved

For a single LLM call, observability is straightforward: input tokens, output tokens, latency, cost, and the response itself. Distributed tracing (OpenTelemetry) captures this well. A waterfall diagram shows the timeline of a single trace — parent spans, child spans, durations.

### 1.2 Multi-Agent Systems Create New Blind Spots

Modern AI agents are not single-prompt systems. Auto SRE, for example, uses a **Council of Experts** architecture:

```
User Query
  └─> Root Agent (Orchestrator)
        ├─> 3-Tier Router (classify intent)
        ├─> Council Orchestrator
        │     ├─> Trace Panel (parallel)
        │     │     ├─> fetch_trace (tool)
        │     │     ├─> analyze_critical_path (tool)
        │     │     └─> Gemini 2.5 Flash (LLM)
        │     ├─> Metrics Panel (parallel)
        │     │     ├─> list_time_series (tool)
        │     │     ├─> detect_metric_anomalies (tool)
        │     │     └─> Gemini 2.5 Flash (LLM)
        │     ├─> Logs Panel (parallel)
        │     ├─> Alerts Panel (parallel)
        │     ├─> Data Panel (parallel)
        │     └─> Synthesizer
        │           └─> Gemini 2.5 Pro (LLM)
        └─> Root Cause Analyst (sub-agent)
              ├─> correlate_metrics_with_traces (tool)
              └─> Gemini 2.5 Pro (LLM)
```

A single investigation can produce **50-200 spans** across **5-15 agents** making **10-30 tool calls** and **5-10 LLM calls**. Multiply this by hundreds of investigations per day, and the following questions become impossible to answer from individual traces:

1. **Structural questions**: Which agents call which tools? How deep is the delegation chain? Are there unexpected back-edges (agent A calling agent B which calls agent A)?
2. **Cost questions**: Where do tokens concentrate? Is the Synthesizer consuming 60% of the total cost? Is one tool call dominating the budget?
3. **Reliability questions**: Which edges have the highest error rates? Is `fetch_trace` failing 20% of the time? Does the Trace Panel have a higher error rate than the Metrics Panel?
4. **Performance questions**: What is the P95 latency for each agent-tool edge? Where are the bottlenecks across all traces?
5. **Evolution questions**: Has the agent's behavior changed? Are new tool calls appearing? Are some paths becoming dominant?

### 1.3 The Gap: Aggregate Structural Observability

Traditional observability tools provide:
- **Traces**: Single-execution waterfalls (span-level detail)
- **Metrics**: Time-series aggregates (request rate, error rate, latency)
- **Logs**: Textual event streams

None of these capture the **structural topology** of multi-agent reasoning. You can see that a trace took 5 seconds, but not that the `Trace Panel → fetch_trace` edge is responsible for 40% of all latency across all traces. You can see that an error occurred, but not that the `Root Agent → BigQuery Tool` path has a 15% error rate while all other paths are under 1%.

The Agent Graph fills this gap.

---

## 2. Theory: Reasoning Paths and Trajectories

### 2.1 Agents as Directed Graphs

Every multi-agent execution can be modeled as a directed acyclic graph (DAG):

- **Nodes**: Agents, tools, LLM calls
- **Edges**: Delegation relationships (parent invokes child)
- **Properties**: Tokens, latency, cost, error status

A single execution produces one *trace graph*. Across many executions, these trace graphs overlap — the same agent calls the same tools, the same delegation patterns recur. The **multi-trace agent graph** is the union of all trace graphs, with edge and node metrics aggregated.

### 2.2 Reasoning Trajectories

An agent's *reasoning trajectory* is the sequence of decisions it makes: which tools to call, which sub-agents to delegate to, and in what order. In a multi-agent system, the trajectory is a path through the agent graph.

Understanding reasoning trajectories at scale reveals:

- **Dominant paths**: The most common reasoning strategies (e.g., "80% of investigations start with trace analysis, then metrics, then logs")
- **Divergence points**: Where the agent's reasoning branches (e.g., "after initial triage, it either escalates to Council or handles directly")
- **Dead ends**: Paths that are invoked but rarely produce useful results
- **Cost hotspots**: Paths that consume disproportionate tokens relative to their contribution

### 2.3 Why Multi-Agent Observability Matters

| Concern | Single-Trace View | Multi-Trace Graph View |
| :--- | :--- | :--- |
| **Cost optimization** | "This trace cost $0.05" | "The Synthesizer node costs $0.03 per investigation on average — 60% of total" |
| **Reliability** | "This tool call failed" | "The BigQuery tool has a 12% error rate across 500 calls" |
| **Performance** | "This trace took 8 seconds" | "P95 latency for Trace Panel → fetch_trace is 3.2 seconds" |
| **Architecture** | "This trace had 47 spans" | "The agent hierarchy has 12 nodes and 18 edges; 3 nodes are leaves" |
| **Debugging** | "What happened in this execution?" | "Why does the Logs Panel never get invoked for metric-related queries?" |
| **Regression detection** | Manual comparison | "Tool call count increased 3x after last deployment" |

---

## 3. Product Description

### 3.1 What the Agent Graph Shows

The Agent Graph is an interactive visualization that renders the **aggregated topology** of all agent executions within a time window. Each node represents an agent, tool, or LLM. Each edge represents a delegation relationship with aggregated metrics.

**Node information:**
- Node type (Agent, Sub-Agent, Tool, LLM) with visual differentiation
- Total tokens (input + output breakdown)
- Estimated cost (USD, based on model-specific pricing)
- Average and P95 latency
- Error rate and error flag
- Sub-call distribution (how many tool calls and LLM calls this agent makes)
- Topology flags: root, leaf, user entry point

**Edge information:**
- Call count (how many times source invoked target)
- Error count and error rate
- Token flow (input, output, total)
- Average and P95 latency per call
- Unique sessions
- Estimated cost
- Sample error message

### 3.2 User Workflows

1. **Architecture overview**: Open the graph to see the full agent hierarchy. Identify which agents exist, how they connect, and where the entry points are.
2. **Cost analysis**: Look for nodes with high cost badges. Click to see the token breakdown and cost relative to the total graph.
3. **Error investigation**: Find red-highlighted nodes and edges with non-zero error rates. Click edges to see sample error messages and drill down.
4. **Performance optimization**: Sort by P95 latency to find bottleneck edges. Identify which tool calls are contributing to tail latency.
5. **Trace exploration**: Click "Explore Traces" on any node or edge to navigate to the trace explorer filtered for that specific agent or tool interaction.

### 3.3 Time Range and Performance

The graph supports 12 preset time ranges (5 minutes to 30 days) plus custom ranges. For ranges >= 1 hour, the query uses a pre-aggregated hourly table that loads in under 1 second, even for graphs with hundreds of nodes.

---

## 4. Technical Architecture

### 4.1 Data Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. TELEMETRY EMISSION                                               │
│                                                                      │
│  Google ADK (Agent Development Kit) automatically instruments every  │
│  agent invocation, tool call, and LLM request as OpenTelemetry spans │
│  with semantic attributes:                                           │
│    • gen_ai.operation.name (invoke_agent, execute_tool, generate_content)
│    • gen_ai.agent.name, gen_ai.tool.name, gen_ai.response.model     │
│    • gen_ai.usage.input_tokens, gen_ai.usage.output_tokens          │
│    • gen_ai.agent.description, gen_ai.tool.description              │
│                                                                      │
│  Spans are exported to Google Cloud Trace via the GenAI SDK.         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. MATERIALIZED VIEW (agent_spans_raw)                              │
│                                                                      │
│  A BigQuery Materialized View extracts and denormalizes the raw      │
│  Cloud Trace spans (_AllSpans table) into a flat, queryable schema.  │
│  Refreshes every 60 minutes. Clusters on (trace_id, session_id,     │
│  node_label) for fast lookups.                                       │
│                                                                      │
│  Key transformations:                                                │
│    • JSON attribute extraction → typed columns                       │
│    • Node classification: invoke_agent→Agent, execute_tool→Tool,    │
│      generate_content→LLM, else→Glue (filtered out)                 │
│    • Display label resolution: agent name > tool name > model > span │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. PROPERTY GRAPH (agent_trace_graph)                               │
│                                                                      │
│  A BigQuery Property Graph defined over the Materialized View:       │
│    • NODE TABLE: Each span is a node (KEY: span_id)                  │
│    • EDGE TABLE: Parent-child relationships (SOURCE: parent_id,     │
│      DESTINATION: span_id)                                           │
│                                                                      │
│  Enables recursive graph traversal via GRAPH_TABLE SQL:              │
│    MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)                   │
│  This finds all parent→child paths up to 5 hops deep, skipping      │
│  "Glue" spans and self-referential loops.                            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. PRE-AGGREGATED HOURLY TABLE (agent_graph_hourly)                 │
│                                                                      │
│  A scheduled BQ query runs every hour and performs the expensive     │
│  GRAPH_TABLE recursive traversal for just the last hour of data.    │
│  Results are appended to a partitioned + clustered table:            │
│    • PARTITION BY DATE(time_bucket)                                   │
│    • CLUSTER BY source_id, target_id                                 │
│                                                                      │
│  Stored metrics per (hour, source, target):                          │
│    • Edge: call_count, error_count, tokens, cost, duration, sessions │
│    • Node: total_tokens, error_count, cost, description              │
│    • Subcalls: tool_call_count, llm_call_count                       │
│                                                                      │
│  Initial backfill covers 30 days. Deduplication via ExistingBuckets  │
│  CTE prevents double-counting on re-runs.                            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  5. FLUTTER QUERY + VISUALIZATION                                    │
│                                                                      │
│  The Flutter app queries via the FastAPI backend:                     │
│    POST /api/tools/bigquery/query { sql: "...", project_id: "..." } │
│                                                                      │
│  Query routing (in AgentGraphRepository):                            │
│    • timeRange >= 1h → buildPrecomputedGraphSql() against hourly    │
│      table (GROUP BY + SUM, sub-second)                              │
│    • timeRange < 1h  → buildGraphSql() with live GRAPH_TABLE        │
│      (recursive traversal, 1-3s for small data)                      │
│                                                                      │
│  Response: Single JSON string with {nodes: [...], edges: [...]}      │
│  Parsed into Freezed models: MultiTraceGraphPayload                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 BigQuery Property Graph

The foundation is BigQuery's **Property Graph** feature, which models the span data as a graph database:

```sql
CREATE OR REPLACE PROPERTY GRAPH `project.dataset.agent_trace_graph`
  NODE TABLES (
    `project.dataset.agent_spans_raw` AS Span
      KEY (span_id)
      LABEL Span
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    `project.dataset.agent_spans_raw` AS ParentOf
      KEY (span_id)
      SOURCE KEY (parent_id) REFERENCES Span (span_id)
      DESTINATION KEY (span_id) REFERENCES Span (span_id)
      LABEL ParentOf
  );
```

The `GRAPH_TABLE` SQL function then enables recursive path matching:

```sql
SELECT * FROM GRAPH_TABLE(
  `project.dataset.agent_trace_graph`
  MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)
  WHERE src.node_type != 'Glue' AND dst.node_type != 'Glue'
    AND src.node_label != dst.node_label
  COLUMNS (
    src.node_label AS source_id, src.node_type AS source_type,
    dst.node_label AS target_id, dst.node_type AS target_type,
    dst.duration_ms, dst.input_tokens, dst.output_tokens, ...
  )
)
```

The `->{1,5}` syntax matches paths of 1 to 5 hops, collapsing intermediate "Glue" spans to reveal the true agent-to-tool delegation structure.

### 4.3 Cost Calculation

Cost is estimated per-span using model-specific pricing:

```sql
COALESCE(input_tokens, 0) * CASE
  WHEN response_model LIKE '%flash%' THEN 0.00000015    -- $0.15/1M input
  WHEN response_model LIKE '%2.5-pro%' THEN 0.00000125  -- $1.25/1M input
  WHEN response_model LIKE '%1.5-pro%' THEN 0.00000125  -- $1.25/1M input
  ELSE 0.0000005                                         -- default
END
+ COALESCE(output_tokens, 0) * CASE
  WHEN response_model LIKE '%flash%' THEN 0.0000006     -- $0.60/1M output
  WHEN response_model LIKE '%2.5-pro%' THEN 0.00001     -- $10.00/1M output
  WHEN response_model LIKE '%1.5-pro%' THEN 0.000005    -- $5.00/1M output
  ELSE 0.000002                                          -- default
END AS span_cost
```

### 4.4 Pre-Aggregation Strategy

The recursive `GRAPH_TABLE` traversal is expensive (seconds to minutes for large datasets). The pre-aggregation strategy eliminates this cost for the common case:

**Offline (hourly scheduled query):**
1. Run `GRAPH_TABLE` traversal for the last hour of new data
2. Compute per-edge and per-node aggregates (call count, tokens, cost, latency, errors)
3. Append to `agent_graph_hourly` table (partitioned by date, clustered by source/target)
4. Deduplication prevents double-counting on re-runs

**Online (user query):**
1. Query `agent_graph_hourly` with simple `GROUP BY source_id, target_id` + `SUM`
2. No recursive traversal, no GRAPH_TABLE — just standard SQL aggregation
3. Sub-second response guaranteed

**Metric approximations across hourly buckets:**
- `avg_duration_ms`: Weighted average via `SUM(sum_duration_ms) / SUM(call_count)`
- `p95_duration_ms`: Conservative upper bound via `MAX(max_p95_duration_ms)`
- `unique_sessions`: Approximated by `SUM` (may overcount at bucket boundaries)
- `error_rate_pct`: Recomputed as `SUM(error_count) / SUM(call_count) * 100`

| Time Range | Query Path | Expected Latency |
| :--- | :--- | :--- |
| 5m – 30m | Live GRAPH_TABLE | 1–3s (small data volume) |
| 1h – 30d | Pre-aggregated hourly table | < 1s |

---

## 5. Implementation Details

### 5.1 Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Telemetry** | Google ADK + Cloud Trace (OTel) | Automatic span instrumentation for all agent/tool/LLM calls |
| **Storage** | BigQuery Materialized View | Denormalized span data with 60-minute refresh |
| **Graph Engine** | BigQuery Property Graph + GRAPH_TABLE | Recursive path matching (1-5 hops) |
| **Pre-aggregation** | BigQuery Scheduled Query | Hourly pre-computation of graph metrics |
| **API** | FastAPI + Dio (HTTP client) | SQL execution via `/api/tools/bigquery/query` |
| **State Management** | Riverpod 3.0 + Freezed | Reactive state with code generation |
| **Graph Layout** | graphview (Sugiyama algorithm) | Hierarchical DAG layout with layering and crossing minimization |
| **Graph Rendering** | fl_nodes | Interactive node editor with ports, links, and custom node widgets |
| **UI Framework** | Flutter Web (Material 3) | Cross-platform rendering with CanvasKit |

### 5.2 Domain Models (Dart/Freezed)

```dart
@freezed
abstract class MultiTraceNode with _$MultiTraceNode {
  const factory MultiTraceNode({
    required String id,                                    // e.g., "router", "BigQueryTool"
    required String type,                                  // Agent, Tool, LLM, Sub_Agent
    String? description,                                   // Agent/tool description
    @Default(0) int totalTokens,                          // Input + output
    @Default(0) int inputTokens,
    @Default(0) int outputTokens,
    @Default(false) bool hasError,
    @Default(0.0) double avgDurationMs,
    @Default(0.0) double p95DurationMs,
    @Default(0.0) double errorRatePct,
    double? totalCost,                                     // Estimated USD
    @Default(0) int toolCallCount,                        // Downstream tool calls
    @Default(0) int llmCallCount,                         // Downstream LLM calls
    @Default(false) bool isRoot,                          // No incoming edges
    @Default(false) bool isLeaf,                          // No outgoing edges
    @Default(false) bool isUserEntryPoint,                // Root + Agent type
  }) = _MultiTraceNode;
}

@freezed
abstract class MultiTraceEdge with _$MultiTraceEdge {
  const factory MultiTraceEdge({
    required String sourceId,
    required String targetId,
    @Default('') String sourceType,
    @Default('') String targetType,
    @Default(0) int callCount,                            // Total invocations
    @Default(0) int errorCount,
    @Default(0.0) double errorRatePct,
    String? sampleError,                                   // Example error message
    @Default(0) int edgeTokens,                           // Total tokens on this edge
    @Default(0) int inputTokens,
    @Default(0) int outputTokens,
    @Default(0) int avgTokensPerCall,
    @Default(0.0) double avgDurationMs,
    @Default(0.0) double p95DurationMs,
    @Default(0) int uniqueSessions,
    double? totalCost,
  }) = _MultiTraceEdge;
}
```

### 5.3 Visual Grammar

| Node Type | Shape | Icon | Color | Notes |
| :--- | :--- | :--- | :--- | :--- |
| User Entry Point | Circle (80x80) | Person | Blue | Always the graph root |
| Agent | Rounded rect | Brain | Teal | Brighter border if root |
| Sub-Agent | Rounded rect | Brain | Cyan | |
| Tool | Rounded rect | Build | Orange | |
| LLM | Rounded rect | Sparkle | Purple | |

**Badges on nodes:**
- Token count (e.g., "12.5K")
- Cost badge (e.g., "$0.042") if cost > 0
- Subcall badge (e.g., "5T 3L" = 5 tool + 3 LLM calls) for agents
- Error badge with count

**Edge styling:**
- Width proportional to call count
- Color: red if error rate > 0, white otherwise
- Dashed line for back-edges (cycles in the graph)

### 5.4 Layout Engine

The graph uses the **Sugiyama algorithm** (from the `graphview` package) for hierarchical layout:

1. **Layer assignment**: Nodes are assigned to layers based on their distance from root nodes (BFS)
2. **Crossing minimization**: Nodes within each layer are reordered to minimize edge crossings
3. **Coordinate assignment**: Nodes are positioned with configurable spacing

An alternative **force-directed layout** is available via a toggle button, useful for exploring non-hierarchical relationships.

### 5.5 Test Coverage

| Test File | Tests | Coverage |
| :--- | :--- | :--- |
| `domain/models_test.dart` | 39 | All fields: fromJson, toJson, equality, copyWith for all 4 model types |
| `data/agent_graph_repository_test.dart` | 11 | SQL generation (live + precomputed), dual-path routing, response parsing, error handling |
| `application/agent_graph_notifier_test.dart` | 16 | State lifecycle, parameter passthrough, selection management |
| `presentation/agent_graph_details_panel_test.dart` | 11+ | Widget rendering, badges, metrics display, close callback |
| `presentation/multi_trace_graph_canvas_test.dart` | 6 | Empty state, node count, legend, selection, layout toggle |
| `presentation/interactive_graph_canvas_test.dart` | 1 | Empty graph rendering (view mode tests disabled due to fl_nodes timer leak) |

---

## 6. Setup and Deployment

### 6.1 Prerequisites

- A GCP project with Cloud Trace API enabled and agent traces being exported
- BigQuery API enabled
- The `_AllSpans` table populated with Cloud Trace data (automatic when using Cloud Trace)

### 6.2 One-Time Setup

```bash
./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
```

This creates:
1. The `agent_spans_raw` Materialized View
2. The `agent_trace_graph` Property Graph
3. The `agent_graph_hourly` pre-aggregated table
4. A 30-day backfill of historical data

### 6.3 Scheduled Query

After setup, configure a BigQuery Scheduled Query (via Cloud Console) to run hourly. The setup script prints the exact SQL to use. This keeps the hourly table current with new trace data.

### 6.4 Flutter Configuration

Update the default dataset in `lib/features/agent_graph/data/agent_graph_repository.dart`:

```dart
const kDefaultDataset = 'your-project.your_dataset';
```

Or allow users to configure it via the graph page UI (already supported via the dataset text field).

---

## 7. Future Directions

- **Live mode**: Stream new edges as they appear (via Pub/Sub notifications on BQ insert)
- **Diff view**: Compare agent graphs across time windows to detect behavioral changes
- **Anomaly detection**: Automatically flag edges with unusual error rates or latency spikes
- **Cost attribution**: Per-user or per-session cost breakdown overlaid on the graph
- **Graph-based alerting**: Alert when graph topology changes (new nodes, missing nodes, new back-edges)
- **Embedding-based similarity**: Cluster similar reasoning trajectories to identify investigation archetypes

---

*Last updated: 2026-02-19*
