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

The agent now includes a specific "Learning Protocol" to improve its diagnostic efficiency over time.

### 1. Investigation Pattern Object
Instead of just storing raw text, the agent crystallizes successful investigations into a structured `InvestigationPattern`:

| Field | Description | Example |
| :--- | :--- | :--- |
| `symptom_type` | The observed issue from the user or alert. | `high_latency_checkout` |
| `root_cause_category` | The confirmed category of the failure. | `connection_pool_saturation` |
| `tool_sequence` | Ordered list of tools that led to the solution. | `["query_metrics", "fetch_trace_exemplar", "get_logs_for_trace"]` |
| `confidence` | Reinforcement score (0.0-1.0). | `0.8` (boosted by repeated success) |

### 2. The Learning Loop
1.  **Reflection**: At the end of an investigation, the agent calls `learn_from_investigation` to extract the pattern.
2.  **Reinforcement**: If the pattern already exists, its `confidence` score is boosted.
3.  **Proactive Retrieval**: At the start of a *new* investigation, the agent calls `get_recommended_strategy` to find high-confidence tool sequences for the reported symptom.

This allows the agent to skip "exploration" steps for known problems and jump straight to the correct diagnostics.
