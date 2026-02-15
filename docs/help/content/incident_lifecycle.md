### Incident Investigation Lifecycle

AutoSRE follows a structured investigation lifecycle that mirrors industry-standard SRE incident response practices. Each investigation progresses through defined phases, tracked internally via an `InvestigationState` model.

### Investigation Phases

| Phase | Description | Key Activities |
|-------|-------------|----------------|
| **Triage** | Initial signal gathering | Collect Golden Signals (Latency, Errors, Traffic, Saturation). Identify which service is most likely the source. Check active alerts. |
| **Analysis** | Deep signal investigation | Deep dive into logs and specific metric windows. Correlate anomalies across different services and signals. Examine trace patterns. |
| **Root Cause** | Failure mode identification | Identify the primary failure mode (e.g., OOM, saturated connection pool, failed dependency, code regression). Formulate a clear explanation with cross-signal evidence. |
| **Remediation** | Fix planning and execution | Suggest actionable fixes ranked by risk and effort. Provide verification steps. Generate gcloud commands if applicable. |
| **Completed** | Investigation closed | Final report generated. Postmortem drafted if needed. Lessons learned recorded. |

### The 3-Stage Analysis Pipeline

Under the hood, AutoSRE uses a pipeline of specialist sub-agents:

1. **Stage 0 -- Aggregate Analysis** (Data Analyst): Analyzes traces at scale using BigQuery. Identifies fleet-wide patterns, finds exemplar traces, and builds service dependency graphs.

2. **Stage 1 -- Triage** (Trace Analyst): Analyzes individual traces for latency bottlenecks, errors, structural anomalies, and resiliency anti-patterns. Uses the `analyze_trace_comprehensive` mega-tool to reduce tool call overhead.

3. **Stage 2 -- Deep Dive** (Root Cause Analyst): Synthesizes findings from all signals to determine causality, impact (blast radius), and the triggering change (deployment, config, IAM). Provides remediation suggestions.

### Investigation State Tracking

The agent maintains a rich state model throughout the investigation:

- **Structured Findings**: Each finding includes a description, source tool, confidence level (High/Medium/Low), signal type, and severity.
- **Timeline**: Chronological record of phase transitions and key events with ISO timestamps.
- **Affected Services**: Tracks all services identified as impacted during the investigation.
- **Signals Analyzed**: Records which signal types have been examined (trace, log, metric, alert, change).
- **Investigation Score**: A quality score (0--100) based on signal coverage (30pts), findings depth (20pts), root cause identification (20pts), remediation suggestion (15pts), timeline completeness (10pts), and phase progression (5pts).

### Example Workflow

1. You say: "Help me investigate the spike in checkout errors."
2. **Triage**: The agent gathers Golden Signals -- queries error rates, checks active alerts, and lists recent traces with errors.
3. **Analysis**: The agent examines log patterns, correlates metrics windows, and identifies anomalies in the affected timeframe.
4. **Root Cause**: The agent performs causal analysis, correlates the issue with a recent deployment, and measures downstream impact.
5. **Remediation**: The agent suggests specific fixes (e.g., rollback the deployment, increase connection pool size) ranked by risk and effort, with ready-to-run gcloud commands.
6. **Completed**: The agent generates a postmortem draft following Google SRE best practices.

### Tips

- The agent auto-selects the appropriate investigation phase based on the information gathered so far.
- You can nudge the agent toward a specific phase: "Skip to remediation" or "Generate a postmortem."
- The investigation score helps you gauge whether the analysis has been thorough enough before acting on recommendations.
- All phase transitions are recorded in the investigation timeline for audit purposes.
