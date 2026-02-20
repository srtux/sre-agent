# Frontend Documentation (Flutter)

The SRE Agent frontend is a high-performance Flutter Web application designed for real-time diagnostic visualization and interaction.

## Architecture & State Management

The frontend follows the **Provider** pattern for centralized state management via `MultiProvider` in `SreNexusApp` (`autosre/lib/app.dart`).

### Key Providers
- **`AuthService`**: Manages Google Sign-In lifecycle and local credential caching.
- **`ConnectivityService`**: Monitors network state and backend availability.
- **`ProjectService`**: Tracks the user's selected GCP project across all components.
- **`SessionService`**: Manages conversation history, loading/saving sessions from the backend.
- **`DashboardState`**: Centralized state manager for the investigation dashboard.
- **`ExplorerQueryService`**: Manages structured and natural language query execution for the data explorer.
- **`PromptHistoryService`**: Manages prompt history for the conversation input.
- **`ToolConfigService`**: Manages tool configuration state.
- **`VersionService`**: Fetches and caches backend version information.
- **`HelpService`**: Manages help center content.

---

## The Conversational Engine

The heart of the UI is the `ConversationPage` (`lib/pages/conversation_page.dart`), which orchestrates the interaction loop.

### 1. NDJSON Stream Handling
The frontend consumes a **Streaming NDJSON** API from the backend.
- It processes events in real-time as they are emitted by the Agent Engine.
- Events include: `text` (markdown), `thought` (reasoning), `tool_call` (step tracking), `widget` (GenUI), and **`dashboard`** (dedicated data channel).

### 2. AdkContentGenerator (`lib/agent/adk_content_generator.dart`)
A specialized class that handles the low-level HTTP streaming and transforms the JSON stream into a high-level `GenUiConversation` model.
- **`dashboardStream`**: A dedicated stream that emits flat metric and alert data for the Investigation Dashboard, decoupled from the chat-based A2UI protocol.

---

## Interceptors & Security

Every request sent by the frontend is intercepted by the `ProjectInterceptorClient` (`lib/services/api_client.dart`).

- **Auth Injection**: Automatically includes the `Authorization: Bearer <token>` header using the cached Google token.
- **Project Scope**: Injects the `X-GCP-Project-ID` header based on the global selection.
- **Identity Hint**: Injects `X-User-ID` (user's email) to assist the backend in robust session lookups when cookies are the primary auth method.
- **Web Credentials**: Dynamically enables `withCredentials = true` for Web platforms to allow secure cross-origin cookie propagation.

---

## GenUI (Generative UI) Widgets

The SRE Agent uses a dynamic widget system to visualize telemetry. When the backend emits a `widget` event, the frontend looks up a corresponding renderer.

| Widget | Purpose | Data Source |
| :--- | :--- | :--- |
| **TraceWaterfall** | Visualizes distributed tracing | `fetch_trace` |
| **MetricChart**| Timeseries visualization | `query_promql` |
| **LogPatternViewer**| Cluster log visualization | `extract_log_patterns` |

---

## Agent Graph Feature (`lib/features/agent_graph/`)

The Agent Graph feature provides an interactive multi-trace property graph visualization built on BigQuery's GRAPH_TABLE. It visualizes the full agent execution hierarchy across multiple traces and sessions.

### Architecture

The feature follows the Feature-First pattern with clean separation:

| Layer | Path | Responsibility |
| :--- | :--- | :--- |
| **Domain** | `domain/models.dart` | Freezed models: `MultiTraceNode`, `MultiTraceEdge`, `MultiTraceGraphPayload`, `SelectedGraphElement` |
| **Data** | `data/agent_graph_repository.dart` | BQ query generation (live + pre-aggregated), HTTP via Dio, JSON parsing |
| **Application** | `application/agent_graph_notifier.dart` | Riverpod state management (`AgentGraphState`: payload, loading, error, selection, time range) |
| **Presentation** | `presentation/` | `MultiTraceGraphPage`, `InteractiveGraphCanvas` (fl_nodes + graphview Sugiyama), `AgentGraphDetailsPanel` |

### Dual-Path Query Routing

For performance, the repository uses two query paths:

- **Pre-aggregated** (time range >= 1 hour): Queries the `agent_graph_hourly` table with simple GROUP BY + SUM. Sub-second response times.
- **Live GRAPH_TABLE** (sub-hour ranges): Performs the recursive BQ Property Graph traversal. Used for small data volumes where the cost is acceptable.

### Node Types & Visual Grammar

| Type | Icon | Color | Shape |
| :--- | :--- | :--- | :--- |
| **User Entry** (root Agent) | Person | Blue | Circular |
| **Agent** / **Sub-Agent** | Brain | Teal / Cyan | Rounded rectangle |
| **Tool** | Build | Orange | Rounded rectangle |
| **LLM** | Sparkle | Purple | Rounded rectangle |

Each node displays: token count, cost badge, latency, error rate, and subcall distribution (tool/LLM calls).

### Setup

See [BigQuery Agent Graph Setup](../guides/bigquery_agent_graph_setup.md) for the complete BQ schema, Property Graph, and pre-aggregation setup.

---

## The Investigation Dashboard (Decoupled)

The SRE Agent features a dedicated Investigation Dashboard that provides real-time situational awareness. Unlike standard GenUI widgets that are nested within the chat, the dashboard data is transmitted via a **Dedicated Data Channel** (`type: dashboard` events).

### Key Components:
- **`DashboardState`** (`lib/services/dashboard_state.dart`): Centralized state manager for the dashboard.
- **`DashboardPanel`** (`lib/widgets/dashboard/dashboard_panel.dart`): The main dashboard container.
- **`SreToolbar`** (`lib/widgets/dashboard/sre_toolbar.dart`): Dashboard toolbar controls.
- **Live Panels**:
  - `LiveAlertsPanel`: Real-time alert monitoring.
  - `LiveChartsPanel`: Metric chart visualization.
  - `LiveCouncilPanel`: Council investigation activity.
  - `LiveLogsExplorer`: Log entry exploration.
  - `LiveMetricsPanel`: Metrics data display.
  - `LiveTracePanel`: Trace data display.

### Visual Data Explorer

The dashboard includes a **Visual Data Explorer** (`lib/widgets/dashboard/visual_data_explorer.dart`) that supports structured query execution against GCP telemetry data:

- **`ManualQueryBar`**: Allows users to type structured queries (Cloud Trace filters, Cloud Logging filters, PromQL, BigQuery SQL).
- **`QueryLanguageToggle`**: Switches between query domains (traces, logs, metrics, BigQuery).
- **`QueryLanguageBadge`**: Displays the active query language.
- **`QueryAutocompleteOverlay`**: Provides autocomplete suggestions for query syntax.
- **`BigQuerySidebar`**: Dataset and table browser for BigQuery exploration.
- **`SqlResultsTable`**: Renders BigQuery query results in a tabular format.
- **Natural Language Queries**: Users can type natural language descriptions that are translated by the LLM into structured queries via the `/api/tools/nl/query` endpoint.

---

## Visualization Canvases (`lib/widgets/canvas/`)

The frontend includes multiple custom-painted canvases for high-performance visualization:

| Canvas | Purpose |
| :--- | :--- |
| **AgentActivityCanvas** | Visualizes agent execution steps and timing |
| **AgentGraphCanvas** | Council activity graph (panel interactions) |
| **AgentTraceCanvas** | Agent-level trace visualization |
| **AiReasoningCanvas** | Displays AI reasoning chain |
| **AlertsDashboardCanvas** | Alert overview and severity distribution |
| **IncidentTimelineCanvas** | Temporal view of incident events |
| **MetricsDashboardCanvas** | High-performance timeseries rendering (custom painting) |
| **ServiceTopologyCanvas** | Service dependency topology map |

---

## UI Components & Aesthetics

The UI is built with a "Deep Space" aesthetic using a custom design system in `autosre/lib/theme/app_theme.dart`.

- **Material 3**: The app uses Material 3 design language with a dark theme.
- **Common Widgets** (`lib/widgets/common/`):
  - `ErrorBanner`: Dismissible error notifications.
  - `ShimmerLoading`: Loading skeleton animations.
  - `SourceBadge`: Displays the data source for dashboard panels.
  - `ExplorerEmptyState`: Empty state illustration for the data explorer.

### Pages (`lib/pages/`)
- **`LoginPage`**: Google Sign-In with guest mode bypass.
- **`ConversationPage`**: Main investigation interface (chat + dashboard split view).
- **`ToolConfigPage`**: Tool enable/disable management with connectivity testing.
- **`HelpPage`**: Searchable help center with Documentation-as-Code content.
