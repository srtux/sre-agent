### Extending AutoSRE with Custom Tools

AutoSRE is designed to be extensible. You can add new tools to enhance the agent's capabilities, connect external data sources, or integrate with your organization's specific infrastructure.

### Architecture Overview

AutoSRE's tool system has three layers:

1. **Native Python Tools**: Custom async functions decorated with `@adk_tool` in `sre_agent/tools/`. This is the primary extension point.
2. **MCP Servers**: External Model Context Protocol servers that provide specialized data access (BigQuery, heavy PromQL, custom databases). Configured in `tools/mcp/`.
3. **Tool Configuration**: The `.tool_config.json` file and `tools/config.py` registry enable or disable specific tools at runtime.

### Adding a New Tool (Step by Step)

**1. Create the tool function:**

```python
# sre_agent/tools/my_domain/my_tool.py
from sre_agent.tools.common.decorators import adk_tool
from sre_agent.schema import BaseToolResponse, ToolStatus

@adk_tool
async def my_custom_tool(
    service_name: str,
    time_range: str = "1h",
    tool_context: Any = None,
) -> str:
    """Describe what this tool does clearly.

    Args:
        service_name: The GCP service to analyze.
        time_range: Time range for the analysis (default: 1h).
        tool_context: ADK tool context (injected automatically).

    Returns:
        JSON string with tool results.
    """
    result = BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={"service": service_name, "data": "..."}
    )
    return result.model_dump_json()
```

**2. Register the tool (4 registration points):**

| Location | What to Do |
|----------|------------|
| `sre_agent/tools/__init__.py` | Add to `__all__` exports |
| `sre_agent/agent.py` | Add to `base_tools` list and `TOOL_NAME_MAP` |
| `sre_agent/tools/config.py` | Add a `ToolConfig` entry |
| `sre_agent/council/tool_registry.py` | Add to the relevant panel/sub-agent tool set (if used by council) |

**3. Write tests:**

```python
# tests/unit/sre_agent/tools/my_domain/test_my_tool.py
import pytest
from sre_agent.tools.my_domain.my_tool import my_custom_tool

@pytest.mark.asyncio
async def test_my_custom_tool_success():
    result = await my_custom_tool("frontend-service", "2h")
    assert '"status": "success"' in result
```

**4. Run quality checks:**

```bash
uv run poe lint    # Ruff format + lint + MyPy + codespell + deptry
uv run poe test    # pytest + 80% coverage gate
```

### Tool Implementation Requirements

- **Async**: All tool functions must be `async` -- external I/O (GCP APIs, databases) must use `async/await`.
- **Type Hints**: Explicit type hints on all parameters and return values. No implicit `Any`.
- **Return Format**: Return `BaseToolResponse` JSON (or plain JSON string). The `@adk_tool` decorator handles serialization.
- **Docstring**: Clear docstring with Args section -- the LLM uses this to understand when and how to call the tool.
- **Error Handling**: Catch exceptions and return `ToolStatus.ERROR` with a meaningful error message rather than letting exceptions propagate.
- **Skip Summarization**: Use `@adk_tool(skip_summarization=True)` for tools that return structured data the LLM should pass through directly.

### Tool Access Levels

The policy engine (`core/policy_engine.py`) classifies tools by access level:

| Level | Behavior | Examples |
|-------|----------|---------|
| **READ_ONLY** | Execute immediately, no approval needed | `fetch_trace`, `list_log_entries`, `query_promql` |
| **WRITE** | Requires human approval before execution | `restart_pod`, `scale_deployment`, `rollback_deployment` |
| **ADMIN** | Restricted, requires approval and elevated permissions | `delete_resource`, `modify_iam` |

### Connecting MCP Servers

For data sources that require heavy computation or specialized access:

1. Implement an MCP server following the Model Context Protocol specification.
2. Configure the MCP connection in `tools/mcp/`.
3. The agent includes automatic MCP-to-direct-API fallback for resilience.

### Tips

- Start by reviewing existing tools in `sre_agent/tools/` for patterns and conventions.
- Missing any of the 4 registration points is the most common error when adding new tools.
- Use the tool configuration system to enable/disable tools per environment without code changes.
- The `@adk_tool` decorator automatically handles telemetry, caching (TTL 300s), and error wrapping.
