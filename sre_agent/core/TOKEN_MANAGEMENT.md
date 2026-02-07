# Token & Context Management Strategy

The SRE Agent handles complex, long-running investigations that can generate millions of tokens across parallel analysis panels. To ensure stability and stay within the Gemini context limits (e.g., 1M tokens), we implement a multi-layered token management strategy.

## 1. Multi-Stage Compaction

### Sliding Window Compaction (Runner Level)
The `context_compactor.py` implements a persistent sliding window at the `Runner` level. As events are added to a session, older events are summarized into a natural language narrative, while the most recent `N` events are kept in full.

- **Trigger**: ~24k tokens.
- **Budget**: ~32k tokens.
- **Goal**: Keep the core agent's loop efficient and fast.

### Emergency History Compaction (LLM Callback Level)
In `model_callbacks.py`, we implement an "Emergency Brake" to prevent `400 INVALID_ARGUMENT` errors when the LLM's hard limit is approached. This typically happens during deep-dive investigations where tool results are massive.

- **Trigger**: 850,000 tokens estimated payload.
- **Strategy**:
    1. Keep the System instructions and first User message.
    2. Keep the **10 most recent messages** (5 turns) in full.
    3. Condense the entire "middle" history into a bulleted summary of tool calls and key thoughts.
- **Benefit**: Prevents the agent from crashing while retaining the high-level progress of the investigation.

## 2. Large Payload Sandbox Handler (NEW)

The `large_payload_handler.py` in `core/` intercepts oversized tool results **before** they reach the LLM context window and processes them through the sandbox (local or cloud). This is the primary defense against token limit exceedance from tool outputs.

- **Trigger**: >50 items or >100k characters (configurable via env vars).
- **Pipeline** (in `composite_after_tool_callback`):
    1. **Known tools** (metrics, logs, traces, time series): Automatically routed to pre-built sandbox templates that compute statistical summaries.
    2. **Unknown tools** with sandbox enabled: Processed via a generic summarization template that discovers data shape, field distribution, and samples.
    3. **No sandbox available**: Returns a compact data sample + schema hint + code-generation prompt. The LLM can then write analysis code and call `execute_custom_analysis_in_sandbox` to process the full dataset without it ever entering the context window.
- **Graceful degradation**: On any failure, falls through to the truncation guard below.
- **Metadata**: All processed results include `large_payload_handled`, `handling_mode`, `original_items`, `original_chars`, and `processing_ms` for observability.

## 3. Tool Output Truncation (Safety Net)

Massive tool outputs (e.g., 2MB of unfiltered logs) that slip past the Large Payload Handler are caught by the `truncate_tool_output_callback` in `tool_callbacks.py`.

- **Limit**: 200,000 characters (~50k tokens) per tool result.
- **Behaviors**:
    - **Strings**: Truncated with a visible indicator.
    - **Lists**: Capped at the first 500 items.
    - **Dicts**: If too large, replaced with a preview and an error message suggesting better filtering.

## 4. Usage & Cost Tracking

All agents are wrapped with `before_model_callback` and `after_model_callback` to track telemetry:

- **Token Auditing**: Exact prompt and candidate token counts are recorded via `UsageTracker`.
- **Cost Estimation**: Real-time USD cost estimation based on Gemini 2.5 Flash/Pro pricing.
- **Hard Budgeting**: A session-wide token budget can be enforced via `SRE_AGENT_TOKEN_BUDGET` (environment variable). If exceeded, the agent will pause and ask to summarize findings with available data.

## Configuration

| Environment Variable | Default | Description |
| :--- | :--- | :--- |
| `SRE_AGENT_TOKEN_BUDGET` | `0` (unlimited) | Max total tokens per session before halting. |
| `SAFE_TRIGGER_TOKENS` | `850,000` | Token count at which emergency compaction starts. |
| `MAX_RESULT_CHARS` | `200,000` | Max characters for a single tool output result. |
| `SRE_AGENT_LARGE_PAYLOAD_ENABLED` | `true` | Enable/disable automatic large payload sandbox processing. |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS` | `50` | Item count above which sandbox processing triggers. |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS` | `100,000` | Character count above which sandbox processing triggers. |

---
*Zero Broken Markdown & Zero Crashed Contexts.*
