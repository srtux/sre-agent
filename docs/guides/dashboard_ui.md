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

### 3. Incident Timeline (Metrics & Alerts)
*   **Purpose**: Visual correlation of triggered alerts with agent activities.
*   **View**: A Gantt-chart style view showing when alerts fired vs. when the agent took action.

### 4. Remediation Plan
*   **Purpose**: Guided resolution steps.
*   **Mechanism**:
    *   The agent generates a structured "Remediation Plan".
    *   The UI renders this as a checklist.
    *   **Risk Badges**: High-risk commands (e.g., `restart`, `scale`) are highlighted with warning badges.

## 🛠️ Architecture

*   **State Management**: `DashboardState` (Provider) acts as the singleton store for all telemetry data.
*   **Data Source**: The backend streams `ToolCall` and `LogEntry` objects via the unified Server-Sent Events (SSE) or GenUI protocol.
*   **Performance**: The dashboard uses virtualized lists to handle thousands of log entries without lag.

## 🚀 How to Use

1.  **Open Dashboard**: Click the "Pulse" icon in the top-right app bar.
2.  **Split View**: The dashboard opens in a split pane next to the chat.
3.  **Drill Down**:
    *   If the agent says "I found an error", open the **Logs** tab to see the raw error.
    *   If the agent seems slow, open the **Traces** tab to see which tool is hanging.
