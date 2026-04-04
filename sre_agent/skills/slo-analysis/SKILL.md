---
name: slo-analysis
description: "SLO burn rate analysis and error budget tracking. Use when analyzing Service Level Objectives, predicting budget exhaustion, or assessing SLI compliance across Google Cloud services."
---

## SLO Analysis Workflow

Use this skill to analyze Service Level Objectives (SLOs), track error budgets, and predict budget exhaustion.

### Step 1: Identify SLOs

1. Use `list_slo_services` to discover services with configured SLOs
2. Use `get_slo_status` to retrieve current SLO compliance for a service

### Step 2: Analyze Burn Rate

1. Use `analyze_multi_window_burn_rate` to evaluate burn rates across multiple time windows:
   - **1h window**: Detect fast burns (outages, major incidents)
   - **6h window**: Detect moderate burns (degraded performance)
   - **24h window**: Detect slow burns (gradual degradation)
   - **72h window**: Detect chronic issues
2. Compare current burn rate against alerting thresholds:
   - Fast burn: >14.4x in 1h AND >14.4x in 5min
   - Slow burn: >6x in 6h AND >6x in 30min
   - Chronic: >3x in 24h AND >3x in 6h

### Step 3: Error Budget Assessment

1. Use `predict_budget_exhaustion` to forecast when the error budget will run out
2. Assess budget consumption rate:
   - **< 25% consumed**: Healthy, room for experimentation
   - **25-50% consumed**: Monitor closely, reduce risk
   - **50-75% consumed**: Caution, limit deployments
   - **> 75% consumed**: Critical, freeze non-essential changes
   - **100% consumed**: Budget exhausted, incident response mode

### Step 4: Cross-Signal Correlation

1. Use `get_golden_signals` to check the four golden signals for the service
2. Use `correlate_trace_with_metrics` to link SLI violations to specific traces
3. Use `detect_metric_anomalies` to find metric anomalies correlated with SLO burns

### Step 5: Remediation

1. If fast burn detected:
   - Investigate as a production incident (use `incident-investigation` skill)
   - Use `generate_remediation_suggestions` for immediate fixes
2. If slow/chronic burn:
   - Use `detect_trend_changes` to identify gradual degradation
   - Use `extract_log_patterns` to find recurring error patterns
   - Consider capacity planning or architectural changes

### Key Concepts

- **SLI** (Service Level Indicator): The metric being measured (e.g., request latency < 200ms)
- **SLO** (Service Level Objective): Target percentage (e.g., 99.9% of requests < 200ms)
- **Error Budget**: Allowed failure (e.g., 0.1% = ~43 minutes/month of downtime)
- **Burn Rate**: How fast the error budget is being consumed (1x = steady-state, >1x = burning)

### Tips

- Always check multiple time windows to distinguish between spikes and trends
- A brief fast burn may consume less budget than a prolonged slow burn
- Error budget resets are typically monthly; plan accordingly
- Use SLO-based alerting to catch burns before they exhaust the budget
