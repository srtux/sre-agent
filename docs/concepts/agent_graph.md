# Agent Graph: Multi-Agent Observability for Reasoning Systems

## Abstract

As AI agents evolve from single-prompt models into multi-agent orchestration systems — where a root agent delegates to specialist sub-agents, each invoking tools, LLMs, and further sub-agents — the need for structural observability becomes critical. Individual trace waterfalls show *what happened* in a single execution. The **Agent Graph** reveals *how the system behaves* across thousands of executions: which reasoning paths are dominant, where tokens and cost concentrate, which tool calls fail, and how the agent hierarchy actually operates in production.

This document describes the theory, strategy, and implementation of Auto SRE's Agent Graph — a property graph visualization built on BigQuery `GRAPH_TABLE` that aggregates multi-trace telemetry into an interactive, explorable topology of agent behavior. It covers the full data pipeline from OpenTelemetry span emission through BigQuery materialized views and pre-aggregated hourly tables, to two complementary visualization surfaces: a React Flow topology graph and a Nivo Sankey trajectory diagram. It details the SQL constructs — recursive CTEs, property graph path matching, model-specific cost estimation, and deduplication-safe scheduled queries — that make sub-second multi-trace aggregation possible. It describes the use cases that make this system indispensable for debugging, cost optimization, and architectural understanding of production reasoning systems.

---

## Table of Contents

1. [The Problem: Observability Gaps in Multi-Agent Systems](#1-the-problem-observability-gaps-in-multi-agent-systems)
2. [Theory: Reasoning Paths and Trajectories](#2-theory-reasoning-paths-and-trajectories)
3. [Product Description](#3-product-description)
4. [Data Pipeline: From Spans to Graphs](#4-data-pipeline-from-spans-to-graphs)
5. [BigQuery Schema Deep Dive](#5-bigquery-schema-deep-dive)
6. [Visualization Architecture](#6-visualization-architecture)
7. [API Layer](#7-api-layer)
8. [Real-Time Auto-Refresh and Time-Series Sparklines](#8-real-time-auto-refresh-and-time-series-sparklines)
9. [Use Cases and Debugging Patterns](#9-use-cases-and-debugging-patterns)
10. [Setup and Deployment](#10-setup-and-deployment)
11. [Test Coverage](#11-test-coverage)
12. [Future Directions](#12-future-directions)

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

A single investigation can produce **50–200 spans** across **5–15 agents** making **10–30 tool calls** and **5–10 LLM calls**. Multiply this by hundreds of investigations per day, and the following questions become impossible to answer from individual traces:

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

### 2.4 Two Complementary Views: Topology and Trajectory

The Agent Graph provides two fundamentally different perspectives on the same data:

**Topology View** — a directed graph where nodes represent logical components (agents, tools, LLMs) and edges represent delegation relationships. This is the *structural* view: it answers "what calls what?" with aggregated metrics on every edge and node. The topology collapses all traces into a single unified graph.

**Trajectory View** — a Sankey flow diagram where the width of each flow is proportional to the number of traces that follow a given path. This is the *behavioral* view: it answers "in what order does reasoning unfold?" and reveals dominant reasoning strategies, branching points, and pathological loops.

Together, these views provide the equivalent of a "call graph" and a "flame graph" for multi-agent AI systems.

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
- Inline sparkline showing metric trends over time (error rate, token usage, or latency depending on view mode)

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
2. **Cost analysis**: Switch to "Cost Hotspots" view mode to see token-weighted heatmaps. Click nodes to see token breakdowns and cost relative to the total graph.
3. **Error investigation**: Switch to "Topology" view to see error-rate heatmaps. Find red-highlighted nodes and edges with non-zero error rates. Click edges to see sample error messages and drill down to raw payloads.
4. **Performance optimization**: Switch to "Latency" view to find bottleneck edges. Identify which tool calls contribute to tail latency via P95/P99 breakdowns in the side panel.
5. **Trend monitoring**: Enable auto-refresh to watch the graph update on a 30s/1m/5m cadence. Observe sparklines on each node to spot emerging issues — a rising error rate or growing latency before it becomes an incident.
6. **Trajectory analysis**: Switch to the Trajectory Flow tab to see a Sankey diagram of reasoning paths. Identify dominant strategies, dead-end paths, and pathological retry loops highlighted in orange.
7. **Deep payload inspection**: Click any node, scroll to "Raw Payloads" to inspect the actual prompts, completions, tool inputs, and tool outputs for recent executions — with syntax-highlighted JSON rendering.

### 3.3 View Modes

The toolbar provides three view modes that control both the node heatmap coloring and the sparkline metric:

| Mode | Node Heatmap | Sparkline Metric | Use Case |
| :--- | :--- | :--- | :--- |
| **Topology** | Error rate (green → red) | Error rate over time | Reliability analysis |
| **Cost Hotspots** | Token count (blue → intense) | Token usage over time | Cost optimization |
| **Latency** | Avg duration (amber → intense) | Avg latency over time | Performance tuning |

### 3.4 Time Range and Performance

The graph supports time ranges from 2 hours to 30 days. All queries use the pre-aggregated hourly table that loads in under 1 second, even for graphs with hundreds of nodes.

---

## 4. Data Pipeline: From Spans to Graphs

The Agent Graph data pipeline transforms raw OpenTelemetry spans into interactive, sub-second graph queries through five stages. Each stage makes a deliberate trade-off between freshness and query cost, culminating in a system where the expensive recursive graph traversal runs exactly once per hour in the background, while user-facing queries are simple `GROUP BY` aggregations.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 1: TELEMETRY EMISSION                                         │
│                                                                      │
│  Google ADK (Agent Development Kit) automatically instruments every  │
│  agent invocation, tool call, and LLM request as OpenTelemetry spans │
│  with semantic attributes:                                           │
│    • gen_ai.operation.name (invoke_agent, execute_tool,              │
│      generate_content)                                               │
│    • gen_ai.agent.name, gen_ai.tool.name, gen_ai.response.model     │
│    • gen_ai.usage.input_tokens, gen_ai.usage.output_tokens          │
│    • gen_ai.agent.description, gen_ai.tool.description              │
│    • gen_ai.conversation.id (session identifier)                     │
│                                                                      │
│  Spans are exported to Google Cloud Trace via the GenAI SDK.         │
│  The trace data lands in the `_AllSpans` table within BigQuery       │
│  (via Cloud Trace's BigQuery export).                                │
│                                                                      │
│  Key insight: ADK instruments *every* operation — including          │
│  internal "glue" spans (content formatting, routing decisions) that  │
│  are structural overhead, not meaningful agent operations. The       │
│  pipeline must filter these out to reveal the true topology.         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 2: MATERIALIZED VIEW (agent_spans_raw)                        │
│                                                                      │
│  A BigQuery Materialized View extracts and denormalizes the raw      │
│  Cloud Trace spans into a flat, queryable schema. Auto-refreshes     │
│  every 5 minutes with a max staleness of 30 minutes. Clustered      │
│  on (trace_id, session_id, node_label) for fast lookups.             │
│                                                                      │
│  Key transformations:                                                │
│    • JSON attribute extraction → typed columns (SAFE_CAST)           │
│    • Status code mapping: 0→UNSET, 1→OK, 2→ERROR                    │
│    • Duration normalization: nanoseconds → milliseconds              │
│    • Node classification:                                            │
│        invoke_agent → Agent                                          │
│        execute_tool → Tool                                           │
│        generate_content → LLM                                        │
│        everything else → Glue (filtered out downstream)              │
│    • Display label resolution (priority cascade):                    │
│        gen_ai.agent.name > gen_ai.tool.name >                        │
│        gen_ai.response.model > span name                             │
│    • Logical node ID: "Type::Label" (e.g., "Agent::root",           │
│        "Tool::fetch_trace", "LLM::gemini-2.5-flash")                │
│    • Service filter: only spans from service.name = 'sre-agent'     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 3: VIEWS — Nodes, Edges, and Trajectories                     │
│                                                                      │
│  Three SQL views built atop the materialized view provide the        │
│  semantic layers consumed by the property graph and the hourly       │
│  pre-aggregation:                                                    │
│                                                                      │
│  a) agent_topology_nodes — per-(trace, node) aggregation with        │
│     a synthetic "User::session" entry point node                     │
│  b) agent_topology_edges — recursive CTE that skips Glue spans       │
│     to connect agents directly to their tools/LLMs, plus             │
│     synthetic User → Root Agent edges                                │
│  c) agent_trajectories — chronological step-to-step flow links       │
│     for Sankey visualization, aggregated across traces               │
│                                                                      │
│  The recursive CTE in agent_topology_edges is the most important     │
│  piece of the pipeline — see Section 5.3 for a detailed walkthrough. │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 4: PROPERTY GRAPH (agent_topology_graph)                      │
│                                                                      │
│  A BigQuery Property Graph defined over the node and edge views:     │
│    • NODE TABLE: agent_topology_nodes                                │
│      KEY: (trace_id, logical_node_id)                                │
│    • EDGE TABLE: agent_topology_edges                                │
│      KEY: (trace_id, source_node_id, destination_node_id)            │
│      SOURCE → NODE, DESTINATION → NODE                               │
│                                                                      │
│  This enables GRAPH_TABLE SQL queries with recursive path matching   │
│  for ad-hoc graph exploration. In practice, the pre-aggregated       │
│  hourly table (Stage 5) is used for all production queries.          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 5: PRE-AGGREGATED HOURLY TABLE (agent_graph_hourly)           │
│                                                                      │
│  A scheduled BQ query runs every hour, joins the node and edge       │
│  views, computes per-model cost estimates, and appends results to    │
│  a partitioned + clustered table:                                    │
│    • PARTITION BY DATE(time_bucket)                                   │
│    • CLUSTER BY source_id, target_id                                 │
│                                                                      │
│  32 columns per row covering:                                        │
│    • Edge metrics: call_count, error_count, tokens, cost, duration   │
│    • Node metrics: tokens, errors, cost, duration, description       │
│    • Subcall counts: tool_call_count, llm_call_count                 │
│    • Downstream rollups: total_tokens, total_cost, call counts       │
│    • Session tracking: ARRAY<STRING> for cross-bucket dedup          │
│                                                                      │
│  Deduplication via ExistingBuckets CTE prevents double-counting      │
│  on re-runs. Initial backfill covers 30 days.                        │
│                                                                      │
│  Result: all user-facing queries are simple GROUP BY + SUM           │
│  aggregations that return in < 1 second.                             │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.1 Why This Architecture

The key design decision is **separating the expensive operation (recursive graph traversal) from the user-facing operation (aggregation)**. This is analogous to how OLAP systems use pre-aggregated cubes, or how Prometheus uses recording rules to pre-compute expensive queries.

| Operation | Complexity | Latency | When It Runs |
| :--- | :--- | :--- | :--- |
| Recursive CTE / GRAPH_TABLE | O(spans × depth) | 1–60 seconds | Hourly (background) |
| `GROUP BY + SUM` on hourly table | O(buckets × edges) | < 1 second | Per user request |

The 5-minute materialized view refresh + hourly pre-aggregation means data is at most ~65 minutes stale. For a system where users typically analyze windows of hours to days, this staleness is imperceptible.

---

## 5. BigQuery Schema Deep Dive

### 5.1 Materialized View: `agent_spans_raw`

The foundation of the entire pipeline. Transforms raw `_AllSpans` rows (with deeply nested JSON attributes) into flat, typed, query-friendly columns.

```sql
CREATE MATERIALIZED VIEW `{project}.{dataset}.agent_spans_raw`
CLUSTER BY trace_id, session_id, node_label
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 5,
  max_staleness = INTERVAL "30" MINUTE,
  allow_non_incremental_definition = true
)
AS
SELECT
  span_id,
  parent_span_id AS parent_id,
  trace_id,
  start_time,
  JSON_VALUE(attributes, '$.\"gen_ai.conversation.id\"') AS session_id,
  CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
  CASE status.code
    WHEN 0 THEN 'UNSET'  WHEN 1 THEN 'OK'  WHEN 2 THEN 'ERROR'
    ELSE CAST(status.code AS STRING)
  END AS status_code,
  status.message AS status_desc,
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.input_tokens\"') AS INT64)
    AS input_tokens,
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.output_tokens\"') AS INT64)
    AS output_tokens,
  -- Node classification (the four-way discriminator)
  CASE
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'invoke_agent'
      THEN 'Agent'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'execute_tool'
      THEN 'Tool'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'generate_content'
      THEN 'LLM'
    ELSE 'Glue'
  END AS node_type,
  -- Human-readable label (priority cascade)
  COALESCE(
    JSON_VALUE(attributes, '$.\"gen_ai.agent.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.tool.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.response.model\"'),
    name
  ) AS node_label,
  -- Logical node ID: "Type::Label"
  CONCAT(
    CASE ... END,  -- same classification as node_type
    '::',
    COALESCE(...)  -- same cascade as node_label
  ) AS logical_node_id
FROM `{project}.{trace_dataset}._AllSpans`
WHERE JSON_VALUE(resource.attributes, '$.\"service.name\"') = 'sre-agent';
```

**Design decisions:**
- **`SAFE_CAST` for tokens**: Raw attributes are strings; `SAFE_CAST` returns `NULL` instead of failing on malformed data.
- **`allow_non_incremental_definition`**: Required because the view uses `COALESCE`, `CASE`, and `JSON_VALUE` which prevent incremental refresh. The MV refreshes fully every 5 minutes.
- **Service filter**: Only `sre-agent` spans are included — other services sharing the same `_AllSpans` table are excluded.
- **`logical_node_id`**: A composite `"Type::Label"` key that uniquely identifies a node in the topology. Two spans with the same logical_node_id are the same logical component, even if they occurred in different traces.

### 5.2 Topology Nodes View: `agent_topology_nodes`

Aggregates per-(trace, logical_node_id) and injects a **synthetic `User::session` node** as the graph entry point.

```sql
CREATE OR REPLACE VIEW `{project}.{dataset}.agent_topology_nodes` AS
-- Real nodes: per-trace aggregation of Agent/Tool/LLM spans
SELECT
  trace_id, session_id, logical_node_id,
  ANY_VALUE(node_type) AS node_type,
  ANY_VALUE(node_label) AS node_label,
  COUNT(span_id) AS execution_count,
  SUM(duration_ms) AS total_duration_ms,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  COUNTIF(status_code = 'ERROR') AS error_count,
  MIN(start_time) AS start_time
FROM `{project}.{dataset}.agent_spans_raw`
WHERE node_type != 'Glue'
GROUP BY 1, 2, 3

UNION ALL

-- Synthetic User node: the visible entry point for the graph
SELECT
  trace_id, session_id,
  'User::session' AS logical_node_id,
  'User' AS node_type, 'session' AS node_label,
  COUNT(DISTINCT span_id) AS execution_count,
  SUM(duration_ms) AS total_duration_ms,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  COUNTIF(status_code = 'ERROR') AS error_count,
  MIN(start_time) AS start_time
FROM `{project}.{dataset}.agent_spans_raw`
WHERE node_type = 'Agent'
  AND (parent_id IS NULL OR parent_id NOT IN (
    SELECT span_id FROM `{project}.{dataset}.agent_spans_raw`
    WHERE node_type != 'Glue'
  ))
GROUP BY 1, 2;
```

**Why a synthetic User node?** Without it, the graph would start at the root agent — but the root agent has no incoming edge, making it visually disconnected. The `User::session` node provides a clear "this is where execution begins" anchor. It aggregates metrics from root-level agent spans to give a meaningful summary of user-triggered activity.

**Root detection logic:** A span is considered a root if it either has `parent_id IS NULL` (true root) or its parent is a Glue span (not in the set of non-Glue span IDs). This handles the common case where ADK wraps agent invocations in a top-level infrastructure span.

### 5.3 Topology Edges View: `agent_topology_edges`

This is the most sophisticated piece of SQL in the pipeline — a **recursive CTE that traverses the span tree and skips Glue spans** to reveal the true agent-to-tool delegation structure.

```sql
CREATE OR REPLACE VIEW `{project}.{dataset}.agent_topology_edges` AS
WITH RECURSIVE span_tree AS (
  -- Base case: Root spans (no parent or parent not in dataset)
  SELECT
    span_id, trace_id, session_id, node_type, logical_node_id,
    CAST(NULL AS STRING) AS ancestor_logical_id,
    duration_ms, input_tokens, output_tokens, status_code
  FROM `{project}.{dataset}.agent_spans_raw`
  WHERE parent_id IS NULL
    OR parent_id NOT IN (SELECT span_id FROM agent_spans_raw)

  UNION ALL

  -- Recursive step: Traverse to children, carrying the ancestor
  SELECT
    child.span_id, child.trace_id, child.session_id,
    child.node_type, child.logical_node_id,
    -- THE BRIDGE: If parent is meaningful, it's the ancestor.
    -- If parent is Glue, inherit the ancestor from higher up.
    IF(parent.node_type != 'Glue',
       parent.logical_node_id,
       parent.ancestor_logical_id),
    child.duration_ms, child.input_tokens, child.output_tokens,
    child.status_code
  FROM agent_spans_raw child
  JOIN span_tree parent ON child.parent_id = parent.span_id
)
-- Aggregate edges: source (ancestor) → target (child)
SELECT
  trace_id, session_id,
  ancestor_logical_id AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms) as total_duration_ms,
  SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
  SUM(IFNULL(input_tokens, 0)) as input_tokens,
  SUM(IFNULL(output_tokens, 0)) as output_tokens,
  COUNTIF(status_code = 'ERROR') as error_count
FROM span_tree
WHERE node_type != 'Glue'
  AND ancestor_logical_id IS NOT NULL
  AND ancestor_logical_id != logical_node_id  -- exclude self-loops
GROUP BY 1, 2, 3, 4

UNION ALL

-- Synthetic User → Root Agent edges
SELECT
  trace_id, session_id,
  'User::session' AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms), SUM(IFNULL(input_tokens,0) + IFNULL(output_tokens,0)),
  SUM(IFNULL(input_tokens,0)), SUM(IFNULL(output_tokens,0)),
  COUNTIF(status_code = 'ERROR')
FROM span_tree
WHERE node_type = 'Agent' AND ancestor_logical_id IS NULL
GROUP BY 1, 2, 3, 4;
```

**The Glue-bridging algorithm explained:**

Consider this span tree from a real trace:

```
Root Agent (Agent)                          ← ancestor_logical_id = NULL
  └─> _handle_request (Glue)               ← inherits NULL → becomes NULL
        └─> _invoke_tool (Glue)            ← inherits NULL → becomes NULL
              └─> fetch_trace (Tool)        ← parent is Glue, so inherits:
                                               ancestor = grandparent's ancestor
                                               → but grandparent is also Glue
                                               → eventually resolves to Root Agent
```

At each level of the recursion:
- If the **parent is a non-Glue span** (Agent, Tool, LLM), it becomes the `ancestor_logical_id` for the child. This creates a direct edge: `Root Agent → fetch_trace`.
- If the **parent is a Glue span**, the child inherits the `ancestor_logical_id` from higher up the chain. Glue spans are transparent — they do not appear in the resulting topology.

This produces a clean graph where agents connect directly to the tools and LLMs they invoke, even when multiple layers of framework infrastructure sit between them in the raw span tree.

### 5.4 Trajectories View: `agent_trajectories`

While the topology edges view captures *structural* relationships (who calls whom), the trajectories view captures *temporal* relationships (what happened in what order). This powers the Sankey diagram.

```sql
CREATE OR REPLACE VIEW `{project}.{dataset}.agent_trajectories` AS
WITH sequenced_steps AS (
  -- Number each meaningful span chronologically within its trace
  SELECT
    trace_id, session_id, span_id, node_type, node_label,
    logical_node_id, start_time, duration_ms, status_code,
    input_tokens, output_tokens,
    ROW_NUMBER() OVER(
      PARTITION BY trace_id ORDER BY start_time ASC
    ) AS step_sequence
  FROM agent_spans_raw
  WHERE node_type != 'Glue'
),
trajectory_links AS (
  -- Self-join: step N → step N+1 within each trace
  SELECT
    a.trace_id, a.session_id,
    a.logical_node_id AS source_node, b.logical_node_id AS target_node,
    a.node_type AS source_type, b.node_type AS target_type,
    a.step_sequence AS source_step, b.step_sequence AS target_step,
    -- Carry forward metrics for both sides
    a.duration_ms AS source_duration_ms, b.duration_ms AS target_duration_ms,
    a.status_code AS source_status, b.status_code AS target_status,
    COALESCE(a.input_tokens,0) + COALESCE(a.output_tokens,0) AS source_tokens,
    COALESCE(b.input_tokens,0) + COALESCE(b.output_tokens,0) AS target_tokens
  FROM sequenced_steps a
  JOIN sequenced_steps b
    ON a.trace_id = b.trace_id
    AND a.step_sequence + 1 = b.step_sequence
)
-- Aggregate flow volumes across all traces
SELECT
  source_node, source_type, source_label,
  target_node, target_type, target_label,
  COUNT(DISTINCT trace_id) AS trace_count,
  SUM(source_duration_ms) AS total_source_duration_ms,
  SUM(target_duration_ms) AS total_target_duration_ms,
  SUM(source_tokens) AS total_source_tokens,
  SUM(target_tokens) AS total_target_tokens,
  COUNTIF(source_status = 'ERROR' OR target_status = 'ERROR') AS error_transition_count
FROM trajectory_links
GROUP BY 1, 2, 3, 4, 5, 6;
```

**Design insight:** The self-join on `step_sequence + 1 = step_sequence` creates a Markov-chain-like model of agent behavior — each link represents "after the agent did X, it did Y." Aggregated across traces, the `trace_count` on each link reveals the probability distribution of reasoning transitions.

### 5.5 Property Graph: `agent_topology_graph`

```sql
CREATE OR REPLACE PROPERTY GRAPH `{project}.{dataset}.agent_topology_graph`
  NODE TABLES (
    `{project}.{dataset}.agent_topology_nodes` AS Node
      KEY (trace_id, logical_node_id)
      LABEL Component
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    `{project}.{dataset}.agent_topology_edges` AS Interaction
      KEY (trace_id, source_node_id, destination_node_id)
      SOURCE KEY (trace_id, source_node_id)
        REFERENCES Node (trace_id, logical_node_id)
      DESTINATION KEY (trace_id, destination_node_id)
        REFERENCES Node (trace_id, logical_node_id)
      LABEL Interaction
      PROPERTIES ALL COLUMNS
  );
```

The property graph enables ad-hoc queries using BigQuery's `GRAPH_TABLE` syntax (e.g., recursive path matching with `->{1,5}`). In practice, the pre-aggregated hourly table is preferred for all production queries because it avoids the expensive recursive traversal at query time.

### 5.6 Pre-Aggregated Hourly Table: `agent_graph_hourly`

The hourly table is the performance-critical cornerstone. It stores **32 columns** per (time_bucket, source_id, target_id) row:

```sql
CREATE TABLE `{project}.{dataset}.agent_graph_hourly`
(
  -- Bucketing
  time_bucket TIMESTAMP NOT NULL,

  -- Edge identity
  source_id STRING NOT NULL,
  target_id STRING NOT NULL,
  source_type STRING,
  target_type STRING,

  -- Edge metrics (pre-aggregated per hour)
  call_count INT64,
  error_count INT64,
  edge_tokens INT64,
  input_tokens INT64,
  output_tokens INT64,
  total_cost FLOAT64,
  sum_duration_ms FLOAT64,
  max_p95_duration_ms FLOAT64,
  unique_sessions INT64,
  sample_error STRING,

  -- Target-node metrics (pre-aggregated per hour for the dst span)
  node_total_tokens INT64,
  node_input_tokens INT64,
  node_output_tokens INT64,
  node_has_error BOOL,
  node_sum_duration_ms FLOAT64,
  node_max_p95_duration_ms FLOAT64,
  node_error_count INT64,
  node_call_count INT64,
  node_total_cost FLOAT64,
  node_description STRING,

  -- Source-node subcall counts
  tool_call_count INT64,
  llm_call_count INT64,

  -- Hierarchical rollup metrics
  downstream_total_tokens INT64,
  downstream_total_cost FLOAT64,
  downstream_tool_call_count INT64,
  downstream_llm_call_count INT64,

  -- Session tracking (for cross-bucket dedup)
  session_ids ARRAY<STRING>
)
PARTITION BY DATE(time_bucket)
CLUSTER BY source_id, target_id
OPTIONS (
  description = 'Pre-aggregated hourly agent graph data for sub-second UI queries'
);
```

**Column taxonomy:**

| Category | Columns | Purpose |
| :--- | :--- | :--- |
| **Identity** | `time_bucket`, `source_id`, `target_id`, `source_type`, `target_type` | Row key — one row per (hour, edge) |
| **Edge metrics** | `call_count`, `error_count`, `edge_tokens`, `input_tokens`, `output_tokens`, `total_cost`, `sum_duration_ms`, `max_p95_duration_ms`, `unique_sessions`, `sample_error` | Aggregate metrics on the delegation edge |
| **Node metrics** | `node_*` columns | Aggregate metrics on the target node (used for topology node rendering and timeseries) |
| **Subcall counts** | `tool_call_count`, `llm_call_count` | How many tool/LLM calls the source node made (displayed as badges) |
| **Downstream rollups** | `downstream_*` columns | Hierarchical totals including all transitive children |
| **Session tracking** | `session_ids` | `ARRAY<STRING>` for approximate cross-bucket unique session counting |

**Partitioning and clustering rationale:**
- `PARTITION BY DATE(time_bucket)` enables BigQuery partition pruning — a query for "last 24 hours" only scans 1-2 partitions, not the entire table.
- `CLUSTER BY source_id, target_id` co-locates all rows for a given edge, making per-edge aggregation extremely fast.

### 5.7 Cost Calculation Model

Cost is estimated per-span using model-specific pricing tiers derived from the Google Cloud Vertex AI pricing page:

```sql
COALESCE(input_tokens, 0) * CASE
  WHEN target_id LIKE '%flash%'   THEN 0.00000015    -- $0.15/1M input
  WHEN target_id LIKE '%2.5-pro%' THEN 0.00000125    -- $1.25/1M input
  WHEN target_id LIKE '%1.5-pro%' THEN 0.00000125    -- $1.25/1M input
  ELSE 0.0000005                                       -- default fallback
END
+ COALESCE(output_tokens, 0) * CASE
  WHEN target_id LIKE '%flash%'   THEN 0.0000006     -- $0.60/1M output
  WHEN target_id LIKE '%2.5-pro%' THEN 0.00001       -- $10.00/1M output
  WHEN target_id LIKE '%1.5-pro%' THEN 0.000005      -- $5.00/1M output
  ELSE 0.000002                                        -- default fallback
END AS span_cost
```

The model name is embedded in the `target_id` (logical node ID), so pattern matching via `LIKE` provides accurate per-model pricing. Tool and Agent spans have zero token cost by default; only LLM spans contribute to cost.

### 5.8 Backfill and Incremental Update

**Initial backfill** (runs once during setup):
- Processes the last 30 days (720 hours) of data
- Joins `agent_topology_edges` with `agent_topology_nodes` to get timestamps
- Applies cost calculation per span
- Groups by `(time_bucket, source_id, target_id, source_type, target_type)`

**Scheduled incremental query** (runs every hour):
- Processes only the last 2 hours of data (`INTERVAL 2 HOUR`) with an upper bound of `TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR)` to avoid processing incomplete hours
- Uses an `ExistingBuckets` CTE to deduplicate — any time_bucket already present in the table is skipped:

```sql
ExistingBuckets AS (
  SELECT DISTINCT time_bucket
  FROM `{project}.{dataset}.agent_graph_hourly`
  WHERE time_bucket >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
),
NewPaths AS (
  SELECT cp.* FROM CostPaths cp
  LEFT JOIN ExistingBuckets eb ON cp.time_bucket = eb.time_bucket
  WHERE eb.time_bucket IS NULL
)
```

This deduplication strategy makes the scheduled query idempotent — running it twice for the same hour produces no duplicate rows. The 2-hour lookback window provides a safety margin for late-arriving spans.

### 5.9 Metric Approximations Across Hourly Buckets

When user queries aggregate multiple hourly buckets (e.g., "last 7 days" = 168 buckets), some metrics require approximation:

| Metric | Aggregation Method | Accuracy |
| :--- | :--- | :--- |
| `call_count` | `SUM(call_count)` | Exact |
| `error_count` | `SUM(error_count)` | Exact |
| `error_rate` | `SUM(error_count) / SUM(call_count) * 100` | Exact (recomputed) |
| `avg_duration_ms` | `SUM(sum_duration_ms) / SUM(call_count)` | Exact (weighted average) |
| `p95_duration_ms` | `MAX(max_p95_duration_ms)` | Conservative upper bound |
| `unique_sessions` | `SUM(unique_sessions)` | Overcount at bucket boundaries |
| `total_cost` | `SUM(total_cost)` | Exact |
| `tokens` | `SUM(edge_tokens)` | Exact |

The P95 approximation (`MAX` of per-bucket P95s) is deliberately conservative — the true cross-bucket P95 can only be lower. For exact P95 computation across buckets, the raw materialized view would need to be queried directly (which the system supports but does not expose by default).

---

## 6. Visualization Architecture

The Agent Graph Dashboard provides two visualization surfaces implemented as a React single-page application.

### 6.1 Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Graph layout** | dagre | Hierarchical DAG layout (Sugiyama-style layering) |
| **Graph rendering** | React Flow | Interactive graph canvas with zoom, pan, node selection |
| **Sankey diagram** | @nivo/sankey (ResponsiveSankey) | Flow visualization with link gradients |
| **Side panel** | Custom React components | Detail drill-down with syntax-highlighted payload inspection |
| **Sparklines** | Custom SVG polyline (zero dependencies) | Inline trend charts on nodes and in detail panel |
| **HTTP client** | axios | API communication |
| **Code highlighting** | react-syntax-highlighter (hljs) | JSON/SQL payload rendering |

### 6.2 Topology Graph (React Flow)

The topology graph transforms backend data into a dagre-laid-out React Flow graph:

**Node types and visual grammar:**

| Node Type | Shape | Color | Border |
| :--- | :--- | :--- | :--- |
| Agent | Rounded rectangle | Teal background | Brighter border if root |
| Tool | Rounded rectangle | Orange background | Standard |
| LLM | Rounded rectangle | Purple background | Standard |

**Node content (from top to bottom):**
1. Type icon + label
2. Metric badges: execution count, error count (if > 0), total tokens (formatted as K/M)
3. Inline sparkline (when time-series data is available and view mode is active)

**Edge styling:**
- Width: proportional to `callCount` (scaled logarithmically)
- Color: red if `errorCount > 0`, otherwise default gray
- Arrow: directional, showing delegation flow
- Label: call count

**Heatmap overlays** (controlled by view mode):
- **Topology mode**: Node border intensity proportional to error rate (green → red)
- **Cost mode**: Node background intensity proportional to token count
- **Latency mode**: Node background intensity proportional to average duration

**Layout algorithm** (dagre):
1. Nodes are assigned to layers by topological sort (root at top)
2. Edge crossings are minimized within each layer
3. Spacing: `nodesep=50`, `ranksep=80` between layers
4. When sparkline data is present, node height is increased by `SPARK_H + 4` (28px) to accommodate the inline chart without overlapping edges

### 6.3 Trajectory Sankey (Nivo)

The Sankey diagram shows temporal flow — the chronological sequence of agent operations:

- **Nodes**: Logical components (same as topology nodes), colored by type
- **Links**: Flow width proportional to `trace_count` (how many traces followed this path)
- **Loop detection**: Nodes participating in detected loops are highlighted in orange (`#FF6D00`); a warning banner appears at the bottom

**Cycle handling**: The Sankey library (Nivo) does not support cycles natively. The `removeCyclicLinks()` utility performs a DFS-based topological analysis:
1. Build adjacency list from links
2. Sort nodes by in-degree (roots first) as DFS start order
3. DFS traversal with recursion stack tracking
4. **Back-edges** (edges to nodes currently in the recursion stack) are **dropped** from the safe dataset
5. Cross-edges and forward-edges are preserved

This allows the Sankey to render without crashing while the loop detection metadata (from the backend) highlights which nodes and edges are part of pathological cycles.

### 6.4 Side Panel (Detail Drill-Down)

Clicking a node or edge opens a slide-in side panel with full detail:

**Node detail view:**
1. **Trend sparkline**: SVG polyline showing the selected metric (error rate / token usage / latency) over time, rendered at 320x40px
2. **Metrics section**: Total invocations, error rate (color-coded badge), error count
3. **Tokens section**: Input tokens, output tokens, total, estimated cost
4. **Latency section**: P50/P95/P99 percentile bars with proportional fill
5. **Top Errors**: Most frequent error messages with occurrence counts
6. **Raw Payloads**: Expandable accordion of recent span payloads with syntax-highlighted JSON (prompts, completions, tool inputs, tool outputs)

**Edge detail view:**
1. **Call metrics**: Call count, error count, error rate
2. **Performance**: Avg duration, P95 duration, P99 duration
3. **Tokens**: Total, input, output

### 6.5 Sparkline Component

The sparkline is a zero-dependency inline SVG chart used in both topology nodes and the side panel:

```
┌────────────────────────────────────────┐
│  ╱╲    ╱╲                              │  ← SVG polyline
│ ╱  ╲  ╱  ╲    ╱                        │     width: 160px (node) / 320px (panel)
│╱    ╲╱    ╲  ╱                          │     height: 24px (node) / 40px (panel)
│           ╲╱                            │
└────────────────────────────────────────┘
```

The `extractSparkSeries()` function maps `TimeSeriesPoint[]` to `number[]` based on the active view mode:

| View Mode | Extracted Metric | Stroke Color |
| :--- | :--- | :--- |
| Topology | `errorCount / callCount` (error rate) | Red (`#f85149`) |
| Cost | `totalTokens` | Blue (`#58a6ff`) |
| Latency | `avgDurationMs` | Amber (`#d29922`) |

Points are normalized to the `[min, max]` range of the series, with 2px padding on all sides. The polyline uses `strokeLinejoin="round"` and `strokeLinecap="round"` for smooth visual rendering.

---

## 7. API Layer

The Agent Graph backend is a FastAPI router (`sre_agent/api/routers/agent_graph.py`) that exposes six endpoints. All endpoints validate inputs against regex patterns to prevent SQL injection and query the `agent_graph_hourly` table for sub-second response times.

### 7.1 Endpoint Summary

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `GET /api/v1/graph/topology` | GET | Full graph topology (nodes + edges) |
| `GET /api/v1/graph/trajectories` | GET | Sankey flow data with loop detection |
| `GET /api/v1/graph/node/{node_id}` | GET | Detail for a specific node |
| `GET /api/v1/graph/edge/{source_id}/{target_id}` | GET | Detail for a specific edge |
| `GET /api/v1/graph/timeseries` | GET | Per-bucket time-series for sparklines |

### 7.2 Common Parameters

All endpoints share these query parameters:

| Parameter | Type | Default | Validation |
| :--- | :--- | :--- | :--- |
| `project_id` | `str` | required | Regex: `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$` |
| `dataset` | `str` | `"agent_graph"` | Same identifier regex |
| `hours` | `int` | `24` | `ge=1, le=720` (timeseries: `ge=2`) |
| `start_time` | `str \| None` | `None` | ISO 8601 format |
| `end_time` | `str \| None` | `None` | ISO 8601 format |

### 7.3 Input Validation

Three levels of input validation prevent SQL injection and ensure data integrity:

1. **Identifier validation** (`_validate_identifier`): Project ID and dataset name must match `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`. These values are interpolated into SQL strings, so strict validation is essential.

2. **Node ID validation** (`_validate_logical_node_id`): Node IDs like `Agent::root` or `Tool::fetch_trace` must match `^[a-zA-Z0-9_.:/-]{1,256}$`.

3. **ISO 8601 validation** (`_validate_iso8601`): Timestamps must match a strict ISO 8601 regex and are validated as real datetime values.

### 7.4 Topology Endpoint

Queries the hourly table with `GROUP BY source_id, target_id` and returns React Flow-compatible node/edge structures. Includes:
- Automatic node type classification and React Flow type mapping
- Node color assignment per type
- Edge data with call count, error count, tokens, duration
- Errors-only filtering (when `errors_only=true`, edges with `error_count = 0` are excluded)

### 7.5 Trajectories Endpoint

Queries the `agent_trajectories` view for Sankey flow data, then runs **loop detection** on the results:

The `_detect_loops()` algorithm:
1. Builds an adjacency graph from trajectory links
2. Runs DFS with a recursion stack to find back-edges
3. When a back-edge is found, traces the cycle by walking backward through the recursion stack
4. Returns a list of `LoopTrace` objects, each containing the cycle node sequence and repetition count

Loops are appended to the response as `loopTraces`, enabling the frontend to highlight pathological retry cycles.

### 7.6 Timeseries Endpoint

Returns per-bucket time-series for sparkline rendering:

```python
@router.get("/timeseries")
async def get_timeseries(
    project_id: str,
    dataset: str = "agent_graph",
    hours: int = Query(default=24, ge=2, le=720),  # ge=2: need >=2 points
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
```

**SQL:**
```sql
SELECT
    time_bucket,
    target_id AS node_id,
    SUM(node_call_count) AS call_count,
    SUM(node_error_count) AS error_count,
    SAFE_DIVIDE(
        SUM(node_sum_duration_ms),
        NULLIF(SUM(node_call_count), 0)
    ) AS avg_duration_ms,
    SUM(node_total_tokens) AS total_tokens,
    SUM(node_total_cost) AS total_cost
FROM `{project}.{dataset}.agent_graph_hourly`
WHERE {time_filter}
  AND node_call_count IS NOT NULL
GROUP BY time_bucket, target_id
ORDER BY target_id, time_bucket ASC
```

**Response shape:**
```json
{
  "series": {
    "Agent::root": [
      {"bucket": "2026-02-20T10:00:00+00:00", "callCount": 12, "errorCount": 1,
       "avgDurationMs": 432.1, "totalTokens": 840, "totalCost": 0.001234},
      {"bucket": "2026-02-20T11:00:00+00:00", "callCount": 15, ...}
    ],
    "Tool::fetch_trace": [...]
  }
}
```

The `hours >= 2` constraint ensures at least 2 data points for a meaningful sparkline. Rows are grouped into a `defaultdict(list)` keyed by `node_id`, then ordered by `time_bucket ASC` to produce chronologically sorted series.

---

## 8. Real-Time Auto-Refresh and Time-Series Sparklines

### 8.1 Auto-Refresh Mechanism

The dashboard supports configurable auto-refresh that re-fetches all data on a periodic cadence without disrupting the user's interaction state.

**Configuration:**
- Toggle: On/Off (default: Off)
- Intervals: 30 seconds, 1 minute, 5 minutes
- Visual indicator: "Updated HH:MM:SS" timestamp in the toolbar

**Implementation** (`App.tsx`):

The `fetchAll(isSilent: boolean)` function is the core data-fetching primitive:

- **`fetchAll(false)`** — Manual "Load" button click. Clears selection, clears errors, resets all data, then fetches topology + trajectories + timeseries in parallel.
- **`fetchAll(true)`** — Auto-refresh tick. Preserves the current selection and any open side panel. Only updates the underlying data, allowing the user to continue inspecting a node or edge while the graph refreshes around them.

The auto-refresh timer:
```typescript
useEffect(() => {
  if (!autoRefresh.enabled || lastUpdated === null) return
  const id = setInterval(
    () => fetchAll(true),
    autoRefresh.intervalSeconds * 1000
  )
  return () => clearInterval(id)
}, [autoRefresh.enabled, autoRefresh.intervalSeconds, lastUpdated, fetchAll])
```

**Key design decisions:**
- Timer only starts after the first successful load (`lastUpdated !== null`), preventing auto-refresh from firing before the user has entered a project ID.
- `Promise.allSettled` is used so a single endpoint failure (e.g., timeseries) doesn't block the other endpoints from updating.
- Timeseries data is only fetched when `hours >= 2` (the endpoint requires at least 2 buckets).

### 8.2 Data Flow for Sparklines

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐
│ /timeseries  │───>│ App.tsx      │───>│ TopologyGraph.tsx     │
│  endpoint    │    │ timeseriesData│    │ node._sparklinePoints │
└─────────────┘    │              │    │ + dagre height adjust  │
                   │              │    └──────────────────────┘
                   │              │    ┌──────────────────────┐
                   │              │───>│ SidePanel.tsx         │
                   │              │    │ NodeDetailView trend  │
                   └──────────────┘    └──────────────────────┘
```

1. `App.tsx` fetches `/api/v1/graph/timeseries` and stores the result as `timeseriesData: TimeSeriesData | null`
2. `TopologyGraph` receives `sparklineData` and injects `_sparklinePoints` (the per-node series) and `_viewMode` into each React Flow node's data
3. When sparkline data has >= 2 points, the node's dagre height is increased by `SPARK_H + 4` (28px) to prevent edge overlaps
4. Each node component renders a `<Sparkline>` after its metric badges
5. `SidePanel` receives the same data and renders a wider sparkline (320x40px) in the node detail view with a contextual label ("Error Rate Trend", "Token Usage Trend", or "Latency Trend")

---

## 9. Use Cases and Debugging Patterns

### 9.1 Cost Attribution and Optimization

**Scenario**: Monthly LLM costs increased 40% but the number of investigations stayed constant.

**Using the Agent Graph:**
1. Switch to **Cost Hotspots** view mode
2. Observe which nodes have the deepest blue (highest token consumption)
3. Click the dominant node — likely the Synthesizer (Gemini 2.5 Pro)
4. In the side panel, compare input vs. output tokens
5. Check the sparkline: did cost spike at a specific time (correlating with a deployment)?
6. Navigate to **Raw Payloads** to inspect whether prompts grew in size (perhaps due to larger context being passed)

**Typical findings:**
- A single panel (e.g., Trace Panel) is fetching overly large payloads and passing them to the Synthesizer
- The Synthesizer's output tokens doubled due to a prompt change requesting more detailed analysis
- A tool is being called in a loop due to retry logic, consuming tokens on each retry

### 9.2 Error Rate Investigation

**Scenario**: Users report intermittent "investigation failed" errors, but individual error logs are unhelpful because the errors occur at different points in different executions.

**Using the Agent Graph:**
1. Load the graph with the default **Topology** view mode
2. Red-highlighted edges immediately show where errors concentrate
3. Click the `Root Agent → BigQuery Tool` edge — error rate is 12%
4. In the side panel, expand **Top Errors** to see "BigQuery quota exceeded: too many concurrent queries"
5. Check the sparkline: errors spike at 2:00 PM and 5:00 PM — exactly when the scheduled query runs alongside peak user activity

**Resolution**: Rate-limit BigQuery tool calls or schedule the hourly pre-aggregation query during off-peak hours.

### 9.3 Latency Bottleneck Identification

**Scenario**: P95 end-to-end investigation latency regressed from 8 seconds to 15 seconds after a release.

**Using the Agent Graph:**
1. Switch to **Latency** view mode
2. The `Trace Panel → fetch_trace` edge glows amber — P95 is 4.2 seconds (was 1.5 seconds)
3. Click the edge: P99 is 8.1 seconds
4. Inspect raw payloads: the tool is now fetching 500 spans per trace instead of 100 due to a pagination change
5. The sparkline confirms the latency increase started on the deployment date

**Resolution**: Restore the 100-span default or implement server-side filtering to reduce payload size.

### 9.4 Pathological Loop Detection

**Scenario**: Some investigations consume 5x the normal token budget and take 2 minutes instead of 15 seconds.

**Using the Agent Graph:**
1. Switch to the **Trajectory Flow** tab
2. The Sankey diagram shows orange-highlighted nodes with a warning: "3 traces with pathological loops detected"
3. The loop is `Root Agent → Router → Root Agent` — the router is classifying the query as needing sub-agent delegation, but the sub-agent is bouncing back to the root
4. Click on the topology to inspect the `Router → Root Agent` back-edge
5. Raw payloads reveal the router's classification prompt is ambiguous for a specific class of queries

**Resolution**: Add a guard clause in the routing logic to prevent delegation back to the root, or refine the classification prompt to handle the ambiguous case.

### 9.5 Architecture Discovery and Onboarding

**Scenario**: A new team member needs to understand how the agent system works.

**Using the Agent Graph:**
1. Load the graph for the last 7 days
2. The topology shows the full hierarchy: User → Root Agent → Router → Council Orchestrator → 5 Panels → Synthesizer
3. Node badges show relative importance: the Trace Panel handles 40% of all tool calls, while the Data Panel handles only 5%
4. Click each panel to see its tool dependencies and error rates
5. Switch to Trajectory Flow to see the most common reasoning paths: "80% of investigations follow Router → Trace Panel → Metrics Panel → Synthesizer"

**Outcome**: The new engineer understands the system architecture, the dominant reasoning patterns, and where to focus optimization efforts — all without reading a single line of code.

### 9.6 Regression Detection via Sparklines

**Scenario**: After a routine deployment, you want to verify nothing regressed.

**Using the Agent Graph:**
1. Enable auto-refresh at 30-second intervals
2. Load the topology view with a 24-hour window
3. Observe sparklines on each node — they should show continuous, smooth lines
4. If a node's error rate sparkline shows a step-function increase starting at the deployment time, that's a regression
5. If a node's latency sparkline shows a gradual increase (ramp), that's a resource exhaustion issue

**Key insight**: Sparklines make time-dependent regressions visible at a glance without requiring manual before/after comparison. The auto-refresh ensures you're watching live data.

### 9.7 Council Mode Effectiveness Analysis

**Scenario**: You want to validate whether the Debate mode (with Critic feedback loops) produces better outcomes than Standard mode.

**Using the Agent Graph:**
1. Load two time windows: one during Debate mode testing, one during Standard mode
2. Compare the topology structures — Debate mode shows additional `Critic → Panel` back-edges
3. Compare error rates on the `Synthesizer` node: is it lower with Debate mode?
4. Compare cost: Debate mode adds token cost for the Critic loop — is the improvement worth it?
5. Check trajectory flows: does Debate mode produce more consistent reasoning paths?

---

## 10. Setup and Deployment

### 10.1 Prerequisites

- A GCP project with Cloud Trace API enabled and agent traces being exported
- BigQuery API enabled with the `_AllSpans` table populated (automatic when using Cloud Trace's BigQuery export)
- `bq` CLI tool installed and authenticated (`gcloud auth application-default login`)

### 10.2 One-Time Setup

```bash
./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
```

**Arguments:**
| Argument | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `project_id` | Yes (or in `.env`) | — | GCP project ID |
| `trace_dataset` | No | `traces` | Dataset containing `_AllSpans` |
| `graph_dataset` | No | `agent_graph` | Target dataset for all graph objects |

**What it creates:**

| Object | Type | Purpose |
| :--- | :--- | :--- |
| `agent_spans_raw` | Materialized View | Flat, typed span data with 5-minute refresh |
| `agent_topology_nodes` | View | Per-(trace, node) aggregation with synthetic User node |
| `agent_topology_edges` | View | Glue-bridging recursive CTE producing clean delegation edges |
| `agent_trajectories` | View | Chronological step-to-step flow links for Sankey |
| `agent_topology_graph` | Property Graph | Graph structure for GRAPH_TABLE queries |
| `agent_graph_hourly` | Table | Pre-aggregated hourly metrics (32 columns) |

After creation, the script runs a **30-day backfill** that populates `agent_graph_hourly` with historical data.

### 10.3 Scheduled Query

After setup, configure a BigQuery Scheduled Query to run every hour. The setup script prints the exact SQL to use. Configure via:
- Cloud Console > BigQuery > Scheduled Queries, or
- `bq mk --transfer_config` CLI command

The scheduled query:
1. Processes the last 2 hours of data (safety margin for late-arriving spans)
2. Skips any time_bucket already present (idempotent via `ExistingBuckets` CTE)
3. Appends new rows to `agent_graph_hourly` using `WRITE_APPEND`

### 10.4 React Dashboard Setup

The Agent Graph React UI is located at `agent_ops_ui/` and communicates with the FastAPI backend endpoints at `/api/v1/graph/*`.

```bash
cd agent_ops_ui
npm install
npm run dev    # Development server (proxies API to backend)
npm run build  # Production build
```

The dashboard is served as part of the FastAPI application in production.

---

## 11. Test Coverage

### 11.1 Backend Tests

The backend endpoint tests (`tests/unit/sre_agent/api/routers/test_agent_graph.py`) provide comprehensive coverage with **96 test methods**:

| Test Class | Tests | Coverage |
| :--- | :--- | :--- |
| `TestValidateIdentifier` | 8 | Regex validation for project_id, dataset |
| `TestValidateLogicalNodeId` | 5 | Regex validation for node IDs |
| `TestValidateIso8601` | 5 | ISO 8601 timestamp validation |
| `TestBuildTimeFilter` | 6 | Time filter SQL generation |
| `TestGetBqClient` | 2 | BigQuery client creation |
| `TestTopologyEndpoint` | 16 | Full topology endpoint (happy path, errors, filtering, edge cases) |
| `TestTrajectoryEndpoint` | 15 | Trajectory endpoint with loop detection |
| `TestNodeDetailEndpoint` | 10 | Node detail drill-down |
| `TestEdgeDetailEndpoint` | 10 | Edge detail drill-down |
| `TestTimeSeriesEndpoint` | 14 | Timeseries endpoint (series dict, field validation, ordering, bounds, BQ errors) |
| `TestRouterConfiguration` | 5 | Route existence verification for all 5 endpoints |

### 11.2 Flutter Tests (Native Dashboard)

The Flutter-based native dashboard (used in the mobile/desktop app) has its own test suite:

| Test File | Tests | Coverage |
| :--- | :--- | :--- |
| `domain/models_test.dart` | 39 | Freezed model serialization, equality, copyWith |
| `data/agent_graph_repository_test.dart` | 11 | SQL generation, dual-path routing, response parsing |
| `application/agent_graph_notifier_test.dart` | 16 | State lifecycle, parameter passthrough, selection |
| `presentation/agent_graph_details_panel_test.dart` | 11+ | Widget rendering, badges, metrics display |
| `presentation/multi_trace_graph_canvas_test.dart` | 6 | Empty state, node count, legend, layout |
| `presentation/interactive_graph_canvas_test.dart` | 1 | Empty graph rendering |

---

## 12. Future Directions

- **Live mode**: Stream new edges as they appear (via Pub/Sub notifications on BQ insert)
- **Diff view**: Compare agent graphs across time windows to detect behavioral changes after deployments
- **Anomaly detection**: Automatically flag edges with unusual error rates or latency spikes using statistical process control
- **Cost attribution**: Per-user or per-session cost breakdown overlaid on the graph
- **Graph-based alerting**: Alert when graph topology changes (new nodes, missing nodes, new back-edges)
- **Embedding-based similarity**: Cluster similar reasoning trajectories to identify investigation archetypes
- **Cross-project comparison**: Overlay graphs from staging and production to detect behavioral divergence
- **Token budget visualization**: Show remaining budget alongside consumption on each node, with alerts when a node approaches budget limits
- **Trace drill-through**: Click any node or edge to navigate directly to the trace explorer filtered for that specific interaction

---

*Last updated: 2026-02-20*
