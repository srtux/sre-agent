# SRE Agent Memory Best Practices

## Patterns for ReAct Agents
Effective memory in ReAct (Reasoning + Acting) agents relies on three distinct layers. This architecture ensures the agent remains strictly grounded while retaining the ability to "learn" from past investigations.

### 1. Working Memory (Context)
* **Purpose**: Immediate short-term recall for the current active turn.
* **Mechanism**: LLM Context Window (System Prompt + Recent Messages).
* **Content**: Current tools output, immediate thoughts, and user's last query.
* **Lifecycle**: Ephemeral; discarded or summarized when context limit is reached.

### 2. Episodic Memory (Memory Bank)
* **Purpose**: Long-term recall of "events" (investigations) and "facts" (findings).
* **Mechanism**: `MemoryManager` (`sre_agent/memory/manager.py`) backed by Vertex AI Memory Bank (production) or `LocalMemoryService` (`sre_agent/memory/local.py`) fallback.
* **Content**: Confirmed findings, successful tool sequences, and state transitions.
* **Indexing**: Semantic (embedding-based) and Metadata (Time, User, Tool).
* **Shared Scope**: Patterns and tool errors are mirrored to a global `system_shared_patterns` scope for collective learning across all users.
* **Lifecycle**: Persistent; survives restart. Findings are isolated by `user_id`, while patterns are shared.

### 3. Procedural Memory (Tools & RAG)
* **Purpose**: "How-to" knowledge and static documentation.
* **Mechanism**: Tool definitions and RAG over documentation (`docs/`).
* **Content**: Runbooks, API schemas, and architecture guides.
* **Lifecycle**: Static (updated via code deployments).

## Personalization & Security
Agents must be personalizable but secure. Data leaks between users are unacceptable.

### 1. Strict User Isolation
* **Principle**: A user MUST NEVER access another user's memories.
* **Implementation**: user_id is a mandatory partition key in all storage.
  * `MemoryManager`: Enforces `user_id` filter on READ and WRITE.
  * `Storage`: All database tables must have `user_id` column.
* **Anonymous Access**: treated as a distinct "anonymous" user, or denied entirely depending on configuration.

### 2. User Context Propagation
* **Start**: User Identity is established at the API Gateway / Middleware level (OAuth Token).
* **Propagate**: Identity flows through `auth.py` ContextVars to `ToolContext`.
* **Execution**: Tools extract `user_id` from `ToolContext` before accessing memory.

### 3. Adaptive Suggestions
* **Goal**: Tailor "Next Steps" based on *this specific user's* past successful investigations and global best practices.
* **Mechanism**: When generating suggestions, query Memory Bank for:
  `filter: (user_id == current_user OR user_id == "system_shared_patterns") AND (type == "investigation_pattern")`
* **Result**: The agent "learns" the user's preferred triage style while benefiting from globally discovered tool sequences.

## Cross-User Learning & Privacy

The SRE Agent balances collective intelligence with strict privacy requirements. While findings and session history are private to each user, **strategies** and **tool usage patterns** are shared to enable self-improvement for the entire team.

### 1. Global Pattern Sharing
* **Mechanism**: When `complete_investigation` or `record_tool_failure_pattern` is called, two copies are persisted:
  1. **Private Copy**: Stored under the user's `user_id`. Contains full context, including specific project IDs.
  2. **Global Copy**: Stored under the `system_shared_patterns` ID. This copy is automatically **sanitized** before storage.

### 2. Automatic Sanitization (`MemorySanitizer`)
To prevent data leaks, the `MemorySanitizer` utility (`sre_agent/memory/sanitizer.py`) scrubs all data destined for the global scope:
* **Context Identifiers**: Automatically redacts the current user's email and project ID (e.g., `my-secret-project` -> `<PROJECT_ID>`).
* **General PII**: Redacts IP addresses, standard email formats, and authentication tokens.
* **Infrastructure Patterns**: Anonymizes environment-specific strings like GKE cluster names (`gke_proj_us-central1_cluster` -> `gke_<PROJECT>_<ZONE>_<CLUSTER>`).

This ensures that User A can benefit from User B's realization that "Tool X requires flag Y," without ever seeing User B's project name or sensitive data.

For Memory Bank to work correctly in production, the following must be set:

| Environment Variable | Purpose | Required |
| :--- | :--- | :--- |
| `SRE_AGENT_ID` | Agent Engine ID -- passed as `agent_engine_id` to `VertexAiMemoryBankService`. Without this, memory falls back to local SQLite. | Yes (production) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID for Vertex AI APIs | Yes |
| `GOOGLE_CLOUD_LOCATION` | GCP region (default: `us-central1`) | No |

### How Memory Bank Is Wired

1. **`MemoryManager`** (`sre_agent/memory/manager.py`): Custom manager that wraps `VertexAiMemoryBankService` (or `LocalMemoryService` fallback). Requires `agent_engine_id` from `SRE_AGENT_ID` env var. Provides `add_finding`, `get_relevant_findings`, `update_state`, `add_session_to_memory`, and the learning pattern API.
2. **`get_memory_manager()`** (`sre_agent/memory/factory.py`): Returns a singleton `MemoryManager` instance.
3. **`get_adk_memory_service()`** (`sre_agent/memory/factory.py`): Returns the raw `VertexAiMemoryBankService` instance (with `agent_engine_id`) for ADK's built-in `PreloadMemoryTool` and `LoadMemoryTool`. Enables `tool_context.search_memory()`.
4. **`InvocationContext.memory_service`**: Set in both `api/routers/agent.py` (local mode) and `core/runner.py` (policy runner). Enables `tool_context.search_memory()`.
5. **`after_agent_memory_callback`** (`sre_agent/memory/callbacks.py`): Automatically calls `add_session_to_memory()` after each agent turn to trigger asynchronous memory extraction and consolidation.

### IAM Permissions

The service account running the agent must have:
- `aiplatform.reasoningEngines.get` on the Agent Engine resource
- `aiplatform.memoryBanks.*` permissions for memory read/write

### Common Troubleshooting

- **No memories generated**: Ensure `SRE_AGENT_ID` is set and the session contains populated events before memory generation is triggered.
- **"Agent Engine ID missing" errors**: The `agent_engine_id` parameter was not passed to `VertexAiMemoryBankService`. Check that `SRE_AGENT_ID` is set.
- **Non-meaningful content**: Memory Bank uses topics to identify persistable information. If conversation content doesn't align with configured topics, no memories are generated. Customize memory topics in the Agent Engine configuration.
- **Operation errors**: Check for `Failed to extract memories: Please use a valid role: user, model` -- this indicates session events have incorrect roles.

## Recommended Schema
For local fallback or new memory implementations, adhere to this schema:

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,         -- CRITICAL: Partition Key
    session_id TEXT NOT NULL,      -- Traceability
    content TEXT NOT NULL,         -- The finding/fact
    metadata TEXT,                 -- JSON: source_tool, confidence, timestamp
    embedding BLOB,                -- Vector for semantic search (optional in SQLite)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_memories ON memories(user_id, created_at DESC);
```

## Memory Subsystem Architecture

The memory subsystem (`sre_agent/memory/`) consists of these modules:

| Module | Purpose |
| :--- | :--- |
| `manager.py` | `MemoryManager` -- central interface for storing/retrieving findings and learned patterns |
| `factory.py` | Singleton factories: `get_memory_manager()`, `get_adk_memory_service()` |
| `local.py` | `LocalMemoryService` -- SQLite-based fallback for local/test mode |
| `callbacks.py` | Automatic learning callbacks: `before_tool_memory_callback`, `after_tool_memory_callback`, `on_tool_error_memory_callback`, `after_agent_memory_callback` |
| `sanitizer.py` | `MemorySanitizer` -- PII/project redaction for global pattern sharing |
| `mistake_store.py` | `MistakeMemoryStore` -- structured persistent storage for tool mistakes |
| `mistake_learner.py` | `MistakeLearner` -- captures mistakes and detects self-corrections |
| `mistake_advisor.py` | `MistakeAdvisor` -- provides pre-call advice based on past mistakes |

## Investigation Patterns & Self-Improvement

The agent includes a comprehensive "Learning Protocol" to improve its diagnostic efficiency over time. The system automatically tracks tool sequences, records significant findings, and learns from both successes and failures.

### 1. Investigation Pattern Object
Instead of just storing raw text, the agent crystallizes successful investigations into a structured `InvestigationPattern` (`sre_agent/memory/manager.py`):

| Field | Description | Example |
| :--- | :--- | :--- |
| `symptom_type` | The observed issue from the user or alert. | `high_latency_checkout` |
| `root_cause_category` | The confirmed category of the failure. | `connection_pool_saturation` |
| `tool_sequence` | Ordered list of tools that led to the solution. | `["query_metrics", "fetch_trace_exemplar", "get_logs_for_trace"]` |
| `confidence` | Reinforcement score (0.0-1.0). | `0.8` (boosted by repeated success) |
| `resolution_summary` | Brief description of the resolution. | `Increased pool size from 10 to 50` |
| `occurrence_count` | Number of times this pattern was observed. | `3` |

### 2. The Learning Loop
1.  **Tool Tracking**: The `before_tool_memory_callback` automatically records every tool call during an investigation.
2.  **Success Recording**: The `after_tool_memory_callback` detects significant successful findings (bottlenecks, anomalies, root causes) and records them to memory.
3.  **Failure Learning**: The `after_tool_memory_callback` detects learnable API syntax errors and records them to memory.
4.  **Exception Learning**: The `on_tool_error_memory_callback` records tool exceptions.
5.  **Pattern Extraction**: At investigation completion, call `complete_investigation` to persist the learned pattern.
6.  **Tool Failure Patterns**: Use `record_tool_failure_pattern` when a tool syntax or logic error is corrected. This is shared globally so no other agent repeats the same tool-calling mistake.
7.  **Reinforcement**: If the pattern already exists, its `confidence` score is boosted (capped at 1.0, incremented by 0.1 per occurrence).
8.  **Proactive Retrieval**: At the start of a *new* investigation, use `get_recommended_investigation_strategy` to find high-confidence tool sequences (both private and global).

This allows the agent to skip "exploration" steps for known problems and jump straight to the correct diagnostics.

### 3. Automatic Memory Callbacks

The agent uses four async callbacks for automatic learning and persistence (all in `sre_agent/memory/callbacks.py`):

| Callback | Trigger | What It Records |
| :--- | :--- | :--- |
| `before_tool_memory_callback` | Before every tool call | Tool name for sequence tracking; emits `tool_tracked` event for UI (skips noisy tools like `get_current_time`, `preload_memory`, `load_memory`) |
| `after_tool_memory_callback` | After every tool call | API syntax failures AND significant successful findings; also triggers `MistakeLearner` for self-correction detection |
| `on_tool_error_memory_callback` | On tool exceptions | Exception details and parameter mistakes (only for learnable patterns); also triggers `MistakeLearner` |
| `after_agent_memory_callback` | After each agent turn | Triggers `add_session_to_memory` for asynchronous memory extraction via `VertexAiMemoryBankService` |

The `after_agent_memory_callback` follows the [ADK-recommended pattern](https://google.github.io/adk-docs/sessions/memory/) for automatic memory persistence, ensuring that session conversations are continuously extracted into long-term memory without requiring explicit `complete_investigation` calls.

All callbacks are designed to be **non-blocking**: failures in memory recording never break tool execution (errors are caught and logged at `debug` level).

### 4. Mistake Learner & Self-Correction

The `MistakeLearner` (`sre_agent/memory/mistake_learner.py`) is a specialized component that captures structured mistakes and detects self-corrections:

1. **Mistake Capture**: When a tool fails with a learnable error (syntax errors, invalid arguments, parse errors), the learner records a structured `MistakeRecord` to the `MistakeMemoryStore`.
2. **Self-Correction Detection**: When a tool that recently failed now succeeds, the learner compares the failed and successful arguments to identify what changed, and records a human-readable correction description.
3. **In-Memory Buffer**: Recent failures are buffered per-tool (capped at 5 per tool) to enable fast self-correction matching without querying persistent storage.
4. **UI Events**: Both mistakes and self-corrections emit `MemoryEvent` objects for real-time visibility in the frontend.

The `MistakeMemoryStore` (`sre_agent/memory/mistake_store.py`) provides structured persistent storage with fingerprinting (to deduplicate identical mistakes), occurrence counting, and category classification (`MistakeCategory`).

The `MistakeAdvisor` (`sre_agent/memory/mistake_advisor.py`) provides pre-call advice based on past mistakes, allowing the agent to avoid repeating known errors.

**Significant Finding Tools**: The system automatically records successful results from these analysis tools:
- `analyze_critical_path` -- Critical path bottleneck identification
- `find_bottleneck_services` -- Service bottleneck discovery
- `detect_metric_anomalies` -- Metric anomaly detection
- `detect_latency_anomalies` -- Latency anomaly detection
- `detect_cascading_timeout` -- Cascading timeout patterns
- `detect_retry_storm` -- Retry storm detection
- `detect_connection_pool_issues` -- Connection pool problems
- `detect_circular_dependencies` -- Circular dependency detection
- `analyze_log_anomalies` -- Log anomaly pattern identification
- `extract_log_patterns` -- Error pattern extraction from logs
- `perform_causal_analysis` -- Root cause analysis
- `correlate_changes_with_incident` -- Incident-change correlation
- `find_similar_past_incidents` -- Historical incident matching
- `generate_remediation_suggestions` -- Remediation plans
- `analyze_error_budget_burn` -- Error budget consumption analysis
- `detect_all_sre_patterns` -- SRE anti-pattern detection

### 5. Memory Tools for the Agent

| Tool | Purpose | When to Use |
| :--- | :--- | :--- |
| `search_memory` | Semantic search over past findings | "Have we seen this before?" |
| `add_finding_to_memory` | Explicitly store a discovery | Important insights, correct API syntax |
| `complete_investigation` | Mark investigation complete and learn | After resolving a root cause |
| `record_tool_failure_pattern` | Share tool syntax correction globally | After figuring out correct tool usage |
| `get_recommended_investigation_strategy` | Get proven tool sequences | Starting a new investigation |
| `analyze_and_learn_from_traces` | Self-analyze past agent traces | Periodic self-improvement |

## Cloud Trace Self-Analysis

The agent can analyze its own past execution traces from Cloud Trace/BigQuery to learn and self-improve.

### How It Works

1. **Query Past Traces**: Use `analyze_and_learn_from_traces` to generate SQL for finding agent traces
2. **Execute Query**: Run the SQL via `mcp_execute_sql` to list recent agent executions
3. **Analyze Patterns**: Use `detect_agent_anti_patterns` to find inefficiencies
4. **Store Lessons**: Use `add_finding_to_memory` to record insights

### Example Workflow

```
User: "Analyze your traces from the last 24 hours and learn from them"
Agent:
1. analyze_and_learn_from_traces(trace_project_id="my-agent-project", hours_back=24)
2. mcp_execute_sql(sql_query) -> List of trace IDs
3. For interesting traces:
   - detect_agent_anti_patterns(trace_id) -> Inefficiencies found
   - add_finding_to_memory(description="Avoid calling X before Y...")
```

### Anti-Patterns Detected

The system can identify these common agent inefficiencies:
- **Excessive Retries**: Same tool called >3 times under one parent span
- **Token Waste**: Output tokens >5x input tokens on intermediate LLM calls
- **Long Chains**: >8 consecutive LLM calls without tool use
- **Redundant Tool Calls**: Same tool invoked >3 times across the trace

### Prerequisites

For self-analysis to work:
1. Agent traces must be exported to BigQuery (OpenTelemetry format)
2. User must have access to the trace project
3. The `otel._AllSpans` table must exist in the project

## Memory Event Visibility

The agent provides real-time visibility into memory actions through an event streaming system. Users can see when the agent is learning from failures, recording findings, or applying past patterns.

### Memory Event Types

| Action | Category | Description |
| :--- | :--- | :--- |
| `stored` | `failure` | Learning from a tool failure (API syntax error, invalid parameters) |
| `stored` | `success` | Recording a significant successful finding |
| `searched` | `search` | Memory search was performed |
| `pattern_learned` | `pattern` | New investigation pattern learned after resolution (also emitted on self-correction) |
| `pattern_applied` | `pattern` | Past pattern being used to guide investigation |
| `tool_tracked` | `tracking` | Tool call recorded for sequence tracking |

### Event Schema

Memory events are streamed as NDJSON with the following structure:

```json
{
  "type": "memory",
  "action": "stored|searched|pattern_learned|pattern_applied|tool_tracked",
  "category": "failure|success|pattern|search|tracking",
  "title": "Short title for toast notification",
  "description": "Detailed description of the event",
  "tool_name": "The tool that triggered this (optional)",
  "metadata": { "additional": "data" },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Frontend Integration

The Flutter frontend subscribes to memory events and displays toast notifications for significant actions:

- **Stored (Failure)**: Shows when the agent learns from a mistake
- **Stored (Success)**: Shows when a significant finding is recorded
- **Pattern Learned**: Shows when a new investigation pattern is crystallized or a self-correction is detected

### Backend Event Emission

Memory events are emitted through the `MemoryEventBus` singleton (from `sre_agent/api/helpers/memory_events.py`):

```python
from sre_agent.api.helpers.memory_events import (
    get_memory_event_bus,
    create_failure_learning_event,
    create_success_finding_event,
    create_pattern_learned_event,
    create_tool_tracking_event,
)

# Get the singleton event bus
event_bus = get_memory_event_bus()

# Create and emit an event
event = create_failure_learning_event(
    tool_name="query_metrics",
    error_summary="invalid filter: resource.type required",
    lesson="Always specify resource.type in metric filters",
)
await event_bus.emit(session_id, event)
```

### Disabling Memory Events

Memory events can be disabled if needed:

```python
event_bus = get_memory_event_bus()
event_bus.set_enabled(False)  # Disable all memory event emission
```

### Event Flow

1. **Callback triggers**: Memory callbacks detect learnable moments
2. **Event creation**: Helper functions create structured `MemoryEvent` objects
3. **Event emission**: `MemoryEventBus.emit()` queues the event for the session
4. **Stream delivery**: Agent router drains events and yields them as NDJSON
5. **Frontend display**: Flutter parses events and shows toasts for significant actions

This visibility helps users understand when and what the agent is learning, building trust in the adaptive behavior of the system.

---

*Last verified: 2026-02-21
