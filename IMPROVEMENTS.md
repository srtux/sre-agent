# SRE Agent Improvements

> **Note**: This content has been integrated into [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) under "Phase 2.5: SRE Reliability Suite". This file is kept for historical reference. For the living roadmap, see PROJECT_PLAN.md.

This document details the improvements made to elevate the Auto SRE Agent toward world-class reliability engineering automation, following Google SRE best practices.

## Overview

Five major features were implemented across the Python ADK backend and Flutter UI:

| Feature | Category | Files | Tests |
|---------|----------|-------|-------|
| Circuit Breaker Pattern | Resilience | `sre_agent/core/circuit_breaker.py` | 20 |
| Multi-Window SLO Burn Rate Analyzer | SLO Alerting | `sre_agent/tools/analysis/slo/burn_rate.py` | 19 |
| Change Correlation Tool | Root Cause Analysis | `sre_agent/tools/analysis/correlation/change_correlation.py` | 17 |
| Automated Postmortem Generator | Incident Learning | `sre_agent/tools/analysis/remediation/postmortem.py` | 21 |
| Enhanced Investigation Model | State Tracking | `sre_agent/models/investigation.py` | 28 |

Total: **105 new tests**, all passing.

---

## 1. Circuit Breaker Pattern

**File**: `sre_agent/core/circuit_breaker.py`

### Problem
When external GCP APIs (Cloud Trace, Logging, Monitoring) experience outages, the agent would repeatedly call failing endpoints, wasting tokens and time while cascading failures through the investigation pipeline.

### Solution
Implemented a Circuit Breaker with three states following the standard resilience pattern:

- **CLOSED**: Normal operation. Failures are counted.
- **OPEN**: After `failure_threshold` consecutive failures, all calls are short-circuited for `recovery_timeout` seconds.
- **HALF_OPEN**: After timeout, a limited number of probe calls are allowed. If `success_threshold` probes succeed, the circuit closes. Any failure reopens it.

### Key Design Decisions
- **Singleton Registry**: `CircuitBreakerRegistry` uses a singleton pattern so all tools share circuit state.
- **Per-tool Configuration**: Critical tools (e.g., `fetch_trace`) can have custom thresholds.
- **Status API**: `get_status()` and `get_open_circuits()` enable the agent to reason about which tools are unavailable.

### Usage
```python
from sre_agent.core.circuit_breaker import get_circuit_breaker_registry

registry = get_circuit_breaker_registry()
if registry.pre_call("fetch_trace"):
    try:
        result = await fetch_trace(...)
        registry.record_success("fetch_trace")
    except Exception:
        registry.record_failure("fetch_trace")
```

---

## 2. Multi-Window SLO Burn Rate Analyzer

**File**: `sre_agent/tools/analysis/slo/burn_rate.py`

### Problem
The existing SLO tools (`get_slo_status`, `analyze_error_budget_burn`) provided point-in-time snapshots but lacked Google's recommended multi-window alerting strategy that distinguishes between fast burns (pages) and slow burns (tickets).

### Solution
Implemented Google's SRE Workbook multi-window, multi-burn-rate alerting:

| Window | Long | Short | Threshold | Action | Budget Consumed |
|--------|------|-------|-----------|--------|----------------|
| Fast burn | 1h | 5m | 14.4x | PAGE | 2% in 1h |
| Medium burn | 6h | 30m | 6.0x | PAGE | 5% in 6h |
| Slow burn | 24h | 2h | 3.0x | TICKET | 10% in 24h |
| Chronic burn | 72h | 6h | 1.0x | TICKET | 10% in 3d |

### Two Operating Modes
1. **Per-window data**: Precise calculation using error/total counts per window from Cloud Monitoring.
2. **Single error rate**: Quick estimation when only a current error rate is available.

### Error Budget Projection
`_calculate_error_budget_status()` projects time-to-exhaustion and classifies urgency:
- **CRITICAL**: < 24 hours to exhaustion
- **WARNING**: 24-72 hours
- **ELEVATED**: Burning faster than sustainable but not critical
- **HEALTHY**: Within limits

### Reference
[Google SRE Workbook - Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)

---

## 3. Change Correlation Tool

**File**: `sre_agent/tools/analysis/correlation/change_correlation.py`

### Problem
"Most outages are caused by changes" (Google SRE Book). The agent had no systematic way to identify recent deployments, config changes, or infrastructure modifications that temporally correlate with an incident.

### Solution
A tool that queries GCP Audit Logs to find and rank changes by temporal correlation and risk level.

### Change Classification
Changes are classified into categories with associated risk levels:
- **Deployment** (high risk): Cloud Run updates, GKE deployments, App Engine versions
- **Configuration** (medium risk): IAM policy changes, Secret Manager updates, SQL patches
- **Infrastructure** (medium risk): Node pool resizing, compute instance changes
- **Networking** (high risk): Firewall rules, network/subnet changes
- **Feature flags** (medium risk): Firebase Remote Config updates

### Temporal Correlation Scoring
Changes are scored based on proximity to the incident:
- Within 15 minutes: 0.95 (very strong)
- Within 1 hour: 0.80 (strong)
- Within 6 hours: 0.50 (moderate)
- Beyond 6 hours: Decaying score based on lookback window

### Graceful Degradation
When audit logs are unavailable (missing credentials, API not enabled), the tool returns actionable guidance including a `gcloud` command and a checklist of manual investigation steps.

---

## 4. Automated Postmortem Generator

**File**: `sre_agent/tools/analysis/remediation/postmortem.py`

### Problem
Postmortems are critical for organizational learning but are often skipped due to the effort required. The agent could investigate incidents but had no way to synthesize findings into a structured, blameless postmortem.

### Solution
A tool that generates Google SRE-style postmortems including:

1. **Severity Assessment**: Multi-factor severity scoring based on user impact, error budget consumption, duration, and revenue impact.
2. **Incident Metrics**: Time-to-Detect (TTD), Time-to-Mitigate (TTM), total duration.
3. **Action Items**: Auto-generated P0-P2 items based on root cause category:
   - Detection improvements (always included)
   - Root cause fix (P0)
   - Category-specific items (canary deployments for deployment issues, capacity planning for scaling issues, config validation for config issues)
   - Contributing factor mitigations
   - Runbook updates (always included)
4. **Lessons Learned**: Auto-populated based on detection method and timing metrics.

### Blameless by Design
The postmortem focuses on systemic improvements, not individual blame. Action items target teams and processes, not people.

---

## 5. Enhanced Investigation Model

**File**: `sre_agent/models/investigation.py`

### Problem
The existing `InvestigationState` tracked only flat string lists for findings and hypotheses. There was no way to measure investigation quality, track which signal types had been analyzed, or record structured findings with confidence levels.

### Solution
Enhanced the model with:

- **`InvestigationFinding`**: Frozen Pydantic model with `description`, `source_tool`, `confidence` (HIGH/MEDIUM/LOW), `signal_type`, `severity`, and `timestamp`.
- **`InvestigationTimeline`**: Frozen model recording phase transitions and key events.
- **`InvestigationState` enhancements**:
  - `structured_findings`: List of typed findings (alongside backward-compatible flat `findings` list)
  - `affected_services`: Tracked with deduplication
  - `signals_analyzed`: Which signal types (trace, log, metric, alert, change) have been examined
  - `timeline`: Ordered list of phase transitions and events
  - `calculate_score()`: Quality score (0-100) based on signal coverage, finding depth, root cause identification, remediation suggestions, and timeline completeness

### Investigation Quality Scoring
The score formula weights:
- Signal coverage: 30 points (5 signal types)
- Finding depth: 20 points (4 per finding, max 20)
- Root cause identified: 20 points
- Remediation suggested: 15 points
- Timeline completeness: 10 points (2 per event, max 10)
- Phase progression: 5 points (reaching remediation or completed)

### Backward Compatibility
`from_dict()` handles both old-format data (flat lists only) and new-format data, ensuring zero-downtime upgrades.

---

## 6. Flutter UI Widgets

### SLO Burn Rate Card
**File**: `autosre/lib/widgets/slo_burn_rate_card.dart`

Visualizes the multi-window burn rate analysis with:
- Severity badge (CRITICAL/WARNING/OK) with color coding
- SLO target display
- Animated error budget gauge bar
- Per-window breakdown showing burn rates vs thresholds
- Exhaustion projection timeline

### Postmortem Card
**File**: `autosre/lib/widgets/postmortem_card.dart`

Displays generated postmortems with:
- Title and severity header
- Impact summary section
- Expandable timeline view
- Root cause analysis section
- Interactive action items with priority badges (P0/P1/P2) and checkboxes
- Lessons learned section

Both widgets follow the Deep Space aesthetic with glassmorphism effects.

---

## Tool Registration

All new tools are registered in:
- `sre_agent/tools/__init__.py` (imports and `__all__`)
- `sre_agent/agent.py` (`base_tools` list and `TOOL_NAME_MAP`)
- `sre_agent/tools/config.py` (`ToolConfig` entries)
- `sre_agent/core/policy_engine.py` (`ToolPolicy` entries, all READ_ONLY)

---

## Future Improvements

Areas identified for further development:

1. **LoopAgent for iterative refinement** - Re-examine findings across multiple passes
2. **Knowledge Graph for RCA** - Build service dependency graphs from trace data
3. **Chaos Engineering sub-agent** - Validate resilience hypotheses
4. **Error budget as first-class objects** - Track budget across SLOs in state
5. **Rate limiting / backpressure** - Complement circuit breakers with request rate limiting
6. **Runbook automation** - Execute verified remediation steps (with human approval gates)
7. **Cross-incident learning** - Use embeddings to find similar past incidents
8. **Proactive SLO forecasting** - Predict violations before they happen using trend analysis
