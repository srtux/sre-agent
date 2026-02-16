# SRE Agent Observability Explorer

The **Observability Explorer** is a GCP Console-style interactive dashboard built into the Flutter frontend (`autosre`). It provides dual-mode access to telemetry data: users can directly query GCP Cloud Monitoring, Cloud Logging, Cloud Trace, BigQuery, and alert policies alongside AI agent-pushed insights.

## Key Features

### Observability Toolbar (`SreToolbar`)

The toolbar (`lib/widgets/dashboard/sre_toolbar.dart`) is a unified dashboard header that dynamically reflects the currently active tab. It has been refactored from a multi-control toolbar into a streamlined, context-aware header bar.

**Layout**: `[Dynamic Tab icon+label] | ...spacer... | [Item Count] [Maximize] [Close]`

*   **Dynamic Tab Label**: The toolbar displays an icon and label that change based on the active `DashboardDataType` (Traces, Logs, Metrics, Alerts, Remediation, Council, Charts). Each tab has a unique icon and accent color defined in `_tabConfig()`.
*   **Item Count Badge**: Shows the number of items currently collected for the active tab (e.g., "3 items") with a cyan pill badge.
*   **Maximize/Restore**: Toggle the dashboard between side-panel and full-width mode.
*   **Close**: Dismiss the dashboard panel entirely.

**Note**: Time range selection, refresh, and auto-refresh controls have been moved **into the `ManualQueryBar`** itself (see below). The toolbar no longer manages time range state directly.

### ManualQueryBar (`ManualQueryBar`)

The `ManualQueryBar` (`lib/widgets/dashboard/manual_query_bar.dart`) is the primary query input widget used by every explorer panel. It has been significantly expanded from a simple text input into a full-featured query editor with 550+ lines of functionality.

#### Core Features

*   **Monospace Text Input**: JetBrains Mono font for structured queries, Google Inter for natural language mode.
*   **Single-Line Mode**: Default compact bar with pill-shaped border (20px radius). Used by Trace, Log, Metrics, and Alert panels.
*   **Multi-Line Mode**: Expandable editor (80-200px height) with rounded rectangle border (12px radius). Used by the BigQuery SQL panel. Submit with `Ctrl+Enter` (or `Cmd+Enter` on macOS).
*   **Language Badge/Selector**: A leading badge showing the current query language (e.g., "TRACE", "LOG FILTER", "MQL Filter", "PromQL", "BigQuery SQL"). When multiple languages are available, it becomes a dropdown selector using `PopupMenuButton`.
*   **Run Query Button**: Submits the query. Replaced by a `CircularProgressIndicator` while loading.
*   **Clear Button**: Appears when text is present; clears the input and refocuses.
*   **Embedded Time Controls**: When `dashboardState` is provided, a time controls row renders below the text input, separated by a divider. This row contains:
    *   Time range preset chips (1H, 6H, 1D, 1W, Custom)
    *   Custom date range picker (Syncfusion `SfDateRangePicker` dialog)
    *   Manual refresh button
    *   Auto-refresh toggle (30-second interval)

#### Context-Aware Autocomplete

The autocomplete system is powered by `QuerySnippet` objects defined in `query_helpers.dart` and rendered via `QueryAutocompleteOverlay` (`query_autocomplete_overlay.dart`).

*   **Trigger**: Activates automatically as the user types in structured query mode (not NL mode). Filters snippets based on the current word at the cursor position.
*   **Special Prefix Matching**: For `key="value"` style queries (MQL/Logs), the autocomplete matches within the value portion after known prefixes like `metric.type="`, `resource.type="`, `metric.labels.`, and `resource.labels.`.
*   **Keyboard Navigation**: Arrow Up/Down to highlight, Tab or Enter to insert, Escape to dismiss.
*   **Visual Design**: Floating overlay positioned via `CompositedTransformFollower`/`LayerLink`. Each suggestion shows a category icon, monospace label, description, and category badge.
*   **Max Suggestions**: Capped at 8 visible suggestions at a time.

#### Query Templates & Helpers

Accessed via the lightbulb button (`Icons.lightbulb_outline_rounded`), the `QueryTemplatesPicker` opens a floating popup with:

*   **Pre-Built Queries**: Grouped by category (e.g., "Performance", "Errors", "Cloud Run"), each with a title, description, and full query string. Selecting a template inserts it into the query bar.
*   **Natural Language Examples**: A separate "Ask in Plain English" section at the top shows example NL prompts. Selecting one switches the bar to NL mode and inserts the example text.

#### Natural Language Mode

*   **Toggle**: Available when `enableNaturalLanguage: true`. The language badge dropdown includes a "Natural Language" option with a sparkle icon (`Icons.auto_awesome_rounded`).
*   **Visual Cue**: When NL mode is active, the border and glow change from cyan to purple (`AppColors.secondaryPurple`), and the text font switches from monospace to sans-serif (Google Inter).
*   **Submission**: NL queries are routed via `onSubmitWithMode(query, isNaturalLanguage: true)`, which typically calls `onPromptRequest` to send the query as a chat message to the AI agent rather than executing a direct API call.

### Per-Panel Snippet & Template Catalogs

All snippet and template data is centralized in `lib/widgets/dashboard/query_helpers.dart`:

| Panel | Language Label | Snippets | Templates | NL Examples |
|-------|---------------|----------|-----------|-------------|
| **Traces** | `TRACE` | `traceSnippets` (8): span filters, duration, labels, status | `traceTemplates` (5): slow APIs, errors, service spans | `traceNaturalLanguageExamples` (4) |
| **Logs** | `LOG FILTER` | `loggingSnippets` (12): severity, resource, payload, operators | `loggingTemplates` (7): errors, Cloud Run, GKE, audit | `loggingNaturalLanguageExamples` (4) |
| **Metrics (MQL)** | `MQL Filter` | `mqlSnippets` (16): metric types, resource types, common GCP metrics | `metricsTemplates` (4): CPU, Cloud Run, SQL, LB | `metricsNaturalLanguageExamples` (4) |
| **Metrics (PromQL)** | `PromQL` | `promqlSnippets` (10): rate, sum, avg, quantile, range vectors | `promqlTemplates` (4): request rate, error %, P95, memory | (shared with MQL) |
| **Charts (SQL)** | `BigQuery SQL` | `sqlSnippets` (12): SELECT, FROM, WHERE, functions | `sqlTemplates` (5): OTel spans, error count, P95, slowest | `sqlNaturalLanguageExamples` (4) |
| **Alerts** | *(none)* | *(none)* | *(none)* | *(none)* |

### 1. Trace Explorer (`LiveTracePanel`)

File: `lib/widgets/dashboard/live_trace_panel.dart`

*   **Query Modes**:
    *   **Cloud Trace Filter**: Filter expressions like `+span:name:my_service`, `RootSpan:/api/`, `MinDuration:1s`, `Status:ERROR`. Uses `ExplorerQueryService.queryTraceFilter()`.
    *   **Trace ID Lookup**: Prefix with `trace=` to fetch a single trace by ID. Uses `ExplorerQueryService.queryTrace()`.
    *   **Natural Language**: Routes to the AI agent via `onPromptRequest`.
*   **Syntax Help**: Inline reference bar showing `Tab to autocomplete | Syntax: +span:name:<value> RootSpan:<path> MinDuration:<dur> HasLabel:<key>:<value>`.
*   **Trace Waterfall**: Expandable custom `TraceWaterfall` chart per trace. First trace in list is expanded by default.
*   **Cloud Trace Deep Link**: "Open in Cloud Trace" button constructs a `console.cloud.google.com/traces/list?tid=...&project=...` URL.
*   **Card Management**: Each trace is wrapped in `DashboardCardWrapper` with collapse, copy JSON, and remove controls.

### 2. Log Explorer (`LiveLogsExplorer`)

File: `lib/widgets/dashboard/live_logs_explorer.dart`

*   **Manual Query**: Cloud Logging filter expressions with autocomplete (e.g., `severity>=ERROR AND resource.type="gce_instance"`). Uses `ExplorerQueryService.queryLogs()`.
*   **Natural Language**: Routes to the AI agent via `onPromptRequest`.
*   **Severity Filtering**: Interactive `FilterChip` widgets with per-severity counts (CRITICAL, ERROR, WARNING, INFO, DEBUG). Clicking filters the aggregated entry list.
*   **Full-Text Search**: Real-time search across `payloadPreview` of all collected entries.
*   **Log Aggregation**: Entries from multiple tool calls are merged, deduplicated by timestamp, and sorted newest-first.
*   **Pattern Summary**: When `logPatterns` data exists, displays top 3 Drain3-extracted patterns with occurrence counts (e.g., "450x Connection refused to database").
*   **Expandable JSON Payloads**: Click any `isJsonPayload` entry to expand the full structured payload in a dark code block with `JetBrainsMono` font.
*   **ANSI Parsing**: Log text payloads are rendered via `AnsiParser.parse()` for color-coded terminal output.
*   **External Docs**: Link to Cloud Logging query language documentation.

### 3. Metrics Explorer (`LiveMetricsPanel`)

File: `lib/widgets/dashboard/live_metrics_panel.dart`

*   **Dual Query Language**: Toggle between `MQL Filter` (ListTimeSeries) and `PromQL` via the language dropdown in the `ManualQueryBar`. The `languages` parameter is set to `['MQL Filter', 'PromQL']`.
    *   **MQL**: `ExplorerQueryService.queryMetrics()` — filter syntax like `metric.type="compute.googleapis.com/instance/cpu/utilization"`.
    *   **PromQL**: `ExplorerQueryService.queryMetricsPromQL()` — expressions like `rate(http_requests_total[5m])`.
*   **Natural Language**: Routes to the AI agent via `onPromptRequest`.
*   **Query Language State**: Managed via `DashboardState.metricsQueryLanguage` (0 = MQL, 1 = PromQL). Changing the language swaps the hint text, snippets, and templates.
*   **Syntax Help**: Context-sensitive inline help that changes based on the selected language.
*   **Syncfusion Charts**: `SyncfusionMetricChart` with interactive line charts, zoom, pan, and trackball tooltips.
*   **Golden Signals Dashboard**: `MetricsDashboardCanvas` for agent-pushed multi-metric dashboards.
*   **Responsive Layout**: Charts render at 450px height on wide screens (>500px) and 350px on narrow screens.

### 4. Alerts Explorer (`LiveAlertsPanel`)

File: `lib/widgets/dashboard/live_alerts_panel.dart`

*   **Manual Query**: Alert filter expressions (e.g., `state="OPEN" AND severity="CRITICAL"`). Uses `ExplorerQueryService.queryAlerts()`.
*   **Alerts Dashboard Canvas**: `AlertsDashboardCanvas` renders incident timelines with severity indicators, metadata cards, and agent correlation data.
*   **Prompt Request**: Supports `onPromptRequest` for agent-assisted alert investigation.

### 5. Charts & BigQuery Explorer (`LiveChartsPanel`)

File: `lib/widgets/dashboard/live_charts_panel.dart`

*   **Dual View Mode**: Toggle between "BigQuery SQL" and "Agent Charts" via the language dropdown.
*   **SQL Editor**: Multi-line `ManualQueryBar` with SQL autocomplete, templates, and NL mode. Uses `ExplorerQueryService.queryBigQuery()`.
*   **BigQuery Sidebar** (`bigquery_sidebar.dart`): Left panel that shows available datasets, tables, and column schemas. Click a table name to insert it into the SQL editor; click a column to append it.
*   **Table Results** (`SqlResultsTable`): Sortable, scrollable data table with column sorting, row hover highlighting, and CSV/JSON clipboard export.
*   **Visual Data Explorer** (`VisualDataExplorer`): Tableau-like interactive visualization builder. Supports:
    *   Assigning columns as dimensions or measures
    *   Selecting chart types (bar, line, area, scatter, pie, heatmap, table)
    *   Applying aggregation functions (SUM, AVG, COUNT, MIN, MAX, COUNT DISTINCT)
    *   Group-by and interactive filtering
*   **Results View Toggle**: Switch between Table and Visual Explorer views with a chip-based toggle bar showing the row count.
*   **Agent Charts**: Vega-Lite chart specifications generated by the analytics agent during investigations. Each chart card shows the question, answer text, chart type icon, and an expandable JSON spec viewer with copy-to-clipboard.

### 6. Remediation Plan (`LiveRemediationPanel`)

*   **Purpose**: Actionable, tool-driven resolution steps (agent-generated only).
*   **Features**:
    *   **Checklists**: Steps are rendered as interactive checklists.
    *   **Risk Assessment**: Every plan includes a risk badge (Low, Medium, High).
    *   **One-Click Action**: Terminal commands (gcloud, kubectl) can be copied directly from the dashboard.

### 7. Council of Experts Dashboard (`LiveCouncilPanel`)

*   **Expert Findings View**: Specialist panel (Trace, Metrics, Logs, Alerts, Data) assessments with severity indicators, confidence scores, and specialist summaries.
*   **Specialist Indicators**: Each finding includes a domain-specific icon and status badge (CRITICAL, WARNING, HEALTHY, INFO).
*   **Evidence Sections**: Detailed evidence lists parsed from agent responses, supporting specific findings.
*   **Critic Report**: In Debate mode, shows agreements, contradictions, and identified gaps between specialist assessments.
*   **Activity Graph View** (`council_activity_graph.dart`): Tree visualization of agent hierarchy with timeline mode and tool call details.
*   **Integration**: Findings from council experts automatically correlate with telemetry across all all other dashboard tabs.

## Architecture

### Dashboard Panel (`DashboardPanel`)

File: `lib/widgets/dashboard/dashboard_panel.dart`

The `DashboardPanel` is the top-level container for the entire dashboard. It has been simplified to a clean, declarative structure:

*   **Entrance Animation**: Slide-in from the left (-400px) with fade, using `AnimationController` (300ms, easeOutCubic).
*   **Visual Style**: Dark background (`AppColors.backgroundDark`) with a right border and drop shadow.
*   **Layout**: `Column` containing `SreToolbar` at the top and an `Expanded` content area wrapped in `SelectionArea` for text selection.
*   **Content Dispatch**: A `ListenableBuilder` on `DashboardState` switches between seven panel types based on `activeTab`:

| Tab Type | Widget | File |
|----------|--------|------|
| `DashboardDataType.traces` | `LiveTracePanel` | `live_trace_panel.dart` |
| `DashboardDataType.logs` | `LiveLogsExplorer` | `live_logs_explorer.dart` |
| `DashboardDataType.metrics` | `LiveMetricsPanel` | `live_metrics_panel.dart` |
| `DashboardDataType.alerts` | `LiveAlertsPanel` | `live_alerts_panel.dart` |
| `DashboardDataType.remediation` | `LiveRemediationPanel` | `live_remediation_panel.dart` |
| `DashboardDataType.council` | `LiveCouncilPanel` | `live_council_panel.dart` |
| `DashboardDataType.charts` | `LiveChartsPanel` | `live_charts_panel.dart` |

Each panel receives `items` (filtered by type), `dashboardState`, and optionally `onPromptRequest` for NL query routing.

### Dual Data Source Model

The dashboard supports two data sources tracked via the `DataSource` enum:
-   **`DataSource.agent`** (default): Data pushed by the Council of Experts via SSE `dashboard` events during investigations.
-   **`DataSource.manual`**: Data fetched by the user via the `ExplorerQueryService` through manual query bars.

Both sources feed into the same `DashboardState` and render identically, with manual items displaying a "MANUAL" badge via `SourceBadge`.

### Data Flow

```
Agent Path:     Tool Result -> create_dashboard_event() -> genui_adapter.transform_*() -> SSE -> DashboardState.addFromEvent()
Manual Path:    ManualQueryBar -> ExplorerQueryService -> HTTP POST -> Backend Endpoint -> _unwrap_tool_result() -> genui_adapter.transform_*() -> DashboardState.add*()
NL Query Path:  ManualQueryBar (NL mode) -> onPromptRequest -> Chat message to agent -> Agent investigation -> Dashboard events
```

Both the agent and manual paths use the same `genui_adapter.transform_*()` functions, ensuring consistent data formats for the frontend `fromJson` parsers.

### Backend Endpoints (Manual Query)

| Endpoint | Method | Tool Function | Transform |
|----------|--------|---------------|-----------|
| `/api/tools/metrics/query` | POST | `list_time_series` | `transform_metrics` |
| `/api/tools/metrics/promql` | POST | `query_promql` | `transform_metrics` |
| `/api/tools/alerts/query` | POST | `list_alerts` | `transform_alerts_to_timeline` |
| `/api/tools/logs/query` | POST | `list_log_entries` | `transform_log_entries` |
| `/api/tools/trace/{trace_id}` | GET | `fetch_trace` | `transform_trace` |
| `/api/tools/traces/query` | POST | `list_traces` | `transform_trace` (list) |
| `/api/tools/bigquery/query` | POST | BigQuery SQL execution | Tabular (columns + rows) |
| `/api/tools/bigquery/datasets` | GET | List BQ datasets | Dataset names |
| `/api/tools/bigquery/datasets/{id}/tables` | GET | List tables in dataset | Table names |
| `/api/tools/bigquery/datasets/{id}/tables/{tid}/schema` | GET | Table schema | Column definitions |

All endpoints unwrap `BaseToolResponse` envelopes via `_unwrap_tool_result()` before applying transforms.

### State Management

-   **`DashboardState`** (`lib/services/dashboard_state.dart`): `ChangeNotifier` providing per-tab data storage, loading states, error states, time range, auto-refresh, BigQuery results, and query language selection. Registered in the Provider tree.
    -   **`DashboardDataType` enum**: `logs`, `metrics`, `traces`, `alerts`, `remediation`, `council`, `charts`.
    -   **`DashboardItem`**: Typed data container with fields for `logData`, `logPatterns`, `metricSeries`, `metricsDashboard`, `traceData`, `alertData`, `remediationPlan`, `councilData`, and `chartData`.
    -   **`classifyComponent()`**: Maps GenUI widget types (e.g., `x-sre-metric-chart`) to `DashboardDataType` values.
    -   **`addFromEvent()`**: Primary event ingestion method. Processes dashboard events by `widget_type`, auto-opens the dashboard on first data, and switches to the relevant tab.
    -   **BigQuery State**: `bigQueryColumns`, `bigQueryResults`, `setBigQueryResults()`, `clearBigQueryResults()`.
    -   **Metrics Language State**: `metricsQueryLanguage` (0=MQL, 1=PromQL), `setMetricsQueryLanguage()`.
    -   **Per-Tab Query Persistence**: `getLastQueryFilter()` / `setLastQueryFilter()` stores the most recent query string per panel type.
-   **`ExplorerQueryService`** (`lib/services/explorer_query_service.dart`): HTTP client for manual queries. Provides `queryMetrics()`, `queryMetricsPromQL()`, `queryLogs()`, `queryTrace()`, `queryTraceFilter()`, `queryAlerts()`, `queryBigQuery()`, `getDatasets()`, `getTables()`, `getTableSchema()`. Depends on `DashboardState` for time range and result storage.
-   **`TimeRange`** (`lib/models/time_range.dart`): Immutable model with `TimeRangePreset` enum (1H, 6H, 1D, 1W, Custom) and factory constructors.

### Shared UI Components

| Widget | Location | Purpose |
|--------|----------|---------|
| `ManualQueryBar` | `lib/widgets/dashboard/manual_query_bar.dart` | Full-featured query editor with autocomplete, templates, NL toggle, and embedded time controls |
| `QueryAutocompleteOverlay` | `lib/widgets/dashboard/query_autocomplete_overlay.dart` | Floating dropdown showing filtered autocomplete suggestions with keyboard navigation |
| `QueryTemplatesPicker` | `lib/widgets/dashboard/query_autocomplete_overlay.dart` | Floating popup with pre-built query templates grouped by category and NL examples |
| `QuerySnippet` | `lib/widgets/dashboard/query_helpers.dart` | Data model for an autocomplete suggestion (label, insertText, description, category, icon, color) |
| `QueryTemplate` | `lib/widgets/dashboard/query_helpers.dart` | Data model for a pre-built query template (title, description, query, category, icon) |
| `SreToolbar` | `lib/widgets/dashboard/sre_toolbar.dart` | Unified dashboard header: dynamic tab icon/label, item count, maximize, close |
| `DashboardCardWrapper` | `lib/widgets/dashboard/dashboard_card_wrapper.dart` | Collapsible card with header, expand/collapse toggle, copy JSON, and remove button |
| `DashboardPanel` | `lib/widgets/dashboard/dashboard_panel.dart` | Top-level container with entrance animation, toolbar, and content dispatch |
| `BigQuerySidebar` | `lib/widgets/dashboard/bigquery_sidebar.dart` | Left sidebar showing datasets, tables, and schemas for the BigQuery SQL panel |
| `SqlResultsTable` | `lib/widgets/dashboard/sql_results_table.dart` | Sortable, scrollable data table with export capabilities |
| `VisualDataExplorer` | `lib/widgets/dashboard/visual_data_explorer.dart` | Tableau-like interactive visualization builder for BigQuery results |
| `ErrorBanner` | `lib/widgets/common/error_banner.dart` | Dismissible error display for panel-level errors; allows manual clearing of error states via `onDismiss` callback |
| `SourceBadge` | `lib/widgets/common/source_badge.dart` | "MANUAL" badge for manually-queried items |
| `ExplorerEmptyState` | `lib/widgets/common/explorer_empty_state.dart` | Glass morphism empty state with query hints |
| `ShimmerLoading` | `lib/widgets/common/shimmer_loading.dart` | Shimmer placeholder during API calls |

### Chart Library

-   **Syncfusion Flutter Charts** (Community Edition): `SfCartesianChart` with `LineSeries`, `ScatterSeries`, and `RangeBarSeries`.
-   **Chart Theme** (`lib/theme/chart_theme.dart`): Centralized configuration using Deep Space palette from `app_theme.dart`.
-   **Canvas Widgets**: `CustomPainter`-based visualizations (`metrics_dashboard_canvas.dart`, `agent_activity_canvas.dart`, `alerts_dashboard_canvas.dart`, etc.) remain unchanged.

## How to Use

1.  **Open Dashboard**: Click the "Pulse" icon in the top-right app bar.
2.  **Select a Panel**: Use the tab navigation to switch between Traces, Logs, Metrics, Alerts, Remediation, Council, and Charts.
3.  **Set Time Range**: Use the preset chips (1H/6H/1D/1W) embedded in the query bar, or click "Custom" for a date range picker.
4.  **Structured Query**: Type a filter expression in any panel's query bar. Autocomplete suggestions appear as you type -- use Tab or Enter to accept, arrow keys to navigate.
5.  **Use Templates**: Click the lightbulb icon to open the template picker. Choose a pre-built query or NL example.
6.  **Natural Language Query**: Toggle to NL mode via the language badge dropdown, then describe what you want in plain English. The query is sent to the AI agent for investigation.
7.  **Switch Query Languages**: In the Metrics panel, toggle between MQL Filter and PromQL. In the Charts panel, toggle between BigQuery SQL and Agent Charts.
8.  **Agent Investigation**: Start a conversation with the agent -- its findings automatically appear in the relevant tabs.
9.  **BigQuery Analysis**: In the Charts tab, use the SQL editor with the schema sidebar. Run queries with Ctrl+Enter. View results as a table or build interactive visualizations.
10. **Drill Down**:
    *   Enter a trace filter or `trace=<ID>` in the **Traces** tab to visualize the distributed waterfall.
    *   Query `severity>=ERROR` in the **Logs** tab to find recent error patterns.
    *   Use the **Metrics** tab to correlate metric spikes with the investigation timeline.
    *   Write SQL in the **Charts** tab to analyze OTel spans, logs, or custom BigQuery tables.
11. **Zoom & Pan**: Use mouse wheel or pinch to zoom into chart regions. Drag to pan along the time axis.
12. **Card Management**: Collapse, copy JSON data, or remove individual result cards using the card header controls.
