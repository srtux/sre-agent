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
* **Mechanism**: `MemoryManager` backed by Vertex AI Vector Search (Production) or SQLite (Local).
* **Content**: Confirmed findings, successful tool sequences, and state transitions.
* **Indexing**: Semantic (embedding-based) and Metadata (Time, User, Tool).
* **Lifecycle**: Persistent; survives restart. strictly isolated by `user_id`.

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
* **Goal**: Tailor "Next Steps" based on *this specific user's* past successful investigations.
* **Mechanism**: When generating suggestions, query Memory Bank for:
  `filter: (user_id == current_user) AND (outcome == success)`
* **Result**: The agent "learns" the user's preferred triage style over time.

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

## Investigation Patterns & Self-Improvement

The agent now includes a comprehensive "Learning Protocol" to improve its diagnostic efficiency over time. The system automatically tracks tool sequences, records significant findings, and learns from both successes and failures.

### 1. Investigation Pattern Object
Instead of just storing raw text, the agent crystallizes successful investigations into a structured `InvestigationPattern`:

| Field | Description | Example |
| :--- | :--- | :--- |
| `symptom_type` | The observed issue from the user or alert. | `high_latency_checkout` |
| `root_cause_category` | The confirmed category of the failure. | `connection_pool_saturation` |
| `tool_sequence` | Ordered list of tools that led to the solution. | `["query_metrics", "fetch_trace_exemplar", "get_logs_for_trace"]` |
| `confidence` | Reinforcement score (0.0-1.0). | `0.8` (boosted by repeated success) |
| `resolution_summary` | Brief description of the resolution. | `Increased pool size from 10 to 50` |
| `occurrence_count` | Number of times this pattern was observed. | `3` |

### 2. The Learning Loop
1.  **Tool Tracking**: The `before_tool_callback` automatically records every tool call during an investigation.
2.  **Success Recording**: The `after_tool_callback` detects significant successful findings (bottlenecks, anomalies, root causes) and records them to memory.
3.  **Failure Learning**: The `on_tool_error_callback` records API syntax errors and invalid parameters to avoid repeating mistakes.
4.  **Pattern Extraction**: At investigation completion, call `complete_investigation` to persist the learned pattern.
5.  **Reinforcement**: If the pattern already exists, its `confidence` score is boosted (min 1.0).
6.  **Proactive Retrieval**: At the start of a *new* investigation, use `get_recommended_investigation_strategy` to find high-confidence tool sequences.

This allows the agent to skip "exploration" steps for known problems and jump straight to the correct diagnostics.

### 3. Automatic Memory Callbacks

The agent uses three callbacks for automatic learning:

| Callback | Trigger | What It Records |
| :--- | :--- | :--- |
| `before_tool_memory_callback` | Before every tool call | Tool name for sequence tracking |
| `after_tool_memory_callback` | After every tool call | API syntax failures AND significant successful findings |
| `on_tool_error_memory_callback` | On tool exceptions | Exception details and parameter mistakes |

**Significant Finding Tools**: The system automatically records successful results from these analysis tools:
- `analyze_critical_path` - Critical path bottleneck identification
- `find_bottleneck_services` - Service bottleneck discovery
- `detect_metric_anomalies` - Metric anomaly detection
- `detect_latency_anomalies` - Latency anomaly detection
- `detect_cascading_timeout` - Cascading timeout patterns
- `detect_retry_storm` - Retry storm detection
- `detect_connection_pool_issues` - Connection pool problems
- `perform_causal_analysis` - Root cause analysis
- `generate_remediation_suggestions` - Remediation plans

### 4. Memory Tools for the Agent

| Tool | Purpose | When to Use |
| :--- | :--- | :--- |
| `search_memory` | Semantic search over past findings | "Have we seen this before?" |
| `add_finding_to_memory` | Explicitly store a discovery | Important insights, correct API syntax |
| `complete_investigation` | Mark investigation complete and learn | After resolving a root cause |
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
2. mcp_execute_sql(sql_query) → List of trace IDs
3. For interesting traces:
   - detect_agent_anti_patterns(trace_id) → Inefficiencies found
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
| `pattern_learned` | `pattern` | New investigation pattern learned after resolution |
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
- **Pattern Learned**: Shows when a new investigation pattern is crystallized

Toast notifications appear in the bottom-right corner with the format:
```
🧠 [Title from event]
```

### Backend Event Emission

Memory events are emitted through the `MemoryEventBus` singleton:

```python
from sre_agent.api.helpers.memory_events import (
    get_memory_event_bus,
    create_failure_learning_event,
    create_success_finding_event,
    create_pattern_learned_event,
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

This visibility helps users understand when and what the agent is learning, building trust in the adaptive behavior of the system
