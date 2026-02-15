### Security, Safety, and Access Control

AutoSRE is built with defense-in-depth safety principles. Multiple layers of protection ensure the agent operates safely within your GCP environment.

### Read-Only by Default

The agent is primarily a read-only analysis tool. The vast majority of its 100+ tools are observability queries that fetch and analyze telemetry data without modifying any resources.

### Tool Access Levels

The **Policy Engine** (`core/policy_engine.py`) classifies every tool into one of three access levels:

| Access Level | Behavior | Count | Examples |
|-------------|----------|-------|----------|
| **READ_ONLY** | Executes immediately, no approval required | 80+ tools | `fetch_trace`, `list_log_entries`, `query_promql`, `detect_metric_anomalies` |
| **WRITE** | Requires explicit human approval before execution | 5 tools | `restart_pod`, `scale_deployment`, `rollback_deployment`, `acknowledge_alert`, `silence_alert` |
| **ADMIN** | Restricted, requires approval and elevated IAM | 2 tools | `delete_resource`, `modify_iam` |

### Tool Categories

The policy engine also organizes tools by functional category:

| Category | Description |
|----------|-------------|
| **Observability** | Trace, log, metric queries |
| **Analysis** | Pure analysis functions (no side effects) |
| **Orchestration** | Sub-agent coordination and delegation |
| **Infrastructure** | GKE, compute resource queries (read-only) |
| **Alerting** | Alert listing and policy queries |
| **Remediation** | Suggestion generation and risk assessment (read-only) |
| **Memory** | Investigation state and memory management |
| **Discovery** | GCP resource discovery |
| **Mutation** | Write operations (restarts, scaling, deletions) |

### Human Approval Workflow

For WRITE and ADMIN tools, the agent:

1. Generates a **risk assessment** including risk level, risk factors, and recommended mitigations.
2. Presents a **confirmation prompt** in the UI with the action description and risk details.
3. **Waits for explicit approval** before executing the action.
4. Logs the action in GCP Audit Logs for accountability.

### End-User Credentials (EUC)

AutoSRE supports End-User Credential propagation:

- The frontend sends `Authorization: Bearer <token>` and `X-GCP-Project-ID` headers with each request.
- Middleware extracts credentials into ContextVars for thread-safe access.
- Tools access credentials via `get_credentials_from_tool_context()`.
- When `STRICT_EUC_ENFORCEMENT=true`, the agent uses only your credentials and blocks fallback to Application Default Credentials (ADC). This ensures the agent can only access data you are authorized to see.

### Dynamic Tool Filtering

Tools can be enabled or disabled at runtime via the tool configuration system:

- The `.tool_config.json` file defines which tools are available.
- The `ToolConfigManager` checks tool enabled status before execution.
- This allows administrators to restrict tool availability per environment without code changes.

### Circuit Breaker Protection

When external APIs fail, the circuit breaker prevents the agent from making repeated failing calls:

- After 5 consecutive failures, the circuit opens and calls fail fast.
- After a recovery timeout (60 seconds), a test call is allowed.
- If the test succeeds, normal operation resumes.
- This protects your API quotas and prevents cascading failures.

### Audit and Observability

- **GCP Audit Logs**: Every API call the agent makes is logged in your GCP project's Audit Logs.
- **Cloud Trace**: The agent's own execution is traced via OpenTelemetry, allowing you to analyze agent performance and behavior.
- **Token Tracking**: Input/output token counts are tracked per LLM call for cost monitoring.
- **Investigation Timeline**: All investigation activities are recorded in a timestamped timeline.

### Data Privacy

- **No Persistence**: The agent does not store your telemetry data. It fetches data in real-time, analyzes it within the conversation session, and discards raw data when the session ends.
- **Project Scoping**: All queries are scoped to the GCP project specified in your session context.
- **No Cross-Project Access**: The agent cannot access data from projects you do not have permissions for.
