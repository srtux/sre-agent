# Agent Orchestration & Sub-Agents

The reasoning logic is built on a 3-stage analysis pipeline to ensure rigorous investigative quality.

## Orchestration Strategy
- **Root Agent**: The main orchestrator that interacts with the user and delegates work.
- **Specialized Sub-Agents**: Focused experts for specific data signals.

## 3-Stage Pipeline
1. **Stage 0 (Aggregate)**: `aggregate_analyzer` identifies outliers across the fleet via BigQuery.
2. **Stage 1 (Triage)**: `trace_analyst` and `log_analyst` deep-dive into the failures in parallel.
3. **Stage 2 (Synthesis)**: `root_cause_analyst` correlates findings to determine causality and blast radius.

## Key Specialized Agents
- `trace_analyst`: Expertise in distributed tracing and call graphs.
- `log_analyst`: Pattern recognition via Drain3 clustering.
- `metrics_analyzer`: PromQL/Time-series anomaly detection.
- `alert_analyst`: SLO impact correlation.

## Reasoning Pattern (ReAct)
The agents uses the **Reasoning + Acting** pattern:
1. **Thought**: Formulate a hypothesis.
2. **Action**: Choose and execute a tool.
3. **Observation**: Evaluate the tool output.
4. **Conclusion**: Provide an answer or recurse.
