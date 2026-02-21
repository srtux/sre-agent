# AutoSRE Flutter Frontend Architecture - Comprehensive Overview

## 1. GENUI COMPONENT CATALOG (catalog.dart)

### Components Available
The `CatalogRegistry` in `catalog.dart` defines 12 custom SRE components that render tool/agent data:

#### Data Visualization Components:
1. **x-sre-trace-waterfall** - Distributed trace visualization
   - Input: Trace (traceId, spans with timing)
   - Shows: Span waterfall with parent-child relationships
   - Height: Auto, min 200px

2. **x-sre-metric-chart** - Single metric time-series
   - Input: MetricSeries (metricName, points, labels)
   - Shows: Line chart with anomaly detection
   - Height: 380px

3. **x-sre-log-entries-viewer** - Searchable log viewer
   - Input: LogEntriesData (entries with severity)
   - Shows: Filterable/expandable logs with ANSI parsing
   - Height: 500px

4. **x-sre-log-pattern-viewer** - Log pattern aggregation
   - Input: List<LogPattern> (template, count, severityCounts)
   - Shows: Top patterns with frequency counts
   - Height: 450px

5. **x-sre-metric-chart** - Metric correlation chart
   - Input: MetricSeries with points
   - Shows: XY plot with trend lines
   - Height: 380px

#### Canvas Widgets (Advanced Visualizations):

6. **x-sre-agent-activity** - Real-time agent workflow visualization
   - Input: AgentActivityData (nodes: coordinator/sub_agent/tool/data_source, status)
   - Shows: Animated node graph with pulse effects and phase indicator
   - Height: 450px
   - Features: Active node highlighting, completed steps tracking

7. **x-sre-service-topology** - Service dependency graph
   - Input: ServiceTopologyData (services, connections, affected_path)
   - Shows: Interactive graph layout, health indicators, latency/error rates
   - Height: 500px
   - Features: Incident source highlighting, affected path visualization

8. **x-sre-incident-timeline** - Incident progression timeline
   - Input: IncidentTimelineData (events with type, severity, timestamp)
   - Shows: Vertical timeline with color-coded event types
   - Height: 420px
   - Event types: alert, deployment, config_change, scaling, incident, recovery, agent_action

9. **x-sre-metrics-dashboard** - Multi-metric golden signals dashboard
   - Input: MetricsDashboardData (metrics with status, current/previous values)
   - Shows: Grid of metric cards with status indicators
   - Height: 400px
   - Status colors: critical (red), warning (orange), normal (green)

10. **x-sre-agent-trace** - Agent execution timeline
    - Input: AgentTraceData (nodes with kind, operation, timing, token counts)
    - Shows: Waterfall timeline color-coded by operation kind
    - Height: 550px
    - Operation kinds: agent_invocation (teal), llm_call (purple), tool_execution (warning), sub_agent_delegation (cyan)

11. **x-sre-agent-graph** - Agent call relationship graph
    - Input: AgentGraphData (nodes, edges)
    - Shows: Directed graph of agent interactions
    - Height: 500px

12. **x-sre-tool-log** - Tool execution status indicator
    - Input: ToolLog (toolName, args, status, result, duration)
    - Shows: Inline execution status (running/completed/error)

#### Data Format Unwrapping
All components use `_unwrapComponentData()` to handle nested structures:
1. Direct key match: `{"x-sre-foo": {...}}`
2. Component wrapper: `{"component": {"x-sre-foo": {...}}}`
3. Root type match: `{"type": "x-sre-foo", ...}`
4. Fallback for tool-logs: fields like `tool_name`, `args`, `status`

---

## 2. DASHBOARD ARCHITECTURE

### Dashboard Panel (`widgets/dashboard/dashboard_panel.dart`)
Central investigation dashboard with tabbed interface:
- **Header**: Shows total item count, close button
- **Tab Bar**: 5 categorized tabs with item counts
- **Content Area**: Renders active tab's panel

### Dashboard Data Categories (`services/dashboard_state.dart`)

Enum `DashboardDataType`:
- `traces` - Distributed traces
- `logs` - Log entries and patterns
- `metrics` - Metric series and dashboards
- `alerts` - Incident timelines and active alerts
- `remediation` - Remediation plans

### Dashboard State Management
`DashboardState` (ChangeNotifier):
- Maintains list of `DashboardItem` objects
- Each item has: id, type, toolName, timestamp, rawData, and typed data fields
- Methods:
  - `addTrace()`, `addLogEntries()`, `addLogPatterns()`
  - `addMetricSeries()`, `addMetricsDashboard()`
  - `addAlerts()`, `addRemediation()`
  - `addFromEvent()` - Main entry point from backend
  - `toggleDashboard()`, `openDashboard()`, `closeDashboard()`
  - `setActiveTab()`, `itemsOfType()`, `typeCounts`

### Individual Dashboard Panels

#### 1. LiveTracePanel (`dashboard/live_trace_panel.dart`)
- Lists collected traces in expandable cards
- Shows: traceId (truncated), span count, total duration, tool name
- Expandable: Shows full TraceWaterfall on tap
- Feature: "Open in Cloud Trace" button links to Google Cloud Console

#### 2. LiveLogsExplorer (`dashboard/live_logs_explorer.dart`)
- Aggregates log entries from all tool calls
- Search box: Full-text search across log entries
- Severity chips: Filter by severity level (ALL, ERROR, WARNING, INFO, DEBUG)
- Pattern summary: Shows top 3 most common log patterns above the list
- Log entries: Expandable rows with JSON payload viewer

#### 3. LiveMetricsPanel (`dashboard/live_metrics_panel.dart`)
- Responsive grid of metric charts
- Supports two types:
  - Single metric series: MetricCorrelationChart
  - Dashboard metrics: MetricsDashboardCanvas
- Header shows metric name and point count

#### 4. LiveAlertsPanel (`dashboard/live_alerts_panel.dart`)
- Displays incident timeline with active alerts
- Header with summary stats: Critical, High, Warning counts
- Uses AlertsDashboardCanvas for rendering
- Supports single-item full expand or multi-item list view

#### 5. LiveRemediationPanel (`dashboard/live_remediation_panel.dart`)
- Lists remediation plans from tool calls
- Shows: Issue title, risk level badge (high/medium/low)
- Expandable: Shows RemediationPlanWidget with steps

---

## 3. DATA FLOW ARCHITECTURE

### Backend → Frontend Flow

```
Backend (Python Agent)
    ↓
ADKContentGenerator (adk_content_generator.dart)
    ├→ Multiple StreamControllers:
    │  ├── a2uiController (A2UI messages for chat)
    │  ├── textController (Text responses)
    │  ├── dashboardController ← DASHBOARD DATA
    │  ├── toolCallController (Inline tool status)
    │  ├── traceInfoController (Cloud Trace links)
    │  └── sessionController (Session IDs)
    │
    ↓
ConversationPage (pages/conversation_page.dart)
    ├→ Stream subscriptions in initState():
    │  ├── _dashboardSubscription → _dashboardState.addFromEvent()
    │  ├── _toolCallSubscription → Update _toolCallState
    │  ├── _sessionSubscription → Update SessionService
    │  └── _traceInfoSubscription → Store _currentTraceId
    │
    ↓
DashboardState (services/dashboard_state.dart)
    ├→ Stores all items in _items list
    ├→ notifyListeners() triggers rebuilds
    │
    ↓
DashboardPanel (widgets/dashboard/dashboard_panel.dart)
    ├→ ListenableBuilder watches DashboardState
    ├→ Renders active tab's panel based on state.activeTab
    │
    ↓
Individual Panels (LiveLogsExplorer, LiveMetricsPanel, etc.)
    ├→ Build items from state.itemsOfType()
    ├→ Render catalog widgets through CatalogRegistry
    │
    ↓
Canvas Widgets (agent_activity_canvas.dart, etc.)
    └→ Render final visualization
```

### Dashboard Event Format (from Backend)
```json
{
  "category": "traces|logs|metrics|alerts|remediation",
  "widget_type": "x-sre-trace-waterfall|x-sre-log-entries-viewer|...",
  "tool_name": "get_logs|list_metrics|...",
  "data": {
    // Varies by widget_type
  }
}
```

---

## 4. KEY MODELS (models/adk_schema.dart)

### Trace Models
- `SpanInfo`: spanId, traceId, name, startTime, endTime, attributes, status, parentSpanId, duration
- `Trace`: traceId, List<SpanInfo>

### Metric Models
- `MetricPoint`: timestamp, value, isAnomaly
- `MetricSeries`: metricName, List<MetricPoint>, labels
- `DashboardMetric`: id, name, unit, currentValue, previousValue, threshold, status, anomalyDescription
- `MetricDataPoint`: timestamp, value
- `MetricsDashboardData`: metrics, lastUpdated, status

### Log Models
- `LogEntry`: insertId, timestamp, severity, payload, resourceLabels, resourceType, traceId, spanId, httpRequest, isJsonPayload, payloadPreview
- `LogEntriesData`: entries, filter, projectId, nextPageToken
- `LogPattern`: template, count, severityCounts

### Incident/Alert Models
- `TimelineEvent`: id, timestamp, type, title, description, severity, metadata, isCorrelatedToIncident, incidentId
- `IncidentTimelineData`: title, serviceName, status, events, rootCause, timeToDetect, timeToMitigate, lastUpdated

### Agent/Trace Models
- `AgentTraceNode`: spanId, parentSpanId, name, kind, operation, startOffsetMs, durationMs, depth, inputTokens, outputTokens, modelUsed, toolName, agentName, hasError
- `AgentTraceData`: traceId, rootAgentName, nodes, totalInputTokens, totalOutputTokens, totalDurationMs, llmCallCount, toolCallCount, uniqueAgents, uniqueTools, antiPatterns

### Remediation Models
- `RemediationStep`: command, description
- `RemediationPlan`: issue, risk (low|medium|high), List<RemediationStep>

### Tool Execution Model
- `ToolLog`: toolName, args, status (running|completed|error), result, timestamp, duration

---

## 5. CONVERSATION PAGE INTEGRATION

### Main Layout (ConversationPage)
- **Chat Area** (60% width by default, resizable)
  - AppBar with project selector, help, settings
  - Message list (ChatMessage items)
  - Input area with unified prompt input
  - Hero empty state on first load

- **Dashboard Panel** (40% width, resizable)
  - Slidable from right edge
  - Tabbed interface for categories
  - Shows collected data in real-time

### Data Streams in ConversationPage
```dart
_dashboardSubscription = contentGenerator.dashboardStream.listen((event) {
  _dashboardState.addFromEvent(event);
});

_toolCallSubscription = contentGenerator.toolCallStream.listen((event) {
  // Update inline tool call status in chat
});

_traceInfoSubscription = contentGenerator.traceInfoStream.listen((event) {
  _currentTraceId = event['trace_id'];
  _currentTraceUrl = event['trace_url'];
});
```

### Navigation Between Dashboard Tabs
- Click tab header to switch categories
- Badge shows count of items per category
- Empty state shown if no items in tab

---

## 6. CANVAS WIDGETS - ADVANCED VISUALIZATIONS

### AgentActivityCanvas
- Models: `AgentNode` (id, name, type, status, connections), `AgentActivityData`
- Animations: Pulse (node activity), Flow (connection animation), Entrance
- Shows: Agent workflow with status indicators and phase message

### ServiceTopologyCanvas
- Models: `ServiceNode` (health, latency, errorRate, requestsPerSec), `ServiceTopologyData`
- Layout: Force-directed graph positioning
- Features: Health color coding, incident source highlighting, affected path visualization

### IncidentTimelineCanvas
- Shows: Vertical timeline with color-coded events
- Event types: alert, deployment, config_change, scaling, incident, recovery, agent_action
- Features: Hover state, selected event detail panel, statistics summary

### MetricsDashboardCanvas
- Displays: Grid of metric cards with status indicators
- Status colors: Critical (red), Warning (orange), Normal (green)
- Animation: Entrance animation with pulse effects

### AlertsDashboardCanvas
- List-based view of active alerts
- Severity-based sorting (critical → low)
- Event cards with timestamp, title, metadata
- "Ask AI" button to send prompt from alert

### AIReasoningCanvas
- Shows: Multi-step reasoning breakdown
- Features: Step counter, conclusion summary
- Animation: Sequential step entry

### AgentTraceCanvas
- Shows: Waterfall timeline of agent spans
- Color-coded by operation kind (agent/LLM/tool/sub-agent)
- Token badges showing input/output counts

### AgentGraphCanvas
- Directed graph visualization
- Nodes: agent calls, tool calls
- Edges: call relationships with statistics

---

## 7. EXISTING "EXPLORATION" FUNCTIONALITY

### Dashboard as Exploration/Overview
The Dashboard Panel itself serves as the exploration/overview:
- **Aggregates all tool results** in one place
- **Tabbed organization** by data type (traces, logs, metrics, alerts, remediation)
- **Real-time updates** as agent investigates
- **Auto-opens on first data arrival** and switches to relevant tab
- **Resizable panels** to focus on specific data types

### Investigation Workflow
1. User types prompt in ConversationPage
2. Backend agent executes tools
3. Tool results arrive via `dashboardStream`
4. DashboardState collects items and notifies listeners
5. DashboardPanel updates and renders appropriate panels
6. User can explore/filter data within each tab
7. Can ask follow-up questions to agent about displayed data

### Smart Features
- **Auto-open**: Dashboard opens automatically when first data arrives
- **Auto-tab-switch**: Switches to tab matching the incoming data type
- **Item counting**: Shows count of items per category
- **Cloud Trace integration**: Direct link to trace in Google Cloud Console
- **Log pattern detection**: Automatically shows top patterns
- **Severity filtering**: Quick filter by log severity
- **Cloud Trace button**: Opens traces in external console

---

## 8. THEME & STYLING

### Color Palette (AppColors)
- Primary: Teal (#6366F1), Cyan (#06B6D4), Blue (#3B82F6)
- Secondary: Purple (#A855F7)
- Background: Dark (#0F172A), Card (#1E293B)
- Status: Success (#00E676), Warning (#FFAB00), Error (#FF5252)
- Text: Primary (#F0F4F8), Secondary (#B0BEC5), Muted (#78909C)

### Component Styling
- Glass morphism cards with subtle blur
- Rounded corners (12-16px)
- Border using `surfaceBorder` color
- Consistent padding and spacing
- Shadow effects for elevation

---

## 9. KEY SERVICES

### DashboardState
Central manager for dashboard data collection and presentation.

### ADKContentGenerator
Connects to Python backend, emits events to multiple streams including `dashboardStream`.

### ConversationPage
Main UI orchestrator that:
- Initializes catalog and message processor
- Manages stream subscriptions
- Renders chat and dashboard side-by-side
- Handles resizing and navigation

---

## 10. MULTI-TRACE AGENT GRAPH FEATURE

### Architecture (features/agent_graph/)
Feature-module structure following Riverpod/Freezed patterns:
- **domain/models.dart**: Freezed models — `MultiTraceNode`, `MultiTraceEdge`, `MultiTraceGraphPayload`, `SelectedGraphElement` (sealed union)
- **data/agent_graph_repository.dart**: Riverpod-provided `AgentGraphRepository` executing BQ GRAPH_TABLE SQL via Dio
- **application/agent_graph_notifier.dart**: `AgentGraphNotifier` (Riverpod) holding `AgentGraphState` (payload, isLoading, error, selectedElement, dataset, timeRangeHours)
- **presentation/**: `MultiTraceGraphPage` (full page), `MultiTraceGraphCanvas` (graphview-based), `AgentGraphDetailsPanel` (right-side metadata panel)

### Key Details
- **Data Source**: BigQuery GRAPH_TABLE query on `my-project.agent_graph.agent_trace_graph` (configurable)
- **Graph Library**: `graphview` package (Sugiyama L→R hierarchical + force-directed layout toggle)
- **Progressive Disclosure**: Default (label+icon), Hover (tooltip with tokens), Click (detail panel)
- **Edge Visualization**: Color = error rate (grey→orange→red), Thickness = token cost (log scale)
- **Navigation**: Accessible from InvestigationRail ("Agent Graph" entry)
- **Provider name**: `agentGraphProvider` (not `agentGraphNotifierProvider` — Riverpod strips "Notifier")

---

## Summary
The Flutter frontend is a **modern, real-time investigation dashboard** where:
- Backend agents execute tools and send results via WebSocket/HTTP streams
- DashboardState collects and categorizes results
- DashboardPanel provides tabbed exploration interface
- 12 custom catalog components visualize different data types
- 8 canvas widgets provide advanced visualizations
- All integrated into ConversationPage chat interface
- Fully supports real-time streaming as agent investigates
