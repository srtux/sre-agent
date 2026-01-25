# Frontend Documentation (Flutter)

The SRE Agent frontend is a high-performance Flutter Web application designed for real-time diagnostic visualization and interaction.

## Architecture & State Management

The frontend follows the **Provider** pattern for centralized state management.

### Key Providers (`autosre/lib/app.dart`)
- **`AuthService`**: Manages Google SSO lifecycle and local credential caching.
- **`ConnectivityService`**: Monitors network state and backend availability.
- **`ProjectService`**: Tracks the user's selected GCP project across all components.
- **`SessionService`**: Manages conversation history, loading/saving sessions from the backend.

---

## The Conversational Engine

The heart of the UI is the `ConversationPage`, which orchestrates the interaction loop.

### 1. NDJSON Stream Handling
The frontend consumes a **Streaming NDJSON** API from the backend.
- It processes events in real-time as they are emitted by the Agent Engine.
- Events include: `text` (markdown), `thought` (reasoning), `tool_call` (step tracking), and `widget` (GenUI).

### 2. AdkContentGenerator
A specialized class that handles the low-level HTTP streaming and transforms the JSON stream into a high-level `GenUiConversation` model.

---

## Interceptors & Security

Every request sent by the frontend is intercepted by the `ProjectInterceptorClient`.

- **Auth Injection**: Automatically includes the `Authorization: Bearer <token>` header using the cached Google token.
- **Project Scope**: Injects the `X-GCP-Project-ID` header based on the global selection.
- **Identity Hint**: Injects `X-User-ID` (user's email) to assist the backend in robust session lookups when cookies are the primary auth method.
- **Web Credentials**: Dynamically enables `withCredentials = true` for Web platforms to allow secure cross-origin cookie propagation.

---

## GenUI (Generative UI) Widgets

The SRE Agent uses a dynamic widget system to visualize telemetry. When the backend emits a `widget` event, the frontend looks up a corresponding renderer in the `CatalogRegistry` (`autosre/lib/catalog.dart`).

| Widget | Purpose | Data Source |
| :--- | :--- | :--- |
| **TraceWaterfall** | Visualizes distributed tracing | `fetch_trace` |
| **MetricChart**| Timeseries visualization | `query_promql` |
| **LogPatternViewer**| Cluster log visualization | `extract_log_patterns` |
| **RemediationPlan** | Interactive fix checklists | `generate_remediation_suggestions` |

---

## UI Components & Aesthetics

The UI is built with a "Dark/Tech" aesthetic using a custom design system in `autosre/lib/theme/app_theme.dart`.

- **TechGridPainter**: A custom background painter that gives the app its "Observability" vibe.
- **UnifiedPromptInput**: A context-aware input field that supports multi-line text and keyboard shortcuts (Enter to send, Shift+Enter for newline).
- **ToolLogWidget**: Visualizes the agent's internal reasoning loop, showing tool inputs/outputs in a collapsible, status-aware log.
