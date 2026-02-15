### Intelligent Remediation

AutoSRE does not just diagnose problems -- it suggests actionable fixes ranked by risk and effort, and can generate ready-to-run commands to implement them.

### Remediation Tools

| Tool | Purpose |
|------|---------|
| `generate_remediation_suggestions` | Analyze findings and produce prioritized fix recommendations |
| `estimate_remediation_risk` | Assess the risk level of a proposed remediation action |
| `get_gcloud_commands` | Generate ready-to-run gcloud/kubectl commands for common remediations |
| `find_similar_past_incidents` | Search for similar past incidents and their resolutions |

### How Remediation Suggestions Work

The `generate_remediation_suggestions` tool matches your investigation findings against a built-in knowledge base of common failure patterns and their fixes. Each suggestion includes:

- **Action**: What to do (e.g., "Increase memory limits")
- **Description**: Why this fix addresses the issue
- **Steps**: Ordered list of implementation steps
- **Risk Level**: Low, Medium, or High
- **Effort Level**: Low, Medium, or High

Suggestions are automatically sorted by risk (lowest first) and effort (lowest first), so the safest quick wins appear at the top.

### Recognized Failure Patterns

| Pattern | Category | Examples |
|---------|----------|----------|
| **OOM Killed** | Memory | Container exceeding memory limits, memory leaks |
| **CPU Throttling** | CPU | Container CPU throttled, high CPU utilization |
| **Connection Pool Exhaustion** | Database | Pool exhausted, max connections reached, connection timeout |
| **High Latency / Timeout** | Performance | Deadline exceeded, slow queries, p99 spikes |
| **Error Rate Spike** | Errors | 5xx errors, internal server errors |
| **Cold Starts** | Serverless | Cloud Run/Functions startup latency |
| **Pod Scheduling** | Kubernetes | Pending pods, unschedulable, insufficient resources |
| **Pub/Sub Backlog** | Messaging | Message backlog, dead letter queue, subscription lag |
| **Disk Pressure** | Storage | Disk full, ephemeral storage exhaustion |
| **Connectivity Issues** | Networking | Connection refused, DNS resolution failures, unreachable services |

### Ready-to-Run Commands

The `get_gcloud_commands` tool generates specific commands for common remediations:

| Remediation Type | What It Generates |
|-----------------|------------------|
| `scale_up` | Cloud Run min-instances update |
| `rollback` | Cloud Run traffic routing to previous revision |
| `increase_memory` | Cloud Run memory limit update |
| `scale_gke_nodepool` | GKE node pool autoscaling configuration |
| `increase_sql_connections` | Cloud SQL max_connections flag update |
| `enable_min_instances` | Cloud Run min-instances for cold start prevention |
| `update_hpa` | Kubernetes HPA min/max replicas update |

### Risk Assessment

Before executing any remediation, use `estimate_remediation_risk` to get:

- **Risk Level**: Low, Medium, or High based on the action type
- **Risk Factors**: Specific concerns (e.g., "Database changes can affect data integrity")
- **Mitigations**: Steps to reduce risk (e.g., "Take a backup before proceeding")
- **Pre-Flight Checklist**: A checklist to follow before, during, and after the change

### Safe Execution

Every write action (pod restart, scaling, rollback) requires explicit human approval via a confirmation button. The agent never makes destructive changes autonomously.

- **Read-Only by Default**: The vast majority of tools (80+) are read-only observability queries.
- **Write Tools**: `restart_pod`, `scale_deployment`, `rollback_deployment`, `acknowledge_alert`, `silence_alert` -- all require approval.
- **Admin Tools**: `delete_resource`, `modify_iam` -- restricted and require elevated permissions.

### Example Workflow

1. Agent identifies: "Container frontend-pod is repeatedly OOMKilled."
2. `generate_remediation_suggestions` returns three options:
   - Increase memory limits (Low risk, Low effort) -- recommended first action
   - Investigate memory leaks with Cloud Profiler (Medium risk, High effort)
   - Enable Vertical Pod Autoscaler (Medium risk, Medium effort)
3. You choose to increase memory limits.
4. `get_gcloud_commands("increase_memory", "frontend-service", "my-project")` generates the exact `gcloud run services update` command.
5. `estimate_remediation_risk` confirms: Low risk, restart required.
6. You approve the action and verify the fix with the agent's telemetry tools.

### Learning from Past Incidents

The `find_similar_past_incidents` tool searches a knowledge base for similar issues and their resolutions. For each match, it provides:

- What happened (title and date)
- Root cause and resolution
- Time to detect (TTD) and time to resolve (TTR)
- Prevention measures implemented

This helps avoid re-inventing solutions and accelerates incident response.
