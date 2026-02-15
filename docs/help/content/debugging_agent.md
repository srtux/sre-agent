### Troubleshooting the Agent

Sometimes the agent might get stuck, produce unexpected answers, or encounter permission issues. This guide covers common problems and their solutions.

### 1. "I don't have permission"

- **Cause**: The session token may have expired, or your account lacks the necessary IAM roles.
- **Fix**: Refresh the page to re-authenticate. Check your roles in the GCP Console -- the agent requires `roles/viewer` at minimum for read-only operations. Write operations (pod restarts, scaling) require additional roles.
- **EUC Mode**: When `STRICT_EUC_ENFORCEMENT=true`, the agent uses only your End-User Credentials and will not fall back to Application Default Credentials. Ensure your OAuth token grants access to the target project.

### 2. Hallucinations or Reasoning Loops

- **Cause**: The context window may be cluttered with stale information, or the agent is stuck in a reasoning loop (e.g., repeatedly calling the same tool with the same arguments).
- **Fix**: Use the "New Investigation" button to start a fresh session. This clears context and resets the investigation state.
- **Prevention**: The agent has built-in anti-loop protections via the circuit breaker pattern and context compaction. If loops persist, check backend logs for circuit breaker warnings.

### 3. Missing Tools or MCP Connection Failures

- **Cause**: The agent failed to register MCP tools during startup, or the MCP server is unreachable.
- **Fix**: Check the backend logs for "MCP Connection Failed" errors. Verify your MCP server configuration is correct. The agent includes an MCP fallback mechanism (`tools/mcp/fallback.py`) that falls back to direct API calls when MCP is unavailable.
- **Configuration**: Use `USE_MOCK_MCP=true` in test environments to bypass MCP entirely.

### 4. UI Rendering Issues (GenUI)

- **Cause**: Generative UI rendering may fail for malformed tool output or unsupported data shapes.
- **Fix**: Click the "Raw Response" toggle (if available) to see the text-only output. Check `docs/guides/debugging_genui.md` for detailed troubleshooting steps.

### 5. Slow or Timed-Out Investigations

- **Cause**: The investigation pipeline may be hitting external API rate limits, or the council debate loop is running too many rounds.
- **Fix**: Check the circuit breaker status -- open circuits indicate failing backends. For council investigations, the pipeline enforces a configurable timeout (default 120 seconds). You can adjust `SRE_AGENT_TOKEN_BUDGET` to cap token usage per request.

### 6. Agent Debugger Sub-Agent

AutoSRE includes a built-in **Agent Debugger** sub-agent that can analyze the agent's own behavior using Cloud Trace telemetry. It understands OpenTelemetry GenAI semantic conventions and can help you understand agent performance issues.

**What the Agent Debugger Can Do:**

| Capability | Tool | Description |
|-----------|------|-------------|
| **Find agent runs** | `list_agent_traces` | Search for recent agent executions, filtered by engine ID, agent name, or error status |
| **Reconstruct interactions** | `reconstruct_agent_interaction` | Get the full span tree for a trace -- shows the complete decision chain |
| **Analyze token usage** | `analyze_agent_token_usage` | Understand cost and efficiency by agent, model, and operation type |
| **Detect anti-patterns** | `detect_agent_anti_patterns` | Find optimization opportunities like excessive retries, token waste, and long reasoning chains |

**Anti-Patterns the Debugger Detects:**

- **Excessive Retries**: Same tool called more than 3 times under the same parent span (poor error handling or flaky tools)
- **Token Waste**: Output tokens exceeding 5x input tokens on intermediate LLM calls (excessive content generation before acting)
- **Long Reasoning Chains**: More than 8 consecutive LLM calls without a tool use (stuck in a reasoning loop)
- **Redundant Tool Calls**: Same tool invoked repeatedly across a trace (consider caching)

**Example Prompts:**

- "Debug the last agent run -- was it efficient?"
- "Analyze token usage for recent investigations"
- "Find any agent anti-patterns in the last hour"
- "Reconstruct the interaction for trace ID abc123"

### 7. Backend Connectivity

- **Local Mode**: When `SRE_AGENT_ID` is not set, the agent runs in-process inside the FastAPI server. Check that the backend is running on the expected port (default 8001).
- **Remote Mode**: When `SRE_AGENT_ID` is set, requests are forwarded to Vertex AI Agent Engine. Verify the Agent Engine resource is deployed and accessible. Check the `agent_engine_client.py` for connection issues.
