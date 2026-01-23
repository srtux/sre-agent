# AutoSRE

A next-generation operation dashboard for SREs, built with **Flutter** and **GenUI**.

## Overview
AutoSRE connects to the SRE Agent (Python/ADK) and renders dynamic, generative UIs for distributed tracing, metric analysis, and incident remediation.

### 🚀 Recent Updates
*   **Restored Visualizations**: Fixed `a2ui` protocol parsing to correctly render Trace Waterfalls and Metric Charts.
*   **Session Sync**: Real-time session history synchronization with backend.

It is designed to be served by the unified SRE Agent server, but can also be run independently for development.

## 🎨 Design Aesthetics: "Mission Control"

**Theme**: Deep Space Command Center
- **Core Colors**: Deep Navy Backgrounds (`#0B0E14`), Electric Indigo (`#6366f1`), Signal Cyan (`#06b6d4`).
- **Glassmorphism**: High-opacity frosted glass for containers (bg-opacity-90 + blur-10).
- **Typography**:
  - **Headings**: `Inter` or `Outfit` (Wide, Geometric).
  - **Code**: `JetBrains Mono` or `Fira Code`.

## Key Widgets
- `UnifiedPromptInput`: Centered, pill-shaped input with floating shadow.
- `StatusToast`: Floating glassmorphic notification for system status.
- `SessionPanel`: Sidebar for viewing and managing investigation history sessions.
- `TraceWaterfall`: Gantt chart for distributed traces.
- `MetricCorrelationChart`: Timeline of metrics with anomaly detection.
- `LogPatternViewer`: Visualizes aggregated log patterns.
- `RemediationPlan`: Interactive checklist for fix actions.

## Prerequisites
- **Flutter SDK**: [Install Flutter](https://docs.flutter.dev/get-started/install/macos)
- **SRE Agent Backend**: Can be run via `uv run poe dev` (Unified) or `uv run poe web` (Backend only).
- **Troubleshooting**: See [docs/debugging_connectivity.md](../docs/debugging_connectivity.md) if you have connection issues.

## Getting Started

1.  **Install Dependencies**:
    ```bash
    cd autosre
    flutter pub get
    ```

2.  **Run the App**:
    For macOS desktop:
    ```bash
    flutter run -d macos
    ```
    For Web (Chrome):
    ```bash
    flutter run -d chrome
    ```

## Architecture
- **Framework**: Flutter
- **Protocol**: [GenUI](https://github.com/flutter/genui) + [A2UI](https://a2ui.org)
- **State Management**: Provider
- **Entry Point**: `lib/main.dart`
- **App Configuration**: `lib/app.dart` & `lib/theme/app_theme.dart`
- **Catalog Registry**: `lib/catalog.dart`
- **Screens**: `lib/pages/`
- **Agent Connection**: `lib/agent/adk_content_generator.dart`
- **Backend Adapter**: `sre_agent/tools/analysis/genui_adapter.py` (Python schema transformation)

## Session Management
AutoSRE uses the backend's `SessionService` to persist conversation history.
- **API**: Connects to `/api/sessions` for listing and managing sessions.
- **Context**: Maintains `session_id` to allow the backend to restore conversation history from ADK storage (SQLite/Firestore).
- **History**: Chat history is rehydrated from backend events, ensuring state consistency across reloads.
- **State Reset**: `clearSession()` is used to reset the frontend state and backend `session_id` when starting a new investigation, ensuring no leaked context from previous sessions.



## Canvas Widgets (GenUI Dynamic Visualization)

Advanced Canvas-style widgets for real-time, animated SRE visualizations:

| Widget | Component Name | Description |
|--------|---------------|-------------|
| `AgentActivityCanvas` | `x-sre-agent-activity` | Real-time visualization of agent workflow with animated node connections, status indicators, and phase tracking. Shows coordinator → sub-agents → data sources hierarchy. |
| `ServiceTopologyCanvas` | `x-sre-service-topology` | Interactive service dependency graph with health status, latency metrics, incident path highlighting, and pan/zoom support. |
| `IncidentTimelineCanvas` | `x-sre-incident-timeline` | Horizontal scrollable timeline showing incident progression with event correlation, severity color-coding, TTD/TTM metrics, and root cause analysis. |
| `MetricsDashboardCanvas` | `x-sre-metrics-dashboard` | Grid-based multi-metric display with sparklines, anomaly detection, threshold visualization, and status badges. |
| `AIReasoningCanvas` | `x-sre-ai-reasoning` | Agent thought process visualization showing reasoning steps (observation → analysis → hypothesis → conclusion), evidence collection, and confidence scores. |

### Canvas Widget Features
- **Animated Connections**: Flow particles and pulsing effects for active elements
- **Interactive Elements**: Tap/click nodes for details, hover for metrics
- **Real-time Updates**: Smooth animations when data changes
- **Neural Network Backgrounds**: AI Reasoning canvas features animated neural patterns
- **Glass-morphism UI**: Consistent with the app's modern dark theme

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

4.  **Deploying to Cloud Run**:
    - The deployment scripts automatically configure the `GOOGLE_CLIENT_ID` secret.
    - **Important**: Once deployed, you MUST add your Cloud Run service URL to the **Authorized JavaScript Origins** in the Google Cloud Console.
