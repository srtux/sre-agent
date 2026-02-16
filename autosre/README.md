# AutoSRE

A next-generation observability dashboard for SREs, built with **Flutter** and **GenUI**.

## Overview

AutoSRE connects to the SRE Agent (Python/ADK) backend and renders dynamic, generative UIs for distributed tracing, metric analysis, log exploration, incident remediation, and BigQuery analytics. It features a GCP-style **Observability Explorer** with per-panel query bars, autocomplete, natural language query routing, and a visual data explorer for tabular results.

It is designed to be served by the unified SRE Agent server, but can also be run independently for development.

## Design Aesthetic: "Mission Control"

**Theme**: Deep Space Command Center (`lib/theme/app_theme.dart`)

- **Core Colors**: Slate 900 backgrounds (`#0F172A`), Signal Cyan (`#06B6D4`), Indigo (`#6366F1`), Blue (`#3B82F6`), Purple (`#A855F7`).
- **Glassmorphism**: High-opacity frosted glass containers via `GlassDecoration` builders.
- **Typography**:
  - **Headings / Body**: `Inter` via `google_fonts`.
  - **Code / Queries**: `JetBrains Mono` via `google_fonts`.
- **Chart Theme**: Centralized Syncfusion chart theming (`lib/theme/chart_theme.dart`) providing reusable axis, trackball, zoom, and legend configurations matching the dark theme.

## Prerequisites

- **Flutter SDK** (Dart SDK ^3.10.7): [Install Flutter](https://docs.flutter.dev/get-started/install)
- **SRE Agent Backend**: Run via `uv run poe dev` (unified) or `uv run poe web` (backend only).
- **Troubleshooting**: See [docs/debugging_connectivity.md](../docs/debugging_connectivity.md) for connection issues.

## Getting Started

1. **Install Dependencies**:
    ```bash
    cd autosre
    flutter pub get
    ```

2. **Run the App** (Web):
    ```bash
    flutter run -d chrome
    ```

    For macOS desktop:
    ```bash
    flutter run -d macos
    ```

3. **Run Tests**:
    ```bash
    flutter test
    ```

4. **Lint**:
    ```bash
    flutter analyze
    ```

## Architecture

- **Framework**: Flutter (Material 3)
- **Protocol**: [GenUI](https://github.com/flutter/genui) + [A2UI](https://a2ui.org)
- **State Management**: Provider (`ChangeNotifier` pattern)
- **Entry Point**: `lib/main.dart`
- **App Configuration**: `lib/app.dart`
- **Catalog Registry**: `lib/catalog.dart` (maps A2UI component types to Flutter widgets)
- **Agent Connection**: `lib/agent/adk_content_generator.dart`

## Directory Structure

```
autosre/lib/
├── main.dart                   # App entry point
├── app.dart                    # Root widget, Provider setup
├── catalog.dart                # GenUI/A2UI component registry
│
├── agent/
│   └── adk_content_generator.dart  # Backend streaming connection (SSE)
│
├── models/
│   ├── adk_schema.dart         # ADK data models (Trace, SpanInfo, MetricSeries,
│   │                           #   LogEntriesData, LogPattern, IncidentTimelineData,
│   │                           #   RemediationPlan, CouncilSynthesisData, VegaChartData,
│   │                           #   AgentGraphData, AgentTraceData, etc.)
│   └── time_range.dart         # TimeRange and TimeRangePreset for query time windows
│
├── pages/
│   ├── conversation_page.dart  # Main investigation UI (chat + dashboard + session panel)
│   ├── login_page.dart         # Google Sign-In authentication
│   ├── tool_config_page.dart   # Tool enable/disable configuration
│   └── help_page.dart          # In-app help and documentation
│
├── services/
│   ├── api_client.dart         # HTTP client with auth headers
│   ├── auth_service.dart       # Google OAuth + token management
│   ├── session_service.dart    # Session CRUD (list, create, delete, switch)
│   ├── dashboard_state.dart    # Central dashboard state (ChangeNotifier)
│   ├── explorer_query_service.dart  # Manual telemetry query execution
│   ├── project_service.dart    # GCP project listing and selection
│   ├── connectivity_service.dart    # Backend health checks
│   ├── help_service.dart       # Help topic fetching from backend
│   ├── prompt_history_service.dart  # Per-user prompt history (SharedPreferences)
│   ├── tool_config_service.dart     # Tool category and config management
│   └── version_service.dart    # Backend version metadata
│
├── theme/
│   ├── app_theme.dart          # AppColors, GlassDecoration, AppTheme
│   └── chart_theme.dart        # ChartTheme (Syncfusion axis, trackball, palette)
│
├── utils/
│   └── ansi_parser.dart        # ANSI escape code parser for log rendering
│
└── widgets/
    ├── auth/                           # Authentication widgets
    │   ├── google_sign_in_button.dart  #   Platform-adaptive sign-in button
    │   ├── google_sign_in_button_web.dart
    │   ├── google_sign_in_button_mobile.dart
    │   └── google_sign_in_button_stub.dart
    │
    ├── canvas/                         # GenUI Canvas visualizations
    │   ├── agent_activity_canvas.dart  #   Real-time agent workflow
    │   ├── agent_graph_canvas.dart     #   Agent dependency graph (graphview)
    │   ├── agent_trace_canvas.dart     #   Agent interaction timeline/waterfall
    │   ├── ai_reasoning_canvas.dart    #   Reasoning step visualization
    │   ├── alerts_dashboard_canvas.dart#   List-based active alerts view
    │   ├── incident_timeline_canvas.dart#  Horizontal incident timeline
    │   ├── metrics_dashboard_canvas.dart#  Multi-metric sparkline grid
    │   └── service_topology_canvas.dart #  Service dependency graph
    │
    ├── common/                         # Shared utility widgets
    │   ├── error_banner.dart           #   Error display banner
    │   ├── explorer_empty_state.dart   #   Empty state with query hint
    │   ├── shimmer_loading.dart        #   Shimmer loading placeholder
    │   └── source_badge.dart           #   "MANUAL" badge for user-queried data
    │
    ├── dashboard/                      # Observability Explorer panels
    │   ├── dashboard_panel.dart        #   Main tabbed dashboard container
    │   ├── sre_toolbar.dart            #   Unified dashboard header bar
    │   ├── manual_query_bar.dart       #   Per-panel query input with autocomplete & NL toggle
    │   ├── query_helpers.dart          #   Query snippets, templates, NL examples per signal
    │   ├── query_autocomplete_overlay.dart  # Autocomplete dropdown overlay
    │   ├── query_language_badge.dart   #   Query language indicator badge
    │   ├── query_language_toggle.dart  #   MQL/PromQL language switcher
    │   ├── dashboard_card_wrapper.dart #   Collapsible card wrapper
    │   ├── live_trace_panel.dart       #   Trace explorer (Cloud Trace query syntax)
    │   ├── live_logs_explorer.dart     #   Logs explorer (Cloud Logging query syntax)
    │   ├── live_metrics_panel.dart     #   Metrics explorer (MQL + PromQL)
    │   ├── live_alerts_panel.dart      #   Alerts and incidents panel
    │   ├── live_remediation_panel.dart #   Remediation plans panel
    │   ├── live_council_panel.dart     #   Council decisions and debate outcomes
    │   ├── live_charts_panel.dart      #   BigQuery/SQL results + visual explorer
    │   ├── council_activity_graph.dart #   Council investigation activity graph
    │   ├── cards/
    │   │   └── council_decision_card.dart  # Council decision summary card
    │   ├── bigquery_sidebar.dart       #   Dataset/table browser sidebar
    │   ├── sql_results_table.dart      #   Sortable SQL results table with export
    │   └── visual_data_explorer.dart   #   Tableau-like visual data explorer
    │
    ├── help/
    │   └── help_card.dart              #   Help topic card
    │
    ├── unified_prompt_input.dart  # Centered pill-shaped prompt input
    ├── session_panel.dart         # Session history sidebar
    ├── status_toast.dart          # Glassmorphic notification toast
    ├── tool_log.dart              # Inline tool call status display
    ├── glow_action_chip.dart      # Glowing action chip for suggestions
    ├── error_placeholder.dart     # GenUI error fallback widget
    ├── tech_grid_painter.dart     # Animated tech grid background
    ├── syncfusion_trace_waterfall.dart  # Trace waterfall (Syncfusion)
    ├── syncfusion_metric_chart.dart     # Metric time-series chart (Syncfusion)
    ├── log_entries_viewer.dart    # Raw log entries viewer
    ├── log_pattern_viewer.dart    # Aggregated log pattern viewer
    ├── remediation_plan.dart      # Interactive remediation checklist
    ├── postmortem_card.dart       # Postmortem report card
    └── slo_burn_rate_card.dart    # SLO burn rate display
```

## Observability Explorer (Dashboard Query System)

The dashboard has been transformed into a GCP-style Observability Explorer where each signal panel (Traces, Logs, Metrics, Alerts, Charts) has its own query bar for manual data exploration, independent of the AI agent chat.

### Dashboard Panels

| Panel | Query Language | Features |
|-------|---------------|----------|
| **Traces** | Cloud Trace filter syntax | `+span:name:`, `RootSpan:`, `MinDuration:`, `Status:` filters; trace ID lookup |
| **Logs** | Cloud Logging query language | `severity>=`, `resource.type=`, `textPayload:`, boolean operators (AND/OR/NOT) |
| **Metrics** | MQL (ListTimeSeries) or PromQL | `metric.type=`, `resource.type=`; toggle between MQL and PromQL with `QueryLanguageToggle` |
| **Alerts** | Filter string | Incident and alert policy filters |
| **Charts** | BigQuery SQL | Multi-line SQL editor; dataset/table browser sidebar; sortable results table; visual data explorer |

### ManualQueryBar (`manual_query_bar.dart`)

A 1100+ line widget providing per-panel query input with:

- **Autocomplete**: Context-aware keyword suggestions powered by `QuerySnippet` definitions. Keyboard navigation with arrow keys, Tab to accept, Escape to dismiss.
- **Query Templates**: Lightbulb button opens a `QueryTemplatesPicker` with pre-built queries grouped by category.
- **Natural Language Toggle**: Switch between structured query mode and NL mode via a dropdown badge selector. NL queries are routed to the AI agent for interpretation.
- **Language Selector**: Badge dropdown to switch query languages (e.g., MQL vs PromQL on the metrics panel).
- **Time Range Controls**: Integrated time range chips (1H, 6H, 1D, 1W, Custom) with a Syncfusion date range picker for custom ranges.
- **Auto-Refresh**: Toggle for 30-second automatic refresh.
- **Multi-Line Mode**: For SQL queries, the bar expands with Ctrl+Enter to submit.

### Query Helpers (`query_helpers.dart`)

Defines per-signal catalogs of:

- **`QuerySnippet`**: Autocomplete entries with label, insert text, description, category, icon, and color. Catalogs: `traceSnippets`, `loggingSnippets`, `mqlSnippets`, `promqlSnippets`, `sqlSnippets`.
- **`QueryTemplate`**: Pre-built queries with title, description, full query string, and category. Catalogs: `traceTemplates`, `loggingTemplates`, `metricsTemplates`, `promqlTemplates`, `sqlTemplates`.
- **NL Examples**: Natural language prompt examples per signal type: `traceNaturalLanguageExamples`, `loggingNaturalLanguageExamples`, `metricsNaturalLanguageExamples`, `sqlNaturalLanguageExamples`.

### ExplorerQueryService (`services/explorer_query_service.dart`)

Backend-calling service that executes manual telemetry queries and feeds results into `DashboardState` with `DataSource.manual` tracking. Endpoints:

- `queryMetrics()` -- MQL/ListTimeSeries filter queries
- `queryMetricsPromQL()` -- PromQL queries
- `queryLogs()` -- Cloud Logging queries
- `queryTrace()` -- Single trace lookup by ID
- `queryTraceFilter()` -- Cloud Trace filter queries
- `queryAlerts()` -- Alert/incident queries
- `queryBigQuery()` -- BigQuery SQL execution
- `getDatasets()`, `getTables()`, `getTableSchema()` -- BigQuery metadata browsing

### Visual Data Explorer (`visual_data_explorer.dart`)

A Tableau-like interactive explorer for BigQuery tabular results:

- **Dimension/Measure shelves**: Drag columns into dimension or measure slots.
- **Aggregation functions**: SUM, AVG, COUNT, MIN, MAX, COUNT_DISTINCT.
- **Chart types**: Bar, Line, Area, Scatter, Pie, Heatmap, Table.
- **Auto-detection**: Automatically detects numeric vs categorical columns.
- **Sorting and limits**: Configurable sort direction and row limits.
- **Custom chart painter**: Renders charts directly via `CustomPaint` without external charting libraries.

### SreToolbar (`sre_toolbar.dart`)

Unified dashboard header with:

- **Dynamic tab icon + label**: Displays the active panel type (Traces, Logs, Metrics, Alerts, Remediation, Council, Charts) with color-coded icons.
- **Item count badge**: Shows the number of collected items for the active panel.
- **Maximize/Restore**: Toggle full-width dashboard view.
- **Close**: Dismiss the dashboard.

### Dual-Stream Data Architecture

Dashboard items track their origin via `DataSource`:

- **`DataSource.agent`**: Data pushed by the AI agent during investigation (via A2UI dashboard events).
- **`DataSource.manual`**: Data fetched by the user through the explorer query bars.

Items from both sources coexist in the same panels. The `SourceBadge` widget displays a "MANUAL" indicator for user-queried items.

## Canvas Widgets (GenUI Dynamic Visualization)

Advanced canvas-style widgets for real-time, animated SRE visualizations:

| Widget | Component Name | Description |
|--------|---------------|-------------|
| `AgentActivityCanvas` | `x-sre-agent-activity` | Real-time agent workflow with animated node connections, status indicators, and phase tracking. |
| `AgentGraphCanvas` | `x-sre-agent-graph` | Agent dependency graph using `graphview` package with Sugiyama or force-directed layout. Shows agents, tools, LLM models, and relationships. |
| `AgentTraceCanvas` | `x-sre-agent-trace` | Waterfall-style timeline of agent spans color-coded by kind (agent, LLM, tool, sub-agent) with token badges. |
| `ServiceTopologyCanvas` | `x-sre-service-topology` | Interactive service dependency graph with health status, latency metrics, incident highlighting, and pan/zoom. |
| `IncidentTimelineCanvas` | `x-sre-incident-timeline` | Horizontal scrollable timeline with event correlation, severity color-coding, and TTD/TTM metrics. |
| `MetricsDashboardCanvas` | `x-sre-metrics-dashboard` | Grid-based multi-metric display with sparklines, anomaly detection, and threshold visualization. |
| `AIReasoningCanvas` | `x-sre-ai-reasoning` | Agent reasoning step visualization (observation, analysis, hypothesis, conclusion) with confidence scores. |
| `AlertsDashboardCanvas` | `x-sre-incident-timeline` | List-based active alerts view with severity indicators and prompt-to-investigate actions. |

## Key Widgets

| Widget | Description |
|--------|-------------|
| `UnifiedPromptInput` | Centered, pill-shaped chat input with floating shadow and suggestion chips. |
| `SessionPanel` | Sidebar for viewing and managing investigation history sessions. |
| `StatusToast` | Floating glassmorphic notification for system status. |
| `TraceWaterfall` | Gantt-chart-style distributed trace waterfall. |
| `SyncfusionMetricChart` | Time-series metric chart with anomaly markers (Syncfusion). |
| `LogEntriesViewer` | Raw log entries table with severity coloring and ANSI parsing. |
| `LogPatternViewer` | Aggregated log pattern viewer with occurrence counts. |
| `RemediationPlan` | Interactive checklist for remediation actions. |
| `PostmortemCard` | Postmortem report display card. |
| `SloBurnRateCard` | SLO burn rate visualization. |
| `ToolLog` | Inline tool call status with expand/collapse for output. |
| `GlowActionChip` | Glowing action chip for suggested follow-up prompts. |
| `TechGridPainter` | Animated technical grid background. |
| `CouncilActivityGraphWidget` | Council investigation activity graph (agent hierarchy, tool calls, timeline). |
| `CouncilDecisionCard` | Council decision summary with agent consensus and reasoning. |
| `BigQuerySidebar` | Dataset/table browser for BigQuery SQL panel. |
| `SqlResultsTable` | Paginated, sortable, scrollable, and resizable results table with CSV/JSON export and UNIX timestamp decoding. |

## Session Management

AutoSRE uses the backend's `SessionService` to persist conversation history.

- **API**: Connects to `/api/sessions` for listing and managing sessions.
- **Context**: Maintains `session_id` to restore conversation history from ADK storage (SQLite/Firestore).
- **History**: Chat history is rehydrated from backend events, ensuring state consistency across reloads.
- **State Reset**: `clearSession()` resets frontend state and backend `session_id` when starting a new investigation.
- **Prompt History**: Per-user prompt history persisted locally via `SharedPreferences` with up/down arrow navigation.

## Authentication Setup

1. **Google Cloud Project**:
    - Create an **OAuth 2.0 Client ID** for **Web Application**.
    - **Authorized JavaScript Origins**: `http://localhost`, `http://localhost:8080`, and your Cloud Run URL (once deployed).

2. **Backend Configuration**:
    - The Google Client ID is provided by the backend via the `/api/config` endpoint.
    - Set `GOOGLE_CLIENT_ID` in your `.env` file at the repository root.
    - In Cloud Run, ensure the `GOOGLE_CLIENT_ID` secret or environment variable is set.

3. **Running Locally**:
    - When running with `uv run poe dev`, the Client ID is automatically synchronized from the root `.env`. No manual file changes are required.

4. **Deploying to Cloud Run**:
    - The deployment scripts automatically configure the `GOOGLE_CLIENT_ID` secret.
    - **Important**: Once deployed, you MUST add your Cloud Run service URL to the **Authorized JavaScript Origins** in the Google Cloud Console.

## Dependencies

Key packages from `pubspec.yaml`:

| Package | Purpose |
|---------|---------|
| `genui` / `genui_a2ui` | GenUI framework and A2UI protocol support |
| `provider` | State management |
| `syncfusion_flutter_charts` | Trace waterfall and metric charts |
| `syncfusion_flutter_datepicker` | Custom time range picker |
| `google_sign_in` / `googleapis_auth` | Google OAuth authentication |
| `google_fonts` | Inter and JetBrains Mono typography |
| `http` | HTTP client for backend API calls |
| `shared_preferences` | Local storage for prompt history and preferences |
| `flutter_markdown_plus` | Markdown rendering in chat messages |
| `graphview` | Agent dependency graph layout |
| `fluentui_system_icons` | Additional icon set |
| `shimmer` | Loading state shimmer effects |
| `url_launcher` | Opening external links (Cloud Trace deep links) |
| `uuid` | Session and item ID generation |
| `intl` | Date/time formatting |
