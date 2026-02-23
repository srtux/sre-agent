# Services and Memory Subsystem

> **Source**: `sre_agent/services/` and `sre_agent/memory/` | **Dual-mode**: Local (SQLite) and Managed (Vertex AI)

The Services layer provides session management, user preference storage, and remote
agent connectivity. The Memory subsystem enables the agent to persist investigation
findings, learn from past investigations, and self-improve by recording and replaying
mistake patterns.

---

## Architecture Overview

| Concern | Component | Responsibility |
|---------|-----------|----------------|
| **Session State** | `ADKSessionManager` | CRUD on conversation sessions, event append, state updates |
| **User Preferences** | `StorageService` | Selected project, tool config, recent/saved queries |
| **Agent Connectivity** | `AgentEngineClient` | Streaming queries to Vertex AI Agent Engine with EUC |
| **Investigation Memory** | `MemoryManager` | Persist findings, learn patterns, recommend strategies |
| **Mistake Memory** | `MistakeMemoryStore` + `MistakeLearner` + `MistakeAdvisor` | Self-improving loop |
| **Evaluation** | `eval_worker.py` | Scheduled evaluation of agent interaction spans |

All services use singleton factories with lazy initialization and environment-based
backend selection.

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph API["FastAPI API Layer"]
        MW[Auth + Tracing Middleware]
        ROUTERS[Routers: agent, sessions, tools, health]
    end

    subgraph Services["Services Layer"]
        subgraph SessionSvc["Session Service"]
            SM[ADKSessionManager]
            SS_V[VertexAiSessionService<br/>Remote]
            SS_DB[DatabaseSessionService<br/>SQLite / Local]
            SS_MEM[InMemorySessionService<br/>Fallback]
        end
        subgraph StorageSvc["Storage Service"]
            STOR[StorageService]
            FB_F[FirestoreBackend<br/>Cloud Run]
            FB_J[FileBackend<br/>Local JSON]
        end
        subgraph AgentSvc["Agent Engine Client"]
            AEC[AgentEngineClient]
        end
    end

    subgraph Memory["Memory Subsystem"]
        subgraph Core["Core Memory"]
            MM[MemoryManager]
            MF[Factory / Singleton]
            VAMB[VertexAi MemoryBank<br/>Production]
            LMS[LocalMemoryService<br/>SQLite FTS5]
        end
        subgraph Mistake["Mistake Memory"]
            MMS[MistakeMemoryStore]
            ML[MistakeLearner]
            MA[MistakeAdvisor]
        end
        subgraph Support["Support"]
            SAN[MemorySanitizer]
            MCB[Memory Callbacks]
        end
    end

    subgraph External["External Systems"]
        VERTEX[Vertex AI Agent Engine]
        FIRESTORE[Cloud Firestore]
        SQLITE[(SQLite DB)]
    end

    MW --> ROUTERS
    ROUTERS --> SM & STOR & AEC
    SM --> SS_V & SS_DB & SS_MEM
    SS_V --> VERTEX
    SS_DB --> SQLITE
    STOR --> FB_F & FB_J
    FB_F --> FIRESTORE
    AEC --> VERTEX & SM
    MF --> MM
    MM --> VAMB & LMS
    VAMB --> VERTEX
    LMS --> SQLITE
    MMS --> MM
    ML --> MMS
    MA --> MMS
    MCB --> MM & ML
    SAN --> MM
    SM -->|sync_to_memory| MM
```

---

## Session and Memory Lifecycle

### Session Request Flow

```mermaid
sequenceDiagram
    participant User as User (Frontend)
    participant MW as Auth Middleware
    participant Router as Agent Router
    participant SM as ADKSessionManager
    participant Backend as Session Backend<br/>(SQLite or Vertex AI)
    participant Agent as Root Agent
    participant MM as MemoryManager

    User->>MW: POST /agent/run {message, session_id}
    MW->>MW: Extract Bearer token + X-GCP-Project-ID
    MW->>Router: Authenticated request
    Router->>SM: get_or_create_session(session_id, user_id)
    alt Session exists
        SM->>Backend: get_session(app_name, user_id, session_id)
    else New session
        SM->>Backend: create_session(app_name, user_id, state)
    end
    SM-->>Router: Session object
    Router->>Agent: Execute with session
    Agent-->>Router: Response events (streaming)
    Router->>SM: sync_to_memory(session)
    SM->>MM: add_session_to_memory(session)
    Router-->>User: SSE event stream
```

### Memory Learning Flow

```mermaid
sequenceDiagram
    participant Tool as Tool Function
    participant CB as Memory Callbacks
    participant ML as MistakeLearner
    participant MMS as MistakeMemoryStore
    participant MM as MemoryManager
    participant Store as Memory Store
    participant MA as MistakeAdvisor
    participant Agent as Root Agent

    Note over Tool,Agent: Failure Path
    Tool->>CB: after_tool_callback(error_result)
    CB->>ML: on_tool_failure(tool_name, error, args)
    ML->>MMS: record_mistake(tool_name, error, args)
    MMS->>MM: add_finding(mistake_description)
    MM->>Store: Persist mistake

    Note over Tool,Agent: Self-Correction Path
    Tool->>CB: after_tool_callback(success after failure)
    CB->>ML: on_tool_success(tool_name, new_args)
    ML->>MMS: record_correction(tool_name, correction)
    MMS->>MM: add_finding(correction_description)

    Note over Tool,Agent: Strategy Recommendation
    Agent->>MM: get_recommended_strategy(symptom)
    MM->>Store: Search for [PATTERN] findings
    Store-->>Agent: Sorted InvestigationPattern list

    Note over Tool,Agent: Pre-Call Advice
    Agent->>MA: get_tool_advice(tool_name)
    MA->>MMS: get_mistakes_for_tool(tool_name)
    MMS-->>Agent: "Avoid X, use Y instead"
```

---

## Dual-Mode Execution

Determined by the `SRE_AGENT_ID` environment variable:

| Aspect | Local Mode | Remote (Managed) Mode |
|--------|-----------|----------------------|
| **Trigger** | `SRE_AGENT_ID` not set | `SRE_AGENT_ID` set |
| **Agent execution** | In-process within FastAPI | Forwarded to Vertex AI Agent Engine |
| **Session backend** | `DatabaseSessionService` (SQLite) | `VertexAiSessionService` |
| **Memory backend** | `LocalMemoryService` (SQLite FTS5) | `VertexAiMemoryBankService` |
| **Preferences** | `FilePreferencesBackend` (JSON) | `FirestorePreferencesBackend` |
| **EUC flow** | `ContextVar` set by middleware | Session state `_user_access_token` |

Mode selection happens automatically in each service constructor:

- `ADKSessionManager._create_session_service()` checks `SRE_AGENT_ID` / `RUNNING_IN_AGENT_ENGINE`
- `StorageService._create_backend()` checks `K_SERVICE` / `USE_FIRESTORE`
- `MemoryManager._check_init_memory_service()` checks `SRE_AGENT_ID`

---

## Session Management

**File**: `sre_agent/services/session.py`

The `ADKSessionManager` wraps ADK's `SessionService` with SRE Agent convenience methods.

| Method | Description |
|--------|-------------|
| `create_session(user_id, initial_state)` | Creates session with timestamp |
| `get_session(session_id, user_id)` | Retrieves by ID |
| `list_sessions(user_id)` | Lists all, sorted by `updated_at` descending |
| `delete_session(session_id, user_id)` | Deletes a session |
| `append_event(session, event)` | Appends with safety checks for missing storage |
| `update_session_state(session, state_delta)` | Event-based state update (not direct mutation) |
| `sync_to_memory(session)` | Syncs to long-term Memory Bank |
| `get_or_create_session(...)` | Idempotent get-or-create |

**Singleton**: `from sre_agent.services.session import get_session_service`

**Stale session pitfall**: After `await` in async generators, session objects become
stale. Always re-fetch from the database after yield/await points.

---

## Storage Service

**File**: `sre_agent/services/storage.py`

Manages user preferences with auto backend selection (Firestore on Cloud Run, JSON
locally). Both backends implement `PreferencesBackend` (`get`, `set`, `delete`).

| Preference | Method | Description |
|-----------|--------|-------------|
| Selected project | `get/set_selected_project()` | Current GCP project |
| Tool config | `get/set_tool_config()` | Enabled/disabled tools |
| Recent projects | `get/set_recent_projects()` | MRU project list |
| Starred projects | `get/set_starred_projects()` | Pinned projects |
| Recent queries | `add_recent_query()` | FIFO queue (max 1000), deduplicated |
| Saved queries | `add/update/delete_saved_query()` | User-curated library |

---

## Agent Engine Client

**File**: `sre_agent/services/agent_engine_client.py`

Connects FastAPI proxy to a deployed Vertex AI Agent Engine instance.

Streaming strategy (in order): `async_stream_query` > `stream_query` > `query` (sync
in threadpool). Error responses (invalid JSON, permission denied) are converted to
structured error events.

Before each query, the client updates session state with the encrypted OAuth token
and project ID for EUC propagation.

---

## Memory Subsystem

**File**: `sre_agent/memory/manager.py`

The `MemoryManager` enables long-term learning:

### Memory Types

| Type | Prefix | Description |
|------|--------|-------------|
| **Finding** | (none) | Raw investigation finding from a tool |
| **State Change** | (none) | Investigation phase transition |
| **Investigation Pattern** | `[PATTERN]` | Symptom-to-resolution mapping with tool sequence |
| **Tool Error Pattern** | `[TOOL_ERROR_PATTERN]` | Common failures and correct inputs |

### Pattern Learning

When an investigation succeeds, `learn_from_investigation()` captures symptom type,
root cause category, tool sequence, and resolution. Patterns are stored in both
user-scoped and system-shared (`system_shared_patterns`) memory, enabling cross-user
learning.

### Strategy Recommendation

`get_recommended_strategy(symptom)` searches local cache and persistent memory:

```python
patterns = await memory_manager.get_recommended_strategy("High latency on payment-service")
# Returns: [InvestigationPattern(symptom_type="high_latency", tool_sequence=[...], ...)]
```

**Singleton**: `from sre_agent.memory.factory import get_memory_manager`

---

## Mistake Learning System

A three-component self-improvement loop:

**MistakeMemoryStore** (`memory/mistake_store.py`): Persistent store with fingerprint-
based deduplication. Categories: `syntax_error`, `invalid_filter`, `wrong_resource`,
`permission_denied`, `not_found`, `timeout`, `rate_limit`, `other`. Corrections link
to original mistakes when the agent self-corrects.

**MistakeLearner** (`memory/mistake_learner.py`): Event-driven failure detector.
`on_tool_failure()` records mistakes, `on_tool_success()` detects self-corrections
by comparing against a recent failure buffer, `on_tool_exception()` handles exceptions.

**MistakeAdvisor** (`memory/mistake_advisor.py`): Query interface. `get_tool_advice()`
returns per-tool warnings, `get_prompt_lessons()` injects top lessons into system
prompt, `get_mistake_summary()` provides aggregate statistics.

**Cross-session bootstrap**: `MistakeMemoryStore.load_from_memory_bank()` pre-populates
the in-memory cache at session start from persisted memory.

---

## Memory Sanitization

**File**: `sre_agent/memory/sanitizer.py`

`MemorySanitizer.sanitize_global_record(content, user_id, project_id)` strips user
emails, project IDs, tokens, and session identifiers before writing to the
`system_shared_patterns` scope, preventing cross-user information leakage.

---

## Component Roadmap

| Item | Status | Priority | Description |
|------|--------|----------|-------------|
| Session compression | Planned | High | Compact old events to reduce session size |
| Memory search ranking | Planned | Medium | Improve relevance scoring for patterns |
| Cross-project memory | Planned | Medium | Share sanitized patterns across projects |
| Memory TTL / eviction | Planned | Medium | Expire old findings after configurable period |
| Multi-user isolation audit | Planned | High | Formal audit of memory isolation boundaries |
| Mistake analytics | Planned | Low | Dashboard for most common tool mistakes |
| Memory Bank migration | Planned | Low | Migrate from SQLite to Vertex AI Memory Bank |
| Real-time memory sync | Planned | Medium | Push-based updates across sessions |

---

## For AI Agents

### Key Files to Read First

- `sre_agent/services/session.py` -- `ADKSessionManager` and session backends
- `sre_agent/services/storage.py` -- `StorageService` with Firestore/file backends
- `sre_agent/services/agent_engine_client.py` -- Remote Agent Engine client
- `sre_agent/memory/manager.py` -- `MemoryManager` with pattern learning
- `sre_agent/memory/factory.py` -- Singleton factory
- `sre_agent/memory/mistake_store.py` -- Mistake deduplication and persistence
- `sre_agent/memory/mistake_learner.py` -- Failure detection and self-correction
- `sre_agent/memory/mistake_advisor.py` -- Pre-call advice generation
- `sre_agent/memory/callbacks.py` -- Memory event callbacks (before/after tool)
- `sre_agent/memory/sanitizer.py` -- Cross-user sanitization
- `sre_agent/memory/local.py` -- Local SQLite memory with FTS5

### Common Mistakes

1. **Stale session closure**: After `await` in async generators, re-fetch from DB.
2. **Missing `user_id` in memory ops**: Omitting causes findings stored as `anonymous`.
3. **Direct `session.state` mutation**: Use `update_session_state()` (event-based).
4. **Forgetting `sync_to_memory`**: Call at end of request for persistence.
5. **Memory sanitization bypass**: Always use `MemorySanitizer.sanitize_global_record()`
   before writing to `system_shared_patterns`.
6. **Hardcoded backend**: Use singleton factories that auto-detect.
7. **Blocking in async context**: Wrap sync SDK calls in `asyncio.to_thread()`.

### Quick Lookup

| Question | Answer |
|----------|--------|
| Session manager singleton? | `from sre_agent.services.session import get_session_service` |
| Storage singleton? | `from sre_agent.services.storage import get_storage_service` |
| Memory manager singleton? | `from sre_agent.memory.factory import get_memory_manager` |
| Mistake store singleton? | `from sre_agent.memory.mistake_store import get_mistake_store` |
| Mistake advisor singleton? | `from sre_agent.memory.mistake_advisor import get_mistake_advisor` |
| Local mode trigger? | `SRE_AGENT_ID` not set |
| Session DB location? | `.sre_agent_sessions.db` (SQLite) |
| Firestore trigger? | `K_SERVICE` or `USE_FIRESTORE` env vars |
| Shared memory scope? | `user_id="system_shared_patterns"` |
| Token encryption? | `from sre_agent.auth import encrypt_token` |
| Session tests? | `tests/server/`, `tests/integration/` |
| Memory tests? | `tests/unit/sre_agent/memory/` |
