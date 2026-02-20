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
4.  **Frontend**: The `InteractiveGraphCanvas` executes these queries (via `mcp_server`) and renders the graph using the Sugiyama layout algorithm.

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

## 4. Frontend Visualization (`InteractiveGraphCanvas`)

Located in `autosre/lib/features/agent_graph/presentation/`.

### 4.1. Layout Algorithm (Sugiyama)
We use the **Sugiyama** algorithm (via `graphview` package) for layered graph layout.
-   **Orientation**: Top-to-Bottom calculation, manually rotated to Left-to-Right for rendering.
-   **Node Sizing**: Critical for preventing overlap. We assign estimated sizes before layout:
    -   **Agents**: 260x150 (Large card with metrics)
    -   **LLMs**: 240x100
    -   **Tools**: 200x80
-   **Root Detection**:
    -   Topological Sort is used to find roots.
    -   **Cyclic Graphs**: If cycles exist (no topological root), we heuristically select the node with the **highest Out-Degree** (e.g., `sre_agent`) as the root to ensure full traversal.

### 4.2. Fallback Mechanism (Grid Layout)
If the Sugiyama algorithm fails (e.g., places all nodes at a single point due to complex cycles or math errors):
-   The error is detected (`all nodes at same position`).
-   We automatically fall back to a **Grid Layout**.
-   Nodes are arranged in a 6-column grid to ensure they are visible and editable.

### 4.3. Rendering Features
-   **Zoom & Pan**: Interactive canvas with `InteractiveViewer`.
-   **Auto-Fit**: On load (with a 500ms delay for rendering), the graph automatically zooms and centers to fit the screen.
-   **Tooltips**: Detailed hover cards showing Token Usage, Latency, and Error rates.
-   **Edge Styling**:
    -   Thickness scales with `call_count` (Traffic).
    -   Color turns Red if `error_count > 0` on that path.

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
