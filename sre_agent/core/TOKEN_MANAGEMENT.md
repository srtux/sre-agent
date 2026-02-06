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

## 2. Tool Output Truncation

Massive tool outputs (e.g., 2MB of unfiltered logs) are the primary cause of context explosions. The `truncate_tool_output_callback` in `tool_callbacks.py` provides a safety guard.

- **Limit**: 200,000 characters (~50k tokens) per tool result.
- **Behaviors**:
    - **Strings**: Truncated with a visible indicator.
    - **Lists**: Capped at the first 500 items.
    - **Dicts**: If too large, replaced with a preview and an error message suggesting better filtering.

## 3. Usage & Cost Tracking

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

---
*Zero Broken Markdown & Zero Crashed Contexts.*
