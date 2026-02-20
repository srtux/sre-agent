# AutoSRE Agent Graph Feature - Complete Architecture Exploration

## Overview
The Agent Graph feature is a multi-trace visualization system that aggregates agent execution flows across BigQuery traces and provides an interactive UI for exploration. It uses a 3-layer architecture: BigQuery for data aggregation, Dart/Riverpod for state management, and Flutter for visualization.

---

## 1. BigQuery Setup (`scripts/setup_agent_graph_bq.sh`)

### Purpose
Automates creation of BigQuery objects needed for agent topology visualization. Creates materialized views, property graphs, and pre-aggregated hourly tables.

### Key Components

#### 1.1 Materialized View: `agent_spans_raw`
- **Source**: `{TRACE_DATASET}._AllSpans` table with service.name = 'sre-agent'
- **Clustering**: `trace_id`, `session_id`, `node_label`
- **Refresh**: 5-minute interval with 30-minute max staleness
- **Key Columns**:
  - `span_id`, `parent_id`, `trace_id`, `session_id`
  - `duration_ms` (duration_nano / 1000000.0)
  - `status_code`: UNSET (0), OK (1), ERROR (2)
  - `input_tokens`, `output_tokens` (from attributes)
  - `node_type`: Agent, Tool, LLM, or Glue (based on gen_ai.operation.name)
  - `node_label`: Name from gen_ai.agent.name / gen_ai.tool.name / gen_ai.response.model
  - `logical_node_id`: Computed as "{node_type}::{node_label}" for topology uniqueness

#### 1.2 Topological Nodes View: `agent_topology_nodes`
- **Purpose**: Pre-aggregates metrics per component per trace
- **Grouping**: trace_id, session_id, logical_node_id
- **Metrics**:
  - `execution_count`, `total_duration_ms`, `total_input_tokens`, `total_output_tokens`
  - `error_count`, `start_time`
- **Filter**: Excludes 'Glue' node_type

#### 1.3 Topological Edges View: `agent_topology_edges`
- **Magic Bridge**: Uses recursive CTE to skip 'Glue' spans
- **Algorithm**:
  - Base case: Root spans or spans without parent in dataset
  - Recursive step: If parent is non-Glue, parent becomes ancestor. If parent is Glue, inherit ancestor from higher up.
- **Edges only created** when:
  - Both source and destination are non-Glue
  - ancestor_logical_id != logical_node_id (avoid self-loops)
- **Aggregation**: count, error_count, tokens, status_code per edge

#### 1.4 Property Graph: `agent_topology_graph`
- **Node Table**: agent_topology_nodes with KEY (trace_id, logical_node_id)
- **Edge Table**: agent_topology_edges with SOURCE/DESTINATION references
- **Label**: Component (nodes), Interaction (edges)

#### 1.5 Pre-aggregated Table: `agent_graph_hourly`
- **Purpose**: Sub-second UI queries without expensive GRAPH_TABLE recursion
- **Partitioning**: DATE(time_bucket)
- **Clustering**: source_id, target_id
- **Key Columns**:
  - **Edge metrics**: call_count, error_count, edge_tokens, input_tokens, output_tokens, total_cost, sum_duration_ms, max_p95_duration_ms, unique_sessions, sample_error
  - **Target-node metrics**: node_total_tokens, node_input_tokens, node_output_tokens, node_has_error, node_sum_duration_ms, node_max_p95_duration_ms, node_error_count, node_call_count, node_total_cost, node_description
  - **Source-node subcall counts**: tool_call_count, llm_call_count
  - **Session tracking**: session_ids (ARRAY<STRING>)

#### 1.6 Backfill and Scheduled Updates
- **Backfill**: Last 30 days (720 hours) inserted into `agent_graph_hourly`
- **Uses GRAPH_TABLE**: Matches (src:Span)-[:ParentOf]->{1,5}(dst:Span) with filters
- **Scheduled Query**: Template provided for hourly incremental updates
- **Cost Calculation**: Per-token pricing varies by model (flash vs pro models)

---

## 2. Python Backend (`sre_agent/tools/analysis/agent_trace/graph.py`)

### Tool: `get_agent_graph`

**Purpose**: Retrieves aggregated agent topology graph from BigQuery.

**Parameters**:
- `project_id`: GCP project (optional, defaults to fallback)
- `dataset_id`: BQ dataset ID (defaults to 'agent_graph')
- `start_time`, `end_time`: ISO 8601 timestamps (defaults to last 24h)
- `limit`: Max nodes to return (default 200, prevents massive graphs)

**Implementation**:
- Returns SQL queries (not executed data) following the pattern of other analyzer tools
- Two queries:
  1. **Nodes Query**: Selects distinct logical_node_id, aggregates execution_count, avg_duration_ms, total_tokens, error_count, unique_sessions
  2. **Edges Query**: Selects source_node_id → destination_node_id, aggregates call_count, avg_duration_ms, total_tokens, error_count
- Filters by time window using parameterized timestamps
- Groups edges by source/target, filters having call_count > 0

**Response Structure**:
```json
{
  "status": "success",
  "result": {
    "analysis_type": "agent_graph",
    "queries": [
      {"name": "nodes", "sql": "..."},
      {"name": "edges", "sql": "..."}
    ],
    "description": "Agent Topology Graph query for ...",
    "next_steps": ["Execute queries", "Visualize with Agent Graph component"]
  },
  "metadata": {"project_id": "...", "dataset": "agent_graph"}
}
```

---

## 3. Flutter Domain (`autosre/lib/features/agent_graph/domain/`)

### 3.1 Models (`models.dart`) - Freezed + JSON
All frozen with `extra="forbid"` pattern.

#### `MultiTraceNode`
```dart
class MultiTraceNode {
  final String id;                    // Unique identifier
  final String type;                  // 'Agent', 'Tool', 'LLM', 'SubAgent'
  final String? label;                // Display name
  final String? description;          // Optional description
  final int executionCount;           // Times called (default 0)
  final int totalTokens;              // Sum of input + output tokens
  final int inputTokens;              // Sum of input tokens
  final int outputTokens;             // Sum of output tokens
  final int errorCount;               // Number of errors
  final bool hasError;                // Quick flag for error presence
  final double avgDurationMs;         // Average latency
  final double p95DurationMs;         // P95 latency
  final double errorRatePct;          // Error rate percentage
  final double? totalCost;            // Estimated cost (optional)
  final int toolCallCount;            // Sub-calls to tools
  final int llmCallCount;             // Sub-calls to LLMs
  final int uniqueSessions;           // Distinct session IDs
  final bool isRoot;                  // No incoming edges
  final bool isLeaf;                  // No outgoing edges
  final bool isUserEntryPoint;        // Root agent (user-facing entry)
}
```

#### `MultiTraceEdge`
```dart
class MultiTraceEdge {
  final String sourceId;              // Source node ID
  final String targetId;              // Target node ID
  final String sourceType;            // Source node type
  final String targetType;            // Target node type
  final int callCount;                // Call count
  final int errorCount;               // Error count
  final double errorRatePct;          // Error rate
  final String? sampleError;          // Sample error message
  final int edgeTokens;               // Total tokens (total_tokens field)
  final int inputTokens;              // Input tokens
  final int outputTokens;             // Output tokens
  final int avgTokensPerCall;         // Avg tokens per call
  final double avgDurationMs;         // Average latency
  final double p95DurationMs;         // P95 latency
  final int uniqueSessions;           // Unique sessions
  final double? totalCost;            // Estimated cost
}
```

#### `MultiTraceGraphPayload`
```dart
class MultiTraceGraphPayload {
  final List<MultiTraceNode> nodes;   // Default []
  final List<MultiTraceEdge> edges;   // Default []
}
```

#### `SelectedGraphElement` - Sealed Union Type
```dart
sealed class SelectedGraphElement {
  const factory SelectedGraphElement.node(MultiTraceNode node) = SelectedNode;
  const factory SelectedGraphElement.edge(MultiTraceEdge edge) = SelectedEdge;
}
```

### 3.2 Graph View Mode (`graph_view_mode.dart`)
```dart
enum GraphViewMode {
  standard,         // Color by node type
  tokenHeatmap,     // Color by token consumption
  errorHeatmap,     // Color by error rate
}
```

---

## 4. Flutter Data Layer (`autosre/lib/features/agent_graph/data/agent_graph_repository.dart`)

### 4.1 Repository Pattern with Riverpod
- **Default Dataset**: `kDefaultDataset = 'summitt-gcp.agent_graph'`
- **Precomputed Min Hours**: `kPrecomputedMinHours = 1` (use hourly table for >= 1 hour)

### 4.2 SQL Builders

#### `buildPrecomputedGraphSql()`
- **Purpose**: Sub-second queries using pre-aggregated hourly table
- **Query Structure**:
  1. **HourlyData CTE**: Filters by time_bucket >= CURRENT_TIMESTAMP() - INTERVAL
  2. **AggregatedEdges CTE**: Groups by source_id, target_id, calculates metrics
  3. **NodeSubcallCounts CTE**: Aggregates tool_call_count, llm_call_count by source_id
  4. **BaseNodes CTE**: Union of target nodes (destinations) and source nodes (origins)
  5. **AggregatedNodes CTE**: Enriches with is_root, is_leaf, is_user_entry_point flags
  6. **Final SELECT**: Returns JSON_STRING with nodes and edges arrays

- **Flags**:
  - `is_root`: NOT IN (SELECT target_id FROM AggregatedEdges)
  - `is_leaf`: NOT IN (SELECT source_id FROM AggregatedEdges)
  - `is_user_entry_point`: is_root AND type = 'Agent'

- **Edge Limit**: Optional LIMIT clause if sampleLimit provided

#### `buildGraphSql()`
- **Purpose**: Live topology query for sub-hour ranges
- **Query Structure**:
  1. FilteredNodes: Aggregates agent_topology_nodes by logical_node_id
  2. FilteredEdges: Aggregates agent_topology_edges by source/destination
  3. Final SELECT: Returns JSON_STRING with computed flags

### 4.3 Data Fetching

#### `fetchGraph()`
- **Logic**:
  - timeRangeHours >= 1 → uses `buildPrecomputedGraphSql()`
  - timeRangeHours < 1 → uses `buildGraphSql()` (live fallback)
- **Endpoint**: `/api/tools/bigquery/query` (POST with sql + project_id)
- **Response Parsing**: Extracts 'flutter_graph_payload' JSON column, jsonDecode, creates MultiTraceGraphPayload

#### `fetchNodeDetails()` and `fetchEdgeDetails()`
- **Purpose**: Load extended details (percentiles, top errors) for selected element
- **Node Query**: Latency percentiles (P50, P90, P99, max) from agent_spans_raw
- **Edge Query**: Latency percentiles from agent_topology_edges + top errors

---

## 5. Flutter Application Layer (`autosre/lib/features/agent_graph/application/agent_graph_notifier.dart`)

### 5.1 Riverpod Notifier Pattern

#### `AgentGraphState` (Freezed)
```dart
class AgentGraphState {
  final MultiTraceGraphPayload? payload;
  final bool isLoading;
  final String? error;
  final SelectedGraphElement? selectedElement;
  final String dataset;               // Current dataset (default kDefaultDataset)
  final int timeRangeHours;           // Current time range (default 6)
  final int? sampleLimit;             // Optional edge sampling limit
}
```

#### `AgentGraphNotifier` - Extends StateNotifier
- **build()**: Initializes with AgentGraphRepository, empty state
- **fetchGraph()**: Fetches data, sets isLoading, updates state
  - Parameters: dataset, timeRangeHours, sampleLimit, projectId
  - Clears selectedElement on new fetch
  - Handles DioException → sets error state
- **selectNode()**: Sets selectedElement to SelectedNode
- **selectEdge()**: Sets selectedElement to SelectedEdge
- **clearSelection()**: Clears selectedElement
- **updateDataset()**, **updateTimeRange()**, **updateSampleLimit()**: Utility updates

### 5.2 Extended Detail Providers

#### `fetchExtendedNodeDetails`
- **Parameters**: nodeId (String)
- **Returns**: Future<Map<String, dynamic>>
- **Calls**: `repo.fetchNodeDetails()` with current dataset + timeRangeHours

#### `fetchExtendedEdgeDetails`
- **Parameters**: sourceId, targetId (Strings)
- **Returns**: Future<Map<String, dynamic>>
- **Calls**: `repo.fetchEdgeDetails()` with current dataset + timeRangeHours

---

## 6. Flutter Presentation Layer

### 6.1 Main Page (`multi_trace_graph_page.dart`)

**Layout**:
```
┌────────────────────────────────────────────────────────┐
│ [Back] [Icon] [Title] [TimePicker] [Dataset] [Run]    │
├────────────────────────────────────────────────────────┤
│  Canvas Area               │ Details Panel (if selected)│
└────────────────────────────────────────────────────────┘
```

**Features**:
- Time range picker (default 6 hours)
- Dataset input field (default kDefaultDataset)
- Run button with loading indicator
- Conditional detail panel (shown when element selected)
- States: Loading, Error (with retry), Empty, Rendered

**Key Methods**:
- `_runQuery()`: Calls agentGraphProvider.notifier.fetchGraph()
- `_buildCanvasArea()`: Routes to appropriate canvas based on state
- `_buildEmptyState()`: Guides user to set time range and run

### 6.2 Canvas Widget (`multi_trace_graph_canvas.dart`)

**Purpose**: Visualizes graph using graphview package (Sugiyama/Force-directed layouts).

**Features**:
1. **Graph Building**:
   - Creates Graph object with nodes and edges
   - Edge thickness: log-scale by call count (1-6px)
   - Edge color: Based on error rate (white/transparent if OK, orange/red if errors)

2. **Visual Mapping**:
   - Node colors: Agent (teal), Tool (warning), LLM (purple), Sub-agent (cyan)
   - Node icons: psychology (agent), build (tool), auto_awesome (LLM)
   - Edge thickness proportional to call count

3. **Layout Options**:
   - Sugiyama (hierarchical, left-to-right)
   - Fruchterman-Reingold (force-directed)

4. **View Modes**:
   - Graph view (graphview widget with zoom controls)
   - Edge list view (ListView of edges sorted by call count)

5. **Interactions**:
   - Node click: Calls onNodeSelected, highlights with shadow
   - Pan/zoom: Standard InteractiveViewer
   - Zoom controls: +/-, Reset view

6. **Toolbar**:
   - Node count and edge count display
   - View toggle (Graph/List)
   - Layout toggle (Hierarchical/Force)

7. **Legend**:
   - Node type icons and colors
   - Edge line colors for OK vs Errors

**Caching**:
- Hash-based caching to avoid re-building graph
- Invalidates on payload change or layout toggle

### 6.3 Interactive Graph Canvas (`interactive_graph_canvas.dart`)

**Purpose**: Next-generation canvas using fl_nodes library with drag-and-drop, collapsing, and advanced layout.

**Key Features**:

1. **Initial State**:
   - Auto-collapse if >25 nodes (depth-based, keeps depth 0-1 open)
   - BFS to assign node depth
   - Collapse Agent/SubAgent nodes at depth >= 1

2. **Gradual Disclosure**:
   - Collapsible nodes (toggle method available)
   - Filtered visibility based on collapsed state
   - Smooth reveal/hide on interaction

3. **Layout Algorithm** (Sugiyama):
   - Runs on visible nodes only
   - Node sizes estimated by type (Agent: 260x150, LLM: 240x100, Tool: 200x80)
   - Left-to-right orientation
   - Centering to (0,0) for consistent viewport focus

4. **Back-edge Detection**:
   - Identifies cycles using depth map
   - Back-edges rendered with dashed lines
   - Separate port ('back_out') for back-edges

5. **Custom Node Rendering**:
   - User Entry Point: Large blue circle with person icon
   - Agent: 280px wide, includes metrics, execution count badge
   - LLM: 240px wide, compact with token display
   - Tool: 200px wide, minimal metrics
   - Generic (heatmap mode): Tool node with forced color

6. **Metrics Badges**:
   - Error rate (red if > 0)
   - Latency (timer icon)
   - Tokens (K/M formatting)
   - Cost (if available)
   - Subcall distribution (tool + LLM calls for agents)

7. **Controls** (top-right):
   - Auto Layout: Re-run Sugiyama
   - Fit to Screen: Focus all nodes, zoom to 0.05

8. **Port System**:
   - 'in' port: Left side (input)
   - 'out' port: Right side (forward edges, colored)
   - 'back_out' port: Right side (back-edges, dashed)

### 6.4 Details Panel (`agent_graph_details_panel.dart`)

**Purpose**: Right sidebar showing full metadata for selected node or edge.

**Layout**:
```
┌──────────────────────────────────────┐
│ [Icon] [Title]              [Close] │
├──────────────────────────────────────┤
│ Type Card                            │
│ Description (if available)           │
│ Total Tokens / Estimated Cost        │
│ Token Breakdown (Input/Output)       │
│ Latency Metrics (Avg, P95)           │
│ Error Rate (if errors present)       │
│ Token Percentage of total            │
│ Sub-call Distribution (for agents)   │
│ Badges (Root, Leaf, Has Errors, ...) │
│ "Explore Traces" Button              │
│ ─────────────────────────────────────│
│ Extended Latency (P50, P90, P99, Max)│
│ Recent Errors (top 3)                │
└──────────────────────────────────────┘
```

**Node Detail**:
- Type, description, token breakdown
- Latency metrics (avg, P95)
- Error rate and count
- Token percentage of graph
- Subcall distribution (tool/LLM calls)
- Badges: Root, Leaf, Has Errors, User Entry
- "Explore Traces" button filters by node name

**Edge Detail**:
- Call count, unique sessions
- Estimated cost
- Performance section: avg/P95 duration, avg tokens/call
- Token breakdown (total, input, output)
- Error section: error count, rate, sample error
- "Explore Traces" button filters by source + target

**Extended Details** (Riverpod providers):
- Loaded asynchronously from fetchExtendedNodeDetails/fetchExtendedEdgeDetails
- Shows loading spinner while fetching
- Displays latency percentiles and recent errors

---

## 7. Testing Infrastructure

### 7.1 Data Layer Test (`agent_graph_repository_test.dart`)

**Mock Setup**: MockDio with configurable response and error behavior

**Test Coverage**:
1. **SQL Builder Tests**:
   - Precomputed query includes agent_graph_hourly
   - Live topology query includes agent_topology_nodes
   - Time range substitution verified
   - Edge limit clause only when sampleLimit provided

2. **Query Routing**:
   - timeRangeHours >= 1 → precomputed path
   - timeRangeHours < 1 → live topology path

3. **Parsing Tests**:
   - Correctly extracts 'flutter_graph_payload' column
   - Deserializes to MultiTraceGraphPayload
   - Maps JSON fields to Dart types

4. **Error Handling**:
   - DioException propagates correctly
   - Empty rows return empty payload

### 7.2 Presentation Tests (`multi_trace_graph_canvas_test.dart`)

**Test Coverage**:
1. **Empty State**: Shows icon + message when no nodes
2. **Rendering**: Header text "Multi-Trace Agent Graph" appears
3. **Toolbar**: Shows node count and edge count
4. **Legend**: Displays Agent, Tool, LLM labels
5. **Interactions**: onNodeSelected callback fires on tap
6. **Layout Buttons**: Hierarchical and Force buttons present

---

## 8. Key Architecture Decisions

### 8.1 Two-Path Query Strategy
- **Precomputed Path** (>= 1 hour): Sub-second queries from agent_graph_hourly
- **Live Path** (< 1 hour): Direct GRAPH_TABLE traversal (fallback, slower)
- **Rationale**: Large time ranges need fast aggregation; sub-hour ranges rare in UI

### 8.2 Logical Node IDs
- **Format**: "{node_type}::{node_label}"
- **Purpose**: Topology deduplication across traces and sessions
- **Benefit**: Allows merging of multi-trace node behaviors

### 8.3 Recursive CTE for Glue Skipping
- **Problem**: Raw span tree has 'Glue' nodes that pollute edges
- **Solution**: Recursive CTE in agent_topology_edges view
- **Result**: Clean agent → tool, agent → LLM, tool → LLM edges

### 8.4 Freezed + JSON Code Generation
- **All Domain Models**: Immutable, with fromJson/toJson
- **Riverpod Integration**: Seamless state updates
- **Type Safety**: No implicit Any

### 8.5 Riverpod for State Management
- **agentGraphProvider**: Main notifier with AgentGraphState
- **agentGraphRepository**: Singleton provider for repo
- **fetchExtendedNodeDetails / fetchExtendedEdgeDetails**: Separate providers for async loading

### 8.6 Graceful Degradation in Canvas
- **Multi-canvas support**: Both graphview (traditional) and fl_nodes (advanced)
- **Layout modes**: Sugiyama (default for clarity) and force-directed (for complex graphs)
- **Collapse mechanism**: Auto-reduces >25 node graphs

---

## 9. Integration Points

### 9.1 Backend → Frontend Data Flow
1. Python tool `get_agent_graph` returns SQL queries
2. Frontend executes SQL via `/api/tools/bigquery/query` endpoint
3. BigQuery returns JSON in flutter_graph_payload column
4. Flutter deserializes to MultiTraceGraphPayload
5. Canvas renders nodes + edges, interactive detail panel on selection

### 9.2 Time Range & Dataset Persistence
- **AgentGraphState** stores current dataset and timeRangeHours
- **Extended detail providers** use state values for context
- **Time picker** updates state, triggers new fetch

### 9.3 Trace Explorer Integration
- **"Explore Traces" buttons** call ExplorerQueryService.queryTraceFilter()
- **Filter format**: text:"{nodeId}" or text:"{sourceId}" text:"{targetId}"
- **Navigation**: Closes detail panel, jumps to trace explorer

---

## 10. Performance Considerations

### 10.1 BigQuery Optimization
- **Materialized Views**: agent_spans_raw clusters by trace_id, session_id, node_label
- **Hourly Pre-aggregation**: Avoids expensive GRAPH_TABLE queries
- **Incremental Updates**: Scheduled query only processes last 2 hours
- **Partition Pruning**: agent_graph_hourly partitioned by DATE(time_bucket)

### 10.2 UI Performance
- **Graph Caching**: Hash-based invalidation, avoids re-layout
- **Collapse Optimization**: Only visible nodes rendered
- **Lazy Loading**: Extended details load on-demand
- **Zoom Out Default**: 0.05 scale provides bird's-eye view initially

### 10.3 Token Cost Estimation
- **Per-model pricing**: flash (0.15/0.6 per M input/output), pro (1.25/10 per M)
- **Aggregated**: Summed across all edges + nodes
- **Display**: "$X.XX" formatting, rounded to 4 decimals

---

## 11. File Structure Summary

```
BigQuery Setup:
  scripts/setup_agent_graph_bq.sh

Backend:
  sre_agent/tools/analysis/agent_trace/graph.py
  
Flutter Domain:
  autosre/lib/features/agent_graph/domain/
    - models.dart (MultiTraceNode, MultiTraceEdge, MultiTraceGraphPayload, SelectedGraphElement)
    - graph_view_mode.dart

Flutter Data:
  autosre/lib/features/agent_graph/data/
    - agent_graph_repository.dart (SQL builders, fetchGraph, extended details)

Flutter Application:
  autosre/lib/features/agent_graph/application/
    - agent_graph_notifier.dart (Riverpod state, extended detail providers)

Flutter Presentation:
  autosre/lib/features/agent_graph/presentation/
    - multi_trace_graph_page.dart (Main page with toolbar, time picker, canvas/panel layout)
    - multi_trace_graph_canvas.dart (graphview-based canvas with Sugiyama/Force layout)
    - interactive_graph_canvas.dart (fl_nodes-based canvas with collapse/drag/advanced layout)
    - agent_graph_details_panel.dart (Right sidebar with node/edge metadata)

Tests:
  autosre/test/features/agent_graph/
    - data/agent_graph_repository_test.dart
    - presentation/multi_trace_graph_canvas_test.dart
    - (+ other feature tests for notifier, models, etc.)
```

---

## 12. Key Constants

- **kDefaultDataset**: 'summitt-gcp.agent_graph'
- **kPrecomputedMinHours**: 1 (use agent_graph_hourly if timeRangeHours >= 1)
- **Zoom**: Default 0.05 (20x out for overview)
- **Auto-collapse threshold**: 25 nodes
- **Max node limit**: 200 (in Python tool)
- **Extended detail fetch**: On-demand when detail panel opens
- **Latency percentiles**: P50, P90, P99, Max
- **Error samples**: Top 3 from recent data

---

## 13. Outstanding Design Notes

1. **Python tool currently returns SQL**: Not executed data. User/agent must call mcp_execute_sql. Could be optimized to execute directly if needed.

2. **Two canvas implementations**: graphview is traditional/stable; fl_nodes is newer with more features (drag, collapse). Both available, can coexist.

3. **Collapse state**: Stored in _collapsedNodeIds local state. Could be persisted to provider if needed.

4. **Cost calculation**: Uses model name pattern matching (flash, pro, etc.). Assumes consistent token pricing per model within time window.

5. **Sub-hour queries**: Live topology query is fallback. UI currently doesn't expose sub-hour presets, so this path is rarely exercised.

6. **Back-edge detection**: Assumes DAG-like traversal. Cycles handled by checking tgtDepth <= srcDepth.

---

This comprehensive document captures the full architecture, data flow, UI/UX patterns, and implementation details of the AutoSRE Agent Graph feature as of the latest codebase exploration.
