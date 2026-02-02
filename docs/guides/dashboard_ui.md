# SRE Agent Investigation Dashboard

The **Investigation Dashboard** is a real-time, interactive UI built into the Flutter frontend (`autosre`) to provide "glass-box" visibility into the agent's operations.

## 🌟 Key Features

### 1. Live Traces (Waterfall View)
*   **Purpose**: Visualize the agent's Chain of Thought and tool execution latency.
*   **Components**:
    *   **Waterfall**: Shows parallel vs. sequential tool execution.
    *   **Expandable Spans**: Click on any bar to see the full tool input (arguments) and output (results).
    *   **Status Indicators**: Color-coded bars for Success (Green), Failure (Red), and Running (Blue).

### 2. Live Log Explorer
*   **Purpose**: Real-time stream of backend and agent logs without needing to SSH or check Cloud Logging.
*   **Features**:
    *   **Severity Filtering**: Toggle DEBUG, INFO, WARNING, ERROR.
    *   **Search**: Full-text search across log messages.
    *   **Pattern Summary**: Auto-groups similar logs (e.g., "50 occurrences of Connection Refused").
    *   **Context**: Logs are correlated with the current Trace ID.

### 3. Alerts Dashboard
*   **Purpose**: A prioritized, scannable overview of active and historical alerts.
*   **View**: A high-fidelity list of alert cards prioritized by severity (Critical > High > Warning).
*   **Metadata**: Each card includes the affected service, resource type, specific metric, and precise open/close timestamps.
*   **Correlation**: Alerts are automatically linked to the current incident context.

### 4. Remediation Plan
*   **Purpose**: Actionable, tool-driven resolution steps.
*   **Features**:
    *   **Checklists**: Steps are rendered as interactive checklists.
    *   **Risk Assessment**: Every plan includes a risk badge (Low, Medium, High).
    *   **One-Click Action**: Terminal commands (gcloud, kubectl) can be copied directly from the dashboard.
    *   **Proactive**: Populates automatically when the agent calls the `generate_remediation_suggestions` tool.

## 🛠️ Architecture
-   **Decoupled Data Channel**: The dashboard is independent of the chat-based A2UI protocol. It listens to a dedicated `dashboard` event stream.
-   **State Management**: `DashboardState` (`lib/services/dashboard_state.dart`) acting as a singleton provider.
-   **High-Performance Canvas**: Uses `CustomPainter` (`lib/widgets/canvas/`) for flicker-free, real-time metric visualization.
-   **State Reconstruction**: Automatically rebuilds historical dashboard state from persistent session DB during hot-restarts.

## 🚀 How to Use

1.  **Open Dashboard**: Click the "Pulse" icon in the top-right app bar.
2.  **Split View**: Use the **Resizable Divider** to adjust the balance between chat and situational metrics.
3.  **Drill Down**:
    *   If the agent says "I found an error", open the **Logs** tab to see the raw error.
    *   If the agent seems slow, open the **Traces** tab to see which tool is hanging.
