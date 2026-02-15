# Token & Context Management Strategy

The SRE Agent handles complex, long-running investigations that can generate millions of tokens across parallel analysis panels. To ensure stability and stay within the Gemini context limits (e.g., 1M tokens), we implement a multi-layered token management strategy.

## 1. Multi-Stage Compaction

### Sliding Window Compaction (Runner Level)

The `context_compactor.py` implements a persistent sliding window at the `Runner` level. As events are added to a session, older events are summarized into a natural language narrative, while the most recent events are kept in full.

- **Trigger**: ~24k tokens (`compaction_trigger_tokens`).
- **Budget**: ~32k tokens (`token_budget`).
- **Recent events kept**: 5 (`recent_events_count`).
- **Minimum events**: 10 events before compaction is considered.
- **Chars per token estimate**: 4 (conservative).
- **Goal**: Keep the core agent's loop efficient and fast.

The `Summarizer` class in `summarizer.py` drives this compaction. It uses heuristic-based summarization with tool-specific strategies for common tools (`fetch_trace`, `list_traces`, `list_log_entries`, `analyze_aggregate_metrics`, `analyze_trace_comprehensive`, `extract_log_patterns`, `query_promql`, `list_time_series`). Each strategy extracts the most relevant information (e.g., error counts, latency percentiles, top patterns) and discards raw data.

### Emergency History Compaction (LLM Callback Level)

In `model_callbacks.py`, we implement an "Emergency Brake" to prevent `400 INVALID_ARGUMENT` errors when the LLM's hard limit is approached. This typically happens during deep-dive investigations where tool results are massive.

- **Trigger**: 750,000 estimated tokens (using 2.5 chars/token ratio for realistic log/code content).
- **Strategy**:
    1. Keep the system instructions and first user message.
    2. Keep the **10 most recent messages** (5 turns) in full. If estimated tokens exceed 900,000, this drops to **6 recent messages** (3 turns) to reclaim more space.
    3. Condense the entire "middle" history into a bulleted summary of tool calls, function responses, and key thoughts via `_compact_llm_contents()`.
- **Benefit**: Prevents the agent from crashing while retaining the high-level progress of the investigation.

## 2. Large Payload Sandbox Handler

The `large_payload_handler.py` in `core/` intercepts oversized tool results **before** they reach the LLM context window and processes them through the sandbox (local or cloud). This is the primary defense against token limit exceedance from tool outputs.

- **Trigger**: >50 items or >100k characters (configurable via env vars).
- **Pipeline** (in `composite_after_tool_callback`):
    1. **Known tools** (metrics, logs, traces, time series): Automatically routed to pre-built sandbox templates that compute statistical summaries.
    2. **Unknown tools** with sandbox enabled: Processed via a generic summarization template that discovers data shape, field distribution, and samples.
    3. **No sandbox available**: Returns a compact data sample (3 items, 2k chars max) + schema hint + code-generation prompt. The LLM can then write analysis code and call `execute_custom_analysis_in_sandbox` to process the full dataset without it ever entering the context window.
- **Graceful degradation**: On any failure, falls through to the truncation guard below.
- **Metadata**: All processed results include `large_payload_handled`, `handling_mode`, `original_items`, `original_chars`, and `processing_ms` for observability.

## 3. Tool Output Truncation (Safety Net)

Massive tool outputs (e.g., 2MB of unfiltered logs) that slip past the Large Payload Handler are caught by the `truncate_tool_output_callback` in `tool_callbacks.py`.

- **Limit**: 200,000 characters (~50k tokens) per tool result.
- **Behaviors**:
    - **Strings**: Truncated at 200k characters with a visible `[TRUNCATED BY SRE AGENT SAFETY GUARD]` indicator.
    - **Lists**: Capped at the first 500 items with truncated count metadata.
    - **Dicts**: If too large, replaced with a truncated preview (first 100k chars of stringified representation) and a suggestion to use better filtering.

## 4. Usage & Cost Tracking

All agents are wrapped with `before_model_callback` and `after_model_callback` in `model_callbacks.py` to track telemetry:

- **Token Auditing**: Exact prompt and candidate token counts are recorded via `UsageTracker` (thread-safe, per-session accumulator). Tracks per-agent and aggregate token usage, call counts, and durations.
- **Cost Estimation**: Real-time USD cost estimation based on Gemini pricing:
    - Gemini 2.5 Flash: $0.15/M input, $0.60/M output
    - Gemini 2.5 Pro: $1.25/M input, $10.00/M output
    - Gemini 2.0 Flash: $0.10/M input, $0.40/M output
- **Hard Budgeting**: A session-wide token budget can be enforced via `SRE_AGENT_TOKEN_BUDGET` (environment variable). If exceeded, the agent will pause and ask to summarize findings with available data.

## Configuration

| Environment Variable | Default | Description |
| :--- | :--- | :--- |
| `SRE_AGENT_TOKEN_BUDGET` | `0` (unlimited) | Max total tokens per session before halting. |
| `SRE_AGENT_LARGE_PAYLOAD_ENABLED` | `true` | Enable/disable automatic large payload sandbox processing. |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS` | `50` | Item count above which sandbox processing triggers. |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS` | `100,000` | Character count above which sandbox processing triggers. |

Internal constants (not configurable via env):

| Constant | Value | Location | Description |
| :--- | :--- | :--- | :--- |
| `SAFE_TRIGGER_TOKENS` | `750,000` | `model_callbacks.py` | Token count at which emergency compaction starts. |
| `CHARS_PER_TOKEN` | `2.5` | `model_callbacks.py` | Character-to-token ratio for emergency estimation (realistic for logs/code). |
| `MAX_RESULT_CHARS` | `200,000` | `tool_callbacks.py` | Max characters for a single tool output result. |
| `token_budget` | `32,000` | `context_compactor.py` | Working context token budget for sliding window. |
| `compaction_trigger_tokens` | `24,000` | `context_compactor.py` | Threshold for sliding window compaction. |
| `recent_events_count` | `5` | `context_compactor.py` | Number of recent events kept in full during compaction. |

## Architecture Flow

```
Tool execution
     │
     ▼
@adk_tool decorator
     │
     ▼
composite_after_tool_callback()
  ├─> large_payload_handler()       (sandbox processing for big results)
  │     ├─> known tool template     (metrics/logs/traces/time series)
  │     ├─> generic summarization   (unknown data shapes)
  │     └─> code-gen prompt         (no sandbox available)
  ├─> truncate_tool_output_callback()  (200k char safety net)
  └─> after_tool_memory_callback()     (learning)
         │
         ▼
  LLM context window
         │
         ▼
  before_model_callback()
    ├─> token budget check          (halt if over budget)
    └─> emergency compaction        (compact middle history if >750k tokens)
         │
         ▼
  Gemini API call
         │
         ▼
  after_model_callback()
    └─> usage tracking              (tokens, cost, duration)
```

---
*Zero Broken Markdown & Zero Crashed Contexts.*
