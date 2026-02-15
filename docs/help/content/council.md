### Council of Experts Investigation

AutoSRE can investigate incidents using a **Council of Experts** -- five specialist panels that analyze your system simultaneously, then synthesize their findings into a unified assessment.

### How It Works

1. **Intent Classification**: When you ask a question, the orchestrator classifies it using either a rule-based classifier or an adaptive LLM-augmented classifier. It determines the investigation mode and the best-fit signal type.
2. **Five Panels Run in Parallel**: Trace, Metrics, Logs, Alerts, and Data (BigQuery) specialists each examine the incident from their domain using domain-specific tools.
3. **Synthesis**: A synthesizer agent (powered by Gemini 2.5 Pro) merges all panel findings into a single assessment with overall severity, confidence scores, and recommended actions.
4. **Debate Mode** (optional): For critical incidents, a critic agent cross-examines the panels' conclusions, identifying agreements, contradictions, and gaps. Panels then re-analyze with the critic's feedback, and the synthesizer re-evaluates. This loop repeats until confidence reaches the threshold (default 85%) or the maximum number of debate rounds (default 3) is reached.

### Investigation Modes

| Mode | Typical Duration | Behavior |
|------|-----------------|----------|
| **Fast** | ~5 seconds | Single best-fit panel dispatched based on signal type. Best for "Are there any alerts?" or "What's the error rate?" |
| **Standard** | ~30 seconds | All 5 panels analyze in parallel, then synthesize. Best for multi-signal investigations like latency spikes or error surges. |
| **Debate** | ~60+ seconds | Panels + adversarial critic loop with confidence gating and convergence tracking. Best for P0/P1 production incidents requiring high-confidence root cause analysis. |

### How Mode Selection Works

The classifier uses keyword and pattern matching to route your query:

- **Fast mode triggers**: Keywords like "status", "check", "quick", "health", "overview" in short queries (under 100 characters).
- **Debate mode triggers**: Keywords like "root cause", "deep dive", "incident", "outage", "postmortem", "P0", "P1", "critical", "emergency"; patterns like "why is X failing" or "what caused the errors".
- **Standard mode**: The default for all other queries.

You can also request a mode explicitly: "use debate mode" or "do a quick check."

### The Five Specialist Panels

| Panel | Domain | Key Tools |
|-------|--------|-----------|
| **Trace Panel** | Distributed traces, latency, errors, structural anomalies, resiliency anti-patterns | `analyze_trace_comprehensive`, `detect_retry_storm`, `detect_cascading_timeout`, `analyze_critical_path` |
| **Metrics Panel** | Time-series metrics, SLO violations, anomaly detection, exemplar correlation | `list_time_series`, `query_promql`, `detect_metric_anomalies`, `compare_metric_windows` |
| **Logs Panel** | Log pattern extraction, clustering, anomaly detection | `list_log_entries`, `extract_log_patterns`, `analyze_bigquery_log_patterns` |
| **Alerts Panel** | Active alerts, alert policies, incident signals, remediation suggestions | `list_alerts`, `list_alert_policies`, `get_alert`, `generate_remediation_suggestions` |
| **Data Panel** | BigQuery-based analytical queries against OTel telemetry tables | `query_data_agent`, `mcp_execute_sql` |

Each panel produces a structured `PanelFinding` with a summary, severity (Critical/Warning/Info/Healthy), confidence score (0.0--1.0), supporting evidence, and recommended actions.

### Debate Mode: Convergence and Confidence Gating

In debate mode, the pipeline follows this sequence:

1. **Initial Analysis**: All 5 panels run in parallel, followed by an initial synthesis.
2. **Debate Loop** (up to 3 rounds by default):
   - The **Critic** agent cross-examines all panel findings, producing a `CriticReport` that identifies agreements, contradictions, and gaps.
   - All 5 panels **re-analyze** with the critic's feedback available in session state.
   - The **Synthesizer** re-evaluates with updated findings.
3. **Confidence Gate**: If the synthesizer's overall confidence reaches the threshold (default 0.85), the debate stops early.
4. **Convergence Tracking**: Each round records confidence progression, confidence delta, critic gaps/contradictions count, and round duration for observability.

### Example Prompts

- "Investigate the latency spike in checkout-service" -- Standard mode
- "Quick check -- any active alerts?" -- Fast mode (routes to Alerts panel)
- "What's the CPU utilization for the frontend?" -- Fast mode (routes to Metrics panel)
- "Deep dive into the payment processing outage, I need high confidence" -- Debate mode
- "Root cause analysis for the error rate spike in production" -- Debate mode

### What You See in the Dashboard

- **Tool calls** from each panel appear inline in the chat (trace analysis, metric queries, log searches, alert checks).
- **Council tab** in the Investigation Dashboard shows the synthesized result with severity, confidence, and debate rounds.
- **Signal tabs** (Traces, Metrics, Logs, Alerts) populate with data from each panel's analysis.

### Activity Graph Visualization

The Council tab provides two views you can toggle between:

**Expert Findings View**:
- Shows each panel's assessment with severity indicators (Critical, Warning, Info, Healthy)
- Displays confidence scores and key evidence points
- In Debate mode, shows the critic's report highlighting agreements, contradictions, and gaps
- Expandable sections for detailed evidence and recommended actions

**Activity Graph View**:
- **Graph Mode**: Visualizes the agent hierarchy from the CouncilOrchestrator to panels, critic, and synthesizer
- **Timeline Mode**: Shows a chronological sequence of all tool calls and LLM invocations
- Each agent card shows:
  - Agent type (Orchestrator, Panel, Critic, Synthesizer)
  - Status (Pending, Running, Completed, Error)
  - List of tool calls with duration and results
  - LLM calls with model name and token counts
- Expand any agent to see detailed tool call arguments and results
- Tool calls that produce dashboard data (traces, logs, metrics, alerts) are highlighted

### Configuration

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Enable Council architecture | Disabled |
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent tools to ~20 (recommended with council) | `true` |

### Tips

- Council findings include confidence scores (0--100%). Debate mode drives confidence higher through iterative refinement.
- Each panel has access to a focused set of domain-specific tools curated in the tool registry, so no signal is left unexamined.
- The synthesizer uses the "deep" model (Gemini 2.5 Pro) for higher reasoning quality, while panels and the critic use the "fast" model (Gemini 2.5 Flash) for speed.
- Pipeline execution is subject to a configurable timeout (default 120 seconds) to prevent runaway investigations.
