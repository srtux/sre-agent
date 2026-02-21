# Agent Graph Visualization Setup

This document describes the end-to-end setup for the Agent Graph visualization, including BigQuery Materialized Views, Backend API tools, and the Frontend rendering logic.

## 1. Architecture Overview

The Agent Graph visualizes the topology of your AI Agents, Tools, and LLM calls. It allows you to see:
-   **Structure**: How agents call tools and other agents.
-   **Traffic**: High-volume paths (thicker edges).
-   **Performance**: Latency and Token usage per node.
-   **Health**: Error rates per node and edge.

**Data Flow:**
1.  **Ingestion**: Spans are ingested into the `_AllSpans` table in BigQuery (standard OTel export).
2.  **Processing**: A Materialized View (`agent_spans_raw`) and derivative views (`agent_topology_nodes`, `agent_topology_edges`) aggregate raw spans into a graph structure.
3.  **API**: The `get_agent_graph` tool generates the SQL queries to fetch this aggregated data for a specific time range.
4.  **Frontend**: The React-based `TopologyGraph` and `TrajectorySankey` components fetch the parsed queries and render the graph interactively using dagre and React Flow.

---

## 2. BigQuery Setup

The foundational data structures are created by `scripts/setup_agent_graph_bq.sh`.

### 2.1. Materialized View: `agent_spans_raw`
Base layer that filers `_AllSpans` for `sre-agent` service spans and extracts critical attributes:
-   **`logical_node_id`**: A unique ID combining Type and Name (e.g., `Agent::sre_agent`, `Tool::google_search`).
-   **`node_type`**: Agent, Tool, LLM, or Glue.
-   **`session_id`**: Extracted from GenAI attributes for session grouping.
-   **Metrics**: Duration, Input Tokens, Output Tokens, Status Code.

### 2.2. View: `agent_topology_nodes`
Aggregates metrics per `logical_node_id`:
-   **`execution_count`**: Total calls.
-   **`avg_duration_ms`**: Average latency.
-   **`error_count`**: Number of failed executions.
-   **`unique_sessions`**: Number of distinct user sessions touching this node.

### 2.3. View: `agent_topology_edges`
Constructs the connection graph using a **Recursive CTE** to traverse the span tree:
-   **Skipping Glue**: "Glue" spans (internal implementation details) are skipped to connect meaningful nodes directly (e.g., Agent -> Tool).
-   **Metrics**: Edge Weight (call count), Error Count on that path.

### 2.4. Property Graph: `agent_topology_graph`
A BigQuery Property Graph object that formally defines the nodes and edges, enabling GQL (Graph Query Language) in the future.

---

## 3. Backend Tool (`get_agent_graph`)

Located in `sre_agent/tools/analysis/agent_trace/graph.py`.

**Function**:
-   Accepts `project_id`, `dataset_id`, `start_time`, `end_time`.
-   Returns **SQL Queries** (not raw data) for:
    -   `nodes`: Aggregated node metrics for the time window.
    -   `edges`: Aggregated edge metrics for the time window.

This pattern allows the frontend (or an intermediate executor) to run the queries directly against BigQuery, facilitating caching and potentially large result sets.

---

## 4. Frontend Visualization (`agent_graph_ui` React App)

Located in `agent_graph_ui/src/components/`. We have transitioned to a high-performance React application using `@xyflow/react` and `@nivo/sankey`.

### 4.1. Layout Modes & Engine (`TopologyGraph`)
We use the **Dagre** layout engine to perform deterministic, layered directed graph routing, supporting multiple interactive modes:
-   **Horizontal**: Standard Left-to-Right temporal flow. Connections mount to left/right handles.
-   **Vertical**: Top-to-Bottom layout for deep step-by-step pipelines. Connections automatically adapt to top/bottom handles.
-   **Grouped by Type**: Dynamically clusters identical node types (Agent, LLM, Tool) into bounded compound layout boxes.
-   **Node Sizing**: Fixed compact dimensions (`200x64`) ensure tight layouts without excessive negative space, while preventing rendering overlaps and edge crossings.

### 4.2. Interactive Elements
-   **Click-to-Expand**: Parent agent and sub-agent nodes natively feature inline expansion, allowing users to progressively disclose nested sub-agent trees to reduce visual noise.
-   **Node Overlays**: Each node features real-time calculated inline sparklines illustrating latency trends, colored metrics for token usage, and pulsing red shadows for error statuses.
-   **Edge Styling**: Edge thickness dynamically scales with the `callCount` of the path. Back-edges (cyclical retries) are styled natively with marching ants animations.
-   **Sankey Trajectories**: A separate `TrajectorySankey` visualization provides a deep dive into specific trace spans, cleanly routing complex flow paths and identifying pathological retry loops.

### 4.3. Performance Optimizations
-   **Topology Analysis**: A unified `GraphTopologyHelper` processes the raw nodes and edges into a pure DAG, extracting back-edges and recursive tree hierarchies so that custom React Flow logic can render cyclic agent loops purely and cleanly without crashing the layout engine.

---

## 5. Troubleshooting

**Issue: "Only one node visible"**
-   **Cause**: Graph cycle prevented root detection, causing traversal to stop at a leaf.
-   **Fix**: Update to latest `InteractiveGraphCanvas` which uses "Max Out Out-Degree" root fallback.

**Issue: "Nodes Overlapping"**
-   **Cause**: Sugiyama algorithm treated nodes as 0x0 points.
-   **Fix**: Ensure `node.size` is explicitly set in `_sugiyamaLayout` based on node type.

**Issue: "Green Dot / Empty Screen on Load"**
-   **Cause**: Auto-Fit triggered before widgets were laid out.
-   **Fix**: Increased Auto-Fit delay to 500ms.
