### Powered by Gemini 2.5

AutoSRE is powered by **Google's Gemini 2.5 model family**, with two tiers optimized for different tasks:

### Model Tiers

| Tier | Model | Used For |
|------|-------|----------|
| **Fast** | Gemini 2.5 Flash | Panel analysis, critic cross-examination, intent classification, pattern detection, and most tool-calling tasks. Optimized for low latency and high throughput. |
| **Deep** | Gemini 2.5 Pro | Synthesizer (merging panel findings), root cause analysis, and complex reasoning tasks requiring deeper analysis. Used where accuracy matters more than speed. |

### How Models Are Selected

The agent dynamically selects the model tier based on the task:

- **Council panel agents** (Trace, Metrics, Logs, Alerts, Data) use the **fast** tier for parallel execution speed.
- **The Synthesizer** uses the **deep** tier to produce high-quality unified assessments from multiple panel findings.
- **The Root Cause Analyst** sub-agent uses the **deep** tier for multi-signal causal reasoning.
- **The Critic** uses the **fast** tier since cross-examination is primarily a comparison and checklist task.
- **The Agent Debugger** uses the **fast** tier for trace analysis efficiency.

### Key Capabilities

- **Long Context**: Gemini 2.5 models support large context windows, allowing the agent to ingest extensive trace data, log patterns, and metric histories in a single analysis pass.
- **Structured Output**: The agent uses Pydantic output schemas to ensure panel findings, critic reports, and council results are well-structured and machine-parseable.
- **Tool Calling**: Gemini 2.5's advanced function calling enables the agent to orchestrate 100+ specialized SRE tools efficiently with appropriate argument selection.
- **Safety Layers**: The agent uses a policy engine and approval workflows to ensure the model does not perform destructive actions without explicit human confirmation.

### Context Caching (Optional)

When enabled via `SRE_AGENT_CONTEXT_CACHING=true`, the agent uses Vertex AI context caching to store static system prompt prefixes on the server. This reduces input token costs by up to 75% for repeated calls during an investigation session. The default cache TTL is 1 hour.

### Cost and Token Management

- **Token Budget**: Set `SRE_AGENT_TOKEN_BUDGET` to cap the maximum tokens consumed per investigation request.
- **Model Callbacks**: The agent tracks input/output token counts, cost estimates, and budget enforcement via model callbacks on every LLM call.
- **Tool Output Truncation**: Large tool outputs are automatically truncated to prevent context window overflow.
