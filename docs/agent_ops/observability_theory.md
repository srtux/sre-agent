# Multi-Agent Observability

## Introduction

Traditional observability answers "why is my system behaving this way?" for distributed microservices. Multi-agent observability extends this question to AI reasoning systems: *why is the agent making these decisions, and how can we make it better?*

In a multi-agent architecture like Auto SRE's Council of Experts, a single user query can trigger 5--15 agents making 10--30 tool calls and 5--10 LLM invocations, producing 50--200 OpenTelemetry spans. Multiply by hundreds of investigations per day, and the system's behavior becomes opaque without purpose-built observability surfaces.

Auto SRE addresses this with three complementary observability surfaces, each optimized for a different audience and question type:

1. **Agent Graph** -- Structural topology and reasoning trajectories across all executions
2. **AgentOps Dashboard** -- Fleet-wide operational monitoring with KPIs, charts, and logs
3. **Agent Self-Analysis Tools** -- The agent analyzing its own behavior and self-improving

Together, these surfaces provide a complete picture: the Agent Graph shows *how the system is structured*, the Dashboard shows *how the system is performing*, and the Self-Analysis tools let the system *improve itself*.

---

## The Three Surfaces

### Agent Graph (Topology + Trajectory)

The Agent Graph aggregates thousands of individual traces into an interactive property graph that reveals the structural topology of the multi-agent system. It answers questions that no single trace can: which agents call which tools, where tokens and cost concentrate, which edges have the highest error rates, and how reasoning paths evolve over time.

Two complementary views are provided:

- **Topology View** (React Flow) -- A directed graph showing agents, tools, and LLMs as nodes with delegation relationships as edges. Supports three heatmap modes: error rate, cost hotspots, and latency. Inline sparklines on each node show metric trends.
- **Trajectory View** (Nivo Sankey) -- A flow diagram showing the chronological sequence of agent operations across all traces. Reveals dominant reasoning strategies, divergence points, and pathological loops.

**Best for**: Architecture understanding, cost optimization, error investigation, latency bottleneck identification, regression detection, loop detection.

Full documentation: [Agent Graph](agent_graph.md)

### AgentOps Dashboard

The AgentOps Dashboard provides fleet-wide operational monitoring within the same React application (fifth tab alongside Agents, Tools, Agent Graph, and Trajectory Flow). It presents the system's health at a glance through KPIs, time-series charts, and high-density data tables.

Key sections:

| Section | Components | Purpose |
|---------|-----------|---------|
| KPI Cards | 4 cards with trend arrows | Total Sessions, Avg Turns, Root Invocations, Error Rate |
| Interaction Metrics | 3 ECharts visualizations | Latency (P50/P95), QPS + Error Rate, Token Usage |
| Model & Tool Tables | 2 virtualized tables | Model usage and tool performance with sortable columns |
| Agent Logs | Full-width log stream | Color-coded severity badges, virtualized for 1000+ rows |

Global filtering (time range, agent selection, group-by-agent) applies to all sections via `DashboardFilterContext`.

**Best for**: Operational health monitoring, model utilization tracking, tool performance comparison, log exploration, fleet-wide trends.

Full documentation: [AgentOps Dashboard Guide](../agent_ops/dashboard.md)

### Agent Self-Analysis Tools

The self-analysis tools enable the agent to observe and analyze its own execution telemetry. Unlike the Agent Graph and Dashboard (which are human-facing UIs), these are agent-facing tools invoked during investigations or scheduled self-analysis sessions.

| Tool | Purpose |
|------|---------|
| `list_agent_traces` | List recent agent execution traces from BigQuery |
| `reconstruct_agent_interaction` | Rebuild the full agent interaction tree from a trace |
| `analyze_agent_token_usage` | Break down token consumption by agent, tool, and LLM |
| `detect_agent_anti_patterns` | Identify retries, token waste, long chains, and other inefficiencies |
| `get_agent_graph` | Generate SQL queries for topology visualization |

These tools integrate with the **self-healing OODA loop** -- a closed-loop architecture where the agent observes its own behavior, diagnoses issues in its source code, and submits pull requests to fix itself via GitHub integration.

**Best for**: Automated self-improvement, anti-pattern detection, token waste identification, scheduled health analysis.

Full documentation: [Online Research & Self-Healing](online_research_and_self_healing.md)

---

## Architecture Overview

All three observability surfaces share a common data pipeline rooted in OpenTelemetry spans emitted by Google ADK. The pipeline progressively refines raw span data into query-optimized formats consumed by each surface.

```
                        Google ADK Runtime
                              |
                     OTel Span Emission
                    (agent, tool, LLM spans)
                              |
                              v
                    +-------------------+
                    |   Cloud Trace     |
                    | (_AllSpans table) |
                    +-------------------+
                              |
                    BigQuery Export (automatic)
                              |
                              v
                    +-------------------+
                    | Materialized View |
                    | agent_spans_raw   |
                    | (5-min refresh)   |
                    +-------------------+
                         /    |    \
                        /     |     \
                       v      v      v
               +--------+ +--------+ +-------------+
               | Nodes  | | Edges  | | Trajectories|
               | View   | | View   | | View        |
               +--------+ +--------+ +-------------+
                    \         |          /
                     \        |         /
                      v       v        v
                    +-------------------+
                    | Property Graph    |
                    | (GRAPH_TABLE)     |
                    +-------------------+
                              |
                    Hourly Scheduled Query
                              |
                              v
                    +-------------------+
                    | Pre-Aggregated    |
                    | Hourly Table      |
                    | agent_graph_hourly|
                    +-------------------+
                         /    |    \
                        /     |     \
                       v      v      v
              +---------+ +-------+ +-----------+
              | Agent   | |AgentOps| | Self-     |
              | Graph   | |Dash-  | | Analysis  |
              | React UI| |board  | | Tools     |
              +---------+ +-------+ +-----------+
                  ^           ^           ^
                  |           |           |
              FastAPI Endpoints      Agent Runtime
              /api/v1/graph/*       (tool invocation)
```

### Data Freshness by Surface

| Surface | Data Source | Staleness | Query Latency |
|---------|-----------|-----------|---------------|
| Agent Graph | `agent_graph_hourly` | Up to ~65 min (5-min MV refresh + hourly aggregation) | < 1 second |
| AgentOps Dashboard | Backend API (mock data in dev; production APIs planned) | 30s cache (React Query) | < 1 second |
| Self-Analysis Tools | `agent_spans_raw` MV or direct BigQuery SQL | Up to ~30 min (MV max staleness) | 1--60 seconds |

---

## Agent Graph

The Agent Graph is an interactive visualization that renders the aggregated topology of all agent executions within a configurable time window (2 hours to 30 days). It transforms raw OTel spans through a five-stage data pipeline: span emission, materialized view, SQL views (nodes, edges, trajectories), BigQuery property graph, and pre-aggregated hourly table.

Key capabilities:

- **Three view modes**: Topology (error heatmap), Cost Hotspots (token heatmap), Latency (duration heatmap)
- **Inline sparklines**: Per-node trend lines for the selected metric, enabling at-a-glance regression detection
- **Side panel drill-down**: Metrics, token breakdown, latency percentiles (P50/P95/P99), top errors, and raw payload inspection with syntax-highlighted JSON
- **Auto-refresh**: Configurable intervals (30s, 1m, 5m) with silent updates that preserve user selection state
- **Loop detection**: DFS-based back-edge analysis on trajectory data, with pathological loops highlighted in the Sankey diagram
- **URL deep linking**: All state (project_id, time_range, tab, selected node) encoded in URL parameters for sharing

The Agent Graph React UI lives at `agent_ops_ui/` and communicates with FastAPI endpoints at `/api/v1/graph/*` (topology, trajectories, node detail, edge detail, timeseries).

For the full data pipeline walkthrough, BigQuery schema details, SQL constructs, and use case catalog, see [Agent Graph](agent_graph.md).

---

## AgentOps Dashboard

The AgentOps Dashboard provides fleet-wide operational monitoring as the fifth tab in the AgentOps UI. While the Agent Graph reveals structural relationships, the Dashboard focuses on aggregate operational metrics across the entire agent fleet.

Key capabilities:

- **KPI cards with trend arrows**: Total Sessions, Avg Turns, Root Invocations, and Error Rate, each comparing against the previous period
- **Time-series charts**: Latency Over Time (P50/P95), QPS and Error Rate (dual-axis), Token Usage (stacked area input/output) -- all rendered via ECharts with a dark theme
- **Model Usage table**: Model name, call count, P95 latency, error rate (red when > 5%), quota exits, total tokens
- **Tool Performance table**: Tool name, call count, P95 latency, error rate
- **Agent Logs panel**: Full-width virtualized log stream with color-coded severity badges (INFO, WARNING, ERROR, DEBUG) and trace ID cross-referencing
- **Global filtering**: Time range (1h/6h/24h/7d/30d), agent selection, group-by-agent toggle via `DashboardFilterContext`
- **Virtualized rendering**: TanStack Table + TanStack Virtual for efficient handling of 1000+ row datasets

For the full guide including data flow, dependencies, and test coverage, see [AgentOps Dashboard Guide](../agent_ops/dashboard.md).

---

## Agent Self-Analysis

The self-analysis tools in `sre_agent/tools/analysis/agent_trace/` enable the agent to introspect on its own execution telemetry. Unlike the human-facing UIs, these tools are invoked programmatically -- either by the agent during an investigation or by a scheduled self-analysis job.

### Available Tools

| Tool | Function | Input | Output |
|------|----------|-------|--------|
| `list_agent_traces` | Enumerate recent traces | `hours_back`, `limit` | List of trace IDs with metadata |
| `reconstruct_agent_interaction` | Rebuild the interaction tree | `trace_id` | Hierarchical agent/tool/LLM call tree |
| `analyze_agent_token_usage` | Token consumption breakdown | `trace_id` | Per-node token counts (input, output, cost) |
| `detect_agent_anti_patterns` | Find inefficiencies | `trace_id` | List of anti-patterns with severity |
| `get_agent_graph` | Generate topology SQL | `hours`, `project_id` | SQL queries for graph visualization |

### The Self-Improvement Loop

The self-analysis tools feed into the **OODA self-healing loop**, a closed-loop architecture where the agent can observe, orient, decide, and act on its own behavioral data:

```
OBSERVE                    ORIENT                   DECIDE                    ACT
 analyze_and_learn      search_google             search_memory            github_create_
  _from_traces          fetch_web_page            get_recommended_          pull_request
 detect_agent_          github_read_file           investigation_         (draft PR with
  anti_patterns         github_search_code          strategy               auto-fix/ branch)
                                                                                |
      ^                                                                         |
      |                     CI/CD validates + deploys                            |
      +-------------------------------------------------------------------------+
```

Anti-patterns detected by the self-analysis tools include:

- **Excessive retries** -- Same tool called more than 3 times under one parent span
- **Token waste** -- Output tokens exceeding 5x input tokens on intermediate LLM calls
- **Tool syntax errors** -- Repeated failures from incorrect API filter syntax or parameters
- **Slow investigation** -- More than 8 consecutive LLM calls without meaningful tool use

Safety guardrails ensure human oversight: all agent-generated PRs are drafts by default, branch names must start with `auto-fix/`, PRs are labeled `agent-generated` and `auto-fix`, and the CI/CD pipeline validates changes before deployment.

For the full OODA loop architecture, GitHub tool details, and safety guardrails, see [Online Research & Self-Healing](online_research_and_self_healing.md).

---

## When to Use What

The following decision table maps common questions to the appropriate observability surface:

| Question | Surface | Why |
|----------|---------|-----|
| Which agents call which tools? | Agent Graph (Topology) | Shows structural delegation relationships |
| Where do tokens concentrate? | Agent Graph (Cost Hotspots) | Token-weighted heatmap on nodes |
| What is the P95 latency for a specific tool? | Agent Graph (Latency) | Per-edge latency percentiles in side panel |
| Are there pathological retry loops? | Agent Graph (Trajectory) | Sankey diagram with loop detection |
| What is the overall error rate today? | AgentOps Dashboard (KPIs) | Fleet-wide error rate card with trend |
| How has latency trended over 7 days? | AgentOps Dashboard (Charts) | P50/P95 latency time-series chart |
| Which model consumes the most tokens? | AgentOps Dashboard (Tables) | Model Usage table sorted by tokens |
| What errors happened in the last hour? | AgentOps Dashboard (Logs) | Agent Logs panel filtered by severity |
| Is a specific tool failing consistently? | AgentOps Dashboard (Tables) | Tool Performance table error rate column |
| Why did a specific investigation fail? | Self-Analysis (`reconstruct_agent_interaction`) | Rebuilds the full interaction tree from a trace |
| Is the agent repeating the same mistakes? | Self-Analysis (`detect_agent_anti_patterns`) | Identifies retries, token waste, and other patterns |
| Can the agent fix its own bugs? | Self-Analysis + GitHub tools | OODA loop: detect, diagnose, propose fix |
| Did a deployment cause a regression? | Agent Graph (Sparklines) | Inline trend charts show metric changes over time |
| How do different council modes compare? | Agent Graph (Topology, two time windows) | Compare structure and error rates across modes |
| What is the dominant reasoning strategy? | Agent Graph (Trajectory) | Sankey shows most common paths by trace count |

---

## Integration Points

The three surfaces share data, context, and navigation pathways:

### Shared Data Pipeline

All three surfaces consume data originating from the same OpenTelemetry spans emitted by Google ADK. The `agent_spans_raw` materialized view is the common foundation:

- The **Agent Graph** queries the pre-aggregated `agent_graph_hourly` table (derived from `agent_spans_raw` via SQL views)
- The **AgentOps Dashboard** queries backend APIs that will source from the same BigQuery tables in production
- The **Self-Analysis Tools** query `agent_spans_raw` directly via BigQuery SQL for trace-level detail

### Shared Context (`AgentContext`)

The AgentOps UI provides a React context (`AgentContext`) that shares `project_id` and `service_name` selection across all tabs. Changing the project or service in one tab automatically filters data in all other tabs, including the Agent Graph, Trajectory, and Dashboard views.

### Navigation and Cross-Referencing

| From | To | Mechanism |
|------|----|-----------|
| Agent Graph node | Dashboard model/tool table | Filter by agent name in Dashboard tab |
| Dashboard log entry | Agent Graph trace | Use trace ID to filter Agent Graph time window |
| Agent/Tool Registry (Agents tab, Tools tab) | Agent Graph | Click an agent or tool to filter the graph by that service |
| Self-Analysis tool output | Agent Graph | Use `get_agent_graph` to generate topology SQL; view in Graph tab |
| Agent Graph loop detection | Self-Analysis | Feed detected loop trace IDs into `detect_agent_anti_patterns` |

### URL Deep Linking

All UI state is encoded in URL parameters (`project_id`, `time_range`, `tab`, `selected_node`), enabling direct links to specific views. This allows cross-referencing between surfaces: a link to a specific Agent Graph node can be shared alongside a Dashboard time range, providing full context for incident review.

---

## Getting Started

### Prerequisites

- A GCP project with Cloud Trace API enabled and BigQuery export configured
- The `_AllSpans` table populated in BigQuery (automatic with Cloud Trace export)
- `bq` CLI installed and authenticated

### Step 1: Set Up the Data Pipeline

Run the one-time BigQuery setup script to create the materialized view, SQL views, property graph, and pre-aggregated hourly table:

```bash
./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
```

Then configure a BigQuery Scheduled Query to run every hour for incremental updates. See [Agent Graph -- Setup and Deployment](agent_graph.md#10-setup-and-deployment) for detailed instructions.

### Step 2: Start the AgentOps UI

```bash
cd agent_ops_ui
npm install
npm run dev
```

The UI serves all three human-facing surfaces: Agent Graph (topology + trajectory), AgentOps Dashboard, and the Agent/Tool Registry. Navigate between them using the tab bar.

### Step 3: Configure Self-Analysis Tools

The self-analysis tools require BigQuery access and are available as standard `@adk_tool` functions. They are automatically registered in the agent's tool set. To run a self-analysis:

```
# Via the agent (conversational)
"Analyze your own traces from the last 24 hours and detect any anti-patterns."

# The agent will invoke:
#   list_agent_traces(hours_back=24)
#   detect_agent_anti_patterns(trace_id=<each trace>)
```

For the self-healing loop (GitHub integration), configure `GITHUB_TOKEN` and `GITHUB_REPO` environment variables. See [Online Research & Self-Healing -- Configuration](online_research_and_self_healing.md) for details.

### Step 4: Explore

| Task | Where to Go |
|------|-------------|
| Understand agent architecture | Agent Graph tab, Topology view, 7-day window |
| Monitor fleet health | Dashboard tab, review KPIs and charts |
| Investigate cost spike | Agent Graph tab, Cost Hotspots view mode |
| Find error patterns | Dashboard tab, Agent Logs panel filtered by ERROR severity |
| Detect reasoning loops | Agent Graph tab, Trajectory Flow, check loop warnings |
| Run self-analysis | Ask the agent to analyze its own traces |

---

## Related Documentation

- [Agent Graph](agent_graph.md) -- Full data pipeline, BigQuery schema, visualization architecture, and use cases
- [AgentOps Dashboard Guide](../agent_ops/dashboard.md) -- Dashboard sections, data flow, and testing
- [Online Research & Self-Healing](online_research_and_self_healing.md) -- OODA loop, GitHub tools, and safety guardrails
- [Observability and OpenTelemetry Concepts](observability.md) -- Foundational OTel concepts (traces, logs, metrics, changes)
- [Agent Orchestration](agent_orchestration.md) -- Council of Experts architecture
- [Configuration Reference](../reference/configuration.md) -- Environment variables

---

*Last updated: 2026-02-21*
